import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
  Info,
  Layers,
  RefreshCw,
  Scissors,
  ShieldCheck,
} from "lucide-react";
import {
  AlertSeverity,
  DashboardOverviewPayload,
  IntegrationSourceStatus,
  fetchDashboardOverview,
} from "../api/dashboard";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { AuthDictionary } from "../i18n/dictionaries";
import { useI18n } from "../i18n/I18nProvider";

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return String(value);
}

interface SummaryCardProps {
  title: string;
  value: number | null | undefined;
  status: IntegrationSourceStatus;
  moduleCode: string;
  unavailableNote: string;
  testId: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  value,
  status,
  moduleCode,
  unavailableNote,
  testId,
}) => {
  const isAvailable = value !== null && value !== undefined;

  return (
    <article
      data-testid={testId}
      className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm flex flex-col justify-between gap-3"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-600 leading-snug">{title}</h3>
        <span className="text-[11px] font-mono font-semibold text-slate-400 shrink-0">
          {moduleCode}
        </span>
      </div>

      <div>
        <p
          data-testid={`${testId}-value`}
          data-available={isAvailable ? "true" : "false"}
          className={`text-2xl sm:text-3xl font-bold tracking-tight ${
            isAvailable ? "text-slate-900" : "text-slate-400"
          }`}
        >
          {formatMetric(value)}
        </p>
        {!isAvailable && (
          <p className="text-xs text-slate-500 mt-1">{unavailableNote}</p>
        )}
      </div>

      <div className="pt-1 border-t border-slate-100 flex items-center justify-between">
        <ProvenanceBadge status={status} compact />
      </div>
    </article>
  );
};

export const DashboardOverviewPage: React.FC = () => {
  const { t } = useI18n();
  const [overview, setOverview] = useState<DashboardOverviewPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadOverview = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setErrorMessage(null);
    try {
      const payload = await fetchDashboardOverview();
      setOverview(payload);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load overview.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview(false);
  }, [loadOverview]);

  if (loading && !overview) {
    return (
      <div
        role="status"
        className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm"
      >
        <RefreshCw
          className="h-6 w-6 text-slate-500 animate-spin mx-auto mb-3"
          aria-hidden="true"
        />
        <p className="text-sm font-medium text-slate-700">{t.loadingDashboard}</p>
      </div>
    );
  }

  if (errorMessage && !overview) {
    return (
      <div
        role="alert"
        className="bg-white rounded-2xl border border-red-200 p-6 sm:p-8 shadow-sm max-w-xl mx-auto"
      >
        <div className="flex items-center gap-3 text-red-700 mb-2">
          <AlertCircle className="h-6 w-6 shrink-0" aria-hidden="true" />
          <h1 className="text-lg font-semibold">{t.dashboardLoadErrorHeading}</h1>
        </div>
        <p className="text-sm text-slate-600 mb-5">{errorMessage}</p>
        <button
          type="button"
          onClick={() => void loadOverview(false)}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 min-h-[44px]"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          <span>{t.retryButton}</span>
        </button>
      </div>
    );
  }

  if (!overview) return null;

  const isFullScope = overview.access_scope === "FULL";
  const orderEnv = overview.order_overview;
  const fabricEnv = overview.fabric_overview;

  const resolvePendingTitle = (titleKey: string, fallbackCode: string): string => {
    const candidate = t[titleKey as keyof AuthDictionary];
    return typeof candidate === "string" ? candidate : fallbackCode;
  };

  const severityStyles: Record<
    AlertSeverity,
    { container: string; Icon: React.ComponentType<{ className?: string }> }
  > = {
    CRITICAL: {
      container: "border-red-200 bg-red-50/70 text-red-900",
      Icon: AlertCircle,
    },
    WARNING: {
      container: "border-amber-200 bg-amber-50/70 text-amber-950",
      Icon: AlertTriangle,
    },
    INFO: {
      container: "border-slate-200 bg-slate-50 text-slate-800",
      Icon: Info,
    },
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Unmistakable MOCK_DEV Warning Banner */}
      {overview.has_mock_data && (
        <div
          role="alert"
          data-testid="mock-dev-banner"
          className="rounded-xl border-2 border-amber-400 bg-amber-50 p-4 sm:p-5 shadow-sm"
        >
          <div className="flex items-start gap-3">
            <FlaskConical
              className="h-6 w-6 text-amber-800 shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <div>
              <h2 className="text-sm sm:text-base font-bold text-amber-950">
                {t.mockBannerTitle}
              </h2>
              <p className="text-xs sm:text-sm text-amber-900 mt-1">
                {t.mockBannerBody}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Page Heading & Refresh Control */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              {t.dashboardHeading}
            </h1>
            <span
              data-testid="integration-mode-chip"
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                overview.integration_mode === "mock_dev"
                  ? "bg-amber-100 text-amber-900 border-amber-300"
                  : "bg-emerald-50 text-emerald-800 border-emerald-200"
              }`}
            >
              {overview.integration_mode === "mock_dev"
                ? t.integrationModeMock
                : t.integrationModeLive}
            </span>
          </div>
          <p className="text-sm text-slate-600">
            {isFullScope ? t.dashboardFullSubtitle : t.dashboardLimitedSubtitle}
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <button
            type="button"
            disabled={refreshing}
            onClick={() => void loadOverview(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60 min-h-[42px]"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            <span>{refreshing ? t.refreshingButton : t.refreshButton}</span>
          </button>
        </div>
      </div>

      {/* Key Operational Summary Cards */}
      <section aria-labelledby="summary-cards-heading">
        <h2
          id="summary-cards-heading"
          className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3"
        >
          {t.summarySectionHeading}
        </h2>

        {isFullScope ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <SummaryCard
              testId="card-total-orders"
              title={t.cardTotalOrders}
              value={orderEnv.data?.total_orders ?? null}
              status={orderEnv.source_status}
              moduleCode="M07"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-active-production"
              title={t.cardActiveProductionOrders}
              value={orderEnv.data?.active_production_orders ?? null}
              status={orderEnv.source_status}
              moduleCode="M07"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-active-fabrics"
              title={t.cardActiveCatalogueFabrics}
              value={fabricEnv.data?.total_active_fabrics ?? null}
              status={fabricEnv.source_status}
              moduleCode="M02"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-admin-accounts"
              title={t.cardActiveAdminAccounts}
              value={overview.governance_summary?.active_admin_users_count ?? null}
              status={overview.governance_summary?.source_status ?? "VERIFIED"}
              moduleCode="M08"
              unavailableNote={t.metricNotAvailableNote}
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <SummaryCard
              testId="card-staff-active-orders"
              title={t.cardActiveWorkshopOrders}
              value={orderEnv.data?.active_orders ?? null}
              status={orderEnv.source_status}
              moduleCode="M07"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-staff-stitching"
              title={t.cardInStitchingOrders}
              value={orderEnv.data?.in_stitching_orders ?? null}
              status={orderEnv.source_status}
              moduleCode="M07"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-staff-ready"
              title={t.cardReadyForDeliveryOrders}
              value={orderEnv.data?.ready_for_delivery_orders ?? null}
              status={orderEnv.source_status}
              moduleCode="M07"
              unavailableNote={t.metricNotAvailableNote}
            />
            <SummaryCard
              testId="card-staff-available-variants"
              title={t.cardAvailableVariants}
              value={fabricEnv.data?.available_variants ?? null}
              status={fabricEnv.source_status}
              moduleCode="M02"
              unavailableNote={t.metricNotAvailableNote}
            />
          </div>
        )}
      </section>

      {/* Module 07 Order Status Overview & Module 02 Fabric Catalogue Overview */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Module 07 Order Status Overview */}
        <section
          data-testid="order-overview-section"
          aria-labelledby="order-section-heading"
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col"
        >
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div className="flex items-start gap-2.5">
              <Scissors className="h-5 w-5 text-slate-700 shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <h2 id="order-section-heading" className="text-base font-semibold text-slate-900">
                  {t.orderSectionHeading}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">{t.orderSectionSubtitle}</p>
              </div>
            </div>
            <ProvenanceBadge status={orderEnv.source_status} />
          </div>

          {orderEnv.data ? (
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-1">
              {isFullScope && (
                <>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.stagePendingReview}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(orderEnv.data.pending_review_orders)}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.stageAwaitingConfirmation}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(orderEnv.data.awaiting_confirmation_orders)}
                    </dd>
                  </div>
                </>
              )}
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageCutting}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.in_cutting_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageStitching}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.in_stitching_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageFinishing}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.in_finishing_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageQualityCheck}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.quality_check_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageReadyForDelivery}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.ready_for_delivery_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageOnHold}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.on_hold_orders)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.stageUrgentActive}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(orderEnv.data.urgent_active_orders)}
                </dd>
              </div>
              {isFullScope && (
                <>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.stageCompleted}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(orderEnv.data.completed_orders)}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.stageCancelled}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(orderEnv.data.cancelled_orders)}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          ) : (
            <div
              data-testid="order-unavailable-panel"
              className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 mt-1 flex-1 flex flex-col justify-center"
            >
              <p className="text-sm font-semibold text-slate-800">
                {t.orderUnavailableTitle} (—)
              </p>
              <p className="text-xs text-slate-600 mt-1">
                {orderEnv.error_message || t.metricNotAvailableNote}
              </p>
            </div>
          )}
        </section>

        {/* Module 02 Fabric Catalogue Overview */}
        <section
          data-testid="fabric-overview-section"
          aria-labelledby="fabric-section-heading"
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col"
        >
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div className="flex items-start gap-2.5">
              <Layers className="h-5 w-5 text-slate-700 shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <h2 id="fabric-section-heading" className="text-base font-semibold text-slate-900">
                  {t.fabricSectionHeading}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">{t.fabricSectionSubtitle}</p>
              </div>
            </div>
            <ProvenanceBadge status={fabricEnv.source_status} />
          </div>

          {fabricEnv.data ? (
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-1">
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricTotalActive}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(fabricEnv.data.total_active_fabrics)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricActiveCategories}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(fabricEnv.data.total_active_categories)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricDistinctColours}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(fabricEnv.data.total_distinct_colours)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricTotalVariants}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(fabricEnv.data.total_variants)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricAvailableVariants}</dt>
                <dd className="text-lg font-bold text-emerald-800 mt-0.5">
                  {formatMetric(fabricEnv.data.available_variants)}
                </dd>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                <dt className="text-xs text-slate-500">{t.fabricOutOfStockVariants}</dt>
                <dd className="text-lg font-bold text-slate-900 mt-0.5">
                  {formatMetric(fabricEnv.data.out_of_stock_variants)}
                </dd>
              </div>
              {isFullScope && (
                <>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.fabricLowStockVariants}</dt>
                    <dd className="text-lg font-bold text-amber-800 mt-0.5">
                      {formatMetric(fabricEnv.data.low_stock_variants)}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.fabricOnRequestVariants}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(fabricEnv.data.on_request_variants)}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
                    <dt className="text-xs text-slate-500">{t.fabricDiscontinuedVariants}</dt>
                    <dd className="text-lg font-bold text-slate-900 mt-0.5">
                      {formatMetric(fabricEnv.data.discontinued_variants)}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          ) : (
            <div
              data-testid="fabric-unavailable-panel"
              className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 mt-1 flex-1 flex flex-col justify-center"
            >
              <p className="text-sm font-semibold text-slate-800">
                {t.fabricUnavailableTitle} (—)
              </p>
              <p className="text-xs text-slate-600 mt-1">
                {fabricEnv.error_message || t.metricNotAvailableNote}
              </p>
            </div>
          )}
        </section>
      </div>

      {/* Pending Administrative Actions & Operational Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Administrative Actions */}
        <section
          aria-labelledby="pending-actions-heading"
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm"
        >
          <div className="flex items-start gap-2.5 mb-4">
            <ClipboardList
              className="h-5 w-5 text-slate-700 shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <div>
              <h2
                id="pending-actions-heading"
                className="text-base font-semibold text-slate-900"
              >
                {t.pendingActionsHeading}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">{t.pendingActionsSubtitle}</p>
            </div>
          </div>

          {overview.pending_actions.length === 0 ? (
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600 flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" aria-hidden="true" />
              <span>{t.pendingActionsEmpty}</span>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {overview.pending_actions.map((action) => (
                <li
                  key={action.action_code}
                  className="py-3 first:pt-0 last:pb-0 flex flex-wrap items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900">
                      {resolvePendingTitle(action.title_key, action.action_code)}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span className="text-[11px] font-mono text-slate-500">
                        {action.source_module}
                      </span>
                      <ProvenanceBadge status={action.source_status} compact />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-2.5 py-1 text-xs font-bold text-white min-w-[32px]">
                      {action.count}
                    </span>
                    {action.target_route && (
                      <Link
                        to={action.target_route}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-950"
                      >
                        <span>{t.openSectionLink}</span>
                        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Operational & Integration Alerts */}
        <section
          aria-labelledby="operational-alerts-heading"
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm"
        >
          <div className="flex items-start gap-2.5 mb-4">
            <AlertTriangle
              className="h-5 w-5 text-slate-700 shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <div>
              <h2
                id="operational-alerts-heading"
                className="text-base font-semibold text-slate-900"
              >
                {t.alertsHeading}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">{t.alertsSubtitle}</p>
            </div>
          </div>

          {overview.operational_alerts.length === 0 ? (
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600 flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" aria-hidden="true" />
              <span>{t.alertsEmpty}</span>
            </div>
          ) : (
            <ul className="space-y-3">
              {overview.operational_alerts.map((alert) => {
                const { container, Icon } = severityStyles[alert.severity];
                return (
                  <li
                    key={alert.alert_code}
                    className={`rounded-xl border p-3.5 ${container}`}
                  >
                    <div className="flex items-start gap-2.5">
                      <Icon className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                          <span className="text-xs font-mono font-semibold">
                            {alert.source_module} • {alert.severity}
                          </span>
                          <ProvenanceBadge status={alert.source_status} compact />
                        </div>
                        <p className="text-xs sm:text-sm leading-relaxed">{alert.message}</p>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      {/* Ecosystem Integration Health Indicators */}
      <section
        data-testid="integration-health-section"
        aria-labelledby="integrations-heading"
        className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm"
      >
        <div className="flex items-start gap-2.5 mb-4">
          <Activity className="h-5 w-5 text-slate-700 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h2 id="integrations-heading" className="text-base font-semibold text-slate-900">
              {t.integrationsHeading}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">{t.integrationsSubtitle}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {overview.integration_health.map((item) => (
            <div
              key={item.module_code}
              data-testid={`health-${item.module_code}`}
              className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 flex flex-col justify-between gap-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-mono font-bold text-slate-700">
                    {item.module_code}
                  </span>
                  <h3 className="text-sm font-semibold text-slate-900">
                    {item.module_name}
                  </h3>
                </div>
                <ProvenanceBadge status={item.source_status} compact />
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">{item.status_note}</p>
              {item.latency_ms !== null && (
                <p className="text-[11px] font-mono text-slate-500">
                  {t.latencyLabel}: {item.latency_ms} ms
                </p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Module 08 Local Governance Summary & Recent Activity (FULL scope only) */}
      {isFullScope && overview.governance_summary && (
        <section
          data-testid="governance-section"
          aria-labelledby="governance-heading"
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm space-y-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-emerald-700 shrink-0" aria-hidden="true" />
              <h2 id="governance-heading" className="text-base font-semibold text-slate-900">
                {t.governanceHeading}
              </h2>
            </div>
            <ProvenanceBadge status={overview.governance_summary.source_status} compact />
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl bg-slate-50 border border-slate-100 p-3.5">
              <dt className="text-xs text-slate-500">{t.governanceActiveUsers}</dt>
              <dd className="text-xl font-bold text-slate-900 mt-0.5">
                {overview.governance_summary.active_admin_users_count}
              </dd>
            </div>
            <div className="rounded-xl bg-slate-50 border border-slate-100 p-3.5">
              <dt className="text-xs text-slate-500">{t.governanceActiveSessions}</dt>
              <dd className="text-xl font-bold text-slate-900 mt-0.5">
                {overview.governance_summary.active_sessions_count}
              </dd>
            </div>
            <div className="rounded-xl bg-slate-50 border border-slate-100 p-3.5">
              <dt className="text-xs text-slate-500">{t.governanceSecurityEvents24h}</dt>
              <dd className="text-xl font-bold text-slate-900 mt-0.5">
                {overview.governance_summary.security_events_last_24h_count !== null
                  ? overview.governance_summary.security_events_last_24h_count
                  : "—"}
              </dd>
              {overview.governance_summary.security_events_last_24h_count === null && (
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {t.metricRoleRestrictedNote}
                </p>
              )}
            </div>
          </dl>

          {overview.recent_activity && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2.5">
                {t.recentActivityHeading}
              </h3>
              {overview.recent_activity.length === 0 ? (
                <p className="text-xs text-slate-500">{t.recentActivityEmpty}</p>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200 text-xs">
                    <thead className="bg-slate-50 text-slate-600">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold">{t.auditColAction}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t.auditColActor}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t.auditColResource}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t.auditColOutcome}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {overview.recent_activity.map((ev) => (
                        <tr key={ev.event_id}>
                          <td className="px-3 py-2 font-mono font-medium text-slate-900">
                            {ev.action_type}
                          </td>
                          <td className="px-3 py-2 text-slate-700">
                            {ev.actor_username || "—"}
                          </td>
                          <td className="px-3 py-2 font-mono text-slate-600">
                            {ev.resource_type}
                          </td>
                          <td className="px-3 py-2 font-mono font-semibold text-slate-800">
                            {ev.outcome}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
};
