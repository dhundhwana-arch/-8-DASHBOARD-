"""Administrative user governance & RBAC matrix endpoints (`/api/v1/admin/users`, `/rbac`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthenticatedPrincipal,
    extract_client_ip,
    require_authenticated_principal,
    require_permission,
)
from app.core.config import Settings
from app.core.rbac import ROLE_PERMISSION_MATRIX, Permission, has_permission
from app.db.models import AdminRole
from app.db.session import get_db
from app.schemas.auth import AdminUserOut, RevokeSessionsOut
from app.schemas.users import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    CallerRbacOut,
    OwnerResetPasswordRequest,
    PasswordChangeOut,
)
from app.services.user_service import UserManagementService

router = APIRouter(tags=["users-and-rbac"])


@router.get("/rbac/permissions", response_model=CallerRbacOut)
def get_caller_permissions(
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> CallerRbacOut:
    role_matrix: dict[str, list[str]] | None = None
    if has_permission(principal.user, Permission.USERS_VIEW):
        role_matrix = {
            role.value: sorted(perm.value for perm in perms)
            for role, perms in ROLE_PERMISSION_MATRIX.items()
        }
    return CallerRbacOut(
        role=AdminRole(principal.user.role),
        permissions=sorted(p.value for p in principal.permissions),
        role_matrix=role_matrix,
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_admin_users(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_VIEW, resource_type="ADMIN_USERS")
    ),
    db: Session = Depends(get_db),
) -> list[AdminUserOut]:
    settings: Settings = request.app.state.settings
    users = UserManagementService(settings).list_users(
        db,
        actor=principal.user,
        client_ip=extract_client_ip(request),
    )
    return [AdminUserOut.model_validate(u) for u in users]


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreateRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_MANAGE, resource_type="ADMIN_USERS")
    ),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    settings: Settings = request.app.state.settings
    created = UserManagementService(settings).create_user(
        db,
        actor=principal.user,
        username=payload.username,
        display_name=payload.display_name,
        password=payload.password.get_secret_value(),
        role=payload.role,
        preferred_locale=payload.preferred_locale,
        client_ip=extract_client_ip(request),
    )
    return AdminUserOut.model_validate(created)


@router.get("/users/{public_id}", response_model=AdminUserOut)
def get_admin_user(
    public_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_VIEW, resource_type="ADMIN_USER")
    ),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    settings: Settings = request.app.state.settings
    user = UserManagementService(settings).get_user_by_public_id(
        db,
        actor=principal.user,
        public_id=public_id,
        client_ip=extract_client_ip(request),
    )
    return AdminUserOut.model_validate(user)


@router.patch("/users/{public_id}", response_model=AdminUserOut)
def update_admin_user(
    public_id: str,
    payload: AdminUserUpdateRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_MANAGE, resource_type="ADMIN_USER")
    ),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    settings: Settings = request.app.state.settings
    updated = UserManagementService(settings).update_user(
        db,
        actor=principal.user,
        public_id=public_id,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
        preferred_locale=payload.preferred_locale,
        client_ip=extract_client_ip(request),
    )
    return AdminUserOut.model_validate(updated)


@router.post("/users/{public_id}/reset-password", response_model=PasswordChangeOut)
def owner_reset_user_password(
    public_id: str,
    payload: OwnerResetPasswordRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_MANAGE, resource_type="ADMIN_USER")
    ),
    db: Session = Depends(get_db),
) -> PasswordChangeOut:
    settings: Settings = request.app.state.settings
    revoked_count = UserManagementService(settings).reset_user_password(
        db,
        actor=principal.user,
        public_id=public_id,
        new_password=payload.new_password.get_secret_value(),
        client_ip=extract_client_ip(request),
    )
    return PasswordChangeOut(revoked_sessions_count=revoked_count)


@router.post("/users/{public_id}/revoke-sessions", response_model=RevokeSessionsOut)
def owner_revoke_user_sessions(
    public_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(Permission.USERS_MANAGE, resource_type="ADMIN_USER")
    ),
    db: Session = Depends(get_db),
) -> RevokeSessionsOut:
    settings: Settings = request.app.state.settings
    revoked_count = UserManagementService(settings).revoke_user_sessions(
        db,
        actor=principal.user,
        public_id=public_id,
        client_ip=extract_client_ip(request),
    )
    return RevokeSessionsOut(revoked_count=revoked_count)
