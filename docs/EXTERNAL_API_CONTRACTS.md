# EXTERNAL API CONTRACTS & ADAPTER SPECIFICATION — MODULE 08

| Field | Value |
|---|---|
| **Project** | CUSTOM SHIRT STUDIO |
| **Module** | 08 / 08 — Small Business Admin Dashboard (`dhundhwana-arch/-8-DASHBOARD-`) |
| **Inspection Date** | `2026-11-16` |
| **Status** | Phase 02 Baseline — Verified Against Live GitHub Repositories |

---

## 1. Cross-Module GitHub Contract Registry

Every sibling repository under `https://github.com/dhundhwana-arch/` was inspected directly before defining Module 08's adapter layer. Module 08 **never invents production endpoints** for modules whose contracts do not yet exist.

| Module | GitHub Repository | `main` Commit SHA | Inspected Dev Branch & SHA | Contract Verification Status | Module 08 Production Default (`INTEGRATION_MODE=live`) |
|---|---|---|---|---|---|
| **01 — Customer Platform** | `custom-shirt-studio` | `8ebb2e65e4b3...` (Scaffold) | *None* | **MISSING / BLOCKED** | `CONTRACT_UNCONFIGURED` (unless verified URL configured) |
| **02 — Fabric Catalogue** | `fabric-catalog-system` | `6524f79dc9a9...` (Scaffold) | `arena/9fb44bec-fabric-catalog-system` (`4ce3e10d5c89...`) | **VERIFIED ON DEV BRANCH** (`/api/v1`, FastAPI `1.0.1`; unmerged to `main`) | Live HTTP `/api/v1` when `MODULE_02_BASE_URL` set; else `UNAVAILABLE` |
| **03 — 2D Designer** | `-3-2D-CLOTHING-DESIGNER` | `da5add67923e...` (Scaffold) | `arena/bbe947ab-3-2d-clothing-designer` (`d4ae96e75242...`) | **SCHEMA VERIFIED ON DEV BRANCH** (`DSG-*` v`1.0.0`; no admin HTTP API) | Embedded read-only schema parser on order payloads |
| **04 — 3D Preview** | `-4-CLOTHING-PREVIEW` | `1806ce250000...` (Scaffold) | *None* | **MISSING** (Optional reference only) | Optional read-only `preview_ref` / URL pass-through |
| **05 — Price Engine** | `clothing-price-engine` | `20ea4718c001...` (Scaffold) | *None* | **MISSING / BLOCKED** | `CONTRACT_UNCONFIGURED` (zero local price calculation) |
| **06 — Measurement Guide** | `-6-MEASUREMENT-GUIDE` | `bdc8205f80c3...` (Scaffold) | *None* | **MISSING / BLOCKED** | `CONTRACT_UNCONFIGURED` |
| **07 — Order Manager** | `-7-TAILORING-ORDER-MANAGER` | `d83caf532420...` (Scaffold) | *None* | **MISSING / BLOCKED** | `CONTRACT_UNCONFIGURED` |

---

## 2. Standard Adapter Envelope & Runtime Modes

### 2.1 `INTEGRATION_MODE` Policy
- **`live` (Default & Mandatory in `APP_ENV=production`):**
  - Uses real `httpx` adapters against configured `MODULE_XX_BASE_URL` environment variables.
  - If a module has no verified contract or no configured base URL, the adapter immediately returns `source_status = "CONTRACT_UNCONFIGURED"` with `data = None`.
  - If a configured service times out, refuses connection, or returns `5xx`, the adapter returns `source_status = "UNAVAILABLE"` with a sanitized diagnostic message.
- **`mock_dev` (Explicit Opt-In Only for Local Development & Automated Tests):**
  - Startup **refuses to boot** if `APP_ENV=production` and `INTEGRATION_MODE=mock_dev`.
  - Unconfigured modules return deterministic development fixtures stamped with `source_status = "MOCK_DEV"`.
  - Every API response and frontend view renders a high-visibility `MOCK_DEV` warning badge so fixture records can never be confused with live verified data.

### 2.2 Canonical `IntegrationEnvelope[T]` Schema
All Module 08 endpoints wrapping external module data return:

```json
{
  "module_code": "MODULE_02",
  "module_name": "fabric-catalog-system",
  "source_status": "VERIFIED",
  "is_verified_live": true,
  "is_mock_data": false,
  "fetched_at": "2026-11-16T05:30:00Z",
  "correlation_id": "9f8c2b1e-4d3a-4c7e-8a11-2c5f90d1e001",
  "error_code": null,
  "error_message": null,
  "data": {}
}
```

Allowed `source_status` values:
- `VERIFIED`: Live HTTP call succeeded and payload validated against schema.
- `MOCK_DEV`: Returned by explicit `INTEGRATION_MODE=mock_dev` fixture adapter.
- `CONTRACT_UNCONFIGURED`: External module contract is not yet available or `MODULE_XX_BASE_URL` is unset.
- `UNAVAILABLE`: Configured external service timed out, failed DNS/TCP connect, or returned `5xx`.
- `CONTRACT_MISMATCH`: Upstream responded `2xx`, but payload violated expected schema (logged with `correlation_id`; never silently coerced into fake numbers).

### 2.3 Transport, Timeout, Retry & Error Mapping Rules
| Condition | Adapter Behaviour | Module 08 HTTP Response / Envelope |
|---|---|---|
| `GET` network timeout / `502`/`503`/`504` | Connect timeout `2.0s`, read timeout `5.0s`; at most **1 retry** (`250ms` delay). | `200` composite view with `source_status="UNAVAILABLE"`, or `503 Service Unavailable` on direct action endpoint. |
| `POST`/`PUT`/`PATCH`/`DELETE` failure | **0 automatic retries** (prevents duplicate mutations / inventory overwrite). | Upstream error mapped cleanly (`400`/`401`/`403`/`404`/`409`/`422`/`429`/`502`) + failed audit log entry. |
| Upstream `401` / `403` | Strip upstream auth headers from logs; record `INTEGRATION_AUTH_ERROR`. | `502 Bad Gateway` (`error_code="UPSTREAM_AUTH_REJECTED"`) — never leaks `MODULE_02_ADMIN_API_KEY`. |
| Upstream `422` validation error | Preserve field-level business message (e.g., Module 02 oversell check). | `422 Unprocessable Entity` with sanitized upstream `detail`. |
| Upstream `429` rate limit | Respect backoff; do not retry immediately. | `429 Too Many Requests` (`error_code="UPSTREAM_RATE_LIMITED"`). |

---

## 3. Module 02 Contract — Fabric Catalog System (VERIFIED ON DEV BRANCH)

- **Repository:** `https://github.com/dhundhwana-arch/fabric-catalog-system`
- **Verified Ref:** `arena/9fb44bec-fabric-catalog-system` (`4ce3e10d5c89c38504da469200ff9acbcdf7943a`), FastAPI `1.0.1`
- **Merge Caveat:** `main` (`6524f79dc9a9ca157de126fb5c3719d8c7269d5d`) is still the initial scaffold; live integration requires running the `arena/9fb44bec-fabric-catalog-system` service (or its post-merge `main` equivalent) at `MODULE_02_BASE_URL`.

### 3.1 Permanent Identifiers & Verified Enums
- **Permanent IDs (atomic, never reused):** `FAB-NNN` (Fabric), `FVAR-NNN` (Variant), `FCAT-NNN` (Category), `FIMG-NNN` (Image), `FLOT-NNN` (Inventory Lot).
- **`AvailabilityStatus`:** `UNKNOWN` | `AVAILABLE` | `LOW_STOCK` | `OUT_OF_STOCK` | `ON_REQUEST` | `DISCONTINUED`
- **`SourcingMethod`:** `CUSTOMER_SUPPLIED` | `BUSINESS_INVENTORY` | `SUPPLIER_SOURCED`
- **`ImageType`:** `FRONT` | `CLOSE_UP` | `TEXTURE` | `SWATCH` | `OTHER`
- **`Unit`:** `METER` | `YARD` | `PIECE` | `SET`
- **`MovementType`:** `RECEIVE` | `RESERVE` | `RELEASE` | `DISPATCH` | `ADJUST`

### 3.2 Verified Endpoints Consumed by Module 08
| Upstream Method & Path | Upstream Auth | Module 08 Required Role | Notes & Constraints |
|---|---|---|---|
| `GET /health` | Public | Any authenticated | Returns `{"status":"ok","module":"fabric-catalog-system","version":"1.0.1"}`. |
| `GET /api/v1/fabrics` | Public | `OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF` | Query params: `search`, `fabric_id`, `category_id`, `fabric_type`, `colour`, `colour_hex`, `availability`, `min_price`, `max_price`, `include_inactive`, `sort`, `order`, `page`, `page_size`. Returns `{items, total, page, page_size, pages}`. |
| `GET /api/v1/fabrics/{pk}` & `/by-code/{FAB-NNN}` | Public | `OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF` | Returns `FabricDetailOut` (`category`, `variants`, `images`). |
| `GET /api/v1/variants` & `/variants/by-code/{FVAR-NNN}` | Public | `OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF` | Monetary `customer_price` serialized as exact decimal (`INR`), never float. |
| `GET /api/v1/categories` & `GET /api/v1/colours` | Public | `OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF` | Active categories and aggregated colour swatch counts (`ColourOut`). |
| `GET /api/v1/prices/variants/{pk}` | Public | `OWNER`, `ADMINISTRATOR` | Fabric-component price history (`PriceOut`). |
| `GET /api/v1/inventory` & `/inventory/{variant_pk}` | Public | `OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF` | Verified lot stock & reserved quantities (`InventoryOut`). Catalogue `AVAILABLE` status is **never** conflated with physical stock when no inventory record exists. |
| `GET /api/v1/export?format=json\|csv` | Public | `OWNER`, `ADMINISTRATOR` | Full public catalogue export (excludes supplier data). |
| `POST / PUT / DELETE /api/v1/fabrics` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` | `DELETE /api/v1/fabrics/{pk}` soft-archives fabric + variants (`is_active=false`); `?hard=true` returns `409` if variants/images exist. |
| `POST / PUT / DELETE /api/v1/variants` & `/categories` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` | `colour_hex` validated against `^#[0-9A-Fa-f]{6}$`. |
| `POST /api/v1/images` & `/images/upload` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` | Upload enforces MIME, magic-byte, and `<= 40 MP` checks (`413`/`415`/`422`). |
| `POST /api/v1/prices` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` | Appends new fabric variant price record (`Numeric(12,2)`, `INR`). |
| `PUT /api/v1/inventory/{variant_pk}` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` | **Critical:** Sets absolute `stock_quantity` and `reserved_quantity` (not deltas). Rejects `reserved_quantity > stock_quantity` with `422`. Module 08 requires confirmation dialog and logs before/after quantities. |
| `GET / POST /api/v1/suppliers` | `Bearer <ADMIN_API_KEY>` | `OWNER`, `ADMINISTRATOR` (restricted) | **Strictly server-side.** Completely blocked (`403`) for `AUTHORIZED_STAFF`. |

### 3.3 Secret Isolation Rule for Module 02
`MODULE_02_ADMIN_API_KEY` resides exclusively in Module 08's backend environment configuration (`SecretStr`). It is injected only into outbound server-to-server `httpx` requests and is **never** returned in API responses, frontend bundles, browser storage, audit summaries, or error logs.

---

## 4. Module 03 Contract — 2D Clothing Designer (SCHEMA VERIFIED ON DEV BRANCH)

- **Repository:** `https://github.com/dhundhwana-arch/-3-2D-CLOTHING-DESIGNER`
- **Verified Ref:** `arena/bbe947ab-3-2d-clothing-designer` (`d4ae96e75242b15b13b62a77f557b766ca0aad68`)
- **Integration Pattern:** Module 03 explicitly defines **no administrative HTTP API** (`INTEGRATION.md` §7). Instead, orders from Module 07 reference a finalized `design_id` (`DSG-[A-Z0-9]{8}`) and/or embed the canonical `schema_version: "1.0.0"` configuration JSON:

```json
{
  "design_id": "DSG-A1B2C3D4",
  "schema_version": "1.0.0",
  "product_type": "shirt",
  "fabric": { "fabric_id": "FAB-001" },
  "components": {
    "color_hex": "#000080",
    "collar": { "style": "classic" },
    "sleeves": { "style": "full" },
    "cuffs": { "style": "standard" },
    "pockets": { "style": "single", "flap_style": "none" },
    "buttons": { "button_id": null, "style": "basic", "placement": "standard" },
    "thread": { "color_hex": "#FFFFFF" },
    "fit": { "type": "regular" }
  },
  "metadata": {
    "current_view": "front",
    "created_at": "2026-11-16T04:37:00Z",
    "updated_at": "2026-11-16T04:37:00Z"
  }
}
```
Module 08's `module03_designs.py` helper validates and renders this read-only garment specification inside Order Details without modifying it.

---

## 5. Missing Upstream Contracts — Typed Adapter Interfaces & Handoff Requirements

Because Modules **01, 04, 05, 06, and 07** currently contain only initial scaffolds on `main`, Module 08 defines strict Python `Protocol` interfaces rather than inventing hard-coded production URLs. Below are the internal adapter contracts and the **outbound handoff requirements** proposed for owner/cross-module alignment.

### 5.1 Module 01 — Customer Platform (`custom-shirt-studio`) [STATUS: BLOCKED / MISSING]
- **Module 08 Adapter Interface (`CustomerServiceAdapter`):**
  - `list_customers(search, status, page, page_size) -> IntegrationEnvelope[PaginatedCustomers]`
  - `get_customer(customer_ref) -> IntegrationEnvelope[CustomerDetail]`
- **Required Handoff Contract from Module 01 (Section 28):**
  1. Stable opaque `customer_ref` (e.g., `CUS-NNNN` or UUID—never raw auto-increment primary keys alone).
  2. Fields: `customer_ref`, `full_name`, `phone_e164` (masked by Module 08 unless authorized), `email` (optional), `preferred_language` (`en`/`gu`), `account_status`, `created_at`.
  3. Server-to-service authentication header (`Authorization: Bearer <SERVICE_TOKEN>`) + pagination `{items, total, page, page_size, pages}`.
  4. Future SSO/session introspection specification if unified admin login is desired later.

### 5.2 Module 04 — 3D Clothing Preview (`-4-CLOTHING-PREVIEW`) [STATUS: MISSING / OPTIONAL]
- **Module 08 Handling:** Accepts optional `preview_ref` and `preview_snapshot_url` fields on Order records when present; shows *"No 3D preview attached"* cleanly when absent.

### 5.3 Module 05 — Clothing Price Engine (`clothing-price-engine`) [STATUS: BLOCKED / MISSING]
- **Module 08 Adapter Interface (`PricingEngineAdapter`):**
  - `list_pricing_configurations() -> IntegrationEnvelope[list[PricingConfigVersion]]`
  - `list_quotations(order_ref, status, page, page_size) -> IntegrationEnvelope[PaginatedQuotations]`
  - `get_quotation(quotation_ref) -> IntegrationEnvelope[QuotationBreakdown]`
  - `request_configuration_update(payload, actor) -> IntegrationEnvelope[PricingConfigVersion]` *(only when supported by Module 05)*
- **Strict Non-Calculation Guarantee:** Module 08 **never** computes official prices. Reported Dhundhwana contextual set charges (`₹450` regular / `₹500` urgent per **shirt-and-pant set**) are rendered in a clearly separated static contextual panel and are never injected into `QuotationBreakdown`.
- **Required Handoff Contract from Module 05:**
  1. Exact `Decimal` string serialization in `INR` (`currency: "INR"`).
  2. Immutable `quotation_ref` (`QTE-...`), `config_version`, `status` (`DRAFT`, `CONFIRMED`, `EXPIRED`, `SUPERSEDED`), and itemized `line_items` (fabric component from Module 02 + tailoring components owned by Module 05).

### 5.4 Module 06 — Measurement Guide (`-6-MEASUREMENT-GUIDE`) [STATUS: BLOCKED / MISSING]
- **Module 08 Adapter Interface (`MeasurementAdapter`):**
  - `list_measurement_summaries(order_ref, page, page_size) -> IntegrationEnvelope[PaginatedMeasurementRefs]` *(metadata only: `measurement_ref`, `profile_version`, `validation_status`, `order_ref`, `updated_at` — **no** body dimensions)*
  - `get_order_measurement_detail(order_ref, measurement_ref, actor) -> IntegrationEnvelope[OrderMeasurementDetail]` *(protected; triggers mandatory `MEASUREMENT_VIEWED` audit log)*
- **Required Handoff Contract from Module 06:**
  1. Separation between lightweight validation metadata (`VALIDATED`, `PENDING_REVIEW`, `NEEDS_CORRECTION`) and protected dimensional values.
  2. Order-pinned measurement snapshot/version (`profile_version`) so historical stitched orders retain exact measurement traceability even if a customer updates their profile later.

### 5.5 Module 07 — Tailoring Order Manager (`-7-TAILORING-ORDER-MANAGER`) [STATUS: BLOCKED / MISSING]
- **Module 08 Adapter Interface (`OrderManagerAdapter`):**
  - `list_orders(filters, page, page_size) -> IntegrationEnvelope[PaginatedOrders]`
  - `get_order_detail(order_ref) -> IntegrationEnvelope[OrderDetail]`
  - `get_production_stage_counts() -> IntegrationEnvelope[ProductionStageSummary]`
  - `request_status_transition(order_ref, target_status, customer_visible_note, actor, correlation_id) -> IntegrationEnvelope[OrderTransitionResult]`
- **Dynamic Lifecycle Compatibility:**
  - Supports all 18 proposed lifecycle statuses (`DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `PRICE_PENDING`, `AWAITING_CUSTOMER_CONFIRMATION`, `CONFIRMED`, `MATERIAL_PENDING`, `READY_FOR_CUTTING`, `CUTTING`, `STITCHING`, `FINISHING`, `QUALITY_CHECK`, `READY_FOR_DELIVERY`, `OUT_FOR_DELIVERY`, `DELIVERED`, `COMPLETED`, `CANCELLED`, `ON_HOLD`) **plus** unknown future status codes gracefully (rendering unknown upstream statuses verbatim with neutral styling rather than failing validation), awaiting Module 07's finalized state machine (`allowed_next_statuses` per order).
- **Required Handoff Contract from Module 07 (Section 28):**
  1. Order payload carrying opaque references: `order_ref` (`ORD-...`), `customer_ref` (`CUS-...`), `design_ref` (`DSG-...`), `fabric_ref` (`FAB-...` / `FVAR-...`), `measurement_ref` (`MSR-...`), `quotation_ref` (`QTE-...`), `quantity`, `garment_type`, `is_urgent`, `current_status`, `allowed_transitions`, `latest_customer_update`, `created_at`, `updated_at`, and `timeline` events.
  2. Validated status transition endpoint enforcing Module 07's state machine and recording `requested_by_admin_id` and `correlation_id`.
  3. Aggregated stage-count endpoint so Dashboard Overview and Production Workload views do not need to paginate through every historical order.
- **Phase 04 Re-Verification Note (2026-11-16):**
  - `main` of `dhundhwana-arch/-7-TAILORING-ORDER-MANAGER` remains stubbed (`d83caf53`), while an unmerged working branch (`arena/77121da8-7-tailoring-order-manager` @ `efac38f4`) introduces draft FastAPI schemas for `GET /api/v1/capacity/workload` (`is_guaranteed_capacity`, `estimated_workload`, `capacity_warnings`, `scheduling_conflicts`) and `GET /api/v1/orders` (`{items, total, page, page_size, pages}`).
  - Per Phase 04 integration boundaries (*"Keep order metrics unavailable until its real contract exists"*), `Module07OrderAdapter` keeps order metrics in `CONTRACT_UNCONFIGURED` (`data: null`, rendered as `—`, never `0`) by default unless `MODULE_07_CONTRACT_VERIFIED=true` + `MODULE_07_BASE_URL` are explicitly enabled after upstream contract merge/approval (or `INTEGRATION_MODE=mock_dev` is explicitly set in non-production dev/test).
  - Similarly, `dhundhwana-arch/fabric-catalog-system` unmerged branch `arena/9fb44bec-fabric-catalog-system` (`fcbb0dce`) was re-verified: `Module02FabricAdapter` consumes strictly its verified public read endpoints (`GET /api/v1/fabrics`, `/api/v1/categories`, `/api/v1/colours`, `/api/v1/variants`) and never exposes `ADMIN_API_KEY` / `SERVICE_API_KEYS` or supplier/inventory procurement fields on Dashboard Overview.

---

## 6. Cross-Module Contract Mismatch & Change Control Procedure

Per **Section 28 & Section 29**, whenever an upstream repository publishes or alters an API contract:
1. **Inspect & Diff:** Verify the upstream repository's branch, commit SHA, and Pydantic/TypeScript schemas directly.
2. **Isolate:** Contain all wire-format changes strictly inside `backend/app/adapters/moduleXX_*.py` without polluting Module 08's internal RBAC or audit models.
3. **Never Unilaterally Rewrite Shared Contracts:** Record any field/type mismatch in `INTEGRATION.md` and `docs/EXTERNAL_API_CONTRACTS.md`, surface `CONTRACT_MISMATCH` safely at runtime rather than fabricating values, and request project owner approval before introducing any breaking change to `/api/v1/admin/...`.
