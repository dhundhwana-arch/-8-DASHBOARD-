"""Audit-log immutability, secret redaction, sensitive-access logging, and prod safeguard tests."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, text, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.config import AppEnvironment, IntegrationMode, Settings
from app.core.errors import AuditLogImmutabilityError
from app.core.logging import configure_logging
from app.db.models import AdminAuditLog, AdminUser, AuditOutcome
from app.services.audit_service import AuditAction, AuditService


def test_audit_log_immutability_at_orm_core_and_database_trigger_layers(
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    entry = AuditService().record_event(
        db_session,
        actor=seeded_users["owner"],
        action_type=AuditAction.SECURITY_ACTION_PERFORMED,
        resource_type="SECURITY_TEST",
        resource_id="SEC-001",
        outcome=AuditOutcome.SUCCESS,
        is_security_event=True,
        change_summary={"status": "recorded"},
    )

    # 1. ORM instance attribute modification -> blocked by before_update listener
    entry.outcome = "FAILURE"
    with pytest.raises(AuditLogImmutabilityError):
        db_session.commit()
    db_session.rollback()

    # 2. ORM instance deletion -> blocked by before_delete listener
    fresh_entry = db_session.get(AdminAuditLog, entry.id)
    assert fresh_entry is not None
    db_session.delete(fresh_entry)
    with pytest.raises(AuditLogImmutabilityError):
        db_session.commit()
    db_session.rollback()

    # 3. SQLAlchemy Core bulk UPDATE -> blocked by do_orm_execute listener
    with pytest.raises(AuditLogImmutabilityError):
        db_session.execute(
            update(AdminAuditLog)
            .where(AdminAuditLog.id == entry.id)
            .values(action_type="TAMPERED")
        )
    db_session.rollback()

    # 4. SQLAlchemy Core bulk DELETE -> blocked by do_orm_execute listener
    with pytest.raises(AuditLogImmutabilityError):
        db_session.execute(delete(AdminAuditLog).where(AdminAuditLog.id == entry.id))
    db_session.rollback()

    # 5. Raw SQL UPDATE/DELETE bypassing ORM -> blocked by SQLite/PostgreSQL trigger
    with pytest.raises((IntegrityError, OperationalError)):
        db_session.execute(
            text("UPDATE admin_audit_logs SET action_type = 'RAW_TAMPER' WHERE id = :id"),
            {"id": entry.id},
        )
    db_session.rollback()

    with pytest.raises((IntegrityError, OperationalError)):
        db_session.execute(
            text("DELETE FROM admin_audit_logs WHERE id = :id"),
            {"id": entry.id},
        )
    db_session.rollback()


def test_secret_and_pii_redaction_in_audit_records_logs_and_error_responses(
    test_settings: Settings,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
    app_instance,
) -> None:
    auditor = AuditService(test_settings)
    m02_secret = test_settings.module_02_admin_api_key.get_secret_value()
    session_secret = test_settings.session_secret_key.get_secret_value()

    # 1. AuditService scrubs nested secrets, tokens, passwords, and raw PII fields
    record = auditor.record_event(
        db_session,
        actor=seeded_users["owner"],
        action_type=AuditAction.SECURITY_ACTION_PERFORMED,
        resource_type="REDACTION_CHECK",
        outcome=AuditOutcome.SUCCESS,
        is_security_event=True,
        change_summary={
            "password": "PlainTextPassword#1",
            "csrf_token": "abcdef123456",
            "session_token": "raw-cookie-token-xyz",
            "phone_e164": "+919876543210",
            "raw_measurements": {"chest": 40, "waist": 34},
            "nested": {
                "authorization": "Bearer secret-upstream-jwt",
                "note": f"Attempted call using {m02_secret} and {session_secret}",
            },
            "safe_field": "kept_intact",
        },
    )
    serialized = str(record.change_summary)
    assert "PlainTextPassword#1" not in serialized
    assert "abcdef123456" not in serialized
    assert "raw-cookie-token-xyz" not in serialized
    assert "+919876543210" not in serialized
    assert "40" not in serialized
    assert "secret-upstream-jwt" not in serialized
    assert m02_secret not in serialized
    assert session_secret not in serialized
    assert record.change_summary is not None
    assert record.change_summary["safe_field"] == "kept_intact"
    assert record.change_summary["password"] == "[REDACTED]"

    # 2. Sensitive customer/measurement access helper records field names ONLY, never values
    sens_record = auditor.record_sensitive_data_access(
        db_session,
        actor=seeded_users["owner"],
        action_type=AuditAction.CUSTOMER_CONTACT_VIEWED,
        resource_type="CUSTOMER",
        resource_id="CUS-0099",
        justification="Order delivery coordination",
        accessed_fields=["phone_e164"],
    )
    assert sens_record.change_summary == {
        "justification": "Order delivery coordination",
        "accessed_field_names": ["phone_e164"],
    }

    # 3. Structured logger filter scrubs literal secrets and Bearer headers
    logger = configure_logging(test_settings)
    captured_messages: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, rec: logging.LogRecord) -> None:
            captured_messages.append(self.format(rec))

    handler = _ListHandler()
    logger.addHandler(handler)
    try:
        logger.warning(
            "Upstream failed with Authorization: Bearer topsecret123 and key=%s",
            m02_secret,
        )
    finally:
        logger.removeHandler(handler)

    assert len(captured_messages) == 1
    assert "topsecret123" not in captured_messages[0]
    assert m02_secret not in captured_messages[0]
    assert "[REDACTED]" in captured_messages[0]

    # 4. Unhandled server exception never leaks secrets or Python tracebacks to HTTP callers
    @app_instance.get("/api/v1/admin/_test_boom")
    def _boom_route():
        raise RuntimeError(f"DB exploded with key={m02_secret} and Bearer leak999")

    with TestClient(app_instance, raise_server_exceptions=False) as err_client:
        boom_resp = err_client.get("/api/v1/admin/_test_boom")
        assert boom_resp.status_code == 500
        text_body = boom_resp.text
        assert m02_secret not in text_body
        assert "leak999" not in text_body
        assert "Traceback" not in text_body
        assert boom_resp.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"


def test_production_configuration_safeguards() -> None:
    strong_secret = SecretStr("prod-cryptographic-random-secret-key-at-least-32-chars!!")

    # Valid production configuration succeeds
    valid_prod = Settings(
        app_env=AppEnvironment.PRODUCTION,
        session_secret_key=strong_secret,
        cookie_secure=True,
        integration_mode=IntegrationMode.LIVE,
        bcrypt_rounds=12,
        cors_origins="https://admin.customshirtstudio.example",
    )
    assert valid_prod.cookie_secure is True

    # 1. Placeholder / default secret rejected in production
    with pytest.raises(ValidationError, match="SESSION_SECRET_KEY"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            cookie_secure=True,
            integration_mode=IntegrationMode.LIVE,
            bcrypt_rounds=12,
            cors_origins="https://admin.customshirtstudio.example",
        )

    # 2. Short secret rejected in production
    with pytest.raises(ValidationError, match="SESSION_SECRET_KEY"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            session_secret_key=SecretStr("too-short-secret"),
            cookie_secure=True,
            integration_mode=IntegrationMode.LIVE,
            bcrypt_rounds=12,
            cors_origins="https://admin.customshirtstudio.example",
        )

    # 3. COOKIE_SECURE=False rejected in production
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            session_secret_key=strong_secret,
            cookie_secure=False,
            integration_mode=IntegrationMode.LIVE,
            bcrypt_rounds=12,
            cors_origins="https://admin.customshirtstudio.example",
        )

    # 4. INTEGRATION_MODE=mock_dev rejected in production
    with pytest.raises(ValidationError, match="INTEGRATION_MODE=mock_dev"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            session_secret_key=strong_secret,
            cookie_secure=True,
            integration_mode=IntegrationMode.MOCK_DEV,
            bcrypt_rounds=12,
            cors_origins="https://admin.customshirtstudio.example",
        )

    # 5. BCRYPT_ROUNDS < 12 rejected in production
    with pytest.raises(ValidationError, match="BCRYPT_ROUNDS"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            session_secret_key=strong_secret,
            cookie_secure=True,
            integration_mode=IntegrationMode.LIVE,
            bcrypt_rounds=10,
            cors_origins="https://admin.customshirtstudio.example",
        )

    # 6. Wildcard CORS rejected in production
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            session_secret_key=strong_secret,
            cookie_secure=True,
            integration_mode=IntegrationMode.LIVE,
            bcrypt_rounds=12,
            cors_origins="*",
        )
