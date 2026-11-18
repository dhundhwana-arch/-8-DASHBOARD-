import React, { useEffect, useState } from "react";
import { AlertCircle, RefreshCw, Users } from "lucide-react";
import { AdminUser } from "../api/client";
import { fetchAdminUsers } from "../api/dashboard";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { useI18n } from "../i18n/I18nProvider";

export const AdminUsersPage: React.FC = () => {
  const { t } = useI18n();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await fetchAdminUsers();
        if (!cancelled) setUsers(rows);
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
          <Users className="h-6 w-6 text-slate-800 shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h1 className="text-xl font-bold text-slate-900">{t.usersPageHeading}</h1>
            <p className="text-sm text-slate-600 mt-0.5">{t.usersPageSubtitle}</p>
          </div>
        </div>
        <ProvenanceBadge status="VERIFIED" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">{t.usersColName}</th>
              <th className="px-4 py-3 text-left font-semibold">{t.usersColUsername}</th>
              <th className="px-4 py-3 text-left font-semibold">{t.usersColRole}</th>
              <th className="px-4 py-3 text-left font-semibold">{t.usersColStatus}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((u) => (
              <tr key={u.public_id}>
                <td className="px-4 py-3 font-medium text-slate-900">{u.display_name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{u.username}</td>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">
                  {u.role}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      u.is_active
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        : "bg-slate-100 text-slate-600 border border-slate-200"
                    }`}
                  >
                    {u.is_active ? t.statusActive : t.statusDisabled}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
