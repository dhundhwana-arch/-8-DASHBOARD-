"""Authentication, session lifecycle, cookie attributes, CSRF rejection, and rate-limiting tests."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CSRF_HEADER_NAME
from app.db.models import AdminAuditLog, AdminSession, AdminUser, utcnow
from app.services.audit_service import AuditAction
from tests.conftest import (
    TEST_ADMIN_PASSWORD,
    TEST_OWNER_PASSWORD,
    TEST_STAFF_PASSWORD,
    login_and_get_csrf,
)


def test_login_sets_secure_httponly_cookie_and_hashes_tokens_at_rest(
    client: TestClient,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    resp = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "owner_main", "password": TEST_OWNER_PASSWORD},
    )
    assert resp.status_code == 200
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "css_admin_session=" in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header
    assert "Path=/api/v1/admin" in set_cookie_header

    payload = resp.json()
    assert payload["auth_federation_status"] == "STANDALONE_LOCAL"
    assert payload["user"]["username"] == "owner_main"
    assert payload["user"]["role"] == "OWNER"
    assert "password_hash" not in payload["user"]
    assert "token_hash" not in payload["session"]
    assert len(payload["csrf_token"]) == 64

    raw_cookie = client.cookies.get("css_admin_session")
    assert raw_cookie is not None

    session_row = db_session.scalar(
        select(AdminSession).where(AdminSession.session_id == payload["session"]["session_id"])
    )
    assert session_row is not None
    # Raw tokens must NEVER be stored in the database
    assert session_row.token_hash != raw_cookie
    assert session_row.csrf_token_hash != payload["csrf_token"]
    assert len(session_row.token_hash) == 64
    assert len(session_row.csrf_token_hash) == 64


def test_generic_login_error_does_not_reveal_account_existence_or_status(
    client: TestClient,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    # Deactivate staff account to verify disabled accounts also return the exact same generic message
    staff = seeded_users["staff"]
    staff.is_active = False
    db_session.commit()

    resp_unknown = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "nonexistent_person", "password": "SomePassword#1234"},
    )
    resp_wrong_pw = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin_manager", "password": "WrongPassword#1234"},
    )
    resp_inactive = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "tailor_staff", "password": TEST_STAFF_PASSWORD},
    )

    assert resp_unknown.status_code == 401
    assert resp_wrong_pw.status_code == 401
    assert resp_inactive.status_code == 401

    err_unknown = resp_unknown.json()["error"]
    err_wrong_pw = resp_wrong_pw.json()["error"]
    err_inactive = resp_inactive.json()["error"]

    assert err_unknown["code"] == err_wrong_pw["code"] == err_inactive["code"] == "INVALID_CREDENTIALS"
    assert (
        err_unknown["message"]
        == err_wrong_pw["message"]
        == err_inactive["message"]
        == "Invalid username or password."
    )


def test_logout_invalidates_session_and_rejects_cookie_replay(
    client: TestClient,
    seeded_users: dict[str, AdminUser],
) -> None:
    auth_data = login_and_get_csrf(client, "admin_manager", TEST_ADMIN_PASSWORD)
    captured_cookie = client.cookies.get("css_admin_session")
    assert captured_cookie is not None

    me_ok = client.get("/api/v1/admin/auth/me")
    assert me_ok.status_code == 200

    logout_resp = client.post(
        "/api/v1/admin/auth/logout",
        headers={CSRF_HEADER_NAME: auth_data["csrf_token"]},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # Replay captured session cookie after logout -> must be rejected as 401 SESSION_EXPIRED
    client.cookies.set("css_admin_session", captured_cookie, path="/api/v1/admin")
    replay_resp = client.get("/api/v1/admin/auth/me")
    assert replay_resp.status_code == 401
    assert replay_resp.json()["error"]["code"] == "SESSION_EXPIRED"


def test_session_absolute_ttl_and_idle_timeout_expiration(
    client: TestClient,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    # 1. Absolute TTL expiration
    auth_1 = login_and_get_csrf(client, "owner_main", TEST_OWNER_PASSWORD)
    s1 = db_session.scalar(
        select(AdminSession).where(AdminSession.session_id == auth_1["session"]["session_id"])
    )
    assert s1 is not None
    s1.expires_at = utcnow() - timedelta(seconds=5)
    db_session.commit()

    resp_ttl = client.get("/api/v1/admin/auth/me")
    assert resp_ttl.status_code == 401
    assert resp_ttl.json()["error"]["code"] == "SESSION_EXPIRED"

    # 2. Idle timeout expiration
    auth_2 = login_and_get_csrf(client, "owner_main", TEST_OWNER_PASSWORD)
    s2 = db_session.scalar(
        select(AdminSession).where(AdminSession.session_id == auth_2["session"]["session_id"])
    )
    assert s2 is not None
    s2.last_seen_at = utcnow() - timedelta(minutes=45)  # test idle timeout = 30 min
    db_session.commit()

    resp_idle = client.get("/api/v1/admin/auth/me")
    assert resp_idle.status_code == 401
    assert resp_idle.json()["error"]["code"] == "SESSION_EXPIRED"

    expired_events = list(
        db_session.scalars(
            select(AdminAuditLog).where(
                AdminAuditLog.action_type == AuditAction.AUTH_SESSION_EXPIRED.value
            )
        ).all()
    )
    assert len(expired_events) == 2


def test_csrf_rejection_on_missing_or_forged_token_logs_security_event(
    client: TestClient,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    login_and_get_csrf(client, "owner_main", TEST_OWNER_PASSWORD)

    # Missing X-CSRF-Token header
    no_csrf_resp = client.post("/api/v1/admin/auth/logout")
    assert no_csrf_resp.status_code == 403
    assert no_csrf_resp.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

    # Forged X-CSRF-Token header
    bad_csrf_resp = client.post(
        "/api/v1/admin/users",
        headers={CSRF_HEADER_NAME: "0" * 64},
        json={
            "username": "forged_staff",
            "display_name": "Forged",
            "password": "Forged#Password2026!",
            "role": "AUTHORIZED_STAFF",
            "preferred_locale": "en",
        },
    )
    assert bad_csrf_resp.status_code == 403
    assert bad_csrf_resp.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

    csrf_audits = list(
        db_session.scalars(
            select(AdminAuditLog).where(
                AdminAuditLog.action_type == AuditAction.CSRF_REJECTED.value
            )
        ).all()
    )
    assert len(csrf_audits) == 2


def test_login_rate_limiting_blocks_brute_force_and_audits(
    client: TestClient,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    # Configured max_attempts=4 in test_settings
    for _ in range(4):
        fail_resp = client.post(
            "/api/v1/admin/auth/login",
            json={"username": "owner_main", "password": "BadPassword#9999"},
        )
        assert fail_resp.status_code == 401

    limited_resp = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "owner_main", "password": TEST_OWNER_PASSWORD},
    )
    assert limited_resp.status_code == 429
    assert limited_resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(limited_resp.headers["Retry-After"]) >= 1

    rl_audit = db_session.scalar(
        select(AdminAuditLog).where(
            AdminAuditLog.action_type == AuditAction.AUTH_LOGIN_RATE_LIMITED.value
        )
    )
    assert rl_audit is not None
    assert rl_audit.outcome == "DENIED"


def test_self_password_change_revokes_other_sessions_and_preserves_current(
    app_instance,
    seeded_users: dict[str, AdminUser],
) -> None:
    with TestClient(app_instance) as client_a, TestClient(app_instance) as client_b:
        auth_a = login_and_get_csrf(client_a, "admin_manager", TEST_ADMIN_PASSWORD)
        login_and_get_csrf(client_b, "admin_manager", TEST_ADMIN_PASSWORD)

        new_pw = "UpdatedAdmin#2026!"
        change_resp = client_a.post(
            "/api/v1/admin/auth/password",
            headers={CSRF_HEADER_NAME: auth_a["csrf_token"]},
            json={
                "current_password": TEST_ADMIN_PASSWORD,
                "new_password": new_pw,
            },
        )
        assert change_resp.status_code == 200
        assert change_resp.json()["revoked_sessions_count"] == 1

        # Current session (client_a) stays active
        assert client_a.get("/api/v1/admin/auth/me").status_code == 200
        # Other session (client_b) is immediately revoked
        assert client_b.get("/api/v1/admin/auth/me").status_code == 401


def test_session_list_manual_revoke_and_cross_user_isolation(
    app_instance,
    seeded_users: dict[str, AdminUser],
) -> None:
    with (
        TestClient(app_instance) as owner_client_1,
        TestClient(app_instance) as owner_client_2,
        TestClient(app_instance) as staff_client,
    ):
        health = owner_client_1.get("/api/v1/admin/health")
        assert health.status_code == 200
        assert health.json()["auth_federation_status"] == "STANDALONE_LOCAL"

        owner_auth_1 = login_and_get_csrf(owner_client_1, "owner_main", TEST_OWNER_PASSWORD)
        owner_auth_2 = login_and_get_csrf(owner_client_2, "owner_main", TEST_OWNER_PASSWORD)
        staff_auth = login_and_get_csrf(staff_client, "tailor_staff", TEST_STAFF_PASSWORD)

        sessions_resp = owner_client_1.get("/api/v1/admin/auth/sessions")
        assert sessions_resp.status_code == 200
        assert len(sessions_resp.json()) == 2

        # Staff user CANNOT revoke the owner's session via /auth/sessions/{id}/revoke
        cross_attempt = staff_client.post(
            f"/api/v1/admin/auth/sessions/{owner_auth_2['session']['session_id']}/revoke",
            headers={CSRF_HEADER_NAME: staff_auth["csrf_token"]},
        )
        assert cross_attempt.status_code == 404
        assert owner_client_2.get("/api/v1/admin/auth/me").status_code == 200

        # Owner revoking their second session succeeds and invalidates owner_client_2
        revoke_resp = owner_client_1.post(
            f"/api/v1/admin/auth/sessions/{owner_auth_2['session']['session_id']}/revoke",
            headers={CSRF_HEADER_NAME: owner_auth_1["csrf_token"]},
        )
        assert revoke_resp.status_code == 200
        assert owner_client_2.get("/api/v1/admin/auth/me").status_code == 401
        assert owner_client_1.get("/api/v1/admin/auth/me").status_code == 200

