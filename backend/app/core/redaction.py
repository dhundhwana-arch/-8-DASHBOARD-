"""Recursive secret & sensitive-field redaction for audit records, logs, and errors."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED_PLACEHOLDER = "[REDACTED]"

SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "password_hash",
        "passwd",
        "secret",
        "secret_key",
        "session_secret_key",
        "token",
        "session_token",
        "token_hash",
        "csrf",
        "csrf_token",
        "csrf_token_hash",
        "x_csrf_token",
        "x-csrf-token",
        "api_key",
        "admin_api_key",
        "module_02_admin_api_key",
        "authorization",
        "cookie",
        "set_cookie",
        "set-cookie",
        "phone",
        "phone_number",
        "phone_e164",
        "raw_measurements",
        "measurements_payload",
    }
)

_SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "csrf",
)

_STRING_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(css_admin_session=)[^;\s,&]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(x-csrf-token\s*[:=]\s*)[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(postgresql(?:\+\w+)?://[^:\s/]+:)([^@\s]+)(@)"), r"\1[REDACTED]\3"),
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SENSITIVE_FIELD_NAMES:
        return True
    return any(sub in normalized for sub in _SENSITIVE_KEY_SUBSTRINGS)


def redact_string_secrets(value: str, extra_literals: Sequence[str] = ()) -> str:
    redacted = value
    for pattern, replacement in _STRING_SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    for literal in extra_literals:
        if literal and len(literal) >= 6 and literal in redacted:
            redacted = redacted.replace(literal, REDACTED_PLACEHOLDER)
    return redacted


def redact_sensitive_data(
    payload: Any,
    *,
    extra_literals: Sequence[str] = (),
    _depth: int = 0,
) -> Any:
    """Return a deep-copied structure with secrets, tokens, and raw credentials scrubbed."""
    if _depth > 12:
        return REDACTED_PLACEHOLDER

    if payload is None or isinstance(payload, (bool, int, float)):
        return payload

    if isinstance(payload, str):
        return redact_string_secrets(payload, extra_literals=extra_literals)

    if isinstance(payload, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_val in payload.items():
            key_str = str(raw_key)
            if is_sensitive_key(key_str):
                sanitized[key_str] = REDACTED_PLACEHOLDER
            else:
                sanitized[key_str] = redact_sensitive_data(
                    raw_val,
                    extra_literals=extra_literals,
                    _depth=_depth + 1,
                )
        return sanitized

    if isinstance(payload, (list, tuple, set, frozenset)):
        return [
            redact_sensitive_data(item, extra_literals=extra_literals, _depth=_depth + 1)
            for item in payload
        ]

    return redact_string_secrets(str(payload), extra_literals=extra_literals)


class RedactingLogFilter(logging.Filter):
    """Logging filter ensuring known secret literals and header patterns never reach log sinks."""

    def __init__(self, secret_provider: Any | None = None) -> None:
        super().__init__()
        self._secret_provider = secret_provider

    def _collect_literals(self) -> list[str]:
        if self._secret_provider is None:
            return []
        try:
            return [s for s in self._secret_provider() if s]
        except Exception:
            return []

    def filter(self, record: logging.LogRecord) -> bool:
        literals = self._collect_literals()
        if isinstance(record.msg, str):
            record.msg = redact_string_secrets(record.msg, extra_literals=literals)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args, extra_literals=literals)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_data(arg, extra_literals=literals) for arg in record.args
                )
        return True
