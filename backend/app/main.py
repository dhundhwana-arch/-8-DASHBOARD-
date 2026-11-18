"""FastAPI application factory for Module 08 (Phase 03 Auth, RBAC, Session & Audit Core)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1 import audit, auth, health, users
from app.core.auth import LocalSessionAuthProvider
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, set_correlation_id
from app.core.rate_limit import LoginRateLimiter
from app.db.session import get_engine, init_db_schema


class SecurityAndCorrelationMiddleware(BaseHTTPMiddleware):
    """Attach correlation ID and defensive HTTP security headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_corr = request.headers.get("X-Correlation-ID")
        corr_id = set_correlation_id(incoming_corr)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Allow live preview iframe embedding in development while enforcing SAMEORIGIN in prod
        settings: Settings = request.app.state.settings
        if settings.app_env.value == "production":
            response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


def create_app(
    settings: Settings | None = None,
    *,
    auto_init_schema: bool = True,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.validate_runtime_safety()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if auto_init_schema:
            init_db_schema(get_engine())
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Custom Shirt Studio — Module 08 Small Business Admin Dashboard Backend. "
            "Phase 03: Authentication, Backend RBAC, Session Security & Immutable Audit Core."
        ),
        docs_url="/api/v1/admin/docs" if resolved_settings.app_env.value != "production" else None,
        redoc_url=None,
        openapi_url=(
            "/api/v1/admin/openapi.json"
            if resolved_settings.app_env.value != "production"
            else None
        ),
        lifespan=lifespan,
    )

    rate_limiter = LoginRateLimiter(
        max_attempts=resolved_settings.login_rate_limit_max_attempts,
        window_seconds=resolved_settings.login_rate_limit_window_seconds,
    )
    auth_provider = LocalSessionAuthProvider(
        settings=resolved_settings,
        rate_limiter=rate_limiter,
    )

    app.state.settings = resolved_settings
    app.state.rate_limiter = rate_limiter
    app.state.auth_provider = auth_provider

    app.add_middleware(SecurityAndCorrelationMiddleware)

    origins = resolved_settings.parsed_cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID", "Retry-After"],
    )

    register_exception_handlers(app, resolved_settings)

    prefix = resolved_settings.api_v1_admin_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)

    return app


app = create_app(auto_init_schema=False)
