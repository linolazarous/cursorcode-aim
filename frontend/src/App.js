import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";

// Pages
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import DashboardPage from "./pages/DashboardPage";
import ProjectPage from "./pages/ProjectPage";
import SettingsPage from "./pages/SettingsPage";
import AdminPage from "./pages/AdminPage";
import PricingPage from "./pages/PricingPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import GitHubCallbackPage from "./pages/GitHubCallbackPage";
import GoogleCallbackPage from "./pages/GoogleCallbackPage";
import TemplatesPage from "./pages/TemplatesPage";
import TemplatePreviewPage from "./pages/TemplatePreviewPage";
import SharedProjectPage from "./pages/SharedProjectPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";
import ContactPage from "./pages/ContactPage";

// Protected Route Component – uses updated AuthContext (full user + localStorage sync)
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-electric border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !user.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ==================== PUBLIC ROUTES ==================== */}
          {/* These match backend exactly (no auth required) */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/shared/:shareId" element={<SharedProjectPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/contact" element={<ContactPage />} />

          {/* ==================== OAUTH CALLBACKS ==================== */}
          {/* Backend: POST /api/auth/github/callback & POST /api/auth/google/callback */}
          {/* These pages receive the code and return full TokenResponse (tokens + user) */}
          <Route path="/auth/github/callback" element={<GitHubCallbackPage />} />
          <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />

          {/* ==================== PROTECTED ROUTES ==================== */}
          {/* All use the updated AuthContext (user from /auth/me + localStorage sync) */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/project/:projectId"
            element={
              <ProtectedRoute>
                <ProjectPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/templates"
            element={
              <ProtectedRoute>
                <TemplatesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/templates/:templateId/preview"
            element={
              <ProtectedRoute>
                <TemplatePreviewPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminPage />
              </ProtectedRoute>
            }
          />

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        <Toaster position="top-right" theme="dark" richColors closeButton />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
