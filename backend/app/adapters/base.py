"""Base integration envelope, 5-state provenance enum, and fault-isolated HTTP client."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings
from app.core.logging import get_correlation_id
from app.core.redaction import redact_string_secrets
from app.db.models import utcnow

T = TypeVar("T")

RETRYABLE_GET_STATUS_CODES: frozenset[int] = frozenset({502, 503, 504})


class IntegrationSourceStatus(StrEnum):
    """Mandatory 5-state upstream data provenance classification."""

    VERIFIED = "VERIFIED"
    MOCK_DEV = "MOCK_DEV"
    CONTRACT_UNCONFIGURED = "CONTRACT_UNCONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    CONTRACT_MISMATCH = "CONTRACT_MISMATCH"


class IntegrationEnvelope(BaseModel, Generic[T]):
    """Typed provenance wrapper ensuring unavailable data is never mistaken for zero."""

    model_config = ConfigDict(extra="forbid")

    module_code: str
    module_name: str
    source_status: IntegrationSourceStatus
    is_verified_live: bool
    is_mock_data: bool
    fetched_at: datetime
    correlation_id: str
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    data: T | None = None

    @classmethod
    def verified(
        cls,
        *,
        module_code: str,
        module_name: str,
        data: T,
        latency_ms: int | None = None,
    ) -> IntegrationEnvelope[T]:
        return cls(
            module_code=module_code,
            module_name=module_name,
            source_status=IntegrationSourceStatus.VERIFIED,
            is_verified_live=True,
            is_mock_data=False,
            fetched_at=utcnow(),
            correlation_id=get_correlation_id(),
            latency_ms=latency_ms,
            data=data,
        )

    @classmethod
    def mock_dev(
        cls,
        *,
        module_code: str,
        module_name: str,
        data: T,
    ) -> IntegrationEnvelope[T]:
        return cls(
            module_code=module_code,
            module_name=module_name,
            source_status=IntegrationSourceStatus.MOCK_DEV,
            is_verified_live=False,
            is_mock_data=True,
            fetched_at=utcnow(),
            correlation_id=get_correlation_id(),
            error_message=(
                "MOCK_DEV fixture data enabled for local development/testing only — "
                "not verified business data."
            ),
            data=data,
        )

    @classmethod
    def contract_unconfigured(
        cls,
        *,
        module_code: str,
        module_name: str,
        message: str,
    ) -> IntegrationEnvelope[T]:
        return cls(
            module_code=module_code,
            module_name=module_name,
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            is_verified_live=False,
            is_mock_data=False,
            fetched_at=utcnow(),
            correlation_id=get_correlation_id(),
            error_code="CONTRACT_UNCONFIGURED",
            error_message=message,
            data=None,
        )

    @classmethod
    def unavailable(
        cls,
        *,
        module_code: str,
        module_name: str,
        error_code: str,
        message: str,
        latency_ms: int | None = None,
    ) -> IntegrationEnvelope[T]:
        return cls(
            module_code=module_code,
            module_name=module_name,
            source_status=IntegrationSourceStatus.UNAVAILABLE,
            is_verified_live=False,
            is_mock_data=False,
            fetched_at=utcnow(),
            correlation_id=get_correlation_id(),
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=message,
            data=None,
        )

    @classmethod
    def contract_mismatch(
        cls,
        *,
        module_code: str,
        module_name: str,
        message: str,
        latency_ms: int | None = None,
    ) -> IntegrationEnvelope[T]:
        return cls(
            module_code=module_code,
            module_name=module_name,
            source_status=IntegrationSourceStatus.CONTRACT_MISMATCH,
            is_verified_live=False,
            is_mock_data=False,
            fetched_at=utcnow(),
            correlation_id=get_correlation_id(),
            latency_ms=latency_ms,
            error_code="CONTRACT_MISMATCH",
            error_message=message,
            data=None,
        )


class UpstreamTransportError(Exception):
    def __init__(self, error_code: str, message: str, latency_ms: int | None = None) -> None:
        self.error_code = error_code
        self.message = message
        self.latency_ms = latency_ms
        super().__init__(message)


class UpstreamContractMismatchError(Exception):
    def __init__(self, message: str, latency_ms: int | None = None) -> None:
        self.message = message
        self.latency_ms = latency_ms
        super().__init__(message)


class SafeHttpTransport:
    """Bounded-timeout HTTP client with max 1 GET retry and strict secret redaction."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._logger = logging.getLogger("module08_admin")

    def get_json(
        self,
        *,
        base_url: str,
        path: str,
        params: dict[str, Any] | None = None,
        bearer_token: str | None = None,
    ) -> tuple[Any, int]:
        url_root = base_url.rstrip("/")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "X-Correlation-ID": get_correlation_id(),
        }
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        timeout = httpx.Timeout(
            connect=self._settings.upstream_connect_timeout_seconds,
            read=self._settings.upstream_read_timeout_seconds,
            write=5.0,
            pool=2.0,
        )

        started = time.perf_counter()
        last_exc: Exception | None = None

        with httpx.Client(
            base_url=url_root,
            timeout=timeout,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            for attempt in range(2):  # Initial GET + at most 1 transient retry
                try:
                    resp = client.get(path, params=params, headers=headers)
                except httpx.TimeoutException as exc:
                    last_exc = exc
                    if attempt == 0:
                        time.sleep(0.05)
                        continue
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    raise UpstreamTransportError(
                        "UPSTREAM_TIMEOUT",
                        "Upstream module request timed out.",
                        latency_ms=elapsed_ms,
                    ) from exc
                except httpx.RequestError as exc:
                    last_exc = exc
                    if attempt == 0:
                        time.sleep(0.05)
                        continue
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    raise UpstreamTransportError(
                        "UPSTREAM_NETWORK_ERROR",
                        "Unable to reach upstream module service.",
                        latency_ms=elapsed_ms,
                    ) from exc

                elapsed_ms = int((time.perf_counter() - started) * 1000)

                if resp.status_code in RETRYABLE_GET_STATUS_CODES and attempt == 0:
                    time.sleep(0.05)
                    continue

                if resp.status_code in (401, 403):
                    self._logger.warning(
                        "Upstream auth rejected on GET %s (status=%s)", path, resp.status_code
                    )
                    raise UpstreamTransportError(
                        "UPSTREAM_AUTH_REJECTED",
                        "Upstream service rejected service credentials.",
                        latency_ms=elapsed_ms,
                    )

                if resp.status_code == 429:
                    raise UpstreamTransportError(
                        "UPSTREAM_RATE_LIMITED",
                        "Upstream service rate-limited the request.",
                        latency_ms=elapsed_ms,
                    )

                if resp.status_code >= 400:
                    raise UpstreamTransportError(
                        f"UPSTREAM_HTTP_{resp.status_code}",
                        f"Upstream service returned HTTP {resp.status_code}.",
                        latency_ms=elapsed_ms,
                    )

                try:
                    return resp.json(), elapsed_ms
                except ValueError as exc:
                    raise UpstreamContractMismatchError(
                        "Upstream service returned non-JSON payload.",
                        latency_ms=elapsed_ms,
                    ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        safe_reason = redact_string_secrets(
            str(last_exc or "Unknown transport error"),
            extra_literals=self._settings.known_secret_literals(),
        )
        raise UpstreamTransportError(
            "UPSTREAM_UNAVAILABLE",
            safe_reason,
            latency_ms=elapsed_ms,
        )
