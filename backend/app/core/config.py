"""Environment-driven application settings with strict production safety validation."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class IntegrationMode(StrEnum):
    LIVE = "live"
    MOCK_DEV = "mock_dev"


_INSECURE_SECRET_MARKERS: frozenset[str] = frozenset(
    {
        "",
        "changeme",
        "change-me",
        "secret",
        "password",
        "default",
        "dev-only-session-secret-not-for-production-use-0123456789",
        "change_me_generate_with_secrets_token_urlsafe_48",
        "replace-with-at-least-32-random-bytes-in-production",
    }
)


class Settings(BaseSettings):
    """Validated runtime configuration for Module 08 Admin Backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Custom Shirt Studio — Small Business Admin Dashboard"
    app_version: str = "0.3.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    api_v1_admin_prefix: str = "/api/v1/admin"

    # Database (PostgreSQL in production; SQLite WAL supported for local dev & tests)
    database_url: str = "sqlite:///./module08_admin_dev.db"

    # Cryptographic session & CSRF secret (stored as SecretStr so repr/str never leak it)
    session_secret_key: SecretStr = Field(
        default=SecretStr("dev-only-session-secret-not-for-production-use-0123456789"),
        repr=False,
    )

    # Cookie & Session lifecycle settings
    session_cookie_name: str = "css_admin_session"
    session_cookie_path: str = "/api/v1/admin"
    session_ttl_minutes: int = Field(default=480, ge=5, le=1440)
    session_idle_timeout_minutes: int = Field(default=120, ge=5, le=1440)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict"] = "lax"

    # Password hashing & login rate limiting
    bcrypt_rounds: int = Field(default=12, ge=10, le=16)
    login_rate_limit_max_attempts: int = Field(default=5, ge=2, le=50)
    login_rate_limit_window_seconds: int = Field(default=300, ge=10, le=3600)

    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # External module integration mode & service URLs (Phase 04+ adapters)
    integration_mode: IntegrationMode = IntegrationMode.LIVE
    module_01_base_url: str = ""
    module_02_base_url: str = ""
    module_02_admin_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    module_05_base_url: str = ""
    module_06_base_url: str = ""
    module_07_base_url: str = ""

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def known_secret_literals(self) -> list[str]:
        """Return non-empty secret strings solely for log/error redaction filters."""
        literals: list[str] = []
        session_secret = self.session_secret_key.get_secret_value()
        if session_secret:
            literals.append(session_secret)
        m02_key = self.module_02_admin_api_key.get_secret_value()
        if m02_key:
            literals.append(m02_key)
        return literals

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> Settings:
        if self.session_idle_timeout_minutes > self.session_ttl_minutes:
            raise ValueError(
                "SESSION_IDLE_TIMEOUT_MINUTES cannot exceed SESSION_TTL_MINUTES."
            )

        if self.app_env == AppEnvironment.PRODUCTION:
            raw_secret = self.session_secret_key.get_secret_value().strip()
            if (
                len(raw_secret) < 32
                or raw_secret.lower() in _INSECURE_SECRET_MARKERS
                or raw_secret.lower().startswith("dev-only-")
                or raw_secret.lower().startswith("change_me")
                or raw_secret.lower().startswith("replace-with")
            ):
                raise ValueError(
                    "Production startup refused: SESSION_SECRET_KEY must be a strong "
                    "random secret of at least 32 characters (not a default/placeholder)."
                )

            if not self.cookie_secure:
                raise ValueError(
                    "Production startup refused: COOKIE_SECURE must be true in production."
                )

            if self.integration_mode == IntegrationMode.MOCK_DEV:
                raise ValueError(
                    "Production startup refused: INTEGRATION_MODE=mock_dev is strictly "
                    "forbidden in production."
                )

            if self.bcrypt_rounds < 12:
                raise ValueError(
                    "Production startup refused: BCRYPT_ROUNDS must be >= 12 in production."
                )

            if "*" in self.parsed_cors_origins:
                raise ValueError(
                    "Production startup refused: wildcard '*' CORS_ORIGINS is forbidden."
                )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
