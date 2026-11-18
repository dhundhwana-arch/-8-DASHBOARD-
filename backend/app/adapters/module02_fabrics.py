"""Module 02 (Fabric Catalog System) adapter bound strictly to its verified `/api/v1` contract."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, ValidationError

from app.adapters.base import (
    IntegrationEnvelope,
    SafeHttpTransport,
    UpstreamContractMismatchError,
    UpstreamTransportError,
)
from app.core.config import IntegrationMode, Settings

MODULE_02_CODE = "MODULE_02"
MODULE_02_NAME = "fabric-catalog-system"

VERIFIED_AVAILABILITY_STATUSES: frozenset[str] = frozenset(
    {
        "AVAILABLE",
        "LOW_STOCK",
        "OUT_OF_STOCK",
        "ON_REQUEST",
        "DISCONTINUED",
        "UNKNOWN",
    }
)


class _M02FabricListItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt
    fabric_id: str
    fabric_name: str
    sourcing_method: str
    is_active: StrictBool


class _M02PaginatedFabrics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[_M02FabricListItem]
    total: StrictInt
    page: StrictInt
    page_size: StrictInt
    pages: StrictInt


class _M02CategoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt
    category_id: str
    name: str
    is_active: StrictBool


class _M02ColourItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    colour_name: str
    colour_hex: str
    variant_count: StrictInt
    available_variant_count: StrictInt


class _M02VariantItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt
    variant_id: str
    fabric_id: StrictInt
    colour_name: str
    colour_hex: str
    availability_status: str
    is_active: StrictBool


class _M02PaginatedVariants(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[_M02VariantItem]
    total: StrictInt
    page: StrictInt
    page_size: StrictInt
    pages: StrictInt


class FabricDashboardSummary(BaseModel):
    """Verified public fabric catalogue summary (never invents physical inventory quantities)."""

    model_config = ConfigDict(extra="forbid")

    total_active_fabrics: int
    total_active_categories: int
    total_distinct_colours: int
    total_variants: int
    available_variants: int | None
    low_stock_variants: int | None
    out_of_stock_variants: int | None
    on_request_variants: int | None
    discontinued_variants: int | None
    unknown_status_variants: int | None
    is_variant_breakdown_complete: bool


class Module02FabricAdapter:
    """Consumes verified Module 02 public read endpoints under `/api/v1`."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._http = SafeHttpTransport(settings=settings, transport=transport)

    def get_catalogue_overview(
        self,
        *,
        include_full_breakdown: bool = True,
    ) -> IntegrationEnvelope[FabricDashboardSummary]:
        base_url = self._settings.module_02_base_url.strip()

        if not base_url:
            if self._settings.integration_mode == IntegrationMode.MOCK_DEV:
                mock_summary = FabricDashboardSummary(
                    total_active_fabrics=6,
                    total_active_categories=3,
                    total_distinct_colours=9,
                    total_variants=14,
                    available_variants=10,
                    low_stock_variants=2 if include_full_breakdown else None,
                    out_of_stock_variants=1,
                    on_request_variants=1 if include_full_breakdown else None,
                    discontinued_variants=0 if include_full_breakdown else None,
                    unknown_status_variants=0 if include_full_breakdown else None,
                    is_variant_breakdown_complete=True,
                )
                return IntegrationEnvelope.mock_dev(
                    module_code=MODULE_02_CODE,
                    module_name=MODULE_02_NAME,
                    data=mock_summary,
                )

            return IntegrationEnvelope.contract_unconfigured(
                module_code=MODULE_02_CODE,
                module_name=MODULE_02_NAME,
                message=(
                    "MODULE_02_BASE_URL is not configured. Connect Module 02 "
                    "(fabric-catalog-system /api/v1) to view live catalogue counts."
                ),
            )

        total_latency_ms = 0
        try:
            fabrics_raw, lat1 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/fabrics",
                params={"page": 1, "page_size": 20},
            )
            categories_raw, lat2 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/categories",
            )
            colours_raw, lat3 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/colours",
            )
            variants_raw, lat4 = self._http.get_json(
                base_url=base_url,
                path="/api/v1/variants",
                params={"page": 1, "page_size": 100},
            )
            total_latency_ms = lat1 + lat2 + lat3 + lat4

            fabrics_page = _M02PaginatedFabrics.model_validate(fabrics_raw)
            if not isinstance(categories_raw, list) or not isinstance(colours_raw, list):
                raise UpstreamContractMismatchError(
                    "Module 02 /categories or /colours did not return a JSON array.",
                    latency_ms=total_latency_ms,
                )
            categories = [_M02CategoryItem.model_validate(c) for c in categories_raw]
            colours = [_M02ColourItem.model_validate(col) for col in colours_raw]
            first_variants_page = _M02PaginatedVariants.model_validate(variants_raw)

            collected_variants = list(first_variants_page.items)
            max_pages_to_scan = min(first_variants_page.pages, 5)
            for next_page in range(2, max_pages_to_scan + 1):
                page_raw, lat_next = self._http.get_json(
                    base_url=base_url,
                    path="/api/v1/variants",
                    params={"page": next_page, "page_size": 100},
                )
                total_latency_ms += lat_next
                parsed_next = _M02PaginatedVariants.model_validate(page_raw)
                collected_variants.extend(parsed_next.items)

            complete_breakdown = first_variants_page.pages <= 5
            counts: dict[str, int] = {key: 0 for key in VERIFIED_AVAILABILITY_STATUSES}
            for variant in collected_variants:
                status_upper = variant.availability_status.strip().upper()
                if status_upper not in VERIFIED_AVAILABILITY_STATUSES:
                    raise UpstreamContractMismatchError(
                        "Unexpected Module 02 variant availability_status "
                        f"'{variant.availability_status}'.",
                        latency_ms=total_latency_ms,
                    )
                counts[status_upper] += 1

            summary = FabricDashboardSummary(
                total_active_fabrics=fabrics_page.total,
                total_active_categories=sum(1 for cat in categories if cat.is_active),
                total_distinct_colours=len(colours),
                total_variants=first_variants_page.total,
                available_variants=counts["AVAILABLE"] if complete_breakdown else None,
                low_stock_variants=(
                    counts["LOW_STOCK"] if (complete_breakdown and include_full_breakdown) else None
                ),
                out_of_stock_variants=counts["OUT_OF_STOCK"] if complete_breakdown else None,
                on_request_variants=(
                    counts["ON_REQUEST"] if (complete_breakdown and include_full_breakdown) else None
                ),
                discontinued_variants=(
                    counts["DISCONTINUED"] if (complete_breakdown and include_full_breakdown) else None
                ),
                unknown_status_variants=(
                    counts["UNKNOWN"] if (complete_breakdown and include_full_breakdown) else None
                ),
                is_variant_breakdown_complete=complete_breakdown,
            )
            return IntegrationEnvelope.verified(
                module_code=MODULE_02_CODE,
                module_name=MODULE_02_NAME,
                data=summary,
                latency_ms=total_latency_ms,
            )

        except UpstreamTransportError as exc:
            return IntegrationEnvelope.unavailable(
                module_code=MODULE_02_CODE,
                module_name=MODULE_02_NAME,
                error_code=exc.error_code,
                message=exc.message,
                latency_ms=exc.latency_ms,
            )
        except (UpstreamContractMismatchError, ValidationError) as exc:
            return IntegrationEnvelope.contract_mismatch(
                module_code=MODULE_02_CODE,
                module_name=MODULE_02_NAME,
                message=(
                    "Module 02 response did not match verified /api/v1 schema: "
                    f"{exc.__class__.__name__}."
                ),
                latency_ms=total_latency_ms or None,
            )
