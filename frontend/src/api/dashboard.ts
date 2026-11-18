/**
 * Typed Phase 04 Dashboard Overview & Phase 03 Governance API contracts.
 * Zero invented financial, supplier, customer PII, or measurement fields.
 */

import { AdminRole, AdminUser, SessionSummary, apiRequest } from "./client";

export type IntegrationSourceStatus =
  | "VERIFIED"
  | "MOCK_DEV"
  | "CONTRACT_UNCONFIGURED"
  | "UNAVAILABLE"
  | "CONTRACT_MISMATCH";

export type DashboardAccessScope = "FULL" | "LIMITED";
export type IntegrationMode = "live" | "mock_dev";
export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface IntegrationEnvelope<T> {
  module_code: string;
  module_name: string;
  source_status: IntegrationSourceStatus;
  is_verified_live: boolean;
  is_mock_data: boolean;
  checked_at: string;
  latency_ms: number | null;
  error_code: string | null;
  error_message: string | null;
  data: T | null;
}

export interface OrderStageCountItem {
  stage_code: string;
  count: number;
}

export interface OrderDashboardSummary {
  total_orders: number | null;
  pending_review_orders: number | null;
  completed_orders: number | null;
  awaiting_confirmation_orders: number | null;
  cancelled_orders: number | null;
  active_orders: number;
  active_production_orders: number;
  in_cutting_orders: number;
  in_stitching_orders: number;
  in_finishing_orders: number;
  quality_check_orders: number;
  ready_for_delivery_orders: number;
  on_hold_orders: number;
  urgent_active_orders: number;
  stage_breakdown: OrderStageCountItem[];
  upstream_warnings: string[];
}

export interface FabricDashboardSummary {
  total_active_fabrics: number;
  total_active_categories: number;
  total_distinct_colours: number;
  total_variants: number;
  available_variants: number | null;
  low_stock_variants: number | null;
  out_of_stock_variants: number | null;
  on_request_variants: number | null;
  discontinued_variants: number | null;
  unknown_status_variants: number | null;
  is_variant_breakdown_complete: boolean;
}

export interface ModuleIntegrationHealthItem {
  module_code: string;
  module_name: string;
  integration_role: string;
  source_status: IntegrationSourceStatus;
  is_verified_live: boolean;
  is_mock_data: boolean;
  latency_ms: number | null;
  status_note: string;
  checked_at: string;
}

export interface PendingAdminActionItem {
  action_code: string;
  title_key: string;
  count: number;
  source_module: string;
  source_status: IntegrationSourceStatus;
  target_route: string | null;
}

export interface OperationalAlertItem {
  alert_code: string;
  severity: AlertSeverity;
  source_module: string;
  source_status: IntegrationSourceStatus;
  message: string;
}

export interface LocalGovernanceSummary {
  source_status: IntegrationSourceStatus;
  active_admin_users_count: number;
  active_sessions_count: number;
  security_events_last_24h_count: number | null;
}

export interface RecentActivityPreviewItem {
  event_id: string;
  action_type: string;
  resource_type: string;
  outcome: string;
  actor_username: string | null;
  created_at: string;
}

export interface DashboardOverviewPayload {
  generated_at: string;
  access_scope: DashboardAccessScope;
  integration_mode: IntegrationMode;
  has_mock_data: boolean;
  order_overview: IntegrationEnvelope<OrderDashboardSummary>;
  fabric_overview: IntegrationEnvelope<FabricDashboardSummary>;
  integration_health: ModuleIntegrationHealthItem[];
  pending_actions: PendingAdminActionItem[];
  operational_alerts: OperationalAlertItem[];
  governance_summary: LocalGovernanceSummary | null;
  recent_activity: RecentActivityPreviewItem[] | null;
}

export interface AuditLogItem {
  event_id: string;
  actor_username: string | null;
  actor_role: AdminRole | null;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  outcome: string;
  is_security_event: boolean;
  correlation_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogListPayload {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

export function fetchDashboardOverview(): Promise<DashboardOverviewPayload> {
  return apiRequest<DashboardOverviewPayload>("/dashboard/overview");
}

export function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>("/users");
}

export function fetchAuditLogs(limit = 25, offset = 0): Promise<AuditLogListPayload> {
  return apiRequest<AuditLogListPayload>(`/audit-logs?limit=${limit}&offset=${offset}`);
}

export function fetchMyActiveSessions(): Promise<SessionSummary[]> {
  return apiRequest<SessionSummary[]>("/auth/sessions");
}
