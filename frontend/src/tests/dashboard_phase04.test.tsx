import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AdminRole, AuthSessionPayload, setInMemoryCsrfToken } from "../api/client";
import { DashboardOverviewPayload } from "../api/dashboard";
import { AuthProvider } from "../auth/AuthContext";
import { I18nProvider } from "../i18n/I18nProvider";

function buildSession(
  role: AdminRole,
  permissions: string[],
  preferredLocale: "en" | "gu" = "en"
): AuthSessionPayload {
  return {
    user: {
      public_id: `ADM-${role}`,
      username: role.toLowerCase(),
      display_name: `${role} User`,
      role,
      preferred_locale: preferredLocale,
      is_active: true,
      last_login_at: "2026-11-16T08:00:00Z",
    },
    session: {
      session_id: `sess-${role}`,
      created_at: "2026-11-16T08:00:00Z",
      last_seen_at: "2026-11-16T08:00:00Z",
      expires_at: "2026-11-16T16:00:00Z",
      is_current: true,
    },
    csrf_token: "c".repeat(64),
    permissions,
    auth_federation_status: "STANDALONE_LOCAL",
  };
}

function renderDashboard(initialPath = "/") {
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

describe("Phase 04 Admin Dashboard Overview — Provenance, RBAC, Responsive Layout & Gujarati i18n", () => {
  beforeEach(() => {
    setInMemoryCsrfToken(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders '—' (never '0') for CONTRACT_UNCONFIGURED / UNAVAILABLE / CONTRACT_MISMATCH and exact counts for VERIFIED", async () => {
    const ownerSession = buildSession("OWNER", [
      "dashboard:view_limited",
      "dashboard:view_full",
      "users:view",
      "users:manage",
      "audit:view_operational",
      "audit:view_all",
    ]);

    const mixedProvenanceOverview: DashboardOverviewPayload = {
      generated_at: "2026-11-16T08:05:00Z",
      access_scope: "FULL",
      integration_mode: "live",
      has_mock_data: false,
      order_overview: {
        module_code: "MODULE_07",
        module_name: "tailoring-order-manager",
        source_status: "CONTRACT_UNCONFIGURED",
        is_verified_live: false,
        is_mock_data: false,
        checked_at: "2026-11-16T08:05:00Z",
        latency_ms: null,
        error_code: null,
        error_message: "Module 07 production contract not configured.",
        data: null,
      },
      fabric_overview: {
        module_code: "MODULE_02",
        module_name: "fabric-catalog-system",
        source_status: "VERIFIED",
        is_verified_live: true,
        is_mock_data: false,
        checked_at: "2026-11-16T08:05:00Z",
        latency_ms: 14,
        error_code: null,
        error_message: null,
        data: {
          total_active_fabrics: 7,
          total_active_categories: 3,
          total_distinct_colours: 11,
          total_variants: 19,
          available_variants: 15,
          low_stock_variants: 4,
          out_of_stock_variants: 0,
          on_request_variants: 0,
          discontinued_variants: 0,
          unknown_status_variants: 0,
          is_variant_breakdown_complete: true,
        },
      },
      integration_health: [
        {
          module_code: "MODULE_02",
          module_name: "fabric-catalog-system",
          integration_role: "Verified public GET /api/v1",
          source_status: "VERIFIED",
          is_verified_live: true,
          is_mock_data: false,
          latency_ms: 14,
          status_note: "Connected to Module 02.",
          checked_at: "2026-11-16T08:05:00Z",
        },
        {
          module_code: "MODULE_05",
          module_name: "clothing-price-engine",
          integration_role: "Official garment pricing",
          source_status: "UNAVAILABLE",
          is_verified_live: false,
          is_mock_data: false,
          latency_ms: null,
          status_note: "Upstream timeout.",
          checked_at: "2026-11-16T08:05:00Z",
        },
        {
          module_code: "MODULE_07",
          module_name: "tailoring-order-manager",
          integration_role: "Order lifecycle",
          source_status: "CONTRACT_MISMATCH",
          is_verified_live: false,
          is_mock_data: false,
          latency_ms: 22,
          status_note: "Schema mismatch detected.",
          checked_at: "2026-11-16T08:05:00Z",
        },
      ],
      pending_actions: [
        {
          action_code: "FABRIC_VARIANTS_ATTENTION",
          title_key: "pendingFabricAttention",
          count: 4,
          source_module: "MODULE_02",
          source_status: "VERIFIED",
          target_route: null,
        },
      ],
      operational_alerts: [
        {
          alert_code: "MODULE_05_UNAVAILABLE",
          severity: "CRITICAL",
          source_module: "MODULE_05",
          source_status: "UNAVAILABLE",
          message: "Module 05 unreachable.",
        },
      ],
      governance_summary: {
        source_status: "VERIFIED",
        active_admin_users_count: 3,
        active_sessions_count: 2,
        security_events_last_24h_count: 1,
      },
      recent_activity: [],
    };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(ownerSession), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mixedProvenanceOverview), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    renderDashboard("/");

    expect(
      await screen.findByRole("heading", { name: "Workshop Dashboard Overview" })
    ).toBeInTheDocument();

    // Unavailable M07 cards MUST show "—" (data-available="false"), NEVER "0"
    const totalOrdersVal = screen.getByTestId("card-total-orders-value");
    expect(totalOrdersVal).toHaveTextContent("—");
    expect(totalOrdersVal).toHaveAttribute("data-available", "false");
    expect(screen.getByTestId("order-unavailable-panel")).toBeInTheDocument();

    // Verified M02 card shows exact count 7
    const fabricsVal = screen.getByTestId("card-active-fabrics-value");
    expect(fabricsVal).toHaveTextContent("7");
    expect(fabricsVal).toHaveAttribute("data-available", "true");

    // No MOCK_DEV banner in live mode
    expect(screen.queryByTestId("mock-dev-banner")).not.toBeInTheDocument();

    // Provenance badges present for VERIFIED, CONTRACT_UNCONFIGURED, UNAVAILABLE, CONTRACT_MISMATCH
    expect(document.querySelector('[data-provenance-status="VERIFIED"]')).not.toBeNull();
    expect(
      document.querySelector('[data-provenance-status="CONTRACT_UNCONFIGURED"]')
    ).not.toBeNull();
    expect(
      document.querySelector('[data-provenance-status="UNAVAILABLE"]')
    ).not.toBeNull();
    expect(
      document.querySelector('[data-provenance-status="CONTRACT_MISMATCH"]')
    ).not.toBeNull();
  });

  it("displays unmistakable MOCK_DEV warning banner when mock_dev data is active", async () => {
    const adminSession = buildSession("ADMINISTRATOR", [
      "dashboard:view_limited",
      "dashboard:view_full",
      "users:view",
      "audit:view_operational",
    ]);

    const mockOverview: DashboardOverviewPayload = {
      generated_at: "2026-11-16T08:10:00Z",
      access_scope: "FULL",
      integration_mode: "mock_dev",
      has_mock_data: true,
      order_overview: {
        module_code: "MODULE_07",
        module_name: "tailoring-order-manager",
        source_status: "MOCK_DEV",
        is_verified_live: false,
        is_mock_data: true,
        checked_at: "2026-11-16T08:10:00Z",
        latency_ms: null,
        error_code: null,
        error_message: null,
        data: {
          total_orders: 18,
          pending_review_orders: 2,
          completed_orders: 11,
          awaiting_confirmation_orders: 1,
          cancelled_orders: 0,
          active_orders: 7,
          active_production_orders: 4,
          in_cutting_orders: 1,
          in_stitching_orders: 2,
          in_finishing_orders: 1,
          quality_check_orders: 0,
          ready_for_delivery_orders: 1,
          on_hold_orders: 0,
          urgent_active_orders: 1,
          stage_breakdown: [],
          upstream_warnings: [],
        },
      },
      fabric_overview: {
        module_code: "MODULE_02",
        module_name: "fabric-catalog-system",
        source_status: "MOCK_DEV",
        is_verified_live: false,
        is_mock_data: true,
        checked_at: "2026-11-16T08:10:00Z",
        latency_ms: null,
        error_code: null,
        error_message: null,
        data: {
          total_active_fabrics: 6,
          total_active_categories: 3,
          total_distinct_colours: 9,
          total_variants: 14,
          available_variants: 10,
          low_stock_variants: 2,
          out_of_stock_variants: 1,
          on_request_variants: 1,
          discontinued_variants: 0,
          unknown_status_variants: 0,
          is_variant_breakdown_complete: true,
        },
      },
      integration_health: [],
      pending_actions: [],
      operational_alerts: [],
      governance_summary: {
        source_status: "VERIFIED",
        active_admin_users_count: 3,
        active_sessions_count: 2,
        security_events_last_24h_count: null,
      },
      recent_activity: [],
    };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(adminSession), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mockOverview), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    renderDashboard("/");

    const banner = await screen.findByTestId("mock-dev-banner");
    expect(banner).toHaveTextContent(/Development Mock Data Active \(MOCK_DEV\)/i);
    expect(document.querySelector('[data-provenance-status="MOCK_DEV"]')).not.toBeNull();
  });

  it("scopes navigation, cards, mobile drawer, and Gujarati localization for AUTHORIZED_STAFF", async () => {
    const staffSession = buildSession(
      "AUTHORIZED_STAFF",
      ["dashboard:view_limited", "orders:view_assigned"],
      "gu"
    );

    const staffOverview: DashboardOverviewPayload = {
      generated_at: "2026-11-16T08:15:00Z",
      access_scope: "LIMITED",
      integration_mode: "live",
      has_mock_data: false,
      order_overview: {
        module_code: "MODULE_07",
        module_name: "tailoring-order-manager",
        source_status: "CONTRACT_UNCONFIGURED",
        is_verified_live: false,
        is_mock_data: false,
        checked_at: "2026-11-16T08:15:00Z",
        latency_ms: null,
        error_code: null,
        error_message: "Not configured",
        data: null,
      },
      fabric_overview: {
        module_code: "MODULE_02",
        module_name: "fabric-catalog-system",
        source_status: "CONTRACT_UNCONFIGURED",
        is_verified_live: false,
        is_mock_data: false,
        checked_at: "2026-11-16T08:15:00Z",
        latency_ms: null,
        error_code: null,
        error_message: "Not configured",
        data: null,
      },
      integration_health: [],
      pending_actions: [],
      operational_alerts: [],
      governance_summary: null,
      recent_activity: null,
    };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(staffSession), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(staffOverview), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    renderDashboard("/");

    // Gujarati dashboard heading rendered from preferred_locale="gu"
    expect(
      await screen.findByRole("heading", { name: "વર્કશોપ ડેશબોર્ડ ઝાંખી" })
    ).toBeInTheDocument();

    // Staff sees workshop-scoped cards, NOT full governance section or Admin Accounts nav
    expect(screen.getByTestId("card-staff-stitching")).toBeInTheDocument();
    expect(screen.queryByTestId("governance-section")).not.toBeInTheDocument();

    const sidebar = screen.getByTestId("desktop-sidebar");
    expect(within(sidebar).getByText("ડેશબોર્ડ ઝાંખી")).toBeInTheDocument();
    expect(within(sidebar).getByText("સક્રિય સત્ર")).toBeInTheDocument();
    expect(within(sidebar).queryByText("એડમિન ખાતાઓ")).not.toBeInTheDocument();
    expect(within(sidebar).queryByText("પ્રવૃત્તિ અને ઓડિટ લોગ")).not.toBeInTheDocument();

    // Responsive mobile drawer opens and closes cleanly
    await userEvent.click(screen.getByRole("button", { name: "નેવિગેશન મેનૂ ખોલો" }));
    expect(screen.getByTestId("mobile-drawer")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "નેવિગેશન મેનૂ બંધ કરો" }));
    expect(screen.queryByTestId("mobile-drawer")).not.toBeInTheDocument();
  });

  it("handles upstream /dashboard/overview fetch failure gracefully and recovers on Retry", async () => {
    const ownerSession = buildSession("OWNER", [
      "dashboard:view_limited",
      "dashboard:view_full",
    ]);

    const recoveredOverview: DashboardOverviewPayload = {
      generated_at: "2026-11-16T08:20:00Z",
      access_scope: "FULL",
      integration_mode: "live",
      has_mock_data: false,
      order_overview: {
        module_code: "MODULE_07",
        module_name: "tailoring-order-manager",
        source_status: "CONTRACT_UNCONFIGURED",
        is_verified_live: false,
        is_mock_data: false,
        checked_at: "2026-11-16T08:20:00Z",
        latency_ms: null,
        error_code: null,
        error_message: "Unconfigured",
        data: null,
      },
      fabric_overview: {
        module_code: "MODULE_02",
        module_name: "fabric-catalog-system",
        source_status: "CONTRACT_UNCONFIGURED",
        is_verified_live: false,
        is_mock_data: false,
        checked_at: "2026-11-16T08:20:00Z",
        latency_ms: null,
        error_code: null,
        error_message: "Unconfigured",
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

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(ownerSession), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: { code: "UPSTREAM_ERROR", message: "Temporary gateway error" },
          }),
          { status: 502, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(recoveredOverview), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    renderDashboard("/");

    expect(
      await screen.findByRole("heading", { name: /Unable to load dashboard overview/i })
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("heading", { name: "Workshop Dashboard Overview" })
    ).toBeInTheDocument();
  });
});
