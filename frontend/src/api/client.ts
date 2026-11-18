/**
 * Relative API client (`/api/v1/admin/*`).
 *
 * Security invariants:
 * - Uses relative URLs only (never hardcoded localhost).
 * - Relies on HttpOnly cookie (`credentials: "include"`).
 * - Holds the CSRF token strictly in JS memory (never localStorage/sessionStorage).
 */

export type AdminRole = "OWNER" | "ADMINISTRATOR" | "AUTHORIZED_STAFF";

export interface AdminUser {
  public_id: string;
  username: string;
  display_name: string;
  role: AdminRole;
  preferred_locale: "en" | "gu";
  is_active: boolean;
  last_login_at: string | null;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface AuthSessionPayload {
  user: AdminUser;
  session: SessionSummary;
  csrf_token: string;
  permissions: string[];
  auth_federation_status: "STANDALONE_LOCAL";
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let inMemoryCsrfToken: string | null = null;

export function setInMemoryCsrfToken(token: string | null): void {
  inMemoryCsrfToken = token;
}

export function getInMemoryCsrfToken(): string | null {
  return inMemoryCsrfToken;
}

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (MUTATING_METHODS.has(method) && inMemoryCsrfToken) {
    headers.set("X-CSRF-Token", inMemoryCsrfToken);
  }

  const response = await fetch(`/api/v1/admin${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    let message = "Request failed.";
    try {
      const errJson = await response.json();
      if (errJson?.error) {
        code = errJson.error.code || code;
        message = errJson.error.message || message;
      }
    } catch {
      // Non-JSON error response; retain safe defaults
    }
    throw new ApiClientError(response.status, code, message);
  }

  return (await response.json()) as T;
}
