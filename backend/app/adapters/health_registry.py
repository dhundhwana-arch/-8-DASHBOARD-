"""Cross-module integration health registry across sibling Modules 01–07."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.adapters.base import IntegrationEnvelope, IntegrationSourceStatus
from app.adapters.module02_fabrics import FabricDashboardSummary
from app.adapters.module07_orders import OrderDashboardSummary

STAFF_VISIBLE_MODULES: frozenset[str] = frozenset({"MODULE_02", "MODULE_06", "MODULE_07"})


class ModuleIntegrationHealthItem(BaseModel):
    """Sanitized status card for one sibling module (never exposes base URLs or API keys)."""

    model_config = ConfigDict(extra="forbid")

    module_code: str
    module_name: str
    responsibility: str
    source_status: IntegrationSourceStatus
    latency_ms: int | None = None
    status_note: str


def build_integration_health_items(
    *,
    fabric_envelope: IntegrationEnvelope[FabricDashboardSummary],
    order_envelope: IntegrationEnvelope[OrderDashboardSummary],
    include_all_modules: bool = True,
) -> list[ModuleIntegrationHealthItem]:
    all_items = [
        ModuleIntegrationHealthItem(
            module_code="MODULE_01",
            module_name="custom-shirt-studio",
            responsibility="Customer accounts & storefront",
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            status_note="Customer API & shared SSO contract not yet available on main.",
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_02",
            module_name="fabric-catalog-system",
            responsibility="Fabric catalogue, variants & availability",
            source_status=fabric_envelope.source_status,
            latency_ms=fabric_envelope.latency_ms,
            status_note=(
                "Connected to verified Module 02 /api/v1 catalogue contract."
                if fabric_envelope.source_status == IntegrationSourceStatus.VERIFIED
                else (fabric_envelope.error_message or "Status reported by Module 02 adapter.")
            ),
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_03",
            module_name="2d-clothing-designer",
            responsibility="2D garment design schema (DSG-*)",
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            status_note=(
                "Read-only DSG-* v1.0.0 snapshot validator ready; no standalone admin HTTP API."
            ),
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_04",
            module_name="3d-clothing-preview",
            responsibility="3D garment preview reference",
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            status_note="Optional read-only preview reference via order snapshots.",
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_05",
            module_name="clothing-price-engine",
            responsibility="Official garment pricing & quotations",
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            status_note=(
                "Official pricing API not yet available; Module 08 performs zero local pricing."
            ),
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_06",
            module_name="measurement-guide",
            responsibility="Protected body measurement records",
            source_status=IntegrationSourceStatus.CONTRACT_UNCONFIGURED,
            status_note=(
                "Measurement API not yet available; measurements are never shown on the dashboard."
            ),
        ),
        ModuleIntegrationHealthItem(
            module_code="MODULE_07",
            module_name="tailoring-order-manager",
            responsibility="Order lifecycle & production stages",
            source_status=order_envelope.source_status,
            latency_ms=order_envelope.latency_ms,
            status_note=(
                "Connected to verified Module 07 order & workload contract."
                if order_envelope.source_status == IntegrationSourceStatus.VERIFIED
                else (order_envelope.error_message or "Status reported by Module 07 adapter.")
            ),
        ),
    ]

    if include_all_modules:
        return all_items
    return [item for item in all_items if item.module_code in STAFF_VISIBLE_MODULES]
