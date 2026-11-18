# ARCHITECTURE — MODULE 08: SMALL BUSINESS ADMIN DASHBOARD

| Field | Value |
|---|---|
| **Project** | CUSTOM SHIRT STUDIO |
| **Module** | 08 / 08 — Small Business Admin Dashboard (`small-business-admin-dashboard`) |
| **GitHub Repository** | `https://github.com/dhundhwana-arch/-8-DASHBOARD-` |
| **Working Branch** | `arena/e48d945c-8-dashboard` (branched from `main` @ `b71713553ff66d049dfe64d35a23d9c590590556`) |
| **Document Status** | Phase 02 Baseline — Approved Technology Stack & Boundaries |
| **API Namespace** | `/api/v1/admin/...` |

---

## 1. Architectural Purpose & Scope

Module 08 is the **internal business administration, operational visibility, and cross-module orchestration layer** for **Custom Shirt Studio**, serving a small family tailoring workshop in **Dhundhwana, Khambha taluka, Amreli district, Gujarat**.

### 1.1 Core Architectural Mandates
1. **Orchestration Without Duplication:** Module 08 coordinates with sibling Modules 01–07 via typed backend adapters. It **never** acts as an alternative source-of-truth database for customer profiles (Module 01), fabric catalogue/inventory (Module 02), 2D designs (Module 03), 3D previews (Module 04), official garment pricing/quotations (Module 05), body measurements (Module 06), or authoritative order statuses (Module 07).
2. **Truthful Operational Telemetry:** Module 08 displays metrics **only** when their upstream source and calculation are verified. Unavailable sources render explicit `UNAVAILABLE` or `CONTRACT_UNCONFIGURED` states—never misleading `0` or `₹0` values. Revenue, profit, expenses, daily output totals, supplier figures, and per-shirt prices are **never** invented.
3. **Standalone Usefulness Under Upstream Outages:** Even when external modules are unconfigured or offline, Module 08 remains genuinely operational for:
   - Integration health & readiness diagnostics across Modules 01–07.
   - Owner/Administrator management of staff accounts, roles, and active sessions.
   - Workshop operational configuration (owner-approved workload warning thresholds, manual equipment status notes, contextual reference rates).
   - Internal-only administrative coordination notes keyed by opaque external reference (`ORD-...`, `CUS-...`).
   - Immutable administrative audit logs and local operational activity reports.
4. **Backend-Enforced Security & Privacy:** Role-Based Access Control (`OWNER`, `ADMINISTRATOR`, `AUTHORIZED_STAFF`), session verification, CSRF validation, rate limiting, PII masking, and sensitive-read audit logging are enforced on the FastAPI backend—never solely via frontend visibility.
5. **Initial Release Scope Exclusion (Owner Decision #4):** Payment record tables, payment abstractions, payment gateways, and payment processing are **explicitly deferred and excluded** from this release.

---

## 2. Ecosystem & System Architecture Diagram

```text
+=========================================================================================+
|                                  CUSTOM SHIRT STUDIO                                    |
|                     MODULE 08 — SMALL BUSINESS ADMIN DASHBOARD                          |
+=========================================================================================+

  Authorized Business User (Owner / Administrator / Authorized Staff)
  [ Mobile (<768px) | Tablet (768-1024px) | Desktop (>1024px) — English (en) / Gujarati (gu) ]
                                           |
                                           | HTTPS / Relative /api/v1/admin/*
                                           | Cookie: css_admin_session (HttpOnly, SameSite=Lax)
                                           | Header: X-CSRF-Token (mutations), X-Correlation-ID
                                           v
+-----------------------------------------------------------------------------------------+
|                         MODULE 08 FRONTEND (React 18 + TS + Vite)                       |
|  - Responsive App Shell & Role-Aware Navigation                                         |
|  - Explicit Provenance Badges: VERIFIED | MOCK_DEV | UNAVAILABLE | CONTRACT_UNCONFIGURED|
|  - Bilingual UI Layer (English / ગુજરાતી) + Confirmation Dialogs for Sensitive Actions    |
+-----------------------------------------------------------------------------------------+
                                           |
                                           | Vite Dev Proxy (/api -> Backend) or Reverse Proxy
                                           v
+-----------------------------------------------------------------------------------------+
|                       MODULE 08 BACKEND (Python 3.11 + FastAPI)                         |
|                                                                                         |
|  [1. Edge Middleware]  Correlation ID -> Structured Logger -> Security Headers -> Rate  |
|                                                                                         |
|  [2. Auth & Session]   Session Authenticator (AuthProvider Interface, Module-01-Ready)  |
|                        CSRF Verifier + Session Expiry / Revocation Check                |
|                                                                                         |
|  [3. RBAC Engine]      Route & Service Guards (OWNER | ADMINISTRATOR | AUTHORIZED_STAFF)|
|                        PII Redaction Policy + Order-Scoped Measurement Access Policy    |
|                                                                                         |
|  [4. Domain Routers]   /auth  /dashboard  /customers  /orders  /production  /fabrics    |
|   (/api/v1/admin/*)    /pricing  /measurements  /operations  /reports  /audit  /settings|
|                                                                                         |
|  [5. Core Services]    AuditService (Append-Only) | OperationsService | ReportService   |
+--------------------+-----------------------------------------------+--------------------+
                     |                                               |
                     | SQLAlchemy 2.0 ORM                            | Typed Adapter Gateway
                     | (PostgreSQL in Prod / SQLite WAL in Dev/Test) | (httpx, Timeouts, Bounded
                     v                                               |  GET Retries, Isolation)
+-----------------------------------------+                          v
|     MODULE 08 LOCAL DATABASE ONLY       |     +-----------------------------------------+
|  - admin_users                          |     |     SIBLING MODULE ADAPTER INTERFACES   |
|  - admin_sessions (hashed tokens)       |     |  - Module01CustomerAdapter    [BLOCKED] |
|  - admin_audit_logs (append-only)       |     |  - Module02FabricAdapter   [/api/v1 OK] |
|  - business_settings                    |     |  - Module03DesignSchema     [DSG-* v1]  |
|  - workshop_resources (contextual notes)|     |  - Module04PreviewRef        [OPTIONAL] |
|  - internal_admin_notes                 |     |  - Module05PricingAdapter     [BLOCKED] |
|                                         |     |  - Module06MeasurementAdapter [BLOCKED] |
|  * ZERO payment tables                  |     |  - Module07OrderAdapter       [BLOCKED] |
|  * ZERO shadow external domain tables   |     +----+-------+-------+-------+-------+----+
+-----------------------------------------+          |       |       |       |       |
                                                     v       v       v       v       v
                                                   [M01]   [M02]   [M05]   [M06]   [M07]
                                                  Customer Fabric  Pricing Measure  Order
                                                  Platform Catalog Engine   Guide  Manager
```

---

## 3. Approved Technology Stack & Project Layout

### 3.1 Stack Summary
| Layer | Technology | Rationale & Ecosystem Alignment |
|---|---|---|
| **Backend Runtime & API** | Python 3.11, FastAPI, Pydantic v2, Uvicorn | Matches Module 02 (`fabric-catalog-system`); strong schema validation and OpenAPI generation under `/api/v1/admin`. |
| **Persistence** | SQLAlchemy 2.0 (`Mapped` / `mapped_column`), PostgreSQL (`psycopg` v3) & SQLite (WAL mode) | Production-ready relational guarantees on PostgreSQL with zero-dependency local dev & `pytest` execution on SQLite. |
| **HTTP Integration** | `httpx` (`Client` / `AsyncClient`) | Strict connect/read timeouts, header injection, and deterministic transport mocking in tests. |
| **Password & Crypto** | `bcrypt` + Python `secrets` & `hashlib` (SHA-256) | Salted adaptive hashing for user passwords; cryptographic random tokens hashed at rest for sessions and CSRF protection. |
| **Frontend UI** | React 18, TypeScript 5, Vite 5, Tailwind CSS 3, React Router v6, Lucide Icons | Matches Module 03 (`-3-2D-CLOTHING-DESIGNER`); lightweight, accessible, mobile-first bundle without enterprise bloat. |
| **Localization** | Custom typed `en` / `gu` i18n context | Zero-overhead English and Gujarati (`ગુજરાતી`) UI labels, navigation, banners, and status translations. |
| **Automated Testing** | `pytest` + `httpx` (Backend), `vitest` + `@testing-library/react` + `jsdom` (Frontend) | Full unit, RBAC, privacy, adapter failure, API contract, and responsive viewport verification. |

### 3.2 Planned Directory Structure (Phases 03–16)
```text
/home/user/-8-DASHBOARD-/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, middleware, lifespan, exception handlers
│   │   ├── core/
│   │   │   ├── config.py            # Validated Pydantic Settings (env-driven, prod safety checks)
│   │   │   ├── security.py          # Password hashing, session token SHA-256, CSRF generation
│   │   │   ├── auth.py              # AuthProvider interface + LocalSessionAuthProvider
│   │   │   ├── rbac.py              # Role definitions, permission matrix & FastAPI dependencies
│   │   │   ├── rate_limit.py        # Login & sensitive-action sliding-window rate limiter
│   │   │   ├── logging.py           # Structured JSON/key-value logging + X-Correlation-ID
│   │   │   └── errors.py            # Sanitized domain/HTTP error envelopes (no stack trace leaks)
│   │   ├── db/
│   │   │   ├── base.py              # SQLAlchemy 2.0 DeclarativeBase
│   │   │   ├── session.py           # Engine & session factory (PostgreSQL + SQLite WAL pragmas)
│   │   │   └── models.py            # ONLY Module 08 internal models (6 tables, zero payment tables)
│   │   ├── adapters/
│   │   │   ├── base.py              # IntegrationEnvelope, SourceStatus, timeout/retry transport
│   │   │   ├── module01_customers.py# CustomerServiceAdapter (Live HTTP + explicit MOCK_DEV)
│   │   │   ├── module02_fabrics.py  # FabricCatalogAdapter (Verified /api/v1 HTTP + MOCK_DEV)
│   │   │   ├── module03_designs.py  # Read-only DSG-* v1.0.0 schema validator/presenter
│   │   │   ├── module05_pricing.py  # PricingEngineAdapter (Live HTTP + explicit MOCK_DEV)
│   │   │   ├── module06_measurements.py # MeasurementAdapter (Live HTTP + explicit MOCK_DEV)
│   │   │   ├── module07_orders.py   # OrderManagerAdapter (Live HTTP + explicit MOCK_DEV)
│   │   │   └── registry.py          # Dependency wiring & health probe aggregator
│   │   ├── schemas/                 # Strict Pydantic v2 request/response contracts
│   │   ├── services/                # Audit, Dashboard, Operations, Reporting & Settings services
│   │   ├── api/v1/                  # Versioned routers mounted under /api/v1/admin
│   │   └── cli/bootstrap_owner.py   # Explicit CLI tool to provision initial OWNER account safely
│   ├── tests/                       # Backend unit, RBAC, privacy, adapter & integration tests
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                     # Typed fetch wrapper (relative /api/v1/admin, CSRF header)
│   │   ├── auth/                    # Auth session context & role-aware route guards
│   │   ├── i18n/                    # English (en.ts) & Gujarati (gu.ts) dictionaries
│   │   ├── components/              # AppShell, Sidebar, ProvenanceBanner, EmptyUnavailableState, ConfirmModal
│   │   ├── pages/                   # Login, Dashboard, Customers, Orders, Production, Fabrics,
│   │   │                            # Pricing, Measurements, Reports, ActivityLogs, Settings
│   │   └── tests/                   # Component, role-visibility, provenance & responsive tests
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts               # host: '0.0.0.0', allowedHosts: true, /api proxy
├── docs/
│   ├── DATA_OWNERSHIP.md
│   ├── EXTERNAL_API_CONTRACTS.md
│   ├── REPORTING_RULES.md           # Added in Phase 11/14
│   ├── AUDIT_LOGGING.md             # Added in Phase 12/14
│   ├── DEPLOYMENT.md                # Added in Phase 14
│   └── CONFIGURATION.md             # Added in Phase 14
├── ARCHITECTURE.md
├── LICENSE                          # Preserved MIT License
└── README.md
```

---

## 4. Module Boundaries & Ownership Summary

| Module | GitHub Repository | Authoritative Responsibility | Module 08 Interaction Rule |
|---|---|---|---|
| **01** | `custom-shirt-studio` | Customer accounts, customer contact PII, customer storefront | Read-only customer lookup & order-history reference via adapter; mask phone numbers by default; never duplicate customer master table. |
| **02** | `fabric-catalog-system` | Fabrics (`FAB-*`), variants (`FVAR-*`), categories (`FCAT-*`), images, prices, lots (`FLOT-*`), suppliers | Proxy catalogue reads & admin mutations to Module 02 `/api/v1`; keep `MODULE_02_ADMIN_API_KEY` strictly on backend; gate `/suppliers` to `OWNER`/`ADMINISTRATOR`. |
| **03** | `-3-2D-CLOTHING-DESIGNER` | 2D shirt customization JSON (`DSG-*` v1.0.0) | Render read-only garment configuration summary when referenced on an order; never modify designs. |
| **04** | `-4-CLOTHING-PREVIEW` | 3D garment preview scenes/links | Display optional read-only preview reference when attached to an order. |
| **05** | `clothing-price-engine` | Official pricing rules, configuration versions, confirmed quotations | Display official quotations & breakdowns from Module 05; never calculate garment prices locally; display reported ₹450/₹500 set rates strictly as contextual reference. |
| **06** | `-6-MEASUREMENT-GUIDE` | Body measurement records, versions, validation status | Access only for authorized order-specific operational need; never display on dashboard/customer lists; write audit log on every view. |
| **07** | `-7-TAILORING-ORDER-MANAGER` | Order lifecycle, production stages, status transitions, customer updates | Read orders/stages from Module 07; forward status-change requests to Module 07's transition API; store internal workshop notes separately in Module 08. |
| **08** | `-8-DASHBOARD-` | Admin auth/RBAC, audit trail, workshop settings, internal notes, cross-module reports | Sole source of truth for internal administrative governance only. |

---

## 5. Data-Flow Diagrams

### 5.1 Flow A — Dashboard Overview Aggregation with Partial Upstream Unavailability
```text
Browser                     FastAPI (/dashboard/overview)        Module 02 Adapter        Module 07 Adapter
  |                                      |                               |                        |
  |-- GET /api/v1/admin/dashboard ------>|                               |                        |
  |   Cookie: css_admin_session          |-- Verify Session & RBAC       |                        |
  |                                      |                               |                        |
  |                                      |-- get_catalogue_summary() --->|                        |
  |                                      |                               |-- GET /api/v1/fabrics ->| (200 OK)
  |                                      |<-- Envelope(status=VERIFIED) -|                        |
  |                                      |                               |                        |
  |                                      |-- get_order_stage_summary() -------------------------->|
  |                                      |                               |   (MODULE_07_BASE_URL unset)
  |                                      |<-- Envelope(status=CONTRACT_UNCONFIGURED, data=null) --|
  |                                      |                                                        |
  |                                      |-- Query Local DB (pending local alerts, settings)      |
  |<-- 200 JSON -------------------------|                                                        |
  |    orders: {status: "CONTRACT_UNCONFIGURED", data: null}  --> UI shows "Unavailable" state    |
  |    fabrics: {status: "VERIFIED", data: {...}}             --> UI shows verified counts        |
```
*Key Guarantee:* Module 07 being unconfigured or offline neither crashes `/dashboard` nor causes order counts to render as `0`.

### 5.2 Flow B — Delegated Cross-Module Administrative Mutation (e.g., Fabric Update or Order Transition)
```text
Browser                     FastAPI (/fabrics/{pk})              Module 02 (/api/v1)        Module 08 Local DB
  |                                      |                               |                        |
  |-- PUT /api/v1/admin/fabrics/1 ------>|                               |                        |
  |   Cookie + X-CSRF-Token              |-- 1. Verify Session & CSRF    |                        |
  |                                      |-- 2. Enforce RBAC             |                        |
  |                                      |      (OWNER / ADMINISTRATOR)  |                        |
  |                                      |-- 3. Validate Payload         |                        |
  |                                      |                               |                        |
  |                                      |-- PUT /api/v1/fabrics/1 ----->|                        |
  |                                      |   Authorization: Bearer <KEY> |                        |
  |                                      |   X-Correlation-ID: <uuid>    |                        |
  |                                      |<-- 200 Updated FabricOut -----|                        |
  |                                      |                               |                        |
  |                                      |-- 4. Append Audit Event ------------------------------>|
  |                                      |      action="FABRIC_UPDATE_REQUESTED"                  |
  |                                      |      source_origin="ADMIN_DASHBOARD", outcome="SUCCESS"|
  |<-- 200 Envelope(status=VERIFIED) ----|                                                        |
```
*Key Guarantee:* `MODULE_02_ADMIN_API_KEY` never leaves the backend; Module 02 mutates the authoritative record; Module 08 logs an immutable audit event with correlation ID.

### 5.3 Flow C — Privacy-Gated Order Measurement Access
```text
Browser                     FastAPI (/orders/{ord_ref}/measurements)    Module 06 Adapter     Module 08 Audit DB
  |                                      |                                      |                     |
  |-- GET /api/v1/admin/orders/          |                                      |                     |
  |       ORD-0042/measurements -------->|                                      |                     |
  |                                      |-- 1. Verify Session                  |                     |
  |                                      |-- 2. Check RBAC + Need-Based Policy  |                     |
  |                                      |      (Deny unauthorized staff -> 403 |                     |
  |                                      |       + log MEASUREMENT_ACCESS_DENIED)                     |
  |                                      |-- 3. Fetch Order-Pinned Reference -->|                     |
  |                                      |<-- Measurement Snapshot/Status ------|                     |
  |                                      |-- 4. Append Mandatory Audit Event ------------------------>|
  |                                      |      action="MEASUREMENT_VIEWED", resource_id="ORD-0042"   |
  |<-- 200 JSON (Cache-Control: no-store)|                                                            |
```

---

## 6. Authentication, Session & RBAC Architecture

### 6.1 Extensible Authentication Boundary (Module 01 Readiness)
- Module 08 defines an internal `AuthProvider` protocol (`authenticate_credentials`, `resolve_session`, `revoke_session`).
- **Initial Implementation (`LocalSessionAuthProvider`):** Authenticates against `admin_users` and `admin_sessions` in Module 08's database because Module 01 (`custom-shirt-studio`) currently has no shared identity contract (`main` @ `8ebb2e65`).
- **Future Federation Hook:** When Module 01 defines an approved SSO/token introspection contract, a `Module01FederatedAuthProvider` can implement the same interface without rewriting Module 08 routers or RBAC guards. Module 08 **explicitly reports federation status as `STANDALONE_LOCAL` (not federated)** until that contract exists.

### 6.2 Credential, Session & CSRF Controls
1. **No Default Production Passwords:** The application ships with **zero** hardcoded or default admin credentials. An explicit CLI command (`python -m app.cli.bootstrap_owner`) provisions the initial `OWNER` account from environment/prompted input. In `APP_ENV=production`, startup fails fast if `SESSION_SECRET_KEY` is missing/weak or if `INTEGRATION_MODE=mock_dev` is set.
2. **Password Hashing:** `bcrypt` (work factor `>= 12`) with minimum 12-character password enforcement for admin users.
3. **Server-Side Sessions:**
   - Login generates a 32-byte (`256-bit`) CSPRNG session token (`secrets.token_urlsafe(32)`).
   - Only `SHA-256(token)` is persisted in `admin_sessions.token_hash` alongside `user_id`, `csrf_token_hash`, `created_at`, `expires_at`, `last_seen_at`, `revoked_at`, `ip_address`, and `user_agent`.
   - Delivered via `HttpOnly`, `SameSite=Lax`, `Path=/api/v1/admin` cookie (`Secure=True` whenever `APP_ENV=production` or HTTPS is active).
   - Sessions expire automatically after configurable idle/absolute TTL (default 8 hours) and are immediately invalidated upon logout, role change, account deactivation, or `OWNER` session revocation.
4. **CSRF Protection:** Each session derives a deterministic HMAC-SHA256 CSRF token (`derive_session_csrf_token`, keyed by `SESSION_SECRET_KEY`, `session_id`, and `session_token_hash`), storing only `SHA-256(csrf_token)` in `admin_sessions.csrf_token_hash` and holding the raw token strictly in frontend JS memory (`X-CSRF-Token`), verified in constant time (`hmac.compare_digest`) on every `POST`, `PUT`, `PATCH`, and `DELETE` endpoint.
5. **Login Rate Limiting:** Fixed/sliding window limiter restricts repeated failed login attempts by IP and username (default: max 5 failures per 5 minutes -> `429 Too Many Requests`), recording `AUTH_LOGIN_RATE_LIMITED` in `admin_audit_logs`.

### 6.3 Backend-Enforced Role & Permission Matrix
All three owner-approved roles enforce least-privilege access at the FastAPI dependency layer (`Depends(require_permission(...))`):

| Capability / Endpoint Group | `OWNER` | `ADMINISTRATOR` | `AUTHORIZED_STAFF` |
|---|---|---|---|
| **Dashboard Overview** (stage counts & alerts) | Full | Allowed | Limited (production & assigned operational counters only) |
| **Customer Listing & Profile** | Full (audited phone reveal) | Allowed (masked phone; audited reveal) | Restricted (order-linked customer name/ref only; no raw phone list) |
| **Orders & Production Workflow** | Full | Allowed | Assigned / authorized operational view & permitted stage requests |
| **Fabric Catalogue (Public Fields)** | Full CRUD | Allowed CRUD | View-only (`GET` fabrics, colours, availability) |
| **Fabric Supplier / Procurement Data** | Full | Allowed (if granted) | **Denied (`403`)** |
| **Pricing Configurations & Quotations** | Full | Read + approved config requests | **Denied (`403`) by default** |
| **Measurement Reference** | Full (order-scoped, audited) | Authorized (order-scoped, audited) | Need-based on assigned active tailoring orders only (audited) |
| **Workshop Operations & Capacity View** | Full | Allowed | Read-only workload view |
| **Business Settings & Thresholds** | Full | Authorized non-critical settings | **Denied (`403`)** |
| **Staff Accounts, Roles & Session Revocation** | Full | Restricted (view staff list only; cannot elevate/modify `OWNER` or roles) | **Denied (`403`)** |
| **Reports & CSV/JSON Exports** | Full | Allowed | Limited (production workload summary only; no exports) |
| **Administrative Audit History** | Full | Authorized (operational events) | **Denied (`403`)** |

---

## 7. Integration Failure Handling & Resilience Strategy

1. **Per-Module Fault Isolation:** Every external call executes inside `BaseModuleAdapter` catching `httpx.TimeoutException`, `httpx.NetworkError`, `httpx.HTTPStatusError`, and Pydantic `ValidationError` (`CONTRACT_MISMATCH`). Failure of one module never raises an unhandled `500` on composite views.
2. **Strict Timeouts & Safe Retries:**
   - Default timeouts: `connect=2.0s`, `read=5.0s`, `write=5.0s`, `pool=2.0s`.
   - Automatic retry (`max_retries=1` with `250ms` backoff) applies **exclusively** to idempotent `GET` requests failing on transient transport errors or `502`/`503`/`504`.
   - Mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) are **never** auto-retried to prevent duplicate side effects (such as overwriting Module 02 inventory or double-submitting Module 07 transitions).
3. **Explicit `INTEGRATION_MODE` Gate:**
   - `INTEGRATION_MODE=live` *(Default)*: Uses real HTTP adapters; any module without a configured base URL returns `status="CONTRACT_UNCONFIGURED"`; unreachable configured modules return `status="UNAVAILABLE"`.
   - `INTEGRATION_MODE=mock_dev` *(Opt-in for local dev & tests only; blocked in `production`)*: Returns deterministic, realistic fixture records stamped with `status="MOCK_DEV"` and accompanied by a persistent UI warning banner (`MOCK_DEV — Development Fixture Data, Not Live Business Data`).
4. **No Silent Stale Caching:** Live operational endpoints fetch fresh state by default (`Cache-Control: no-store` on admin responses). If optional short-lived read memoization is enabled for static metadata (e.g., Module 02 categories), responses include `fetched_at` and `is_cached: true` and are never served past expiry as live data.

---

## 8. Localization, UX & Preview Architecture

1. **Mobile-First Workshop Usability:**
   - Touch-friendly targets (`>= 44px`), single-column stacked cards on mobile (`360px–767px`), two-column operational grids on tablet (`768px–1023px`), and persistent sidebar + dense tables on desktop (`>= 1024px`).
   - High-contrast status pills and plain business terminology tailored for non-technical shop owners.
2. **English (`en`) & Gujarati (`gu`) Localization:**
   - Complete UI dictionary coverage for navigation, headings, status labels, provenance warnings, form labels, confirmation modals, and error messages.
   - Canonical system identifiers (`FAB-001`, `FVAR-001`, `DSG-...`, `ORD-...`) and numeric INR amounts (`₹450.00`) remain invariant across locales to avoid operational confusion.
3. **Live Preview & Deployment Compatibility:**
   - Frontend dev server binds to `0.0.0.0` with host allowlist open for sandbox/reverse-proxy domains and proxies `/api` to the FastAPI backend (`0.0.0.0:8000`), ensuring browser code uses strictly relative URLs (`/api/v1/admin/...`).

---

## 9. Summary of Security Decisions

| Threat / Risk | Architectural Control |
|---|---|
| Credential theft / weak admin passwords | `bcrypt` hashing, zero default passwords, explicit bootstrap CLI, production secret validation on startup. |
| Session hijacking / fixation | Token regenerated on login, SHA-256 hashed in DB, `HttpOnly` + `SameSite=Lax` + `Secure` (prod), server-side revocation. |
| Cross-Site Request Forgery (CSRF) | Mandatory constant-time verified `X-CSRF-Token` header bound to active session on all state-changing calls. |
| Brute-force login attacks | Per-IP and per-account rate limiting returning `429` + audit log entry. |
| Frontend-only RBAC bypass | Every FastAPI endpoint declares explicit `require_permission(...)` dependencies verified in automated security tests. |
| Upstream secret leakage (`MODULE_02_ADMIN_API_KEY`) | Loaded only in backend `Settings` (`repr=False`); stripped from logs/errors; never exposed to browser or `AUTHORIZED_STAFF`. |
| Unauthorized PII / measurement snooping | Default phone masking, opaque refs, order-scoped measurement checks, `Cache-Control: no-store`, mandatory audit trail. |
| Audit tampering | `admin_audit_logs` exposed strictly via append-only service (`INSERT` + `SELECT` only; zero `UPDATE`/`DELETE` paths). |
| Stack trace / internal detail leakage | Global FastAPI exception handlers log technical tracebacks server-side with `correlation_id` and return sanitized error envelopes to clients. |

---

## 10. Phase 04 Implementation Notes — Admin Dashboard Overview (`v0.4.0`)

1. **Dashboard Overview & Integration Endpoints (`backend/app/api/v1/dashboard.py`):**
   - `GET /api/v1/admin/dashboard/overview`: Requires `dashboard:view_limited` at the router gate and applies backend field/module scoping inside `DashboardService`:
     - `OWNER` & `ADMINISTRATOR` (`dashboard:view_full` -> `access_scope="FULL"`): Receive full 7-module `integration_health`, full Module 02 variant breakdown, full Module 07 order counts (when verified), local Module 08 `governance_summary` (`security_events_last_24h_count` populated strictly for `OWNER`), and sanitized `recent_activity`.
     - `AUTHORIZED_STAFF` (`dashboard:view_limited` -> `access_scope="LIMITED"`): Receive workshop-only stage counts (`active_orders`, `in_cutting_orders`, `in_stitching_orders`, `in_finishing_orders`, `quality_check_orders`, `ready_for_delivery_orders`, `on_hold_orders`, `urgent_active_orders`), workshop-relevant `integration_health` (`MODULE_02`, `MODULE_06`, `MODULE_07`), and `None` for business-wide order totals, governance counters, and recent audit activity.
   - `GET /api/v1/admin/dashboard/integrations`: Requires `dashboard:view_full` (`403 PERMISSION_DENIED` + `PERMISSION_DENIED` security event when called by `AUTHORIZED_STAFF`).
2. **Adapter Layer (`backend/app/adapters/`):**
   - `SafeHttpTransport` (`base.py`): Enforces `connect=2.0s`, `read=5.0s` timeouts and a single `150ms` retry strictly on idempotent `GET` transport failures or `502`/`503`/`504`.
   - `Module02FabricAdapter` (`module02_fabrics.py`): Consumes verified public `GET /api/v1/fabrics`, `/api/v1/categories`, `/api/v1/colours`, and `/api/v1/variants` with strict Pydantic v2 validation (`StrictInt`, `StrictBool`, verified `availability_status` enum). Never exposes `MODULE_02_ADMIN_API_KEY` or supplier/procurement data.
   - `Module07OrderAdapter` (`module07_orders.py`): Defaults to `CONTRACT_UNCONFIGURED` (`data=None`, never `0`) until `MODULE_07_CONTRACT_VERIFIED=true` and `MODULE_07_BASE_URL` are explicitly configured (or `INTEGRATION_MODE=mock_dev` in non-production dev/tests).
   - `summarize_design_snapshot` (`module03_designs.py`): Read-only validator for Module 03 `DSG-*` (`schema_version="1.0.0"`) snapshots.
3. **Responsive Bilingual Shell (`frontend/src/`):**
   - Mobile-first `AdminLayout` with collapsible mobile drawer (`< lg`) and persistent desktop sidebar (`>= lg`), rendering **only** implemented & role-accessible sections (`/`, `/users`, `/activity-logs`, `/session`).
   - Full English (`en`) and Gujarati (`gu`) localization, unmistakable `MOCK_DEV` warning banner, 5-state `ProvenanceBadge`, and strict `"—"` rendering whenever a metric is `null`/unavailable.
