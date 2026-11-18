"""Phase 04 Admin Dashboard Overview endpoints (`/api/v1/admin/dashboard/*`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.adapters.module02_fabrics import Module02FabricAdapter
from app.adapters.module07_orders import Module07OrderAdapter
from app.core.auth import (
    AuthenticatedPrincipal,
    extract_client_ip,
    require_permission,
)
from app.core.config import Settings
from app.core.rbac import Permission
from app.db.session import get_db
from app.schemas.dashboard import DashboardIntegrationsOut, DashboardOverviewOut
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(request: Request) -> DashboardService:
    settings: Settings = request.app.state.settings
    fabric_adapter: Module02FabricAdapter = getattr(
        request.app.state,
        "fabric_adapter",
        Module02FabricAdapter(settings=settings),
    )
    order_adapter: Module07OrderAdapter = getattr(
        request.app.state,
        "order_adapter",
        Module07OrderAdapter(settings=settings),
    )
    return DashboardService(
        settings=settings,
        fabric_adapter=fabric_adapter,
        order_adapter=order_adapter,
    )


@router.get("/overview", response_model=DashboardOverviewOut)
def get_dashboard_overview(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.DASHBOARD_VIEW_LIMITED,
            resource_type="DASHBOARD_OVERVIEW",
        )
    ),
    db: Session = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardOverviewOut:
    return service.get_overview(
        db,
        actor=principal.user,
        client_ip=extract_client_ip(request),
    )


@router.get("/integrations", response_model=DashboardIntegrationsOut)
def get_dashboard_integrations(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.DASHBOARD_VIEW_FULL,
            resource_type="DASHBOARD_INTEGRATIONS",
        )
    ),
    db: Session = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardIntegrationsOut:
    return service.get_full_integrations_diagnostics(
        db,
        actor=principal.user,
        client_ip=extract_client_ip(request),
    )
