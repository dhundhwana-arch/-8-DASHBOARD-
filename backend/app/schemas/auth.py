"""Authentication and session Pydantic v2 schemas (zero secret/hash exposure)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.auth import AuthFederationStatus
from app.db.models import AdminRole, SupportedLocale


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=256, repr=False)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr = Field(min_length=1, max_length=256, repr=False)
    new_password: SecretStr = Field(min_length=12, max_length=256, repr=False)


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    username: str
    display_name: str
    role: AdminRole
    preferred_locale: SupportedLocale
    is_active: bool
    last_login_at: datetime | None
    password_changed_at: datetime
    created_at: datetime
    updated_at: datetime


class SessionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    is_current: bool = False


class AuthSessionOut(BaseModel):
    user: AdminUserOut
    session: SessionSummaryOut
    csrf_token: str
    permissions: list[str]
    auth_federation_status: AuthFederationStatus = AuthFederationStatus.STANDALONE_LOCAL


class LogoutOut(BaseModel):
    status: str = "logged_out"


class RevokeSessionsOut(BaseModel):
    revoked_count: int
