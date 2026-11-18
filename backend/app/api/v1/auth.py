"""Authentication & session lifecycle endpoints (`/api/v1/admin/auth/*`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthenticatedPrincipal,
    LocalSessionAuthProvider,
    clear_session_cookie,
    extract_client_ip,
    get_auth_provider,
    require_authenticated_principal,
    set_session_cookie,
)
from app.core.config import Settings
from app.core.errors import AuthenticationRequiredError, SessionExpiredError
from app.db.models import AdminSession, utcnow
from app.db.session import get_db
from app.schemas.auth import (
    AdminUserOut,
    AuthSessionOut,
    ChangePasswordRequest,
    LoginRequest,
    LogoutOut,
    RevokeSessionsOut,
    SessionSummaryOut,
)
from app.schemas.users import PasswordChangeOut
from app.services.user_service import UserManagementService

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_auth_session_out(principal: AuthenticatedPrincipal) -> AuthSessionOut:
    return AuthSessionOut(
        user=AdminUserOut.model_validate(principal.user),
        session=SessionSummaryOut(
            session_id=principal.session.session_id,
            ip_address=principal.session.ip_address,
            user_agent=principal.session.user_agent,
            created_at=principal.session.created_at,
            last_seen_at=principal.session.last_seen_at,
            expires_at=principal.session.expires_at,
            is_current=True,
        ),
        csrf_token=principal.csrf_token,
        permissions=sorted(p.value for p in principal.permissions),
        auth_federation_status=principal.federation_status,
    )


@router.post("/login", response_model=AuthSessionOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    provider: LocalSessionAuthProvider = Depends(get_auth_provider),
) -> AuthSessionOut:
    settings: Settings = request.app.state.settings
    principal, raw_session_token = provider.authenticate_credentials(
        db,
        username=payload.username,
        password=payload.password.get_secret_value(),
        client_ip=extract_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    set_session_cookie(response, raw_session_token, settings)
    return _build_auth_session_out(principal)


@router.post("/logout", response_model=LogoutOut)
def logout(
    request: Request,
    response: Response,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    db: Session = Depends(get_db),
    provider: LocalSessionAuthProvider = Depends(get_auth_provider),
) -> LogoutOut:
    settings: Settings = request.app.state.settings
    provider.logout_session(
        db,
        principal=principal,
        client_ip=extract_client_ip(request),
    )
    clear_session_cookie(response, settings)
    return LogoutOut()


@router.get("/me", response_model=AuthSessionOut)
def current_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    provider: LocalSessionAuthProvider = Depends(get_auth_provider),
) -> AuthSessionOut:
    settings: Settings = request.app.state.settings
    raw_cookie = request.cookies.get(settings.session_cookie_name)
    try:
        principal = provider.resolve_session(
            db,
            raw_session_token=raw_cookie,
            client_ip=extract_client_ip(request),
        )
    except (AuthenticationRequiredError, SessionExpiredError):
        clear_session_cookie(response, settings)
        raise
    return _build_auth_session_out(principal)


@router.post("/password", response_model=PasswordChangeOut)
def change_own_password(
    payload: ChangePasswordRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    db: Session = Depends(get_db),
) -> PasswordChangeOut:
    settings: Settings = request.app.state.settings
    service = UserManagementService(settings)
    revoked_count = service.change_own_password(
        db,
        actor=principal.user,
        current_session_id=principal.session.session_id,
        current_password=payload.current_password.get_secret_value(),
        new_password=payload.new_password.get_secret_value(),
        client_ip=extract_client_ip(request),
    )
    return PasswordChangeOut(revoked_sessions_count=revoked_count)


@router.get("/sessions", response_model=list[SessionSummaryOut])
def list_my_active_sessions(
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    db: Session = Depends(get_db),
) -> list[SessionSummaryOut]:
    now = utcnow()
    rows = list(
        db.scalars(
            select(AdminSession)
            .where(
                AdminSession.user_id == principal.user.id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > now,
            )
            .order_by(AdminSession.last_seen_at.desc())
        ).all()
    )
    return [
        SessionSummaryOut(
            session_id=row.session_id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            is_current=(row.session_id == principal.session.session_id),
        )
        for row in rows
    ]


@router.post("/sessions/revoke-others", response_model=RevokeSessionsOut)
def revoke_other_sessions(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    db: Session = Depends(get_db),
    provider: LocalSessionAuthProvider = Depends(get_auth_provider),
) -> RevokeSessionsOut:
    revoked = provider.revoke_other_sessions(
        db,
        principal=principal,
        client_ip=extract_client_ip(request),
    )
    return RevokeSessionsOut(revoked_count=revoked)


@router.post("/sessions/{session_id}/revoke", response_model=LogoutOut)
def revoke_specific_session(
    session_id: str,
    request: Request,
    response: Response,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    db: Session = Depends(get_db),
    provider: LocalSessionAuthProvider = Depends(get_auth_provider),
) -> LogoutOut:
    settings: Settings = request.app.state.settings
    provider.revoke_session_by_id(
        db,
        actor=principal.user,
        session_id=session_id,
        reason="USER_MANUAL_SESSION_REVOKE",
        client_ip=extract_client_ip(request),
    )
    if session_id == principal.session.session_id:
        clear_session_cookie(response, settings)
    return LogoutOut(status="session_revoked")
