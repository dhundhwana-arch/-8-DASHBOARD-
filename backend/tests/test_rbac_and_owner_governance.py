"""Backend RBAC permission matrix, unauthorized rejection, and OWNER governance tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CSRF_HEADER_NAME
from app.core.errors import PermissionDeniedError
from app.core.rbac import Permission, enforce_permission, has_permission
from app.db.models import AdminAuditLog, AdminUser
from app.services.audit_service import AuditAction
from tests.conftest import (
    TEST_ADMIN_PASSWORD,
    TEST_OWNER_PASSWORD,
    TEST_STAFF_PASSWORD,
    login_and_get_csrf,
)


def test_unauthenticated_requests_rejected_across_all_protected_endpoints(
    client: TestClient,
) -> None:
    protected_gets = [
        "/api/v1/admin/auth/me",
        "/api/v1/admin/auth/sessions",
        "/api/v1/admin/rbac/permissions",
        "/api/v1/admin/users",
        "/api/v1/admin/audit-logs",
    ]
    for path in protected_gets:
        resp = client.get(path)
        assert resp.status_code == 401, f"Expected 401 on {path}, got {resp.status_code}"
        assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_service_layer_rbac_permission_matrix_for_all_three_roles(
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    owner = seeded_users["owner"]
    admin = seeded_users["admin"]
    staff = seeded_users["staff"]

    # OWNER holds every permission in Module 08
    for perm in Permission:
        assert has_permission(owner, perm) is True

    # ADMINISTRATOR cannot manage users, critical owner settings, or full security audit logs
    admin_denied = {
        Permission.USERS_MANAGE,
        Permission.SETTINGS_MANAGE_CRITICAL,
        Permission.AUDIT_VIEW_ALL,
    }
    for perm in Permission:
        expected = perm not in admin_denied
        assert has_permission(admin, perm) is expected, f"Mismatch for ADMINISTRATOR on {perm}"

    # AUTHORIZED_STAFF holds strictly operational least-privilege permissions
    staff_allowed = {
        Permission.DASHBOARD_VIEW_LIMITED,
        Permission.CUSTOMERS_VIEW_LIMITED,
        Permission.ORDERS_VIEW_ASSIGNED,
        Permission.ORDERS_TRANSITION_REQUEST,
        Permission.FABRICS_VIEW,
        Permission.MEASUREMENTS_VIEW_ASSIGNED_NEED,
        Permission.OPERATIONS_VIEW,
        Permission.REPORTS_VIEW_LIMITED,
        Permission.INTERNAL_NOTES_VIEW,
        Permission.INTERNAL_NOTES_WRITE,
    }
    for perm in Permission:
        expected = perm in staff_allowed
        assert has_permission(staff, perm) is expected, f"Mismatch for AUTHORIZED_STAFF on {perm}"

    # Service-layer enforcement raises PermissionDeniedError and writes PERMISSION_DENIED audit
    for denied_perm in (
        Permission.FABRICS_VIEW_SUPPLIERS,
        Permission.PRICING_VIEW,
        Permission.SETTINGS_VIEW,
        Permission.USERS_VIEW,
        Permission.REPORTS_EXPORT,
    ):
        with pytest.raises(PermissionDeniedError):
            enforce_permission(
                db_session,
                staff,
                denied_perm,
                resource_type="RBAC_MATRIX_TEST",
            )


def test_user_governance_enforces_owner_exclusivity_and_revokes_sessions_on_role_change(
    app_instance,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    staff_public_id = seeded_users["staff"].public_id
    owner_public_id = seeded_users["owner"].public_id

    with (
        TestClient(app_instance) as owner_client,
        TestClient(app_instance) as admin_client,
        TestClient(app_instance) as staff_client,
    ):
        owner_auth = login_and_get_csrf(owner_client, "owner_main", TEST_OWNER_PASSWORD)
        admin_auth = login_and_get_csrf(admin_client, "admin_manager", TEST_ADMIN_PASSWORD)
        staff_auth = login_and_get_csrf(staff_client, "tailor_staff", TEST_STAFF_PASSWORD)

        # 1. AUTHORIZED_STAFF cannot even list users
        assert staff_client.get("/api/v1/admin/users").status_code == 403

        # 2. ADMINISTRATOR can view user list (read-only), but CANNOT create, modify, reset, or revoke
        assert admin_client.get("/api/v1/admin/users").status_code == 200
        assert (
            admin_client.post(
                "/api/v1/admin/users",
                headers={CSRF_HEADER_NAME: admin_auth["csrf_token"]},
                json={
                    "username": "unauth_create",
                    "display_name": "Nope",
                    "password": "Valid#Password2026!",
                    "role": "AUTHORIZED_STAFF",
                    "preferred_locale": "en",
                },
            ).status_code
            == 403
        )
        assert (
            admin_client.patch(
                f"/api/v1/admin/users/{staff_public_id}",
                headers={CSRF_HEADER_NAME: admin_auth["csrf_token"]},
                json={"role": "ADMINISTRATOR"},
            ).status_code
            == 403
        )
        assert (
            admin_client.post(
                f"/api/v1/admin/users/{staff_public_id}/reset-password",
                headers={CSRF_HEADER_NAME: admin_auth["csrf_token"]},
                json={"new_password": "Reset#Password2026!"},
            ).status_code
            == 403
        )
        assert (
            admin_client.post(
                f"/api/v1/admin/users/{staff_public_id}/revoke-sessions",
                headers={CSRF_HEADER_NAME: admin_auth["csrf_token"]},
            ).status_code
            == 403
        )

        # 3. Sole active OWNER cannot demote or deactivate themselves (lockout safeguard)
        demote_self = owner_client.patch(
            f"/api/v1/admin/users/{owner_public_id}",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
            json={"role": "ADMINISTRATOR"},
        )
        assert demote_self.status_code == 409

        disable_self = owner_client.patch(
            f"/api/v1/admin/users/{owner_public_id}",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
            json={"is_active": False},
        )
        assert disable_self.status_code == 409

        # 4. OWNER can create a new staff account
        create_resp = owner_client.post(
            "/api/v1/admin/users",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
            json={
                "username": "cutter_staff",
                "display_name": "Master Cutter",
                "password": "Cutter#Workshop2026!",
                "role": "AUTHORIZED_STAFF",
                "preferred_locale": "gu",
            },
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["username"] == "cutter_staff"

        # 5. OWNER changing staff role immediately revokes that staff user's active session
        assert staff_client.get("/api/v1/admin/auth/me").status_code == 200
        role_resp = owner_client.patch(
            f"/api/v1/admin/users/{staff_public_id}",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
            json={"role": "ADMINISTRATOR"},
        )
        assert role_resp.status_code == 200
        assert role_resp.json()["role"] == "ADMINISTRATOR"

        # Existing staff_client session must now be invalid (privilege change took immediate effect)
        assert staff_client.get("/api/v1/admin/auth/me").status_code == 401
        _ = staff_auth

    role_audit = db_session.scalar(
        select(AdminAuditLog).where(
            AdminAuditLog.action_type == AuditAction.USER_ROLE_CHANGED.value
        )
    )
    assert role_audit is not None


def test_audit_log_endpoint_role_scoping(
    app_instance,
    db_session: Session,
    seeded_users: dict[str, AdminUser],
) -> None:
    from app.db.models import AuditOutcome
    from app.services.audit_service import AuditService

    # Record one operational non-security audit event alongside existing security events
    AuditService().record_event(
        db_session,
        actor=seeded_users["admin"],
        action_type="WORKSHOP_NOTE_RECORDED",
        resource_type="WORKSHOP",
        resource_id="RES-001",
        outcome=AuditOutcome.SUCCESS,
        is_security_event=False,
        change_summary={"note_ref": "NTE-001"},
    )

    with (
        TestClient(app_instance) as owner_client,
        TestClient(app_instance) as admin_client,
        TestClient(app_instance) as staff_client,
    ):
        login_and_get_csrf(owner_client, "owner_main", TEST_OWNER_PASSWORD)
        login_and_get_csrf(admin_client, "admin_manager", TEST_ADMIN_PASSWORD)
        login_and_get_csrf(staff_client, "tailor_staff", TEST_STAFF_PASSWORD)

        # Staff denied
        assert staff_client.get("/api/v1/admin/audit-logs").status_code == 403

        # Administrator sees only operational events (is_security_event == False)
        admin_logs = admin_client.get("/api/v1/admin/audit-logs")
        assert admin_logs.status_code == 200
        items_admin = admin_logs.json()["items"]
        assert len(items_admin) >= 1
        assert all(item["is_security_event"] is False for item in items_admin)

        # Administrator explicitly asking for security events is denied (403)
        admin_sec_attempt = admin_client.get(
            "/api/v1/admin/audit-logs?include_security_events=true"
        )
        assert admin_sec_attempt.status_code == 403

        # Owner sees full audit history including security events
        owner_logs = owner_client.get("/api/v1/admin/audit-logs")
        assert owner_logs.status_code == 200
        items_owner = owner_logs.json()["items"]
        assert any(item["is_security_event"] is True for item in items_owner)
        assert any(item["is_security_event"] is False for item in items_owner)


def test_owner_password_reset_session_revocation_and_rbac_metadata_endpoints(
    app_instance,
    seeded_users: dict[str, AdminUser],
) -> None:
    admin_public_id = seeded_users["admin"].public_id
    staff_public_id = seeded_users["staff"].public_id

    with (
        TestClient(app_instance) as owner_client,
        TestClient(app_instance) as admin_client,
        TestClient(app_instance) as staff_client,
    ):
        owner_auth = login_and_get_csrf(owner_client, "owner_main", TEST_OWNER_PASSWORD)
        login_and_get_csrf(admin_client, "admin_manager", TEST_ADMIN_PASSWORD)
        login_and_get_csrf(staff_client, "tailor_staff", TEST_STAFF_PASSWORD)

        # RBAC metadata visibility per role
        owner_rbac = owner_client.get("/api/v1/admin/rbac/permissions").json()
        admin_rbac = admin_client.get("/api/v1/admin/rbac/permissions").json()
        staff_rbac = staff_client.get("/api/v1/admin/rbac/permissions").json()
        assert owner_rbac["role_matrix"] is not None
        assert admin_rbac["role_matrix"] is not None
        assert staff_rbac["role_matrix"] is None

        # User detail read permissions
        assert owner_client.get(f"/api/v1/admin/users/{admin_public_id}").status_code == 200
        assert admin_client.get(f"/api/v1/admin/users/{staff_public_id}").status_code == 200
        assert staff_client.get(f"/api/v1/admin/users/{admin_public_id}").status_code == 403

        # Owner revokes all sessions of admin_manager
        rev_resp = owner_client.post(
            f"/api/v1/admin/users/{admin_public_id}/revoke-sessions",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
        )
        assert rev_resp.status_code == 200
        assert rev_resp.json()["revoked_count"] == 1
        assert admin_client.get("/api/v1/admin/auth/me").status_code == 401

        # Owner resets password of tailor_staff -> invalidates staff session & sets new password
        reset_pw = "BrandNewStaff#2026!"
        reset_resp = owner_client.post(
            f"/api/v1/admin/users/{staff_public_id}/reset-password",
            headers={CSRF_HEADER_NAME: owner_auth["csrf_token"]},
            json={"new_password": reset_pw},
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["revoked_sessions_count"] == 1
        assert staff_client.get("/api/v1/admin/auth/me").status_code == 401

        # Staff can now sign in with the newly reset password
        relogin = staff_client.post(
            "/api/v1/admin/auth/login",
            json={"username": "tailor_staff", "password": reset_pw},
        )
        assert relogin.status_code == 200

