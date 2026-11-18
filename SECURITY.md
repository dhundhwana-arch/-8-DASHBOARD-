# SECURITY ARCHITECTURE & LIMITATIONS — MODULE 08

| Field | Value |
|---|---|
| **Project** | CUSTOM SHIRT STUDIO |
| **Module** | 08 / 08 — Small Business Admin Dashboard (`dhundhwana-arch/-8-DASHBOARD-`) |
| **Current Implementation Phase** | Phase 03 — Authentication, RBAC, Session Security & Audit Core |

---

## 1. Authentication Controls

1. **Zero Default Credentials:** Fresh databases contain `0` accounts (`admin_users` is empty). No default administrator username or password exists in code, migrations, or `.env.example`.
2. **Explicit Owner Bootstrap CLI:** The initial `OWNER` account is provisioned explicitly via `python -m app.cli.bootstrap_owner`, enforcing strong password requirements (`>= 12` characters, `<= 72` UTF-8 bytes, uppercase, lowercase, digit, special character, no common weak patterns, and no username substring) and recording `OWNER_BOOTSTRAPPED` in `admin_audit_logs`.
3. **Adaptive Password Hashing & Timing Protection:**
   - Passwords are hashed with `bcrypt` (`BCRYPT_ROUNDS >= 12` enforced in production).
   - Login explicitly caps password UTF-8 length at 72 bytes so `bcrypt` never silently truncates long inputs.
   - `verify_password_constant_time` performs a real `bcrypt.checkpw` against a precomputed dummy hash when a username does not exist, reducing timing-based account enumeration.
4. **Non-Enumerating Error Responses:** Unknown usernames, wrong passwords, and deactivated accounts all return `401 Unauthorized` with the identical error code (`INVALID_CREDENTIALS`) and message (`"Invalid username or password."`).
5. **Standalone Boundary (Module 01 Readiness):** Authentication currently runs via `LocalSessionAuthProvider` and explicitly reports `auth_federation_status = "STANDALONE_LOCAL"`. Federation with Module 01 is **not** claimed until an approved shared identity contract exists.

---

## 2. Session & Cookie Security

1. **Hashed-at-Rest Tokens:** Login generates a 256-bit CSPRNG opaque cookie token (`secrets.token_urlsafe(32)`). Only `SHA-256(token)` (`64` hex chars) is stored in `admin_sessions.token_hash`.
2. **Cookie Attributes:** Issued under `css_admin_session` with `HttpOnly=True`, `SameSite=Lax`, `Path=/api/v1/admin`, and `Secure=True` enforced in `APP_ENV=production`.
3. **Dual Expiration & Immediate Revocation:**
   - Enforces both absolute session TTL (`SESSION_TTL_MINUTES`, default 8h) and sliding idle timeout (`SESSION_IDLE_TIMEOUT_MINUTES`, default 2h), recording `AUTH_SESSION_EXPIRED` when exceeded.
   - Sessions are immediately revoked on logout, manual session revocation, `OWNER` session revocation, account deactivation, role modification, self password change (revokes all other sessions), and `OWNER` password reset (revokes all target sessions).
4. **CSRF Protection:**
   - Each session binds a deterministic HMAC-SHA256 CSRF token (`derive_session_csrf_token`) keyed by `SESSION_SECRET_KEY`, `session_id`, and `session_token_hash`, storing only `SHA-256(csrf_token)` in `admin_sessions.csrf_token_hash`.
   - The React SPA keeps `csrf_token` strictly in JavaScript memory (never `localStorage` or `sessionStorage`) and sends `X-CSRF-Token` on all `POST`, `PUT`, `PATCH`, and `DELETE` calls.
   - Missing or invalid tokens are rejected in constant time (`hmac.compare_digest`) with `403 CSRF_VALIDATION_FAILED` and recorded as `CSRF_REJECTED` in `admin_audit_logs`.

---

## 3. Backend Authorization (RBAC) & Governance

- Every protected endpoint enforces permissions on the FastAPI backend (`require_permission(...)`) backed by service-layer checks (`enforce_permission(...)`).
- Unauthorized attempts return `403 PERMISSION_DENIED` and commit an immutable `PERMISSION_DENIED` security audit event.
- Account creation, role assignment, account activation/deactivation, password resets, and cross-user session revocations require `Permission.USERS_MANAGE` (`OWNER` exclusively).
- Service-layer lockout protection forbids deactivating or demoting the last remaining active `OWNER` account (`409 CONFLICT`).

---

## 4. Secret Management & Redaction

- `SESSION_SECRET_KEY` and `MODULE_02_ADMIN_API_KEY` use Pydantic `SecretStr` (`repr=False`).
- `RedactingLogFilter`, `AuditService`, and FastAPI exception handlers recursively strip password fields, session/CSRF tokens, `Bearer` headers, cookies, database URLs with embedded credentials, raw customer phone fields, and raw measurement dictionaries before writing logs, audit summaries, or HTTP error payloads.
- Production startup (`APP_ENV=production`) fails fast if `SESSION_SECRET_KEY` is weak/default, `COOKIE_SECURE=false`, `INTEGRATION_MODE=mock_dev`, `BCRYPT_ROUNDS < 12`, or `CORS_ORIGINS` contains `*`. Interactive OpenAPI docs (`/docs`, `/openapi.json`) are disabled in production.

---

## 5. Known Security Limitations & Unresolved Risks

Passing the automated test suite does **not** guarantee complete security. The following limitations remain and must be accounted for in deployment and future phases:

1. **In-Process Rate Limiting:** `LoginRateLimiter` stores sliding-window counters in process memory. Multi-worker Uvicorn/Gunicorn deployments do not share counters across worker processes; a reverse-proxy rate limiter (e.g., Nginx/Cloudflare) or shared Redis store is required for multi-worker production deployments.
2. **Reverse-Proxy Client IP Trust:** `extract_client_ip` currently reads `request.client.host` directly and does not trust raw `X-Forwarded-For` headers (preventing trivial header spoofing). When deployed behind a trusted reverse proxy, Uvicorn's `--proxy-headers --forwarded-allow-ips=<trusted-proxy-ip>` must be configured accurately so rate limiting does not bucket all users under the proxy's IP.
3. **No Multi-Factor Authentication (MFA):** Phase 03 implements single-factor password authentication. Adding TOTP/WebAuthn for `OWNER` and `ADMINISTRATOR` accounts is recommended prior to internet-facing production exposure.
4. **Database Superuser Privilege Boundary:** Although `admin_audit_logs` enforces append-only immutability via service guards, SQLAlchemy ORM/Core listeners, and SQL `BEFORE UPDATE/DELETE` triggers, a compromised database superuser with DDL privileges (`DROP TRIGGER`) could still alter underlying storage. Production PostgreSQL deployments should connect using a least-privilege application DB role without DDL/trigger-drop ownership on `admin_audit_logs`.
5. **Module 01 Shared Authentication Pending:** Standalone Module 08 authentication is active; cross-module SSO/token federation remains blocked until Module 01 publishes a verified identity contract.
6. **Frontend Dev-Dependency Advisory Monitoring:** `npm install` reported upstream advisories in transitive dev/test dependencies (`jsdom` / Vitest toolchain, none shipped in the browser production bundle). Dependencies should be periodically updated and audited before production release.
