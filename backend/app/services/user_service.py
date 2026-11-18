"""Administrative account & role governance service (strict OWNER control)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import (
    ConflictError,
    InvalidCredentialsError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from app.core.rbac import Permission, enforce_permission
from app.core.security import hash_password, validate_password_strength, verify_password
from app.db.models import (
    AdminRole,
    AdminSession,
    AdminUser,
    AuditOutcome,
    SupportedLocale,
    utcnow,
)
from app.services.audit_service import AuditAction, AuditService

_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def normalize_and_validate_username(username: str) -> str:
    cleaned = username.strip().lower()
    if not _USERNAME_RE.match(cleaned):
        raise ValidationDomainError(
            "Username must be 3-64 characters using lowercase letters, digits, '.', '_', or '-'."
        )
    return cleaned


class UserManagementService:
    """Service enforcing least-privilege user/role governance and OWNER lockout protection."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    def _count_active_owners(self, db: Session, *, exclude_user_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(AdminUser).where(
            AdminUser.role == AdminRole.OWNER.value,
            AdminUser.is_active.is_(True),
        )
        if exclude_user_id is not None:
            stmt = stmt.where(AdminUser.id != exclude_user_id)
        return int(db.scalar(stmt) or 0)

    def _revoke_all_user_sessions(
        self,
        db: Session,
        *,
        user_id: int,
        reason: str,
        except_session_id: str | None = None,
    ) -> int:
        stmt = update(AdminSession).where(
            AdminSession.user_id == user_id,
            AdminSession.revoked_at.is_(None),
        )
        if except_session_id is not None:
            stmt = stmt.where(AdminSession.session_id != except_session_id)
        result = db.execute(stmt.values(revoked_at=utcnow(), revoked_reason=reason[:120]))
        return int(result.rowcount or 0)

    def list_users(
        self,
        db: Session,
        *,
        actor: AdminUser,
        client_ip: str | None = None,
    ) -> list[AdminUser]:
        enforce_permission(
            db,
            actor,
            Permission.USERS_VIEW,
            resource_type="ADMIN_USERS",
            client_ip=client_ip,
            audit_service=self._audit,
        )
        stmt = select(AdminUser).order_by(AdminUser.created_at.asc(), AdminUser.id.asc())
        return list(db.scalars(stmt).all())

    def get_user_by_public_id(
        self,
        db: Session,
        *,
        actor: AdminUser,
        public_id: str,
        client_ip: str | None = None,
    ) -> AdminUser:
        enforce_permission(
            db,
            actor,
            Permission.USERS_VIEW,
            resource_type="ADMIN_USERS",
            resource_id=public_id,
            client_ip=client_ip,
            audit_service=self._audit,
        )
        target = db.scalar(select(AdminUser).where(AdminUser.public_id == public_id.strip()))
        if target is None:
            raise ResourceNotFoundError("Administrative user not found.")
        return target

    def create_user(
        self,
        db: Session,
        *,
        actor: AdminUser,
        username: str,
        display_name: str,
        password: str,
        role: AdminRole,
        preferred_locale: SupportedLocale = SupportedLocale.EN,
        client_ip: str | None = None,
    ) -> AdminUser:
        enforce_permission(
            db,
            actor,
            Permission.USERS_MANAGE,
            resource_type="ADMIN_USERS",
            client_ip=client_ip,
            audit_service=self._audit,
        )

        normalized_username = normalize_and_validate_username(username)
        cleaned_display = display_name.strip()
        if not cleaned_display or len(cleaned_display) > 120:
            raise ValidationDomainError("Display name must be between 1 and 120 characters.")

        validate_password_strength(password, username=normalized_username)

        existing = db.scalar(select(AdminUser).where(AdminUser.username == normalized_username))
        if existing is not None:
            raise ConflictError(f"Username '{normalized_username}' is already registered.")

        pw_hash = hash_password(password, rounds=self._settings.bcrypt_rounds)
        new_user = AdminUser(
            username=normalized_username,
            display_name=cleaned_display,
            password_hash=pw_hash,
            role=role.value,
            preferred_locale=preferred_locale.value,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        self._audit.record_event(
            db,
            actor=actor,
            action_type=AuditAction.USER_CREATED,
            resource_type="ADMIN_USER",
            resource_id=new_user.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={
                "created_username": new_user.username,
                "assigned_role": new_user.role,
                "preferred_locale": new_user.preferred_locale,
            },
        )
        return new_user

    def update_user(
        self,
        db: Session,
        *,
        actor: AdminUser,
        public_id: str,
        display_name: str | None = None,
        role: AdminRole | None = None,
        is_active: bool | None = None,
        preferred_locale: SupportedLocale | None = None,
        client_ip: str | None = None,
    ) -> AdminUser:
        enforce_permission(
            db,
            actor,
            Permission.USERS_MANAGE,
            resource_type="ADMIN_USER",
            resource_id=public_id,
            client_ip=client_ip,
            audit_service=self._audit,
        )

        target = db.scalar(select(AdminUser).where(AdminUser.public_id == public_id.strip()))
        if target is None:
            raise ResourceNotFoundError("Administrative user not found.")

        next_role = role.value if role is not None else target.role
        next_active = is_active if is_active is not None else target.is_active

        # Prevent removing or disabling the last active OWNER account
        if target.role == AdminRole.OWNER.value and target.is_active:
            if next_role != AdminRole.OWNER.value or not next_active:
                remaining_owners = self._count_active_owners(db, exclude_user_id=target.id)
                if remaining_owners < 1:
                    raise ConflictError(
                        "Cannot demote or deactivate the sole remaining active OWNER account."
                    )

        changes: dict[str, Any] = {}
        role_changed = False
        status_changed = False

        if display_name is not None:
            cleaned_display = display_name.strip()
            if not cleaned_display or len(cleaned_display) > 120:
                raise ValidationDomainError("Display name must be between 1 and 120 characters.")
            if cleaned_display != target.display_name:
                changes["display_name"] = {"from": target.display_name, "to": cleaned_display}
                target.display_name = cleaned_display

        if preferred_locale is not None and preferred_locale.value != target.preferred_locale:
            changes["preferred_locale"] = {
                "from": target.preferred_locale,
                "to": preferred_locale.value,
            }
            target.preferred_locale = preferred_locale.value

        if role is not None and role.value != target.role:
            changes["role"] = {"from": target.role, "to": role.value}
            target.role = role.value
            role_changed = True

        if is_active is not None and is_active != target.is_active:
            changes["is_active"] = {"from": target.is_active, "to": is_active}
            target.is_active = is_active
            status_changed = True

        revoked_sessions = 0
        if role_changed or (status_changed and not target.is_active):
            reason = "ROLE_CHANGED" if role_changed else "ACCOUNT_DEACTIVATED"
            revoked_sessions = self._revoke_all_user_sessions(
                db, user_id=target.id, reason=reason
            )
            changes["revoked_sessions_count"] = revoked_sessions

        target.updated_at = utcnow()
        db.commit()
        db.refresh(target)

        if role_changed:
            action = AuditAction.USER_ROLE_CHANGED
        elif status_changed:
            action = AuditAction.USER_STATUS_CHANGED
        else:
            action = AuditAction.USER_UPDATED

        self._audit.record_event(
            db,
            actor=actor,
            action_type=action,
            resource_type="ADMIN_USER",
            resource_id=target.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={"target_username": target.username, "changes": changes},
        )
        return target

    def change_own_password(
        self,
        db: Session,
        *,
        actor: AdminUser,
        current_session_id: str,
        current_password: str,
        new_password: str,
        client_ip: str | None = None,
    ) -> int:
        if not verify_password(current_password, actor.password_hash):
            self._audit.record_event(
                db,
                actor=actor,
                action_type=AuditAction.USER_PASSWORD_CHANGED,
                resource_type="ADMIN_USER",
                resource_id=actor.public_id,
                outcome=AuditOutcome.FAILURE,
                is_security_event=True,
                ip_address=client_ip,
                change_summary={"reason": "invalid_current_password"},
            )
            raise InvalidCredentialsError("Current password is incorrect.")

        validate_password_strength(new_password, username=actor.username)
        if verify_password(new_password, actor.password_hash):
            raise ValidationDomainError("New password must differ from the current password.")

        now = utcnow()
        actor.password_hash = hash_password(new_password, rounds=self._settings.bcrypt_rounds)
        actor.password_changed_at = now
        actor.updated_at = now
        revoked_other = self._revoke_all_user_sessions(
            db,
            user_id=actor.id,
            reason="PASSWORD_CHANGED",
            except_session_id=current_session_id,
        )
        db.commit()

        self._audit.record_event(
            db,
            actor=actor,
            action_type=AuditAction.USER_PASSWORD_CHANGED,
            resource_type="ADMIN_USER",
            resource_id=actor.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={"revoked_other_sessions_count": revoked_other},
        )
        return revoked_other

    def reset_user_password(
        self,
        db: Session,
        *,
        actor: AdminUser,
        public_id: str,
        new_password: str,
        client_ip: str | None = None,
    ) -> int:
        enforce_permission(
            db,
            actor,
            Permission.USERS_MANAGE,
            resource_type="ADMIN_USER",
            resource_id=public_id,
            client_ip=client_ip,
            audit_service=self._audit,
        )

        target = db.scalar(select(AdminUser).where(AdminUser.public_id == public_id.strip()))
        if target is None:
            raise ResourceNotFoundError("Administrative user not found.")

        validate_password_strength(new_password, username=target.username)

        now = utcnow()
        target.password_hash = hash_password(new_password, rounds=self._settings.bcrypt_rounds)
        target.password_changed_at = now
        target.updated_at = now
        revoked_count = self._revoke_all_user_sessions(
            db,
            user_id=target.id,
            reason="OWNER_PASSWORD_RESET",
        )
        db.commit()

        self._audit.record_event(
            db,
            actor=actor,
            action_type=AuditAction.USER_PASSWORD_RESET,
            resource_type="ADMIN_USER",
            resource_id=target.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={
                "target_username": target.username,
                "revoked_sessions_count": revoked_count,
            },
        )
        return revoked_count

    def revoke_user_sessions(
        self,
        db: Session,
        *,
        actor: AdminUser,
        public_id: str,
        client_ip: str | None = None,
    ) -> int:
        enforce_permission(
            db,
            actor,
            Permission.USERS_MANAGE,
            resource_type="ADMIN_USER",
            resource_id=public_id,
            client_ip=client_ip,
            audit_service=self._audit,
        )

        target = db.scalar(select(AdminUser).where(AdminUser.public_id == public_id.strip()))
        if target is None:
            raise ResourceNotFoundError("Administrative user not found.")

        revoked_count = self._revoke_all_user_sessions(
            db,
            user_id=target.id,
            reason="OWNER_SESSION_REVOCATION",
        )
        db.commit()

        self._audit.record_event(
            db,
            actor=actor,
            action_type=AuditAction.USER_SESSIONS_REVOKED,
            resource_type="ADMIN_USER",
            resource_id=target.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={
                "target_username": target.username,
                "revoked_sessions_count": revoked_count,
            },
        )
        return revoked_count
