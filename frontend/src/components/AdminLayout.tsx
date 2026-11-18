import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Scissors,
  Users,
  X,
} from "lucide-react";
import { AdminRole } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nProvider";

interface NavItemConfig {
  to: string;
  labelKey:
    | "navDashboardOverview"
    | "navAdminAccounts"
    | "navActivityLogs"
    | "navActiveSession";
  Icon: React.ComponentType<{ className?: string }>;
  requiredPermission?: string;
}

/**
 * Navigation contains ONLY implemented & role-accessible sections (Master Prompt §17).
 * Phase 05+ workflows (Customers, Orders, Pricing, Reports) are intentionally omitted until authorized.
 */
const NAV_ITEMS: NavItemConfig[] = [
  {
    to: "/",
    labelKey: "navDashboardOverview",
    Icon: LayoutDashboard,
    requiredPermission: "dashboard:view_limited",
  },
  {
    to: "/users",
    labelKey: "navAdminAccounts",
    Icon: Users,
    requiredPermission: "users:view",
  },
  {
    to: "/activity-logs",
    labelKey: "navActivityLogs",
    Icon: FileText,
    requiredPermission: "audit:view_operational",
  },
  {
    to: "/session",
    labelKey: "navActiveSession",
    Icon: KeyRound,
  },
];

export const AdminLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { sessionData, logout, hasPermission } = useAuth();
  const { t, toggleLocale } = useI18n();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!sessionData) return null;

  const roleLabels: Record<AdminRole, string> = {
    OWNER: t.roleOwner,
    ADMINISTRATOR: t.roleAdministrator,
    AUTHORIZED_STAFF: t.roleAuthorizedStaff,
  };

  const visibleNavItems = NAV_ITEMS.filter(
    (item) => !item.requiredPermission || hasPermission(item.requiredPermission)
  );

  const renderSidebarContent = (onItemSelect?: () => void) => (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100">
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-amber-500/20 border border-amber-400/40 flex items-center justify-center text-amber-300 shrink-0">
            <Scissors className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold tracking-wider uppercase text-amber-300 truncate">
              {t.brandTitle}
            </p>
            <p className="text-[11px] text-slate-400 truncate">{t.workshopLocationTag}</p>
          </div>
        </div>
      </div>

      <nav
        aria-label={t.navSectionHeading}
        className="flex-1 px-3 py-4 space-y-1 overflow-y-auto"
      >
        <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {t.navSectionHeading}
        </p>
        {visibleNavItems.map(({ to, labelKey, Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={onItemSelect}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors min-h-[44px] ${
                isActive
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{t[labelKey]}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <p className="text-xs font-medium text-white truncate">
          {sessionData.user.display_name}
        </p>
        <p className="text-[11px] text-slate-400 font-mono truncate mb-3">
          {sessionData.user.username} • {roleLabels[sessionData.user.role]}
        </p>
        <button
          type="button"
          onClick={() => void logout()}
          className="inline-flex items-center justify-center gap-2 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-100 hover:bg-slate-700 min-h-[40px]"
        >
          <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          <span>{t.signOutButton}</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900">
      {/* Persistent Desktop Sidebar (>= lg) */}
      <aside
        data-testid="desktop-sidebar"
        className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 z-20"
      >
        {renderSidebarContent()}
      </aside>

      {/* Collapsible Mobile Drawer (< lg) */}
      {mobileMenuOpen && (
        <div
          data-testid="mobile-drawer"
          className="fixed inset-0 z-40 flex lg:hidden"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="fixed inset-0 bg-slate-900/60"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <div className="relative flex w-full max-w-xs flex-1 flex-col bg-slate-900">
            <div className="absolute top-3 right-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label={t.closeMenuLabel}
                className="inline-flex items-center justify-center rounded-lg p-2.5 text-slate-300 hover:text-white hover:bg-slate-800 min-h-[44px] min-w-[44px]"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            {renderSidebarContent(() => setMobileMenuOpen(false))}
          </div>
        </div>
      )}

      {/* Main Content Column */}
      <div className="flex-1 flex flex-col lg:pl-64 min-w-0">
        <header className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(true)}
                aria-label={t.openMenuLabel}
                className="lg:hidden inline-flex items-center justify-center rounded-lg border border-slate-300 p-2 text-slate-700 hover:bg-slate-50 min-h-[44px] min-w-[44px]"
              >
                <Menu className="h-5 w-5" aria-hidden="true" />
              </button>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-500 truncate">
                  {t.moduleSubtitle}
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-0.5">
                  <span className="text-sm font-semibold text-slate-900 truncate">
                    {sessionData.user.display_name}
                  </span>
                  <span
                    data-testid="active-role-badge"
                    className="inline-flex items-center rounded-md bg-slate-100 border border-slate-300 px-2 py-0.5 text-[11px] font-mono font-semibold text-slate-800"
                  >
                    {roleLabels[sessionData.user.role]}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={toggleLocale}
                className="text-xs font-medium px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 min-h-[40px]"
              >
                {t.languageSwitchLabel}
              </button>
              <button
                type="button"
                onClick={() => void logout()}
                className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 text-slate-800 hover:bg-slate-50 min-h-[40px]"
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{t.signOutButton}</span>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
