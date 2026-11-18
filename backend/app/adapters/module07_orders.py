"""Module 07 (Tailoring Order Manager) dashboard overview adapter.

Per Phase 04 integration boundaries:
- Keeps order metrics strictly ``CONTRACT_UNCONFIGURED`` (unavailable, never zero) by default
  until Module 07's production contract is verified and explicitly enabled.
- Supports explicit ``INTEGRATION_MODE=mock_dev`` for local development and automated tests,
  stamping responses as ``MOCK_DEV`` (`is_mock_data=True`).
- When ``MODULE_07_CONTRACT_VERIFIED=true`` and ``MODULE_07_BASE_URL`` are configured, validates
  upstream responses against Module 07's workload & order pagination schema.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, ValidationError

from app.adapters.base import (
    IntegrationEnvelope,
    SafeHttpTransport,
    UpstreamContractMismatchError,
    UpstreamTransportError,
)
from app.core.config import IntegrationMode, Settings

MODULE_07_CODE = "MODULE_07"
MODULE_07_NAME = "tailoring-order-manager"


class OrderStageCountItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_code: str
    count: int


class OrderDashboardSummary(BaseModel):
    """Order and tailoring stage counts (full vs staff-limited fields controlled by backend RBAC)."""

    model_config = ConfigDict(extra="forbid")

    # Full-view business order metrics (None when caller has dashboard:view_limited)
    total_orders: int | None
    pending_review_orders: int | None
    completed_orders: int | None
    awaiting_confirmation_orders: int | None
    cancelled_orders: int | None

    # Workshop & production stage metrics (visible to OWNER, ADMINISTRATOR, and AUTHORIZED_STAFF)
    active_orders: int
    active_production_orders: int
    in_cutting_orders: int
    in_stitching_orders: int
    in_finishing_orders: int
    quality_check_orders: int
    ready_for_delivery_orders: int
    on_hold_orders: int
    urgent_active_orders: int

    stage_breakdown: list[OrderStageCountItem]
    upstream_warnings: list[str]


class _M07EstimatedWorkload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    active_orders: StrictInt
    active_production_orders: StrictInt
    orders_awaiting_review: StrictInt
    awaiting_customer_confirmation_orders: StrictInt
    confirmed_orders: StrictInt
    orders_in_material_preparation: StrictInt
    orders_in_cutting: StrictInt
    orders_in_stitching: StrictInt
    orders_in_finishing: StrictInt
    pending_quality_checks: StrictInt
    ready_orders: StrictInt
    on_hold_orders: StrictInt
    urgent_orders: StrictInt
    completed_orders: StrictInt
    cancelled_orders: StrictInt


class _M07WorkloadPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_guaranteed_capacity: StrictBool
    estimated_workload: _M07EstimatedWorkload
    capacity_warnings: list[dict[str, Any]] = []
    scheduling_conflicts: list[dict[str, Any]] = []


class _M07OrdersPagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[dict[str, Any]]
    total: StrictInt


def _scope_order_summary(
    full_summary: OrderDashboardSummary,
    *,
    include_full_business_totals: bool,
) -> OrderDashboardSummary:
    if include_full_business_totals:
        return full_summary
    return full_summary.model_copy(
        update={
            "total_orders": None,
            "pending_review_orders": None,
            "completed_orders": None,
            "awaiting_confirmation_orders": None,
            "cancelled_orders": None,
        }
    )


class Module07OrderAdapter:
    """Adapter keeping Module 07 order metrics unavailable until its verified contract is active."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._http = SafeHttpTransport(settings=settings, transport=transport)

    def get_order_overview(
        self,
        *,
        include_full_business_totals: bool = True,
    ) -> IntegrationEnvelope[OrderDashboardSummary]:
        base_url = self._settings.module_07_base_url.strip()

        if not base_url or not self._settings.module_07_contract_verified:
            if self._settings.integration_mode == IntegrationMode.MOCK_DEV and not base_url:
                mock_full = OrderDashboardSummary(
                    total_orders=18,
                    pending_review_orders=2,
                    completed_orders=9,
                    awaiting_confirmation_orders=1,
                    cancelled_orders=0,
                    active_orders=9,
                    active_production_orders=6,
                    in_cutting_orders=1,
                    in_stitching_orders=2,
                    in_finishing_orders=1,
                    quality_check_orders=1,
                    ready_for_delivery_orders=1,
                    on_hold_orders=0,
                    urgent_active_orders=1,
                    stage_breakdown=[
                        OrderStageCountItem(stage_code="CUTTING", count=1),
                        OrderStageCountItem(stage_code="STITCHING", count=2),
                        OrderStageCountItem(stage_code="FINISHING", count=1),
                        OrderStageCountItem(stage_code="QUALITY_CHECK", count=1),
                        OrderStageCountItem(stage_code="READY_FOR_DELIVERY", count=1),
                    ],
                    upstream_warnings=[],
                )
                return IntegrationEnvelope.mock_dev(
                    module_code=MODULE_07_CODE,
                    module_name=MODULE_07_NAME,
                    data=_scope_order_summary(
                        mock_full,
                        include_full_business_totals=include_full_business_totals,
                    ),
                )

            return IntegrationEnvelope.contract_unconfigured(
                module_code=MODULE_07_CODE,
                module_name=MODULE_07_NAME,
                message=(
                    "Module 07 (Tailoring Order Manager) verified production contract is not yet "
                    "configured. Order totals and stage counts remain unavailable rather than zero."
                ),
            )

        total_latency_ms = 0
        token = self._settings.module_07_service_bearer_token.get_secret_value().strip() or None
        try:
            workload_raw, lat1 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/capacity/workload",
                bearer_token=token,
            )
            orders_raw, lat2 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/orders",
                params={"page": 1, "page_size": 1},
                bearer_token=token,
            )
            total_latency_ms = lat1 + lat2

            workload = _M07WorkloadPayload.model_validate(workload_raw)
            orders_page = _M07OrdersPagePayload.model_validate(orders_raw)
            est = workload.estimated_workload

            warnings_out: list[str] = []
            for item in workload.capacity_warnings + workload.scheduling_conflicts:
                msg = item.get("message") if isinstance(item, dict) else None
                if isinstance(msg, str) and msg.strip():
                    warnings_out.append(msg.strip()[:240])

            stage_items = [
                OrderStageCountItem(stage_code="CUTTING", count=est.orders_in_cutting),
                OrderStageCountItem(stage_code="STITCHING", count=est.orders_in_stitching),
                OrderStageCountItem(stage_code="FINISHING", count=est.orders_in_finishing),
                OrderStageCountItem(stage_code="QUALITY_CHECK", count=est.pending_quality_checks),
                OrderStageCountItem(stage_code="READY_FOR_DELIVERY", count=est.ready_orders),
                OrderStageCountItem(stage_code="ON_HOLD", count=est.on_hold_orders),
            ]

            full_summary = OrderDashboardSummary(
                total_orders=orders_page.total,
                pending_review_orders=est.orders_awaiting_review,
                completed_orders=est.completed_orders,
                awaiting_confirmation_orders=est.awaiting_customer_confirmation_orders,
                cancelled_orders=est.cancelled_orders,
                active_orders=est.active_orders,
                active_production_orders=est.active_production_orders,
                in_cutting_orders=est.orders_in_cutting,
                in_stitching_orders=est.orders_in_stitching,
                in_finishing_orders=est.orders_in_finishing,
                quality_check_orders=est.pending_quality_checks,
                ready_for_delivery_orders=est.ready_orders,
                on_hold_orders=est.on_hold_orders,
                urgent_active_orders=est.urgent_orders,
                stage_breakdown=stage_items,
                upstream_warnings=warnings_out,
            )
            return IntegrationEnvelope.verified(
                module_code=MODULE_07_CODE,
                module_name=MODULE_07_NAME,
                data=_scope_order_summary(
                    full_summary,
                    include_full_business_totals=include_full_business_totals,
                ),
                latency_ms=total_latency_ms,
            )

        except UpstreamTransportError as exc:
            return IntegrationEnvelope.unavailable(
                module_code=MODULE_07_CODE,
                module_name=MODULE_07_NAME,
                error_code=exc.error_code,
                message=exc.message,
                latency_ms=exc.latency_ms,
            )
        except (UpstreamContractMismatchError, ValidationError) as exc:
            return IntegrationEnvelope.contract_mismatch(
                module_code=MODULE_07_CODE,
                module_name=MODULE_07_NAME,
                message=(
                    f"Module 07 response did not match expected workload/orders schema: "
                    f"{exc.__class__.__name__}."
                ),
                latency_ms=total_latency_ms or None,
            )
