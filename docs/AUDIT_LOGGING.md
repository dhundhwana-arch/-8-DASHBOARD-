# ADMINISTRATIVE AUDIT LOGGING SPECIFICATION — MODULE 08

| Field | Value |
|---|---|
| **Table** | `admin_audit_logs` |
| **Service** | `backend/app/services/audit_service.py` (`AuditService`) |
| **Mutation Policy** | Strictly Append-Only (`INSERT` + `SELECT` only) |

---

## 1. Event Schema

Each row in `admin_audit_logs` records:
- `event_id`: Unique permanent identifier (`AUD-<16-HEX>`).
- `actor_user_id`, `actor_username`, `actor_role`: Identity snapshot at event time (`SET NULL` FK if an account is ever removed, preserving historical username/role).
- `action_type`: Canonical uppercase event code (`AuditAction`).
- `resource_type` & `resource_id`: Target domain and opaque identifier.
- `source_origin`: `ADMIN_DASHBOARD` (Module 08 action) vs `EXTERNAL_MODULE` (upstream event).
- `outcome`: `SUCCESS`, `FAILURE`, or `DENIED`.
- `is_security_event`: Distinguishes authentication/RBAC/governance/PII events (`True`) from routine workshop operational events (`False`).
- `change_summary`: Sanitized JSON metadata (`redact_sensitive_data`).
- `correlation_id` & `ip_address`: Request traceability metadata.
- `created_at`: UTC timestamp.

---

## 2. Phase 03 Covered Audit Actions

- **Bootstrap & Account Governance:** `OWNER_BOOTSTRAPPED`, `USER_CREATED`, `USER_UPDATED`, `USER_ROLE_CHANGED`, `USER_STATUS_CHANGED`, `USER_PASSWORD_CHANGED`, `USER_PASSWORD_RESET`, `USER_SESSIONS_REVOKED`.
- **Authentication & Session Lifecycle:** `AUTH_LOGIN_SUCCEEDED`, `AUTH_LOGIN_FAILED`, `AUTH_LOGIN_RATE_LIMITED`, `AUTH_LOGOUT`, `AUTH_SESSION_EXPIRED`, `AUTH_SESSION_REVOKED`, `AUTH_ALL_SESSIONS_REVOKED`.
- **Access Control & Request Integrity:** `CSRF_REJECTED`, `PERMISSION_DENIED`, `SECURITY_ACTION_PERFORMED`.
- **Sensitive Data Access Hooks (Ready for Phases 05 & 09):** `CUSTOMER_CONTACT_VIEWED`, `MEASUREMENT_VIEWED` (records justification and accessed field *names* only—never raw phone numbers or body dimensions).

---

## 3. Three-Layer Immutability Enforcement

1. **Service Interface:** `AuditService` exposes only `record_event`, `record_sensitive_data_access`, and `list_events`.
2. **ORM & Session Execution Guards:** SQLAlchemy `before_update`, `before_delete`, and `Session.do_orm_execute` listeners raise `AuditLogImmutabilityError` (`403 AUDIT_LOG_IMMUTABLE`) on any single-row or bulk `UPDATE`/`DELETE`.
3. **Database Triggers:** Alembic migration `0001_phase03_core_schema` and `install_audit_immutability_triggers` install `BEFORE UPDATE` and `BEFORE DELETE` triggers on both SQLite and PostgreSQL, blocking raw SQL tampering.
