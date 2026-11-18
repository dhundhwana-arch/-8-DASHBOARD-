"""Append-only Administrative Audit Log service with automatic secret redaction."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import PermissionDeniedError
from app.core.logging import get_correlation_id
from app.core.redaction import redact_sensitive_data
from app.db.models import (
    AdminAuditLog,
    AdminRole,
    AdminUser,
    AuditOutcome,
    AuditSourceOrigin,
)


class AuditAction(StrEnum):
    OWNER_BOOTSTRAPPED = "OWNER_BOOTSTRAPPED"
    AUTH_LOGIN_SUCCEEDED = "AUTH_LOGIN_SUCCEEDED"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_LOGIN_RATE_LIMITED = "AUTH_LOGIN_RATE_LIMITED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    AUTH_ALL_SESSIONS_REVOKED = "AUTH_ALL_SESSIONS_REVOKED"
    CSRF_REJECTED = "CSRF_REJECTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_STATUS_CHANGED = "USER_STATUS_CHANGED"
    USER_PASSWORD_CHANGED = "USER_PASSWORD_CHANGED"  # noqa: S105 - audit event name, not a password
    USER_PASSWORD_RESET = "USER_PASSWORD_RESET"  # noqa: S105 - audit event name, not a password
    USER_SESSIONS_REVOKED = "USER_SESSIONS_REVOKED"
    CUSTOMER_CONTACT_VIEWED = "CUSTOMER_CONTACT_VIEWED"
    MEASUREMENT_VIEWED = "MEASUREMENT_VIEWED"
    SECURITY_ACTION_PERFORMED = "SECURITY_ACTION_PERFORMED"


class AuditService:
    """Append-only service for recording and querying Module 08 audit events.

    Exposes ``record_event`` and ``list_events`` only — never update or delete.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def record_event(
        self,
        db: Session,
        *,
        action_type: str | AuditAction,
        resource_type: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        actor: AdminUser | None = None,
        actor_username_override: str | None = None,
        actor_role_override: str | None = None,
        resource_id: str | None = None,
        source_origin: AuditSourceOrigin = AuditSourceOrigin.ADMIN_DASHBOARD,
        is_security_event: bool = False,
        change_summary: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        commit_immediately: bool = True,
    ) -> AdminAuditLog:
        safe_summary: dict[str, Any] | None = None
        if change_summary is not None:
            redacted = redact_sensitive_data(
                change_summary,
                extra_literals=self._settings.known_secret_literals(),
            )
            safe_summary = redacted if isinstance(redacted, dict) else {"summary": str(redacted)}

        resolved_username = actor.username if actor is not None else actor_username_override
        if resolved_username:
            resolved_username = resolved_username.strip()[:64]

        entry = AdminAuditLog(
            actor_user_id=actor.id if actor is not None else None,
            actor_username=resolved_username,
            actor_role=actor.role if actor is not None else actor_role_override,
            action_type=str(action_type),
            resource_type=resource_type.strip().upper()[:64],
            resource_id=resource_id[:128] if resource_id else None,
            source_origin=source_origin.value,
            outcome=outcome.value,
            is_security_event=is_security_event,
            change_summary=safe_summary,
            correlation_id=(correlation_id or get_correlation_id())[:128],
            ip_address=ip_address[:64] if ip_address else None,
        )
        db.add(entry)
        if commit_immediately:
            db.commit()
            db.refresh(entry)
        else:
            db.flush()
        return entry

    def record_sensitive_data_access(
        self,
        db: Session,
        *,
        actor: AdminUser,
        action_type: AuditAction,
        resource_type: str,
        resource_id: str,
        justification: str,
        accessed_fields: list[str],
        ip_address: str | None = None,
    ) -> AdminAuditLog:
        """Record an auditable sensitive customer/measurement read without storing PII values."""
        return self.record_event(
            db,
            actor=actor,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=ip_address,
            change_summary={
                "justification": justification[:200],
                "accessed_field_names": [str(f)[:64] for f in accessed_fields],
            },
        )

    def list_events(
        self,
        db: Session,
        *,
        actor: AdminUser,
        action_type: str | None = None,
        outcome: str | None = None,
        actor_username: str | None = None,
        resource_type: str | None = None,
        correlation_id: str | None = None,
        include_security_events: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
        client_ip: str | None = None,
    ) -> tuple[list[AdminAuditLog], int]:
        """Query audit events enforcing role-scoped visibility at the service layer."""
        if actor.role == AdminRole.AUTHORIZED_STAFF.value:
            self.record_event(
                db,
                actor=actor,
                action_type=AuditAction.PERMISSION_DENIED,
                resource_type="ADMIN_AUDIT_LOGS",
                outcome=AuditOutcome.DENIED,
                is_security_event=True,
                ip_address=client_ip,
                change_summary={"attempted_operation": "list_audit_logs"},
            )
            raise PermissionDeniedError("Staff accounts cannot access administrative audit logs.")

        stmt: Select[tuple[AdminAuditLog]] = select(AdminAuditLog)

        if actor.role == AdminRole.ADMINISTRATOR.value:
            if include_security_events is True:
                self.record_event(
                    db,
                    actor=actor,
                    action_type=AuditAction.PERMISSION_DENIED,
                    resource_type="ADMIN_AUDIT_LOGS",
                    outcome=AuditOutcome.DENIED,
                    is_security_event=True,
                    ip_address=client_ip,
                    change_summary={"attempted_operation": "view_security_audit_logs"},
                )
                raise PermissionDeniedError(
                    "Only the OWNER may inspect security and account-governance audit events."
                )
            # Administrators receive operational audit events only
            stmt = stmt.where(AdminAuditLog.is_security_event.is_(False))
        elif include_security_events is not None:
            stmt = stmt.where(AdminAuditLog.is_security_event.is_(include_security_events))

        if action_type:
            stmt = stmt.where(AdminAuditLog.action_type == action_type.strip().upper())
        if outcome:
            stmt = stmt.where(AdminAuditLog.outcome == outcome.strip().upper())
        if actor_username:
            stmt = stmt.where(AdminAuditLog.actor_username == actor_username.strip().lower())
        if resource_type:
            stmt = stmt.where(AdminAuditLog.resource_type == resource_type.strip().upper())
        if correlation_id:
            stmt = stmt.where(AdminAuditLog.correlation_id == correlation_id.strip())
        if since is not None:
            stmt = stmt.where(AdminAuditLog.created_at >= since)
        if until is not None:
            stmt = stmt.where(AdminAuditLog.created_at <= until)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int(db.scalar(count_stmt) or 0)

        ordered_stmt = (
            stmt.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(db.scalars(ordered_stmt).all())
        return rows, total
