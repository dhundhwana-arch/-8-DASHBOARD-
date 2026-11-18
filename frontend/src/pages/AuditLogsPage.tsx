import React, { useEffect, useState } from "react";
import { AlertCircle, FileText, RefreshCw } from "lucide-react";
import { AuditLogItem, fetchAuditLogs } from "../api/dashboard";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { useI18n } from "../i18n/I18nProvider";

export const AuditLogsPage: React.FC = () => {
  const { t } = useI18n();
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchAuditLogs(30, 0);
        if (!cancelled) setItems(res.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t.genericError);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t.genericError]);

  if (loading) {
    return (
      <div role="status" className="bg-white rounded-2xl border border-slate-200 p-8 text-center">
        <RefreshCw className="h-5 w-5 animate-spin text-slate-500 mx-auto mb-2" />
        <p className="text-sm text-slate-600">{t.loadingDashboard}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="bg-white rounded-2xl border border-red-200 p-6 text-red-700 flex items-center gap-3">
        <AlertCircle className="h-5 w-5 shrink-0" />
        <span className="text-sm">{error}</span>
      </div>
    );
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <FileText className="h-6 w-6 text-slate-800 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">{t.auditPageHeading}</h1>
            <p className="text-sm text-slate-600 mt-0.5">{t.auditPageSubtitle}</p>
          </div>
        </div>
        <ProvenanceBadge status="VERIFIED" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
        {items.length === 0 ? (
          <p className="p-6 text-sm text-slate-600">{t.recentActivityEmpty}</p>
        ) : (
          <table className="min-w-full divide-y divide-slate-200 text-xs sm:text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">{t.auditColTime}</th>
                <th className="px-4 py-3 text-left font-semibold">{t.auditColActor}</th>
                <th className="px-4 py-3 text-left font-semibold">{t.auditColAction}</th>
                <th className="px-4 py-3 text-left font-semibold">{t.auditColResource}</th>
                <th className="px-4 py-3 text-left font-semibold">{t.auditColOutcome}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((row) => (
                <tr key={row.event_id}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600 whitespace-nowrap">
                    {row.created_at}
                  </td>
                  <td className="px-4 py-3 text-slate-800">{row.actor_username || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-900">
                    {row.action_type}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">
                    {row.resource_type}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">
                    {row.outcome}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};
