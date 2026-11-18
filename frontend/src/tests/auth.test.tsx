import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { getInMemoryCsrfToken, setInMemoryCsrfToken } from "../api/client";
import { DashboardOverviewPayload } from "../api/dashboard";
import { AuthProvider } from "../auth/AuthContext";
import { I18nProvider } from "../i18n/I18nProvider";

function renderAppAt(initialPath: string) {
  return render(
    <I18nProvider>
      <AuthProvider>
        <MemoryRouter
          initialEntries={[initialPath]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <AppRoutes />
        </MemoryRouter>
      </AuthProvider>
    </I18nProvider>
  );
}

const minimalLiveOverview: DashboardOverviewPayload = {
  generated_at: "2026-11-16T08:00:00Z",
  access_scope: "FULL",
  integration_mode: "live",
  has_mock_data: false,
  order_overview: {
    module_code: "MODULE_07",
    module_name: "tailoring-order-manager",
    source_status: "CONTRACT_UNCONFIGURED",
    is_verified_live: false,
    is_mock_data: false,
    checked_at: "2026-11-16T08:00:00Z",
    latency_ms: null,
    error_code: null,
    error_message: "Module 07 contract not yet configured.",
    data: null,
  },
  fabric_overview: {
    module_code: "MODULE_02",
    module_name: "fabric-catalog-system",
    source_status: "CONTRACT_UNCONFIGURED",
    is_verified_live: false,
    is_mock_data: false,
    checked_at: "2026-11-16T08:00:00Z",
    latency_ms: null,
    error_code: null,
    error_message: "Module 02 base URL not configured.",
    data: null,
  },
  integration_health: [],
  pending_actions: [],
  operational_alerts: [],
  governance_summary: {
    source_status: "VERIFIED",
    active_admin_users_count: 1,
    active_sessions_count: 1,
    security_events_last_24h_count: 0,
  },
  recent_activity: [],
};

describe("Phase 03–04 Frontend Auth Gate, CSRF Memory Binding & Route Protection", () => {
  beforeEach(() => {
    setInMemoryCsrfToken(null);
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("redirects unauthenticated users from protected route to /login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "AUTHENTICATION_REQUIRED", message: "Auth required" },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    );

    renderAppAt("/");

    expect(
      await screen.findByRole("heading", { name: /Administrator Sign In/i })
    ).toBeInTheDocument();
  });

  it("switches login labels cleanly between English and Gujarati", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: "AUTHENTICATION_REQUIRED" } }), {
        status: 401,
      })
    );

    renderAppAt("/login");
    const toggleBtn = await screen.findByRole("button", { name: /ગુજરાતી/i });
    await userEvent.click(toggleBtn);

    expect(screen.getByRole("heading", { name: "એડમિન સાઇન ઇન" })).toBeInTheDocument();
    expect(screen.getByLabelText("વપરાશકર્તા નામ")).toBeInTheDocument();
    expect(screen.getByLabelText("પાસવર્ડ")).toBeInTheDocument();
  });

  it("displays generic error on 401 invalid login and rate-limit warning on 429", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { code: "AUTHENTICATION_REQUIRED" } }), {
          status: 401,
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: {
              code: "INVALID_CREDENTIALS",
              message: "Invalid username or password.",
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: {
              code: "RATE_LIMIT_EXCEEDED",
              message: "Too many login attempts.",
            },
          }),
          { status: 429, headers: { "Content-Type": "application/json" } }
        )
      );

    renderAppAt("/login");
    const userField = await screen.findByLabelText("Username");
    const pwField = screen.getByLabelText("Password");
    const submitBtn = screen.getByRole("button", { name: "Sign In" });

    await userEvent.type(userField, "unknown_admin");
    await userEvent.type(pwField, "WrongPass#1234");
    await userEvent.click(submitBtn);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid username or password."
    );

    await userEvent.click(submitBtn);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many login attempts. Please wait before trying again."
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("logs in, keeps CSRF token exclusively in memory, and sends X-CSRF-Token on logout", async () => {
    const csrfValue = "a".repeat(64);
    const sessionPayload = {
      user: {
        public_id: "ADM-0001",
        username: "owner_main",
        display_name: "Workshop Owner",
        role: "OWNER",
        preferred_locale: "en",
        is_active: true,
        last_login_at: "2026-11-16T06:00:00Z",
      },
      session: {
        session_id: "sess-1234",
        created_at: "2026-11-16T06:00:00Z",
        last_seen_at: "2026-11-16T06:00:00Z",
        expires_at: "2026-11-16T14:00:00Z",
        is_current: true,
      },
      csrf_token: csrfValue,
      permissions: [
        "dashboard:view_limited",
        "dashboard:view_full",
        "users:view",
        "users:manage",
        "audit:view_operational",
        "audit:view_all",
      ],
      auth_federation_status: "STANDALONE_LOCAL",
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      // 1. /auth/me -> 401
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { code: "AUTHENTICATION_REQUIRED" } }), {
          status: 401,
        })
      )
      // 2. /auth/login -> 200
      .mockResolvedValueOnce(
        new Response(JSON.stringify(sessionPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      // 3. /dashboard/overview -> 200
      .mockResolvedValueOnce(
        new Response(JSON.stringify(minimalLiveOverview), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      // 4. /auth/logout -> 200
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: "logged_out" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    renderAppAt("/login");
    await userEvent.type(await screen.findByLabelText("Username"), "owner_main");
    await userEvent.type(screen.getByLabelText("Password"), "Owner#Secure2026!");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByRole("heading", { name: /Workshop Dashboard Overview/i })
    ).toBeInTheDocument();

    // CSRF token is held in memory only — never written to browser storage
    expect(getInMemoryCsrfToken()).toBe(csrfValue);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);

    const signOutButtons = screen.getAllByRole("button", { name: /Sign Out/i });
    await userEvent.click(signOutButtons[0]);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Administrator Sign In/i })
      ).toBeInTheDocument();
    });
    expect(getInMemoryCsrfToken()).toBeNull();

    const logoutCall = fetchMock.mock.calls.find(
      (call) => call[0] === "/api/v1/admin/auth/logout"
    );
    expect(logoutCall).toBeDefined();
    const sentHeaders = logoutCall?.[1]?.headers as Headers;
    expect(sentHeaders.get("X-CSRF-Token")).toBe(csrfValue);
  });

  it("blocks AUTHORIZED_STAFF from OWNER-restricted route via permission guard", async () => {
    const staffPayload = {
      user: {
        public_id: "ADM-0003",
        username: "tailor_staff",
        display_name: "Tailor Staff",
        role: "AUTHORIZED_STAFF",
        preferred_locale: "en",
        is_active: true,
        last_login_at: "2026-11-16T06:00:00Z",
      },
      session: {
        session_id: "sess-staff-99",
        created_at: "2026-11-16T06:00:00Z",
        last_seen_at: "2026-11-16T06:00:00Z",
        expires_at: "2026-11-16T14:00:00Z",
        is_current: true,
      },
      csrf_token: "b".repeat(64),
      permissions: ["dashboard:view_limited", "orders:view_assigned"],
      auth_federation_status: "STANDALONE_LOCAL",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(staffPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderAppAt("/owner-governance");

    expect(
      await screen.findByRole("heading", { name: /Access Restricted/i })
    ).toBeInTheDocument();
  });
});
