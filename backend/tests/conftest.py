"""Shared pytest fixtures for isolated Phase 03 backend tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from app.cli.bootstrap_owner import bootstrap_owner_account
from app.core.config import AppEnvironment, IntegrationMode, Settings
from app.db.models import AdminRole, AdminUser, SupportedLocale
from app.db.session import build_engine, get_db, init_db_schema
from app.main import create_app
from app.services.user_service import UserManagementService

TEST_OWNER_PASSWORD = "Owner#Secure2026!"
TEST_ADMIN_PASSWORD = "Admin#Secure2026!"
TEST_STAFF_PASSWORD = "Staff#Secure2026!"


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    db_file = tmp_path / "phase03_test.db"
    return Settings(
        app_env=AppEnvironment.TESTING,
        database_url=f"sqlite:///{db_file}",
        session_secret_key=SecretStr("unit-test-strong-session-secret-key-0123456789abcdef"),
        module_02_admin_api_key=SecretStr("m02-super-secret-upstream-admin-key-999999"),
        bcrypt_rounds=10,
        login_rate_limit_max_attempts=4,
        login_rate_limit_window_seconds=120,
        session_ttl_minutes=60,
        session_idle_timeout_minutes=30,
        cookie_secure=False,
        integration_mode=IntegrationMode.LIVE,
    )


@pytest.fixture()
def db_session_factory(test_settings: Settings) -> Generator[sessionmaker[Session], None, None]:
    engine = build_engine(test_settings.database_url)
    init_db_schema(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def db_session(db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded_users(
    db_session: Session,
    test_settings: Settings,
) -> dict[str, AdminUser]:
    owner = bootstrap_owner_account(
        db_session,
        username="owner_main",
        display_name="Workshop Owner",
        password=TEST_OWNER_PASSWORD,
        preferred_locale=SupportedLocale.GU,
        settings=test_settings,
    )
    user_svc = UserManagementService(test_settings)
    admin = user_svc.create_user(
        db_session,
        actor=owner,
        username="admin_manager",
        display_name="Store Administrator",
        password=TEST_ADMIN_PASSWORD,
        role=AdminRole.ADMINISTRATOR,
        preferred_locale=SupportedLocale.EN,
    )
    staff = user_svc.create_user(
        db_session,
        actor=owner,
        username="tailor_staff",
        display_name="Tailor Staff",
        password=TEST_STAFF_PASSWORD,
        role=AdminRole.AUTHORIZED_STAFF,
        preferred_locale=SupportedLocale.GU,
    )
    return {"owner": owner, "admin": admin, "staff": staff}


@pytest.fixture()
def app_instance(
    test_settings: Settings,
    db_session_factory: sessionmaker[Session],
):
    app = create_app(test_settings, auto_init_schema=False)

    def _override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture()
def client(app_instance) -> Generator[TestClient, None, None]:
    with TestClient(app_instance) as test_client:
        yield test_client


def login_and_get_csrf(client: TestClient, username: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
