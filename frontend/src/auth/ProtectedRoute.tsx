import React from "react";
import { Navigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "./AuthContext";
import { useI18n } from "../i18n/I18nProvider";

interface ProtectedRouteProps {
  requiredPermission?: string;
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requiredPermission,
  children,
}) => {
  const { sessionData, isLoading, hasPermission } = useAuth();
  const { t } = useI18n();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-slate-600">
        <p role="status">{t.loadingSession}</p>
      </div>
    );
  }

  if (!sessionData) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
        <div
          role="alert"
          className="max-w-md w-full bg-white border border-amber-200 rounded-xl p-6 shadow-sm"
        >
          <div className="flex items-center gap-3 text-amber-700 mb-2">
            <ShieldAlert className="h-6 w-6 shrink-0" aria-hidden="true" />
            <h1 className="text-lg font-semibold">{t.accessDeniedHeading}</h1>
          </div>
          <p className="text-sm text-slate-600">{t.accessDeniedMessage}</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
