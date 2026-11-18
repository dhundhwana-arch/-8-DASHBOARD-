"""Role-Based Access Control (RBAC) permission matrix and service/API guards."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.db.models import AdminRole, AdminUser, AuditOutcome
from app.services.audit_service import AuditAction, AuditService


class Permission(StrEnum):
    # Dashboard Overview (Phase 04+)
    DASHBOARD_VIEW_FULL = "dashboard:view_full"
    DASHBOARD_VIEW_LIMITED = "dashboard:view_limited"

    # Customer Management (Phase 05+)
    CUSTOMERS_LIST = "customers:list"
    CUSTOMERS_VIEW_LIMITED = "customers:view_limited"
    CUSTOMERS_REVEAL_CONTACT = "customers:reveal_contact"

    # Orders & Production Workflow (Phase 06+)
    ORDERS_VIEW_ALL = "orders:view_all"
    ORDERS_VIEW_ASSIGNED = "orders:view_assigned"
    ORDERS_TRANSITION_REQUEST = "orders:transition_request"

    # Fabric Catalogue (Phase 07+)
    FABRICS_VIEW = "fabrics:view"
    FABRICS_MANAGE = "fabrics:manage"
    FABRICS_VIEW_SUPPLIERS = "fabrics:view_suppliers"

    # Pricing Administration (Phase 08+)
    PRICING_VIEW = "pricing:view"
    PRICING_MANAGE_CONFIG = "pricing:manage_config"

    # Measurement Reference (Phase 09+)
    MEASUREMENTS_VIEW_AUTHORIZED = "measurements:view_authorized"
    MEASUREMENTS_VIEW_ASSIGNED_NEED = "measurements:view_assigned_need"

    # Workshop Operations & Business Settings (Phase 10+)
    OPERATIONS_VIEW = "operations:view"
    OPERATIONS_MANAGE = "operations:manage"
    SETTINGS_VIEW = "settings:view"
    SETTINGS_MANAGE_NON_CRITICAL = "settings:manage_non_critical"
    SETTINGS_MANAGE_CRITICAL = "settings:manage_critical"

    # Staff & Account Governance (Phase 03)
    USERS_VIEW = "users:view"
    USERS_MANAGE = "users:manage"

    # Reports & Exports (Phase 11+)
    REPORTS_VIEW_FULL = "reports:view_full"
    REPORTS_VIEW_LIMITED = "reports:view_limited"
    REPORTS_EXPORT = "reports:export"

    # Administrative Audit Logs (Phase 03)
    AUDIT_VIEW_ALL = "audit:view_all"
    AUDIT_VIEW_OPERATIONAL = "audit:view_operational"

    # Internal Admin Notes (Phase 06/10+)
    INTERNAL_NOTES_VIEW = "internal_notes:view"
    INTERNAL_NOTES_WRITE = "internal_notes:write"


ROLE_PERMISSION_MATRIX: dict[AdminRole, frozenset[Permission]] = {
    AdminRole.OWNER: frozenset(Permission),
    AdminRole.ADMINISTRATOR: frozenset(
        {
            Permission.DASHBOARD_VIEW_FULL,
            Permission.DASHBOARD_VIEW_LIMITED,
            Permission.CUSTOMERS_LIST,
            Permission.CUSTOMERS_VIEW_LIMITED,
            Permission.CUSTOMERS_REVEAL_CONTACT,
            Permission.ORDERS_VIEW_ALL,
            Permission.ORDERS_VIEW_ASSIGNED,
            Permission.ORDERS_TRANSITION_REQUEST,
            Permission.FABRICS_VIEW,
            Permission.FABRICS_MANAGE,
            Permission.FABRICS_VIEW_SUPPLIERS,
            Permission.PRICING_VIEW,
            Permission.PRICING_MANAGE_CONFIG,
            Permission.MEASUREMENTS_VIEW_AUTHORIZED,
            Permission.MEASUREMENTS_VIEW_ASSIGNED_NEED,
            Permission.OPERATIONS_VIEW,
            Permission.OPERATIONS_MANAGE,
            Permission.SETTINGS_VIEW,
            Permission.SETTINGS_MANAGE_NON_CRITICAL,
            Permission.USERS_VIEW,  # Read-only staff visibility; USERS_MANAGE stays OWNER-only
            Permission.REPORTS_VIEW_FULL,
            Permission.REPORTS_VIEW_LIMITED,
            Permission.REPORTS_EXPORT,
            Permission.AUDIT_VIEW_OPERATIONAL,
            Permission.INTERNAL_NOTES_VIEW,
            Permission.INTERNAL_NOTES_WRITE,
        }
    ),
    AdminRole.AUTHORIZED_STAFF: frozenset(
        {
            Permission.DASHBOARD_VIEW_LIMITED,
            Permission.CUSTOMERS_VIEW_LIMITED,
            Permission.ORDERS_VIEW_ASSIGNED,
            Permission.ORDERS_TRANSITION_REQUEST,
            Permission.FABRICS_VIEW,
            Permission.MEASUREMENTS_VIEW_ASSIGNED_NEED,
            Permission.OPERATIONS_VIEW,
            Permission.REPORTS_VIEW_LIMITED,
            Permission.INTERNAL_NOTES_VIEW,
            Permission.INTERNAL_NOTES_WRITE,
        }
    ),
}


def get_permissions_for_role(role: str | AdminRole) -> frozenset[Permission]:
    try:
        resolved = AdminRole(str(role))
    except ValueError:
        return frozenset()
    return ROLE_PERMISSION_MATRIX.get(resolved, frozenset())


def has_permission(actor: AdminUser, permission: Permission) -> bool:
    if not actor.is_active:
        return False
    return permission in get_permissions_for_role(actor.role)


def enforce_permission(
    db: Session,
    actor: AdminUser,
    permission: Permission,
    *,
    resource_type: str,
    resource_id: str | None = None,
    client_ip: str | None = None,
    audit_service: AuditService | None = None,
) -> None:
    """Service- and route-layer guard recording ``PERMISSION_DENIED`` on violation."""
    if has_permission(actor, permission):
        return

    auditor = audit_service or AuditService()
    auditor.record_event(
        db,
        actor=actor,
        action_type=AuditAction.PERMISSION_DENIED,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=AuditOutcome.DENIED,
        is_security_event=True,
        ip_address=client_ip,
        change_summary={
            "required_permission": permission.value,
            "actor_role": actor.role,
        },
        commit_immediately=True,
    )
    raise PermissionDeniedError(
        f"Role '{actor.role}' is not authorized for '{permission.value}'."
    )
