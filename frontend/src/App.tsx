import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { I18nProvider } from "./i18n/I18nProvider";
import { AuthenticatedGatePage } from "./pages/AuthenticatedGatePage";
import { LoginPage } from "./pages/LoginPage";

export const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/"
      element={
        <ProtectedRoute>
          <AuthenticatedGatePage />
        </ProtectedRoute>
      }
    />
    <Route
      path="/owner-governance"
      element={
        <ProtectedRoute requiredPermission="users:manage">
          <AuthenticatedGatePage />
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
