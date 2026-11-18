"""Pydantic v2 response schemas for Phase 04 Admin Dashboard Overview."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.adapters.base import IntegrationEnvelope, IntegrationSourceStatus
from app.adapters.health_registry import ModuleIntegrationHealthItem
from app.adapters.module02_fabrics import FabricDashboardSummary
from app.adapters.module07_orders import OrderDashboardSummary
from app.core.config import IntegrationMode


class DashboardAccessScope(StrEnum):
    FULL = "FULL"
    LIMITED = "LIMITED"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PendingAdminActionItem(BaseModel):
    """Actionable item backed strictly by verified local or upstream data."""

    model_config = ConfigDict(extra="forbid")

    action_code: str
    title_key: str
    count: int
    source_module: str
    source_status: IntegrationSourceStatus
    target_route: str | None = None


class OperationalAlertItem(BaseModel):
    """Operational or integration alert with explicit provenance."""

    model_config = ConfigDict(extra="forbid")

    alert_code: str
    severity: AlertSeverity
    source_module: str
    source_status: IntegrationSourceStatus
    message: str


class LocalGovernanceSummary(BaseModel):
    """Verified Module 08 internal governance counters (FULL dashboard scope only)."""

    model_config = ConfigDict(extra="forbid")

    source_status: IntegrationSourceStatus = IntegrationSourceStatus.VERIFIED
    active_admin_users_count: int
    active_sessions_count: int
    security_events_last_24h_count: int | None = None


class RecentActivityPreviewItem(BaseModel):
    """Sanitized recent Module 08 activity preview (never includes PII or secrets)."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    action_type: str
    resource_type: str
    outcome: str
    actor_username: str | None
    created_at: datetime


class DashboardOverviewOut(BaseModel):
    """Composite Phase 04 Dashboard Overview response."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    access_scope: DashboardAccessScope
    integration_mode: IntegrationMode
    has_mock_data: bool
    order_overview: IntegrationEnvelope[OrderDashboardSummary]
    fabric_overview: IntegrationEnvelope[FabricDashboardSummary]
    integration_health: list[ModuleIntegrationHealthItem]
    pending_actions: list[PendingAdminActionItem]
    operational_alerts: list[OperationalAlertItem]
    governance_summary: LocalGovernanceSummary | None = None
    recent_activity: list[RecentActivityPreviewItem] | None = None


class DashboardIntegrationsOut(BaseModel):
    """Full 7-module diagnostic view restricted to `dashboard:view_full`."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    integration_mode: IntegrationMode
    items: list[ModuleIntegrationHealthItem]
