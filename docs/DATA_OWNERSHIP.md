# DATA OWNERSHIP & INTEGRITY SPECIFICATION — MODULE 08

| Field | Value |
|---|---|
| **Project** | CUSTOM SHIRT STUDIO |
| **Module** | 08 / 08 — Small Business Admin Dashboard (`dhundhwana-arch/-8-DASHBOARD-`) |
| **Document Purpose** | Authoritative boundary between Module 08 local persistence and sibling module domains |
| **Status** | Phase 02 Approved Baseline |

---

## 1. Unified Ecosystem Source-of-Truth Charter

Custom Shirt Studio comprises eight independent modules operating as one cohesive platform. Each business entity has **exactly one authoritative owning module**. Module 08 is an internal orchestration and governance interface—it **must never create a competing database or shadow source of truth** for records owned by Modules 01–07.

| Domain Data Category | Authoritative Owner | GitHub Repository | Module 08 Permitted Access | Module 08 Prohibited Actions |
|---|---|---|---|---|
| **Customer Master Profiles & Contact PII** | **Module 01** | `custom-shirt-studio` | Read via adapter; mask phone numbers by default; link internal notes by opaque `customer_ref`. | Storing local `customers` table; mutating customer profiles directly in Module 08 DB. |
| **Fabrics, Variants, Colours, Images, Stock & Suppliers** | **Module 02** | `fabric-catalog-system` | Read public & admin `/api/v1` endpoints; send authorized CRUD/stock requests through Module 02 API. | Maintaining a local fabric/stock table; inventing inventory quantities; exposing `/suppliers` to unauthorized roles. |
| **2D Garment Design Configurations (`DSG-*`)** | **Module 03** | `-3-2D-CLOTHING-DESIGNER` | Read/validate `DSG-*` v1.0.0 configuration metadata attached to orders. | Editing or persisting authoritative 2D design documents locally. |
| **3D Visualization Assets & Previews** | **Module 04** | `-4-CLOTHING-PREVIEW` | Render optional read-only preview link/reference when present on an order. | Generating or storing 3D preview scenes locally. |
| **Official Garment Pricing Rules & Quotations** | **Module 05** | `clothing-price-engine` | Read pricing configurations, versions, quotations, and breakdowns via Module 05 API. | Calculating garment prices locally; silently altering confirmed quotations; inventing per-shirt rates, taxes, discounts, or margins. |
| **Customer Body Measurements & Validation** | **Module 06** | `-6-MEASUREMENT-GUIDE` | Order-scoped, role-checked read of measurement reference/snapshot with mandatory audit event. | Copying reusable measurement profiles into Module 08 DB; showing measurements on overview or customer list pages. |
| **Order Lifecycle, Production Stages & Customer Updates** | **Module 07** | `-7-TAILORING-ORDER-MANAGER` | Read orders, stages, and timelines; submit status-transition requests to Module 07's API. | Updating authoritative order status in a local DB; mixing internal admin notes with customer-visible order updates. |
| **Admin Accounts, RBAC, Audit Trail, Workshop Settings & Internal Notes** | **Module 08** | `-8-DASHBOARD-` | **Authoritative Owner (CRUD / Append-Only Audit).** | Exposing internal admin credentials, session hashes, or internal-only notes to public storefronts. |

---

## 2. Module 08 Local Database Schema (Permitted Entities Only)

Module 08's relational database (PostgreSQL in production; SQLite WAL in local development and automated tests) contains **strictly six internal administrative tables**:

```text
+-----------------------+       1 : N       +-------------------------+
|      admin_users      |------------------>|     admin_sessions      |
|-----------------------|                   |-------------------------|
| id (PK)               |                   | id (PK)                 |
| public_id (ADM-...)   |                   | session_id (UUID)       |
| username (UNIQUE)     |                   | user_id (FK)            |
| display_name          |                   | token_hash (SHA-256)    |
| password_hash (bcrypt)|                   | csrf_token_hash         |
| role (ENUM)           |                   | expires_at / revoked_at |
| preferred_locale      |                   | ip_address / user_agent |
| is_active             |                   +-------------------------+
| created_at/updated_at |
+-----------+-----------+
            |
            | recorded_by / actor_user_id
            v
+-----------------------------------+       +-----------------------------------+
|         admin_audit_logs          |       |       internal_admin_notes        |
|-----------------------------------|       |-----------------------------------|
| id (PK)                           |       | id (PK)                           |
| event_id (AUD-UUID, UNIQUE)       |       | note_id (NTE-UUID, UNIQUE)        |
| actor_user_id (FK, nullable)      |       | target_type ('ORDER'|'CUSTOMER'   |
| actor_username / actor_role       |       |              |'WORKSHOP')         |
| action_type                       |       | target_ref (opaque external ref)  |
| resource_type / resource_id       |       | visibility ('INTERNAL_ADMIN_ONLY')|
| source_origin ('ADMIN_DASHBOARD'  |       | content                           |
|                |'EXTERNAL_MODULE')|       | author_user_id (FK)               |
| outcome ('SUCCESS'|'FAILURE'      |       | created_at / updated_at           |
|          |'DENIED')               |       +-----------------------------------+
| change_summary (JSON, redacted)   |
| correlation_id                    |       +-----------------------------------+
| created_at (IMMUTABLE)            |       |         business_settings         |
+-----------------------------------+       |-----------------------------------|
                                            | key (PK)                          |
+-----------------------------------+       | value_json                        |
|        workshop_resources         |       | category                          |
|-----------------------------------|       | is_owner_approved (BOOL)          |
| id (PK)                           |       | updated_by_user_id (FK)           |
| resource_code (RES-..., UNIQUE)   |       | version / updated_at              |
| display_name_en / display_name_gu |       +-----------------------------------+
| resource_category                 |
| reported_count                    |
| operational_note_status           |
| status_is_manual_note (TRUE)      |
| updated_by_user_id (FK)           |
| updated_at                        |
+-----------------------------------+
```

### 2.1 Table-by-Table Ownership Rules
1. **`admin_users`:** Stores only verified administrative accounts provisioned by the business owner (`OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF`). **Never** populated with fictitious employees or unverified staff profiles.
2. **`admin_sessions`:** Stores cryptographic `SHA-256` digests of active session and CSRF tokens—never raw bearer/cookie secrets. Supports immediate revocation and automatic expiration.
3. **`admin_audit_logs`:** Strictly append-only (`INSERT` and `SELECT` only). Distinguishes actions initiated in Module 08 (`source_origin = "ADMIN_DASHBOARD"`) from upstream state events (`source_origin = "EXTERNAL_MODULE"`). Never stores raw passwords, session tokens, `MODULE_02_ADMIN_API_KEY`, full customer phone numbers, or raw body measurement values in `change_summary`.
4. **`business_settings`:** Stores owner-configurable operational parameters (such as active-order workload warning thresholds, default UI locale, and optional operational flags) with explicit `is_owner_approved` tracking and version increments.
5. **`workshop_resources`:** Holds configurable administrative reference records for workshop equipment (seeded only as contextual baseline descriptions when requested, with `status_is_manual_note = True` so operators never mistake manual notes for live machine telemetry).
6. **`internal_admin_notes`:** Stores internal tailoring coordination notes keyed by opaque external identifier (e.g., `target_type="ORDER"`, `target_ref="ORD-0001"`). Hard-coded `visibility="INTERNAL_ADMIN_ONLY"` ensures strict separation from Module 07's customer-visible order status messages.

---

## 3. Explicitly Prohibited & Deferred Persistence

### 3.1 Deferred Feature Exclusion (Owner Decision #4)
- **No Payment Tables or Payment Logic:** `payment_records`, payment gateway webhooks, card/UPI/banking fields, and transaction ledgers are **not approved for the initial release** and must not exist in SQLAlchemy models, migrations, API routes, or UI views.

### 3.2 Prohibited Shadow Tables
Module 08 must **never** define local tables for:
- `customers` or `customer_addresses`
- `orders`, `order_items`, or `order_status_history`
- `fabrics`, `fabric_variants`, `fabric_inventory`, or `fabric_suppliers`
- `designs` or `previews`
- `pricing_rules` or `quotations`
- `measurements` or `measurement_profiles`

### 3.3 Transient Memory & Caching Constraints
- External responses are **never** persisted to disk or SQLite/PostgreSQL in Module 08.
- All `/api/v1/admin/*` responses carry `Cache-Control: no-store` so sensitive customer, order, and measurement payloads are not retained in shared browser caches.
- Every external dataset returned by Module 08 is wrapped in an `IntegrationEnvelope` carrying `source_status` (`VERIFIED`, `MOCK_DEV`, `UNAVAILABLE`, `CONTRACT_UNCONFIGURED`, `DEGRADED`) and `fetched_at`.

---

## 4. Dhundhwana Tailoring Business Context & Data Integrity Rules

Module 08 serves a real family tailoring business in **Dhundhwana (Khambha taluka, Amreli district, Gujarat)**. Reported contextual facts must be handled with strict semantic honesty:

| Reported Contextual Fact | Permitted Treatment in Module 08 | Strictly Forbidden Misuse |
|---|---|---|
| **Regular stitching charge: ₹450 per shirt-and-pant set** | Display in Pricing / Operations context card explicitly labelled *"Reported Contextual Business Rate (1 Shirt-and-Pant Set — Reference Only)"*. | Treating ₹450 as a per-shirt rate; using ₹450 in automated quotation math; multiplying order counts by ₹450 to claim revenue. |
| **Urgent stitching charge: ₹500 per shirt-and-pant set** | Display alongside regular set rate with identical *"Contextual Reference Only — Official Pricing Owned by Module 05"* notice. | Treating ₹500 as a verified live Module 05 pricing rule without Module 05 confirmation. |
| **Approximate capacity: ~2 shirt-and-pant sets per day** | Offer as a configurable reference baseline for workload warning indicators (requires owner confirmation to change thresholds). | Promising customer delivery dates from this figure; presenting it as a guaranteed daily output limit. |
| **Workshop setup: 3 sewing machines, 1 overlock machine, 1 iron, 1 cutting table** | Display as contextual workshop setup reference with optional manual operator notes (`Maintenance`, `In Use`, `Note`). | Assuming all 3 sewing machines operate simultaneously; claiming live IoT/automated resource availability. |
| **Fabric sourcing: Customers currently supply fabric (hybrid sourcing possible later)** | Support Module 02 `SourcingMethod` (`CUSTOMER_SUPPLIED`, `BUSINESS_INVENTORY`, `SUPPLIER_SOURCED`); distinguish catalogue listing status from physical stock. | Assuming catalogue `AVAILABLE` status equals physical rolls on hand when `inventory` is unverified; inventing stock counts. |

### 4.1 Forbidden Invented Statistics
Module 08 must **never** synthesize, estimate, or display unverified figures for:
- Gross/net revenue, profit, margins, taxes, discounts, or business expenses.
- Daily/weekly/monthly completed production totals when Module 07 history is unavailable.
- Individual tailor/staff productivity rankings, working hours, or attendance/holiday calendars.
- Fabric supplier names, wholesale procurement rates, or roll quantities unless returned directly by Module 02 to an authorized `OWNER`/`ADMINISTRATOR`.

### 4.2 Zero vs. Unavailable Semantics
- **`0` (Numeric Zero):** Rendered **only** when the owning module responded successfully (`source_status = "VERIFIED"`, or `"MOCK_DEV"` in explicit dev mode) and the verified count of matching records is genuinely zero.
- **`—` / Unavailable State:** Rendered whenever `source_status` is `UNAVAILABLE` or `CONTRACT_UNCONFIGURED`, accompanied by a clear explanation in English or Gujarati (e.g., *"Module 07 (Order Manager) is not connected — live order counts unavailable"*).

---

## 5. Customer & Measurement Privacy Controls

1. **Opaque Resource Identifiers:** Module 08 addresses external entities via stable opaque codes (`CUS-...`, `ORD-...`, `FAB-...`, `FVAR-...`, `DSG-...`, `QTE-...`, `MSR-...`) wherever provided, avoiding sequential integer enumeration leaks on Module 08-owned routes (`ADM-...`, `NTE-...`, `AUD-...`).
2. **Phone & Contact Redaction:**
   - Customer list responses mask phone numbers (`+91 ******4210`) and email addresses (`r***@example.com`).
   - Full contact details require `OWNER` or authorized `ADMINISTRATOR` permission on the customer detail endpoint (`?reveal_contact=true`), writing a `CUSTOMER_CONTACT_VIEWED` event to `admin_audit_logs`.
   - `AUTHORIZED_STAFF` cannot browse unrestricted customer contact lists.
3. **Measurement Isolation:**
   - Body measurement values are **never** included in Dashboard Overview, Customer Listing, Customer Profile summary, Order Listing, or Export CSVs.
   - Full measurement values are accessible solely via the dedicated order-scoped endpoint (`GET /api/v1/admin/orders/{order_ref}/measurements`) for authorized users with an operational tailoring need, logging `MEASUREMENT_VIEWED` (or `MEASUREMENT_ACCESS_DENIED` on `403`).
