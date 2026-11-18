"""Phase 03 core schema: 6 approved Module 08 internal tables + audit immutability triggers.

Revision ID: 0001_phase03_core_schema
Revises: None
Create Date: 2026-11-16 06:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_phase03_core_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("preferred_locale", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('OWNER', 'ADMINISTRATOR', 'AUTHORIZED_STAFF')",
            name="ck_admin_users_role",
        ),
        sa.CheckConstraint(
            "preferred_locale IN ('en', 'gu')",
            name="ck_admin_users_preferred_locale",
        ),
        sa.CheckConstraint("length(username) >= 3", name="ck_admin_users_username_min_len"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_admin_users_public_id", "admin_users", ["public_id"], unique=True)
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)
    op.create_index("ix_admin_users_role_active", "admin_users", ["role", "is_active"])

    # 2. admin_sessions
    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        sa.CheckConstraint(
            "length(token_hash) = 64", name="ck_admin_sessions_token_hash_sha256"
        ),
        sa.CheckConstraint(
            "length(csrf_token_hash) = 64", name="ck_admin_sessions_csrf_hash_sha256"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_sessions_session_id", "admin_sessions", ["session_id"], unique=True)
    op.create_index("ix_admin_sessions_token_hash", "admin_sessions", ["token_hash"], unique=True)
    op.create_index("ix_admin_sessions_user_id", "admin_sessions", ["user_id"])
    op.create_index(
        "ix_admin_sessions_user_active",
        "admin_sessions",
        ["user_id", "revoked_at", "expires_at"],
    )

    # 3. admin_audit_logs (append-only)
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=64), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("source_origin", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("is_security_event", sa.Boolean(), nullable=False),
        sa.Column("change_summary", sa.JSON(), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_origin IN ('ADMIN_DASHBOARD', 'EXTERNAL_MODULE')",
            name="ck_admin_audit_logs_source_origin",
        ),
        sa.CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'DENIED')",
            name="ck_admin_audit_logs_outcome",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_admin_audit_logs_event_id", "admin_audit_logs", ["event_id"], unique=True)
    op.create_index("ix_admin_audit_logs_actor_user_id", "admin_audit_logs", ["actor_user_id"])
    op.create_index("ix_admin_audit_logs_actor_username", "admin_audit_logs", ["actor_username"])
    op.create_index("ix_admin_audit_logs_action_type", "admin_audit_logs", ["action_type"])
    op.create_index("ix_admin_audit_logs_correlation_id", "admin_audit_logs", ["correlation_id"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])
    op.create_index(
        "ix_admin_audit_logs_action_outcome",
        "admin_audit_logs",
        ["action_type", "outcome"],
    )
    op.create_index(
        "ix_admin_audit_logs_resource",
        "admin_audit_logs",
        ["resource_type", "resource_id"],
    )

    # 4. business_settings
    op.create_table(
        "business_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column("is_owner_approved", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_business_settings_version_positive"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_business_settings_category", "business_settings", ["category"])

    # 5. workshop_resources
    op.create_table(
        "workshop_resources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_code", sa.String(length=32), nullable=False),
        sa.Column("display_name_en", sa.String(length=120), nullable=False),
        sa.Column("display_name_gu", sa.String(length=120), nullable=False),
        sa.Column("resource_category", sa.String(length=64), nullable=False),
        sa.Column("reported_count", sa.Integer(), nullable=False),
        sa.Column("operational_note_status", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status_is_manual_note", sa.Boolean(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reported_count >= 0", name="ck_workshop_resources_count_nonneg"),
        sa.CheckConstraint(
            sa.column("status_is_manual_note") == sa.true(),
            name="ck_workshop_resources_manual_note_only",
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_code"),
    )
    op.create_index(
        "ix_workshop_resources_resource_code",
        "workshop_resources",
        ["resource_code"],
        unique=True,
    )
    op.create_index(
        "ix_workshop_resources_category",
        "workshop_resources",
        ["resource_category"],
    )

    # 6. internal_admin_notes
    op.create_table(
        "internal_admin_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_ref", sa.String(length=128), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "target_type IN ('ORDER', 'CUSTOMER', 'WORKSHOP')",
            name="ck_internal_admin_notes_target_type",
        ),
        sa.CheckConstraint(
            "visibility = 'INTERNAL_ADMIN_ONLY'",
            name="ck_internal_admin_notes_internal_only",
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id"),
    )
    op.create_index(
        "ix_internal_admin_notes_note_id", "internal_admin_notes", ["note_id"], unique=True
    )
    op.create_index(
        "ix_internal_admin_notes_target",
        "internal_admin_notes",
        ["target_type", "target_ref"],
    )

    # Install append-only DB triggers on admin_audit_logs
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_admin_audit_logs_no_update
            BEFORE UPDATE ON admin_audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: UPDATE forbidden on admin_audit_logs');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_admin_audit_logs_no_delete
            BEFORE DELETE ON admin_audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: DELETE forbidden on admin_audit_logs');
            END;
            """
        )
    elif bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION forbid_admin_audit_logs_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'AUDIT_LOG_IMMUTABLE: % forbidden on admin_audit_logs', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_admin_audit_logs_immutable
            BEFORE UPDATE OR DELETE ON admin_audit_logs
            FOR EACH ROW EXECUTE FUNCTION forbid_admin_audit_logs_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_admin_audit_logs_no_update;")
        op.execute("DROP TRIGGER IF EXISTS trg_admin_audit_logs_no_delete;")
    elif bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_admin_audit_logs_immutable ON admin_audit_logs;")
        op.execute("DROP FUNCTION IF EXISTS forbid_admin_audit_logs_mutation();")

    op.drop_table("internal_admin_notes")
    op.drop_table("workshop_resources")
    op.drop_table("business_settings")
    op.drop_table("admin_audit_logs")
    op.drop_table("admin_sessions")
    op.drop_table("admin_users")
