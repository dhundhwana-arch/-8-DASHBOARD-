"""SQLAlchemy 2.0 ORM models for Module 08 (strictly the 6 approved internal tables).

Approved tables ONLY:
1. ``admin_users``
2. ``admin_sessions``
3. ``admin_audit_logs``
4. ``business_settings``
5. ``workshop_resources``
6. ``internal_admin_notes``

Zero payment tables and zero external-module shadow tables are permitted here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    true,
)
from sqlalchemy.orm import Mapped, ORMExecuteState, Session, mapped_column, relationship

from app.core.errors import AuditLogImmutabilityError
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class AdminRole(StrEnum):
    OWNER = "OWNER"
    ADMINISTRATOR = "ADMINISTRATOR"
    AUTHORIZED_STAFF = "AUTHORIZED_STAFF"


class SupportedLocale(StrEnum):
    EN = "en"
    GU = "gu"


class AuditSourceOrigin(StrEnum):
    ADMIN_DASHBOARD = "ADMIN_DASHBOARD"
    EXTERNAL_MODULE = "EXTERNAL_MODULE"


class AuditOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class NoteTargetType(StrEnum):
    ORDER = "ORDER"
    CUSTOMER = "CUSTOMER"
    WORKSHOP = "WORKSHOP"


class NoteVisibility(StrEnum):
    INTERNAL_ADMIN_ONLY = "INTERNAL_ADMIN_ONLY"


# ---------------------------------------------------------------------------
# 1. admin_users
# ---------------------------------------------------------------------------
class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('OWNER', 'ADMINISTRATOR', 'AUTHORIZED_STAFF')",
            name="ck_admin_users_role",
        ),
        CheckConstraint(
            "preferred_locale IN ('en', 'gu')",
            name="ck_admin_users_preferred_locale",
        ),
        CheckConstraint("length(username) >= 3", name="ck_admin_users_username_min_len"),
        Index("ix_admin_users_role_active", "role", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: generate_public_id("ADM"),
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_locale: Mapped[str] = mapped_column(
        String(8), nullable=False, default=SupportedLocale.EN.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    sessions: Mapped[list[AdminSession]] = relationship(
        "AdminSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# 2. admin_sessions
# ---------------------------------------------------------------------------
class AdminSession(Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (
        CheckConstraint("length(token_hash) = 64", name="ck_admin_sessions_token_hash_sha256"),
        CheckConstraint(
            "length(csrf_token_hash) = 64", name="ck_admin_sessions_csrf_hash_sha256"
        ),
        Index("ix_admin_sessions_user_active", "user_id", "revoked_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped[AdminUser] = relationship("AdminUser", back_populates="sessions")


# ---------------------------------------------------------------------------
# 3. admin_audit_logs (APPEND-ONLY)
# ---------------------------------------------------------------------------
class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "source_origin IN ('ADMIN_DASHBOARD', 'EXTERNAL_MODULE')",
            name="ck_admin_audit_logs_source_origin",
        ),
        CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'DENIED')",
            name="ck_admin_audit_logs_outcome",
        ),
        Index("ix_admin_audit_logs_created_at", "created_at"),
        Index("ix_admin_audit_logs_action_outcome", "action_type", "outcome"),
        Index("ix_admin_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: f"AUD-{uuid.uuid4().hex[:16].upper()}",
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_origin: Mapped[str] = mapped_column(
        String(32), nullable=False, default=AuditSourceOrigin.ADMIN_DASHBOARD.value
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    is_security_event: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    change_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


# ---------------------------------------------------------------------------
# 4. business_settings
# ---------------------------------------------------------------------------
class BusinessSetting(Base):
    __tablename__ = "business_settings"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_business_settings_version_positive"),
        Index("ix_business_settings_category", "category"),
    )

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_owner_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# 5. workshop_resources
# ---------------------------------------------------------------------------
class WorkshopResource(Base):
    __tablename__ = "workshop_resources"
    __table_args__ = (
        CheckConstraint("reported_count >= 0", name="ck_workshop_resources_count_nonneg"),
        CheckConstraint(
            sa.column("status_is_manual_note") == true(),
            name="ck_workshop_resources_manual_note_only",
        ),
        Index("ix_workshop_resources_category", "resource_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: generate_public_id("RES"),
    )
    display_name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name_gu: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_category: Mapped[str] = mapped_column(String(64), nullable=False)
    reported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    operational_note_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UNVERIFIED_MANUAL_NOTE"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_is_manual_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# 6. internal_admin_notes
# ---------------------------------------------------------------------------
class InternalAdminNote(Base):
    __tablename__ = "internal_admin_notes"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('ORDER', 'CUSTOMER', 'WORKSHOP')",
            name="ck_internal_admin_notes_target_type",
        ),
        CheckConstraint(
            "visibility = 'INTERNAL_ADMIN_ONLY'",
            name="ck_internal_admin_notes_internal_only",
        ),
        Index("ix_internal_admin_notes_target", "target_type", "target_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: generate_public_id("NTE"),
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NoteVisibility.INTERNAL_ADMIN_ONLY.value
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# Application-layer append-only enforcement on AdminAuditLog
# ---------------------------------------------------------------------------
@event.listens_for(AdminAuditLog, "before_update")
def _block_audit_orm_update(_mapper: Any, _connection: Any, _target: AdminAuditLog) -> None:
    raise AuditLogImmutabilityError()


@event.listens_for(AdminAuditLog, "before_delete")
def _block_audit_orm_delete(_mapper: Any, _connection: Any, _target: AdminAuditLog) -> None:
    raise AuditLogImmutabilityError()


@event.listens_for(Session, "do_orm_execute")
def _block_audit_bulk_mutation(orm_execute_state: ORMExecuteState) -> None:
    if not (orm_execute_state.is_update or orm_execute_state.is_delete):
        return
    stmt = orm_execute_state.statement
    table = getattr(stmt, "table", None)
    if table is not None and getattr(table, "name", None) == AdminAuditLog.__tablename__:
        raise AuditLogImmutabilityError()
    for mapper in orm_execute_state.all_mappers:
        if mapper.class_ is AdminAuditLog:
            raise AuditLogImmutabilityError()


APPROVED_MODULE_08_TABLES: frozenset[str] = frozenset(
    {
        "admin_users",
        "admin_sessions",
        "admin_audit_logs",
        "business_settings",
        "workshop_resources",
        "internal_admin_notes",
    }
)
