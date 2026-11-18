"""Extensible authentication provider, server-side session manager, and FastAPI guards."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from fastapi import Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidCredentialsError,
    RateLimitExceededError,
    ResourceNotFoundError,
    SessionExpiredError,
)
from app.core.rate_limit import LoginRateLimiter
from app.core.rbac import Permission, enforce_permission, get_permissions_for_role
from app.core.security import (
    derive_session_csrf_token,
    generate_opaque_token,
    sha256_hex,
    verify_csrf_token,
    verify_password_constant_time,
)
from app.db.models import AdminSession, AdminUser, AuditOutcome, utcnow
from app.db.session import get_db
from app.services.audit_service import AuditAction, AuditService

MUTATING_HTTP_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER_NAME = "X-CSRF-Token"


class AuthFederationStatus(StrEnum):
    """Explicitly reports standalone status until Module 01 shared auth exists."""

    STANDALONE_LOCAL = "STANDALONE_LOCAL"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: AdminUser
    session: AdminSession
    csrf_token: str
    permissions: frozenset[Permission]
    federation_status: AuthFederationStatus = AuthFederationStatus.STANDALONE_LOCAL


class AuthProvider(Protocol):
    """Extensible authentication boundary ready for future Module 01 integration."""

    def authenticate_credentials(
        self,
        db: Session,
        *,
        username: str,
        password: str,
        client_ip: str | None,
        user_agent: str | None,
    ) -> tuple[AuthenticatedPrincipal, str]: ...

    def resolve_session(
        self,
        db: Session,
        *,
        raw_session_token: str | None,
        client_ip: str | None,
    ) -> AuthenticatedPrincipal: ...

    def revoke_session_by_id(
        self,
        db: Session,
        *,
        actor: AdminUser,
        session_id: str,
        reason: str,
        client_ip: str | None,
    ) -> None: ...


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def extract_client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class LocalSessionAuthProvider:
    """Standalone Module 08 session authentication backed by ``admin_users`` & ``admin_sessions``."""

    def __init__(
        self,
        *,
        settings: Settings,
        rate_limiter: LoginRateLimiter,
        audit_service: AuditService | None = None,
    ) -> None:
        self._settings = settings
        self._rate_limiter = rate_limiter
        self._audit = audit_service or AuditService(settings)

    def authenticate_credentials(
        self,
        db: Session,
        *,
        username: str,
        password: str,
        client_ip: str | None,
        user_agent: str | None,
    ) -> tuple[AuthenticatedPrincipal, str]:
        normalized_username = username.strip().lower()
        ip_str = client_ip or "unknown"

        try:
            self._rate_limiter.check_allowed(client_ip=ip_str, username=normalized_username)
        except RateLimitExceededError:
            self._audit.record_event(
                db,
                actor_username_override=normalized_username or None,
                action_type=AuditAction.AUTH_LOGIN_RATE_LIMITED,
                resource_type="ADMIN_AUTH",
                outcome=AuditOutcome.DENIED,
                is_security_event=True,
                ip_address=ip_str,
                change_summary={"reason": "rate_limit_window_exceeded"},
            )
            raise

        user = db.scalar(select(AdminUser).where(AdminUser.username == normalized_username))
        password_valid = verify_password_constant_time(
            password,
            user.password_hash if user is not None else None,
            rounds=self._settings.bcrypt_rounds,
        )

        if user is None or not password_valid or not user.is_active:
            self._rate_limiter.record_failure(client_ip=ip_str, username=normalized_username)
            failure_reason = (
                "unknown_username"
                if user is None
                else ("inactive_account" if not user.is_active else "bad_password")
            )
            self._audit.record_event(
                db,
                actor=user if user is not None else None,
                actor_username_override=normalized_username if user is None else None,
                action_type=AuditAction.AUTH_LOGIN_FAILED,
                resource_type="ADMIN_AUTH",
                outcome=AuditOutcome.FAILURE,
                is_security_event=True,
                ip_address=ip_str,
                change_summary={"failure_category": failure_reason},
            )
            # Generic authentication error: never reveals whether the username exists or is disabled
            raise InvalidCredentialsError()

        self._rate_limiter.reset_account_window(username=normalized_username)

        now = utcnow()
        raw_session_token = generate_opaque_token(32)
        token_hash = sha256_hex(raw_session_token)
        session_id = str(uuid.uuid4())
        csrf_token = derive_session_csrf_token(
            session_id=session_id,
            session_token_hash=token_hash,
            secret_key=self._settings.session_secret_key.get_secret_value(),
        )
        csrf_hash = sha256_hex(csrf_token)
        expires_at = now + timedelta(minutes=self._settings.session_ttl_minutes)

        session_row = AdminSession(
            session_id=session_id,
            user_id=user.id,
            token_hash=token_hash,
            csrf_token_hash=csrf_hash,
            ip_address=ip_str[:64],
            user_agent=(user_agent or "")[:255] or None,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
        user.last_login_at = now
        db.add(session_row)
        db.commit()
        db.refresh(session_row)
        db.refresh(user)

        self._audit.record_event(
            db,
            actor=user,
            action_type=AuditAction.AUTH_LOGIN_SUCCEEDED,
            resource_type="ADMIN_SESSION",
            resource_id=session_row.session_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=ip_str,
            change_summary={
                "auth_mode": AuthFederationStatus.STANDALONE_LOCAL.value,
                "expires_at": expires_at.isoformat(),
            },
        )

        principal = AuthenticatedPrincipal(
            user=user,
            session=session_row,
            csrf_token=csrf_token,
            permissions=get_permissions_for_role(user.role),
        )
        return principal, raw_session_token

    def resolve_session(
        self,
        db: Session,
        *,
        raw_session_token: str | None,
        client_ip: str | None,
    ) -> AuthenticatedPrincipal:
        if not raw_session_token:
            raise AuthenticationRequiredError()

        token_hash = sha256_hex(raw_session_token.strip())
        session_row = db.scalar(
            select(AdminSession).where(AdminSession.token_hash == token_hash)
        )
        if session_row is None:
            raise SessionExpiredError()

        user = db.get(AdminUser, session_row.user_id)
        now = utcnow()

        if session_row.revoked_at is not None:
            raise SessionExpiredError()

        expires_at = _ensure_utc(session_row.expires_at)
        last_seen = _ensure_utc(session_row.last_seen_at)
        idle_deadline = last_seen + timedelta(minutes=self._settings.session_idle_timeout_minutes)

        if now >= expires_at or now > idle_deadline:
            reason = "ABSOLUTE_TTL_EXPIRED" if now >= expires_at else "IDLE_TIMEOUT_EXPIRED"
            session_row.revoked_at = now
            session_row.revoked_reason = reason
            db.commit()
            self._audit.record_event(
                db,
                actor=user,
                action_type=AuditAction.AUTH_SESSION_EXPIRED,
                resource_type="ADMIN_SESSION",
                resource_id=session_row.session_id,
                outcome=AuditOutcome.FAILURE,
                is_security_event=True,
                ip_address=client_ip,
                change_summary={"expiry_reason": reason},
            )
            raise SessionExpiredError()

        if user is None or not user.is_active:
            session_row.revoked_at = now
            session_row.revoked_reason = "ACCOUNT_INACTIVE"
            db.commit()
            raise SessionExpiredError()

        session_row.last_seen_at = now
        db.commit()
        db.refresh(session_row)

        csrf_token = derive_session_csrf_token(
            session_id=session_row.session_id,
            session_token_hash=session_row.token_hash,
            secret_key=self._settings.session_secret_key.get_secret_value(),
        )
        return AuthenticatedPrincipal(
            user=user,
            session=session_row,
            csrf_token=csrf_token,
            permissions=get_permissions_for_role(user.role),
        )

    def logout_session(
        self,
        db: Session,
        *,
        principal: AuthenticatedPrincipal,
        client_ip: str | None,
    ) -> None:
        now = utcnow()
        principal.session.revoked_at = now
        principal.session.revoked_reason = "USER_LOGOUT"
        db.commit()
        self._audit.record_event(
            db,
            actor=principal.user,
            action_type=AuditAction.AUTH_LOGOUT,
            resource_type="ADMIN_SESSION",
            resource_id=principal.session.session_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={"reason": "USER_LOGOUT"},
        )

    def revoke_session_by_id(
        self,
        db: Session,
        *,
        actor: AdminUser,
        session_id: str,
        reason: str = "MANUAL_REVOCATION",
        client_ip: str | None = None,
    ) -> None:
        session_row = db.scalar(
            select(AdminSession).where(
                AdminSession.session_id == session_id,
                AdminSession.user_id == actor.id,
            )
        )
        if session_row is None:
            raise ResourceNotFoundError("Active session not found.")

        if session_row.revoked_at is None:
            session_row.revoked_at = utcnow()
            session_row.revoked_reason = reason[:120]
            db.commit()

        self._audit.record_event(
            db,
            actor=actor,
            action_type=AuditAction.AUTH_SESSION_REVOKED,
            resource_type="ADMIN_SESSION",
            resource_id=session_row.session_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={"reason": reason[:120]},
        )

    def revoke_other_sessions(
        self,
        db: Session,
        *,
        principal: AuthenticatedPrincipal,
        reason: str = "REVOKE_OTHER_SESSIONS",
        client_ip: str | None = None,
    ) -> int:
        now = utcnow()
        result = db.execute(
            update(AdminSession)
            .where(
                AdminSession.user_id == principal.user.id,
                AdminSession.session_id != principal.session.session_id,
                AdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoked_reason=reason[:120])
        )
        revoked_count = int(result.rowcount or 0)
        db.commit()

        self._audit.record_event(
            db,
            actor=principal.user,
            action_type=AuditAction.AUTH_ALL_SESSIONS_REVOKED,
            resource_type="ADMIN_USER",
            resource_id=principal.user.public_id,
            outcome=AuditOutcome.SUCCESS,
            is_security_event=True,
            ip_address=client_ip,
            change_summary={"revoked_other_sessions_count": revoked_count, "reason": reason[:120]},
        )
        return revoked_count


def set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.session_cookie_path,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path=settings.session_cookie_path,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def get_auth_provider(request: Request) -> LocalSessionAuthProvider:
    return request.app.state.auth_provider


def require_authenticated_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    """Authenticate session cookie and enforce CSRF on state-changing HTTP methods."""
    settings: Settings = request.app.state.settings
    provider: LocalSessionAuthProvider = request.app.state.auth_provider
    client_ip = extract_client_ip(request)
    raw_cookie = request.cookies.get(settings.session_cookie_name)

    principal = provider.resolve_session(
        db,
        raw_session_token=raw_cookie,
        client_ip=client_ip,
    )

    if request.method.upper() in MUTATING_HTTP_METHODS:
        provided_csrf = request.headers.get(CSRF_HEADER_NAME)
        if not verify_csrf_token(provided_csrf, principal.session.csrf_token_hash):
            AuditService(settings).record_event(
                db,
                actor=principal.user,
                action_type=AuditAction.CSRF_REJECTED,
                resource_type="ADMIN_CSRF",
                resource_id=principal.session.session_id,
                outcome=AuditOutcome.DENIED,
                is_security_event=True,
                ip_address=client_ip,
                change_summary={
                    "method": request.method.upper(),
                    "path": request.url.path,
                    "csrf_header_present": bool(provided_csrf),
                },
                commit_immediately=True,
            )
            raise CsrfValidationError()

    return principal


def require_permission(permission: Permission, *, resource_type: str = "ADMIN_API"):
    """FastAPI dependency factory enforcing authentication, CSRF, and RBAC permission."""

    def _dependency(
        request: Request,
        principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
        db: Session = Depends(get_db),
    ) -> AuthenticatedPrincipal:
        settings: Settings = request.app.state.settings
        enforce_permission(
            db,
            principal.user,
            permission,
            resource_type=resource_type,
            resource_id=request.url.path,
            client_ip=extract_client_ip(request),
            audit_service=AuditService(settings),
        )
        return principal

    return _dependency
