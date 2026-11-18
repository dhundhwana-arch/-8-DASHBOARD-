"""Read-only administrative audit trail endpoint (`/api/v1/admin/audit-logs`)."""

from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthenticatedPrincipal,
    extract_client_ip,
    require_permission,
)
from app.core.config import Settings
from app.core.rbac import Permission
from app.db.session import get_db
from app.schemas.audit import AuditEventOut, PaginatedAuditEventsOut
from app.services.audit_service import AuditService

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", response_model=PaginatedAuditEventsOut)
def list_audit_logs(
    request: Request,
    action_type: str | None = Query(default=None, max_length=80),
    outcome: str | None = Query(default=None, max_length=16),
    actor_username: str | None = Query(default=None, max_length=64),
    resource_type: str | None = Query(default=None, max_length=64),
    correlation_id: str | None = Query(default=None, max_length=128),
    include_security_events: bool | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.AUDIT_VIEW_OPERATIONAL, resource_type="ADMIN_AUDIT_LOGS")
    ),
    db: Session = Depends(get_db),
) -> PaginatedAuditEventsOut:
    settings: Settings = request.app.state.settings
    rows, total = AuditService(settings).list_events(
        db,
        actor=principal.user,
        action_type=action_type,
        outcome=outcome,
        actor_username=actor_username,
        resource_type=resource_type,
        correlation_id=correlation_id,
        include_security_events=include_security_events,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
        client_ip=extract_client_ip(request),
    )
    pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return PaginatedAuditEventsOut(
        items=[AuditEventOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
