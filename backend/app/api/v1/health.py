"""Health and authentication-mode readiness endpoint (`/api/v1/admin/health`)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.auth import AuthFederationStatus
from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def admin_health(request: Request) -> dict[str, str]:
    settings: Settings = request.app.state.settings
    return {
        "status": "ok",
        "module": "small-business-admin-dashboard",
        "module_number": "08",
        "version": settings.app_version,
        "auth_federation_status": AuthFederationStatus.STANDALONE_LOCAL.value,
        "integration_mode": settings.integration_mode.value,
    }
