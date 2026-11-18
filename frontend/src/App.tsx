import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AdminLayout } from "./components/AdminLayout";
import { I18nProvider } from "./i18n/I18nProvider";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { DashboardOverviewPage } from "./pages/DashboardOverviewPage";
import { LoginPage } from "./pages/LoginPage";
import { SessionDetailsPage } from "./pages/SessionDetailsPage";

export const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/"
      element={
        <ProtectedRoute requiredPermission="dashboard:view_limited">
          <AdminLayout>
            <DashboardOverviewPage />
          </AdminLayout>
        </ProtectedRoute>
      }
    />
    <Route
      path="/users"
      element={
        <ProtectedRoute requiredPermission="users:view">
          <AdminLayout>
            <AdminUsersPage />
          </AdminLayout>
        </ProtectedRoute>
      }
    />
    <Route
      path="/activity-logs"
      element={
        <ProtectedRoute requiredPermission="audit:view_operational">
          <AdminLayout>
            <AuditLogsPage />
          </AdminLayout>
        </ProtectedRoute>
      }
    />
    <Route
      path="/session"
      element={
        <ProtectedRoute>
          <AdminLayout>
            <SessionDetailsPage />
          </AdminLayout>
        </ProtectedRoute>
      }
    />
    <Route
      path="/owner-governance"
      element={
        <ProtectedRoute requiredPermission="users:manage">
          <AdminLayout>
            <AdminUsersPage />
          </AdminLayout>
        </ProtectedRoute>
      }
    />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export const App: React.FC = () => (
  <I18nProvider>
    <AuthProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  </I18nProvider>
);

export default App;
