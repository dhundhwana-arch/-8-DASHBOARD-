import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Lock } from "lucide-react";
import { ApiClientError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nProvider";

export const LoginPage: React.FC = () => {
  const { sessionData, login } = useAuth();
  const { t, toggleLocale } = useI18n();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (sessionData) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.code === "RATE_LIMIT_EXCEEDED" || err.status === 429) {
          setErrorMsg(t.rateLimitedError);
        } else if (err.status === 401) {
          setErrorMsg(t.invalidCredentialsError);
        } else {
          setErrorMsg(t.genericError);
        }
      } else {
        setErrorMsg(t.genericError);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-slate-100">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8">
        <div className="flex items-start justify-between gap-2 mb-6">
          <div>
            <p className="text-xs font-bold tracking-wider uppercase text-slate-500">
              {t.brandTitle}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">{t.moduleSubtitle}</p>
          </div>
          <button
            type="button"
            onClick={toggleLocale}
            className="text-xs font-medium px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 min-h-[36px]"
          >
            {t.languageSwitchLabel}
          </button>
        </div>

        <div className="flex items-center gap-2.5 mb-2">
          <Lock className="h-5 w-5 text-slate-700" aria-hidden="true" />
          <h1 className="text-xl font-semibold text-slate-900">{t.loginHeading}</h1>
        </div>
        <p className="text-sm text-slate-600 mb-6">{t.loginSubheading}</p>

        {errorMsg && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700"
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label
              htmlFor="admin-username"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              {t.usernameLabel}
            </label>
            <input
              id="admin-username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-slate-800 focus:outline-none min-h-[44px]"
            />
          </div>

          <div>
            <label
              htmlFor="admin-password"
              className="block text-sm font-medium text-slate-700 mb-1"
            >
              {t.passwordLabel}
            </label>
            <input
              id="admin-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-slate-800 focus:outline-none min-h-[44px]"
            />
          </div>

          <button
            type="submit"
            disabled={submitting || !username.trim() || !password}
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 min-h-[44px]"
          >
            {submitting ? t.signingInButton : t.signInButton}
          </button>
        </form>
      </div>
    </main>
  );
};
