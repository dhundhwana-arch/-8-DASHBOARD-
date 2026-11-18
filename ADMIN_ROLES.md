# ADMINISTRATIVE ROLES & PERMISSIONS — MODULE 08

| Field | Value |
|---|---|
| **Project** | CUSTOM SHIRT STUDIO |
| **Module** | 08 / 08 — Small Business Admin Dashboard (`dhundhwana-arch/-8-DASHBOARD-`) |
| **Enforcement Layer** | FastAPI Dependencies (`require_permission`) + Service Layer (`enforce_permission`) |

---

## 1. Approved Roles

1. **`OWNER`** — Full administrative, operational, security-audit, and account-governance authority for the tailoring business. At least one active `OWNER` account must remain enabled at all times.
2. **`ADMINISTRATOR`** — Trusted day-to-day store/workshop manager. Permitted to manage operational workflows, catalogue administration, and operational reports, with **read-only** visibility into staff accounts and operational (non-security) audit events. Cannot create/modify admin users, alter `OWNER` accounts, change critical owner-only settings, or inspect security/governance audit trails.
3. **`AUTHORIZED_STAFF`** — Least-privilege workshop/tailoring staff role. Restricted to operational production views, assigned order transitions, read-only public fabric browsing (strictly **no** supplier/procurement access and **no** pricing configuration access), need-based order measurement checks, and internal workshop notes.

---

## 2. Backend Permission Matrix (`app/core/rbac.py`)

| Permission Code | `OWNER` | `ADMINISTRATOR` | `AUTHORIZED_STAFF` | Implementation Phase |
|---|---|---|---|---|
| `users:view` | Allowed | Allowed (Read-Only) | Denied (`403`) | **Phase 03 (Active)** |
| `users:manage` | **Allowed** | Denied (`403`) | Denied (`403`) | **Phase 03 (Active)** |
| `audit:view_all` | **Allowed** | Denied (`403`) | Denied (`403`) | **Phase 03 (Active)** |
| `audit:view_operational` | Allowed | Allowed | Denied (`403`) | **Phase 03 (Active)** |
| `dashboard:view_full` | Allowed | Allowed | Denied (`403`) | Phase 04 |
| `dashboard:view_limited` | Allowed | Allowed | Allowed | Phase 04 |
| `customers:list` | Allowed | Allowed | Denied (`403`) | Phase 05 |
| `customers:view_limited` | Allowed | Allowed | Allowed | Phase 05 |
| `customers:reveal_contact` | Allowed | Allowed | Denied (`403`) | Phase 05 |
| `orders:view_all` | Allowed | Allowed | Denied (`403`) | Phase 06 |
| `orders:view_assigned` | Allowed | Allowed | Allowed | Phase 06 |
| `orders:transition_request` | Allowed | Allowed | Allowed | Phase 06 |
| `fabrics:view` | Allowed | Allowed | Allowed (Read-Only) | Phase 07 |
| `fabrics:manage` | Allowed | Allowed | Denied (`403`) | Phase 07 |
| `fabrics:view_suppliers` | Allowed | Allowed | **Denied (`403`)** | Phase 07 |
| `pricing:view` | Allowed | Allowed | **Denied (`403`)** | Phase 08 |
| `pricing:manage_config` | Allowed | Allowed | **Denied (`403`)** | Phase 08 |
| `measurements:view_authorized` | Allowed | Allowed | Denied (`403`) | Phase 09 |
| `measurements:view_assigned_need` | Allowed | Allowed | Need-based (Order-scoped) | Phase 09 |
| `operations:view` | Allowed | Allowed | Allowed (Read-Only) | Phase 10 |
| `operations:manage` | Allowed | Allowed | Denied (`403`) | Phase 10 |
| `settings:view` | Allowed | Allowed | Denied (`403`) | Phase 10 |
| `settings:manage_non_critical` | Allowed | Allowed | Denied (`403`) | Phase 10 |
| `settings:manage_critical` | **Allowed** | Denied (`403`) | Denied (`403`) | Phase 10 |
| `reports:view_full` | Allowed | Allowed | Denied (`403`) | Phase 11 |
| `reports:view_limited` | Allowed | Allowed | Allowed | Phase 11 |
| `reports:export` | Allowed | Allowed | Denied (`403`) | Phase 11 |
| `internal_notes:view` | Allowed | Allowed | Allowed | Phase 06 / 10 |
| `internal_notes:write` | Allowed | Allowed | Allowed | Phase 06 / 10 |

---

## 3. Session & Privilege Change Guarantees

- **Immediate Revocation on Role or Status Change:** Whenever an `OWNER` modifies a user's `role` or sets `is_active = false`, `UserManagementService` atomically revokes every active session belonging to that user so stale privileges can never persist.
- **Sole-Owner Lockout Prevention:** The backend rejects (`409 CONFLICT`) any attempt to deactivate or demote an `OWNER` when no other active `OWNER` exists.
- **Frontend Visibility Is Advisory Only:** All authorization decisions are enforced on the backend before any database mutation or upstream adapter call occurs.
