"""Administrative audit log response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    actor_username: str | None
    actor_role: str | None
    action_type: str
    resource_type: str
    resource_id: str | None
    source_origin: str
    outcome: str
    is_security_event: bool
    change_summary: dict[str, Any] | None
    correlation_id: str | None
    ip_address: str | None
    created_at: datetime


class PaginatedAuditEventsOut(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int
    pages: int
