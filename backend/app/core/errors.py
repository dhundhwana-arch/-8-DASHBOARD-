"""Sanitized domain exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.logging import get_correlation_id
from app.core.redaction import redact_sensitive_data, redact_string_secrets


class AdminDomainError(Exception):
    """Base application exception carrying an HTTP status and safe error code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "BAD_REQUEST"
    default_message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers or {}
        super().__init__(self.message)


class InvalidCredentialsError(AdminDomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"
    default_message = "Invalid username or password."


class AuthenticationRequiredError(AdminDomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_REQUIRED"
    default_message = "Authentication is required to access this resource."


class SessionExpiredError(AdminDomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "SESSION_EXPIRED"
    default_message = "Your session has expired or was revoked. Please sign in again."


class CsrfValidationError(AdminDomainError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "CSRF_VALIDATION_FAILED"
    default_message = "CSRF token is missing or invalid."


class PermissionDeniedError(AdminDomainError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    default_message = "You do not have permission to perform this action."


class RateLimitExceededError(AdminDomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    default_message = "Too many login attempts. Please wait before trying again."


class ResourceNotFoundError(AdminDomainError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    default_message = "The requested resource was not found."


class ConflictError(AdminDomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    default_message = "The requested change conflicts with current system state."


HTTP_422_STATUS: int = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class ValidationDomainError(AdminDomainError):
    status_code = HTTP_422_STATUS
    error_code = "VALIDATION_ERROR"
    default_message = "One or more input fields are invalid."


class AuditLogImmutabilityError(AdminDomainError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUDIT_LOG_IMMUTABLE"
    default_message = "Administrative audit records are append-only and cannot be modified or deleted."


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    settings: Settings,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    corr_id = get_correlation_id()
    secret_literals = settings.known_secret_literals()
    safe_message = redact_string_secrets(message, extra_literals=secret_literals)

    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": safe_message,
            "correlation_id": corr_id,
        }
    }
    if details is not None:
        body["error"]["details"] = redact_sensitive_data(details, extra_literals=secret_literals)

    merged_headers = {
        "Cache-Control": "no-store",
        "X-Correlation-ID": corr_id,
    }
    if headers:
        merged_headers.update(headers)
    return JSONResponse(status_code=status_code, content=body, headers=merged_headers)


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    logger = logging.getLogger("module08_admin")

    @app.exception_handler(AdminDomainError)
    async def handle_domain_error(_request: Request, exc: AdminDomainError) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            code=exc.error_code,
            message=exc.message,
            settings=settings,
            headers=exc.headers,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        detail_msg = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error_response(
            status_code=exc.status_code,
            code=f"HTTP_{exc.status_code}",
            message=detail_msg,
            settings=settings,
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        sanitized_items = []
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", ())]
            sanitized_items.append(
                {
                    "field": ".".join(loc),
                    "message": err.get("msg", "Invalid value"),
                    "type": err.get("type", "value_error"),
                }
            )
        return _error_response(
            status_code=HTTP_422_STATUS,
            code="REQUEST_VALIDATION_ERROR",
            message="Input validation failed.",
            details=sanitized_items,
            settings=settings,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Log technical failure securely on backend (filtered for secrets), never expose stack trace
        logger.error(
            "Unhandled server error on %s %s: %s",
            request.method,
            request.url.path,
            redact_string_secrets(str(exc), extra_literals=settings.known_secret_literals()),
        )
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal error occurred.",
            settings=settings,
        )
