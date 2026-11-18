"""User management and RBAC metadata schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.db.models import AdminRole, SupportedLocale


class AdminUserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=12, max_length=256, repr=False)
    role: AdminRole
    preferred_locale: SupportedLocale = SupportedLocale.EN


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: AdminRole | None = None
    is_active: bool | None = None
    preferred_locale: SupportedLocale | None = None


class OwnerResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: SecretStr = Field(min_length=12, max_length=256, repr=False)


class PasswordChangeOut(BaseModel):
    status: str = "password_updated"
    revoked_sessions_count: int


class CallerRbacOut(BaseModel):
    role: AdminRole
    permissions: list[str]
    role_matrix: dict[str, list[str]] | None = None
