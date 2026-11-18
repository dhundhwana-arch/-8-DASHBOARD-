import React from "react";
import { ShieldCheck, LogOut } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nProvider";

/**
 * Phase 03 Authenticated Access Gate ONLY.
 * Phase 04 Dashboard Overview pages, metrics, and navigation are intentionally omitted per Phase 03 scope.
 */
export const AuthenticatedGatePage: React.FC = () => {
  const { sessionData, logout } = useAuth();
  const { t, toggleLocale } = useI18n();

  if (!sessionData) return null;

  return (
    <main className="min-h-screen flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <div className="flex items-center justify-between gap-2 mb-6">
          <div>
            <p className="text-xs font-bold tracking-wider uppercase text-slate-500">
              {t.brandTitle}
            </p>
            <p className="text-xs text-slate-500">{t.moduleSubtitle}</p>
          </div>
          <button
            type="button"
            onClick={toggleLocale}
            className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 min-h-[36px]"
          >
            {t.languageSwitchLabel}
          </button>
        </div>

        <div className="flex items-center gap-2.5 text-emerald-700 mb-2">
          <ShieldCheck className="h-6 w-6 shrink-0" aria-hidden="true" />
          <h1 className="text-lg font-semibold text-slate-900">
            {t.sessionActiveHeading}
          </h1>
        </div>
        <p className="text-sm text-slate-600 mb-6">{t.sessionActiveNote}</p>

        <dl className="divide-y divide-slate-100 border border-slate-100 rounded-xl bg-slate-50 px-4 py-2 text-sm mb-6">
          <div className="py-2 flex justify-between gap-4">
            <dt className="text-slate-500">{t.usernameLabel}</dt>
            <dd className="font-medium text-slate-900">
              {sessionData.user.display_name} ({sessionData.user.username})
            </dd>
          </div>
          <div className="py-2 flex justify-between gap-4">
            <dt className="text-slate-500">{t.roleLabel}</dt>
            <dd className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
              {sessionData.user.role}
            </dd>
          </div>
          <div className="py-2 flex justify-between gap-4">
            <dt className="text-slate-500">{t.authModeLabel}</dt>
            <dd className="font-mono text-xs text-slate-700">
              {sessionData.auth_federation_status}
            </dd>
          </div>
          <div className="py-2 flex justify-between gap-4">
            <dt className="text-slate-500">{t.sessionIdLabel}</dt>
            <dd className="font-mono text-xs text-slate-700 truncate max-w-[220px]">
              {sessionData.session.session_id}
            </dd>
          </div>
        </dl>

        <button
          type="button"
          onClick={() => void logout()}
          className="inline-flex items-center justify-center gap-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 min-h-[44px]"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          {t.signOutButton}
        </button>
      </div>
    </main>
  );
};
