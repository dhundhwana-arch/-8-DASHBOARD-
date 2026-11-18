"""Phase 04 Admin Dashboard Overview backend tests (RBAC, 5-state provenance, fault isolation)."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.module02_fabrics import Module02FabricAdapter
from app.adapters.module03_designs import summarize_design_snapshot
from app.adapters.module07_orders import Module07OrderAdapter
from app.core.config import IntegrationMode, Settings
from app.db.models import AdminAuditLog, AdminUser
from app.services.audit_service import AuditAction
from tests.conftest import (
    TEST_ADMIN_PASSWORD,
    TEST_OWNER_PASSWORD,
    TEST_STAFF_PASSWORD,
    login_and_get_csrf,
)

FORBIDDEN_DASHBOARD_KEYS: frozenset[str] = frozenset(
    {
        "revenue",
        "profit",
        "expenses",
        "sales",
        "supplier_name",
        "procurement_price",
        "stock_quantity",
        "employee_productivity",
        "daily_production_total",
        "phone",
        "phone_e164",
        "measurements",
        "chest",
        "waist",
        "module_02_admin_api_key",
        "session_secret_key",
    }
)


def _collect_all_json_keys(node: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(str(k).lower())
            keys.update(_collect_all_json_keys(v))
    elif isinstance(node, list):
        for item in node:
            keys.update(_collect_all_json_keys(item))
    return keys


def test_dashboard_routes_reject_unauthenticated_requests(client: TestClient) -> None:
    assert client.get("/api/v1/admin/dashboard/overview").status_code == 401
    assert client.get("/api/v1/admin/dashboard/integrations").status_code == 401


def test_default_live_mode_reports_contract_unconfigured_never_fake_zeros(
    client: TestClient,
    test_settings: Settings,
    seeded_users: dict[str, AdminUser],
) -> None:
    login_and_get_csrf(client, "owner_main", TEST_OWNER_PASSWORD)
    resp = client.get("/api/v1/admin/dashboard/overview")
    assert resp.status_code == 200
    body = resp.json()

    assert body["access_scope"] == "FULL"
    assert body["integration_mode"] == "live"
    assert body["has_mock_data"] is False

    # Module 07 & Module 02 are unconfigured -> data MUST be null, NEVER misleading zeros
    assert body["order_overview"]["source_status"] == "CONTRACT_UNCONFIGURED"
    assert body["order_overview"]["is_verified_live"] is False
    assert body["order_overview"]["data"] is None

    assert body["fabric_overview"]["source_status"] == "CONTRACT_UNCONFIGURED"
    assert body["fabric_overview"]["is_verified_live"] is False
    assert body["fabric_overview"]["data"] is None

    # Zero invented financial, supplier, customer PII, measurement, or secret keys
    all_keys = _collect_all_json_keys(body)
    assert all_keys.isdisjoint(FORBIDDEN_DASHBOARD_KEYS)
    assert test_settings.module_02_admin_api_key.get_secret_value() not in resp.text


def test_role_based_dashboard_behavior_owner_admin_and_staff(
    app_instance,
    db_session: Session,
    test_settings: Settings,
    seeded_users: dict[str, AdminUser],
) -> None:
    # Configure mock_dev on a copy of settings to verify FULL vs LIMITED field scoping
    mock_settings = test_settings.model_copy(update={"integration_mode": IntegrationMode.MOCK_DEV})
    app_instance.state.settings = mock_settings
    app_instance.state.fabric_adapter = Module02FabricAdapter(settings=mock_settings)
    app_instance.state.order_adapter = Module07OrderAdapter(settings=mock_settings)

    with (
        TestClient(app_instance) as owner_client,
        TestClient(app_instance) as admin_client,
        TestClient(app_instance) as staff_client,
    ):
        login_and_get_csrf(owner_client, "owner_main", TEST_OWNER_PASSWORD)
        login_and_get_csrf(admin_client, "admin_manager", TEST_ADMIN_PASSWORD)
        login_and_get_csrf(staff_client, "tailor_staff", TEST_STAFF_PASSWORD)

        owner_data = owner_client.get("/api/v1/admin/dashboard/overview").json()
        admin_data = admin_client.get("/api/v1/admin/dashboard/overview").json()
        staff_data = staff_client.get("/api/v1/admin/dashboard/overview").json()

        # 1. Mock warning flag and MOCK_DEV source_status visible to all roles
        assert owner_data["has_mock_data"] is True
        assert owner_data["order_overview"]["source_status"] == "MOCK_DEV"
        assert any(
            a["alert_code"] == "MOCK_DEV_MODE_ACTIVE" for a in owner_data["operational_alerts"]
        )

        # 2. OWNER gets FULL scope + security_events_last_24h_count
        assert owner_data["access_scope"] == "FULL"
        assert len(owner_data["integration_health"]) == 7
        assert owner_data["governance_summary"]["security_events_last_24h_count"] is not None
        assert owner_data["order_overview"]["data"]["total_orders"] == 18

        # 3. ADMINISTRATOR gets FULL operational scope, but owner-only security counter is None
        assert admin_data["access_scope"] == "FULL"
        assert len(admin_data["integration_health"]) == 7
        assert admin_data["governance_summary"]["security_events_last_24h_count"] is None
        assert owner_client.get("/api/v1/admin/dashboard/integrations").status_code == 200
        assert admin_client.get("/api/v1/admin/dashboard/integrations").status_code == 200

        # 4. AUTHORIZED_STAFF gets LIMITED scope enforced on the BACKEND
        assert staff_data["access_scope"] == "LIMITED"
        assert staff_data["governance_summary"] is None
        assert staff_data["recent_activity"] is None
        assert len(staff_data["integration_health"]) == 3
        # Business-wide order totals redacted for staff while workshop stage counts remain
        assert staff_data["order_overview"]["data"]["total_orders"] is None
        assert staff_data["order_overview"]["data"]["completed_orders"] is None
        assert staff_data["order_overview"]["data"]["in_stitching_orders"] == 2

        # AUTHORIZED_STAFF attempting full integrations endpoint is rejected (403) + audited
        denied_resp = staff_client.get("/api/v1/admin/dashboard/integrations")
        assert denied_resp.status_code == 403
        assert denied_resp.json()["error"]["code"] == "PERMISSION_DENIED"

    denied_audit = db_session.scalar(
        select(AdminAuditLog).where(
            AdminAuditLog.action_type == AuditAction.PERMISSION_DENIED.value,
            AdminAuditLog.resource_type == "DASHBOARD_INTEGRATIONS",
        )
    )
    assert denied_audit is not None


def test_module02_verified_retry_unavailable_and_contract_mismatch_states(
    app_instance,
    test_settings: Settings,
    seeded_users: dict[str, AdminUser],
) -> None:
    live_m02_settings = test_settings.model_copy(
        update={"module_02_base_url": "http://module02.internal"}
    )
    app_instance.state.settings = live_m02_settings

    # Case A: Transient 503 on first GET recovers on retry -> VERIFIED
    calls = {"fabrics": 0}

    def _verified_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/fabrics":
            calls["fabrics"] += 1
            if calls["fabrics"] == 1:
                return httpx.Response(503, json={"detail": "Temporary overload"})
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": 1,
                            "fabric_id": "FAB-001",
                            "fabric_name": "Giza Poplin",
                            "sourcing_method": "BUSINESS_INVENTORY",
                            "is_active": True,
                        }
                    ],
                    "total": 4,
                    "page": 1,
                    "page_size": 20,
                    "pages": 1,
                },
            )
        if request.url.path == "/api/v1/categories":
            return httpx.Response(
                200,
                json=[
                    {"id": 1, "category_id": "FCAT-001", "name": "Cotton", "is_active": True},
                    {"id": 2, "category_id": "FCAT-002", "name": "Linen", "is_active": True},
                ],
            )
        if request.url.path == "/api/v1/colours":
            return httpx.Response(
                200,
                json=[
                    {
                        "colour_name": "White",
                        "colour_hex": "#FFFFFF",
                        "variant_count": 3,
                        "available_variant_count": 2,
                    }
                ],
            )
        if request.url.path == "/api/v1/variants":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": 1,
                            "variant_id": "FVAR-001",
                            "fabric_id": 1,
                            "colour_name": "White",
                            "colour_hex": "#FFFFFF",
                            "availability_status": "AVAILABLE",
                            "is_active": True,
                        },
                        {
                            "id": 2,
                            "variant_id": "FVAR-002",
                            "fabric_id": 1,
                            "colour_name": "Navy",
                            "colour_hex": "#000080",
                            "availability_status": "LOW_STOCK",
                            "is_active": True,
                        },
                    ],
                    "total": 2,
                    "page": 1,
                    "page_size": 100,
                    "pages": 1,
                },
            )
        return httpx.Response(404)

    app_instance.state.fabric_adapter = Module02FabricAdapter(
        settings=live_m02_settings,
        transport=httpx.MockTransport(_verified_handler),
    )
    app_instance.state.order_adapter = Module07OrderAdapter(settings=live_m02_settings)

    with TestClient(app_instance) as client:
        login_and_get_csrf(client, "owner_main", TEST_OWNER_PASSWORD)
        ok_body = client.get("/api/v1/admin/dashboard/overview").json()
        assert ok_body["fabric_overview"]["source_status"] == "VERIFIED"
        assert ok_body["fabric_overview"]["is_verified_live"] is True
        assert ok_body["fabric_overview"]["data"]["total_active_fabrics"] == 4
        assert ok_body["fabric_overview"]["data"]["available_variants"] == 1
        assert ok_body["fabric_overview"]["data"]["low_stock_variants"] == 1
        assert ok_body["fabric_overview"]["data"]["out_of_stock_variants"] == 0
        # Order overview stays CONTRACT_UNCONFIGURED while Module 02 is VERIFIED (fault isolation)
        assert ok_body["order_overview"]["source_status"] == "CONTRACT_UNCONFIGURED"

        # Case B: Upstream timeout -> UNAVAILABLE (does not crash dashboard!)
        def _timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Timed out reading Module 02", request=request)

        app_instance.state.fabric_adapter = Module02FabricAdapter(
            settings=live_m02_settings,
            transport=httpx.MockTransport(_timeout_handler),
        )
        unavail_resp = client.get("/api/v1/admin/dashboard/overview")
        assert unavail_resp.status_code == 200
        unavail_body = unavail_resp.json()
        assert unavail_body["fabric_overview"]["source_status"] == "UNAVAILABLE"
        assert unavail_body["fabric_overview"]["data"] is None
        assert any(
            a["alert_code"] == "MODULE_02_UNAVAILABLE"
            for a in unavail_body["operational_alerts"]
        )

        # Case C: Schema violation -> CONTRACT_MISMATCH
        def _mismatch_handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected_shape": "invalid"})

        app_instance.state.fabric_adapter = Module02FabricAdapter(
            settings=live_m02_settings,
            transport=httpx.MockTransport(_mismatch_handler),
        )
        mismatch_resp = client.get("/api/v1/admin/dashboard/overview")
        assert mismatch_resp.status_code == 200
        mismatch_body = mismatch_resp.json()
        assert mismatch_body["fabric_overview"]["source_status"] == "CONTRACT_MISMATCH"
        assert mismatch_body["fabric_overview"]["data"] is None


def test_module03_design_snapshot_readonly_helper() -> None:
    valid_snapshot = {
        "design_id": "DSG-A1B2C3D4",
        "schema_version": "1.0.0",
        "product_type": "shirt",
        "fabric": {"fabric_id": "FAB-001"},
        "components": {
            "collar": {"style": "mandarin"},
            "sleeves": {"style": "full"},
            "cuffs": {"style": "button"},
            "fit": {"type": "regular"},
        },
    }
    summary = summarize_design_snapshot(valid_snapshot)
    assert summary is not None
    assert summary.design_id == "DSG-A1B2C3D4"
    assert summary.collar_style == "mandarin"
    assert summarize_design_snapshot({"design_id": "BAD-ID"}) is None
    assert summarize_design_snapshot(None) is None


def test_module07_contract_gate_and_verified_order_adapter(
    test_settings: Settings,
) -> None:
    # 1. URL set, but module_07_contract_verified=False -> stays CONTRACT_UNCONFIGURED
    unverified_m07 = test_settings.model_copy(
        update={
            "module_07_base_url": "http://module07.internal",
            "module_07_contract_verified": False,
        }
    )
    unverified_env = Module07OrderAdapter(settings=unverified_m07).get_order_overview()
    assert unverified_env.source_status == "CONTRACT_UNCONFIGURED"
    assert unverified_env.data is None

    # 2. Explicitly opted-in verified contract -> VERIFIED
    verified_m07 = test_settings.model_copy(
        update={
            "module_07_base_url": "http://module07.internal",
            "module_07_contract_verified": True,
        }
    )

    def _m07_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/capacity/workload":
            return httpx.Response(
                200,
                json={
                    "is_guaranteed_capacity": False,
                    "estimated_workload": {
                        "active_orders": 3,
                        "active_production_orders": 2,
                        "orders_awaiting_review": 0,
                        "awaiting_customer_confirmation_orders": 0,
                        "confirmed_orders": 0,
                        "orders_in_material_preparation": 0,
                        "orders_in_cutting": 0,
                        "orders_in_stitching": 2,
                        "orders_in_finishing": 0,
                        "pending_quality_checks": 0,
                        "ready_orders": 1,
                        "on_hold_orders": 0,
                        "urgent_orders": 1,
                        "completed_orders": 5,
                        "cancelled_orders": 0,
                    },
                    "capacity_warnings": [{"message": "Advisory workload check"}],
                    "scheduling_conflicts": [],
                },
            )
        if request.url.path == "/api/v1/orders":
            return httpx.Response(
                200,
                json={"items": [], "total": 8, "page": 1, "page_size": 1, "pages": 8},
            )
        return httpx.Response(404)

    verified_env = Module07OrderAdapter(
        settings=verified_m07,
        transport=httpx.MockTransport(_m07_handler),
    ).get_order_overview(include_full_business_totals=True)
    assert verified_env.source_status == "VERIFIED"
    assert verified_env.data is not None
    assert verified_env.data.total_orders == 8
    assert verified_env.data.completed_orders == 5
    assert verified_env.data.cancelled_orders == 0
    assert verified_env.data.in_stitching_orders == 2
    assert verified_env.data.upstream_warnings == ["Advisory workload check"]

    # 3. Malformed Module 07 payload -> CONTRACT_MISMATCH (data=None)
    mismatch_env = Module07OrderAdapter(
        settings=verified_m07,
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(200, json={"is_guaranteed_capacity": False})
        ),
    ).get_order_overview()
    assert mismatch_env.source_status == "CONTRACT_MISMATCH"
    assert mismatch_env.data is None

