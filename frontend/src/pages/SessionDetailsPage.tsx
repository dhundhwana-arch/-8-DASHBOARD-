import React, { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { SessionSummary } from "../api/client";
import { fetchMyActiveSessions } from "../api/dashboard";
import { useAuth } from "../auth/AuthContext";
import { ProvenanceBadge } from "../components/ProvenanceBadge";
import { useI18n } from "../i18n/I18nProvider";

export const SessionDetailsPage: React.FC = () => {
  const { sessionData } = useAuth();
  const { t } = useI18n();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchMyActiveSessions();
        if (!cancelled) setSessions(list);
      } catch {
        // Non-blocking fallback to current session summary
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!sessionData) return null;

  return (
    <section className="space-y-6 max-w-2xl">
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2.5 text-emerald-700">
            <ShieldCheck className="h-6 w-6 shrink-0" aria-hidden="true" />
            <h1 className="text-lg font-bold text-slate-900">{t.sessionActiveHeading}</h1>
          </div>
          <ProvenanceBadge status="VERIFIED" compact />
        </div>
        <p className="text-sm text-slate-600 mb-5">{t.sessionActiveNote}</p>

        <dl className="divide-y divide-slate-100 border border-slate-100 rounded-xl bg-slate-50 px-4 py-2 text-sm">
          <div className="py-2.5 flex justify-between gap-4">
            <dt className="text-slate-500">{t.usernameLabel}</dt>
            <dd className="font-medium text-slate-900">
              {sessionData.user.display_name} ({sessionData.user.username})
            </dd>
          </div>
          <div className="py-2.5 flex justify-between gap-4">
            <dt className="text-slate-500">{t.roleLabel}</dt>
            <dd className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
              {sessionData.user.role}
            </dd>
          </div>
          <div className="py-2.5 flex justify-between gap-4">
            <dt className="text-slate-500">{t.authModeLabel}</dt>
            <dd className="font-mono text-xs text-slate-700">
              {sessionData.auth_federation_status}
            </dd>
          </div>
          <div className="py-2.5 flex justify-between gap-4">
            <dt className="text-slate-500">{t.sessionIdLabel}</dt>
            <dd className="font-mono text-xs text-slate-700 truncate max-w-[240px]">
              {sessionData.session.session_id}
            </dd>
          </div>
        </dl>
      </div>

      {sessions.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">
            {t.sessionsListHeading}
          </h2>
          <ul className="divide-y divide-slate-100 text-xs">
            {sessions.map((s) => (
              <li key={s.session_id} className="py-2.5 flex items-center justify-between gap-3">
                <span className="font-mono text-slate-700 truncate">{s.session_id}</span>
                {s.is_current && (
                  <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                    {t.currentSessionTag}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};
