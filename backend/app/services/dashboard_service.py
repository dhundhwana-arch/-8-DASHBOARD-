"""Phase 04 Dashboard Overview orchestration service with backend RBAC scoping."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.base import IntegrationEnvelope, IntegrationSourceStatus
from app.adapters.health_registry import build_integration_health_items
from app.adapters.module02_fabrics import FabricDashboardSummary, Module02FabricAdapter
from app.adapters.module07_orders import Module07OrderAdapter, OrderDashboardSummary
from app.core.config import IntegrationMode, Settings
from app.core.rbac import Permission, enforce_permission, has_permission
from app.db.models import (
    AdminAuditLog,
    AdminRole,
    AdminSession,
    AdminUser,
    AuditOutcome,
    BusinessSetting,
    utcnow,
)
from app.schemas.dashboard import (
    AlertSeverity,
    DashboardAccessScope,
    DashboardIntegrationsOut,
    DashboardOverviewOut,
    LocalGovernanceSummary,
    OperationalAlertItem,
    PendingAdminActionItem,
    RecentActivityPreviewItem,
)
from app.services.audit_service import AuditService


class DashboardService:
    """Aggregates verified Module 08 & sibling-adapter status without inventing metrics."""

    def __init__(
        self,
        *,
        settings: Settings,
        fabric_adapter: Module02FabricAdapter,
        order_adapter: Module07OrderAdapter,
        audit_service: AuditService | None = None,
    ) -> None:
        self._settings = settings
        self._fabric_adapter = fabric_adapter
        self._order_adapter = order_adapter
        self._audit = audit_service or AuditService(settings)

    def get_full_integrations_diagnostics(
        self,
        db: Session,
        *,
        actor: AdminUser,
        client_ip: str | None = None,
    ) -> DashboardIntegrationsOut:
        enforce_permission(
            db,
            actor,
            Permission.DASHBOARD_VIEW_FULL,
            resource_type="DASHBOARD_INTEGRATIONS",
            client_ip=client_ip,
            audit_service=self._audit,
        )
        fabric_env = self._fabric_adapter.get_catalogue_overview(include_full_breakdown=True)
        order_env = self._order_adapter.get_order_overview(include_full_business_totals=True)
        items = build_integration_health_items(
            fabric_envelope=fabric_env,
            order_envelope=order_env,
            include_all_modules=True,
        )
        return DashboardIntegrationsOut(
            generated_at=utcnow(),
            integration_mode=self._settings.integration_mode,
            items=items,
        )

    def get_overview(
        self,
        db: Session,
        *,
        actor: AdminUser,
        client_ip: str | None = None,
    ) -> DashboardOverviewOut:
        enforce_permission(
            db,
            actor,
            Permission.DASHBOARD_VIEW_LIMITED,
            resource_type="DASHBOARD_OVERVIEW",
            client_ip=client_ip,
            audit_service=self._audit,
        )

        is_full_scope = has_permission(actor, Permission.DASHBOARD_VIEW_FULL)
        is_owner = actor.role == AdminRole.OWNER.value
        scope = DashboardAccessScope.FULL if is_full_scope else DashboardAccessScope.LIMITED

        fabric_env = self._fabric_adapter.get_catalogue_overview(
            include_full_breakdown=is_full_scope
        )
        order_env = self._order_adapter.get_order_overview(
            include_full_business_totals=is_full_scope
        )

        health_items = build_integration_health_items(
            fabric_envelope=fabric_env,
            order_envelope=order_env,
            include_all_modules=is_full_scope,
        )

        has_mock = (
            self._settings.integration_mode == IntegrationMode.MOCK_DEV
            or fabric_env.is_mock_data
            or order_env.is_mock_data
        )

        now = utcnow()
        security_failures_24h = 0
        if is_owner:
            since_24h = now - timedelta(hours=24)
            security_failures_24h = int(
                db.scalar(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.created_at >= since_24h,
                        AdminAuditLog.outcome.in_(
                            [AuditOutcome.FAILURE.value, AuditOutcome.DENIED.value]
                        ),
                    )
                )
                or 0
            )

        pending_actions = self._build_pending_actions(
            db,
            is_full_scope=is_full_scope,
            is_owner=is_owner,
            security_failures_24h=security_failures_24h,
            order_env=order_env,
            fabric_env=fabric_env,
        )

        alerts = self._build_operational_alerts(
            is_full_scope=is_full_scope,
            is_owner=is_owner,
            has_mock=has_mock,
            security_failures_24h=security_failures_24h,
            order_env=order_env,
            fabric_env=fabric_env,
        )

        governance_summary: LocalGovernanceSummary | None = None
        recent_activity: list[RecentActivityPreviewItem] | None = None

        if is_full_scope:
            active_users = int(
                db.scalar(
                    select(func.count())
                    .select_from(AdminUser)
                    .where(AdminUser.is_active.is_(True))
                )
                or 0
            )
            active_sessions = int(
                db.scalar(
                    select(func.count())
                    .select_from(AdminSession)
                    .where(
                        AdminSession.revoked_at.is_(None),
                        AdminSession.expires_at > now,
                    )
                )
                or 0
            )
            governance_summary = LocalGovernanceSummary(
                active_admin_users_count=active_users,
                active_sessions_count=active_sessions,
                security_events_last_24h_count=security_failures_24h if is_owner else None,
            )

            audit_stmt = select(AdminAuditLog)
            if not is_owner:
                audit_stmt = audit_stmt.where(AdminAuditLog.is_security_event.is_(False))
            recent_rows = list(
                db.scalars(
                    audit_stmt.order_by(
                        AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc()
                    ).limit(5)
                ).all()
            )
            recent_activity = [
                RecentActivityPreviewItem(
                    event_id=row.event_id,
                    action_type=row.action_type,
                    resource_type=row.resource_type,
                    outcome=row.outcome,
                    actor_username=row.actor_username,
                    created_at=row.created_at,
                )
                for row in recent_rows
            ]

        return DashboardOverviewOut(
            generated_at=now,
            access_scope=scope,
            integration_mode=self._settings.integration_mode,
            has_mock_data=has_mock,
            order_overview=order_env,
            fabric_overview=fabric_env,
            integration_health=health_items,
            pending_actions=pending_actions,
            operational_alerts=alerts,
            governance_summary=governance_summary,
            recent_activity=recent_activity,
        )

    def _build_pending_actions(
        self,
        db: Session,
        *,
        is_full_scope: bool,
        is_owner: bool,
        security_failures_24h: int,
        order_env: IntegrationEnvelope[OrderDashboardSummary],
        fabric_env: IntegrationEnvelope[FabricDashboardSummary],
    ) -> list[PendingAdminActionItem]:
        actions: list[PendingAdminActionItem] = []

        # 1. Verified or explicit mock order actions (when actual order data is present)
        if order_env.data is not None:
            o_data = order_env.data
            if is_full_scope and o_data.pending_review_orders and o_data.pending_review_orders > 0:
                actions.append(
                    PendingAdminActionItem(
                        action_code="ORDERS_AWAITING_REVIEW",
                        title_key="pendingOrdersReview",
                        count=o_data.pending_review_orders,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                    )
                )
            if (
                is_full_scope
                and o_data.awaiting_confirmation_orders
                and o_data.awaiting_confirmation_orders > 0
            ):
                actions.append(
                    PendingAdminActionItem(
                        action_code="ORDERS_AWAITING_CONFIRMATION",
                        title_key="pendingCustomerConfirmation",
                        count=o_data.awaiting_confirmation_orders,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                    )
                )
            if o_data.quality_check_orders > 0:
                actions.append(
                    PendingAdminActionItem(
                        action_code="ORDERS_QUALITY_CHECK",
                        title_key="pendingQualityChecks",
                        count=o_data.quality_check_orders,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                    )
                )
            if o_data.ready_for_delivery_orders > 0:
                actions.append(
                    PendingAdminActionItem(
                        action_code="ORDERS_READY_FOR_DELIVERY",
                        title_key="pendingReadyForDelivery",
                        count=o_data.ready_for_delivery_orders,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                    )
                )

        # 2. Verified Module 02 catalogue attention items (FULL scope only)
        if is_full_scope and fabric_env.data is not None:
            f_data = fabric_env.data
            attention_variants = (f_data.out_of_stock_variants or 0) + (
                f_data.low_stock_variants or 0
            )
            if attention_variants > 0:
                actions.append(
                    PendingAdminActionItem(
                        action_code="FABRIC_VARIANTS_ATTENTION",
                        title_key="pendingFabricAttention",
                        count=attention_variants,
                        source_module="MODULE_02",
                        source_status=fabric_env.source_status,
                    )
                )

        # 3. Verified local Module 08 security review action (OWNER only)
        if is_owner and security_failures_24h > 0:
            actions.append(
                PendingAdminActionItem(
                    action_code="SECURITY_EVENTS_REVIEW",
                    title_key="pendingSecurityReview",
                    count=security_failures_24h,
                    source_module="MODULE_08",
                    source_status=IntegrationSourceStatus.VERIFIED,
                    target_route="/activity-logs",
                )
            )

        # 4. Owner-approved business settings bootstrap reminder (OWNER only, verified local DB)
        if is_owner:
            approved_settings_cnt = int(
                db.scalar(
                    select(func.count())
                    .select_from(BusinessSetting)
                    .where(BusinessSetting.is_owner_approved.is_(True))
                )
                or 0
            )
            if approved_settings_cnt == 0:
                actions.append(
                    PendingAdminActionItem(
                        action_code="WORKSHOP_SETTINGS_UNCONFIGURED",
                        title_key="pendingWorkshopSettings",
                        count=1,
                        source_module="MODULE_08",
                        source_status=IntegrationSourceStatus.VERIFIED,
                    )
                )

        return actions

    def _build_operational_alerts(
        self,
        *,
        is_full_scope: bool,
        is_owner: bool,
        has_mock: bool,
        security_failures_24h: int,
        order_env: IntegrationEnvelope[OrderDashboardSummary],
        fabric_env: IntegrationEnvelope[FabricDashboardSummary],
    ) -> list[OperationalAlertItem]:
        alerts: list[OperationalAlertItem] = []

        if has_mock:
            alerts.append(
                OperationalAlertItem(
                    alert_code="MOCK_DEV_MODE_ACTIVE",
                    severity=AlertSeverity.WARNING,
                    source_module="MODULE_08",
                    source_status=IntegrationSourceStatus.MOCK_DEV,
                    message=(
                        "MOCK_DEV mode is active for local development/testing. Shown fixture "
                        "counts are NOT verified live business records."
                    ),
                )
            )

        for env in (order_env, fabric_env):
            if env.source_status == IntegrationSourceStatus.UNAVAILABLE:
                alerts.append(
                    OperationalAlertItem(
                        alert_code=f"{env.module_code}_UNAVAILABLE",
                        severity=AlertSeverity.CRITICAL,
                        source_module=env.module_code,
                        source_status=IntegrationSourceStatus.UNAVAILABLE,
                        message=env.error_message
                        or f"{env.module_name} is currently unreachable.",
                    )
                )
            elif env.source_status == IntegrationSourceStatus.CONTRACT_MISMATCH:
                alerts.append(
                    OperationalAlertItem(
                        alert_code=f"{env.module_code}_CONTRACT_MISMATCH",
                        severity=AlertSeverity.CRITICAL,
                        source_module=env.module_code,
                        source_status=IntegrationSourceStatus.CONTRACT_MISMATCH,
                        message=env.error_message
                        or f"{env.module_name} response violated its verified API contract.",
                    )
                )
            elif env.source_status == IntegrationSourceStatus.CONTRACT_UNCONFIGURED:
                alerts.append(
                    OperationalAlertItem(
                        alert_code=f"{env.module_code}_CONTRACT_UNCONFIGURED",
                        severity=AlertSeverity.INFO,
                        source_module=env.module_code,
                        source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
                        message=env.error_message
                        or f"{env.module_name} integration is not yet configured.",
                    )
                )

        if order_env.data is not None:
            if order_env.data.on_hold_orders > 0:
                alerts.append(
                    OperationalAlertItem(
                        alert_code="ORDERS_ON_HOLD",
                        severity=AlertSeverity.WARNING,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                        message=(
                            f"{order_env.data.on_hold_orders} order(s) are currently ON_HOLD "
                            "in tailoring workflow."
                        ),
                    )
                )
            for upstream_msg in order_env.data.upstream_warnings:
                alerts.append(
                    OperationalAlertItem(
                        alert_code="MODULE_07_WORKLOAD_WARNING",
                        severity=AlertSeverity.WARNING,
                        source_module="MODULE_07",
                        source_status=order_env.source_status,
                        message=upstream_msg,
                    )
                )

        if is_full_scope and is_owner and security_failures_24h > 0:
            alerts.append(
                OperationalAlertItem(
                    alert_code="RECENT_SECURITY_EVENTS",
                    severity=AlertSeverity.WARNING,
                    source_module="MODULE_08",
                    source_status=IntegrationSourceStatus.VERIFIED,
                    message=(
                        f"{security_failures_24h} failed or denied security event(s) recorded "
                        "in the last 24 hours."
                    ),
                )
            )

        return alerts
