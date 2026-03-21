import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import Logo from "../components/Logo";

export default function GitHubCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth(); // only need refresh after OAuth success
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const errorParam = searchParams.get("error");

    if (errorParam) {
      setError(searchParams.get("error_description") || "GitHub authentication failed");
      return;
    }

    if (code) {
      handleGitHubCallback(code);
    } else {
      setError("No authorization code received from GitHub");
    }
  }, [searchParams]);

  // =====================================================
  // GITHUB OAUTH CALLBACK – matches backend exactly
  // POST /api/auth/github/callback?code=...
  // Returns full TokenResponse { access_token, refresh_token, user }
  // =====================================================
  const handleGitHubCallback = async (code) => {
    try {
      const response = await api.post(`/auth/github/callback?code=${code}`);
      const { access_token, refresh_token, user: userData } = response.data;

      // Full sync with updated AuthContext + api.js
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      localStorage.setItem("user", JSON.stringify(userData));

      await refreshUser(); // ensures context is up-to-date

      toast.success(`Welcome, ${userData.name || userData.email}!`);
      navigate("/dashboard");
    } catch (err) {
      console.error("GitHub callback error:", err);
      setError(err.response?.data?.detail || "GitHub authentication failed");
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-void noise-bg flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-md w-full text-center"
        >
          <Logo size="large" className="justify-center mb-8" />
          <div className="bg-void-paper border border-red-500/20 rounded-xl p-8">
            <h2 className="font-outfit font-bold text-2xl text-white mb-2">
              Authentication Failed
            </h2>
            <p className="text-red-400 mb-6">{error}</p>
            <button
              onClick={() => navigate("/login")}
              className="text-electric hover:underline"
            >
              Back to Login
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-void noise-bg flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center"
      >
        <Logo size="large" className="justify-center mb-8" />
        <Loader2 className="w-12 h-12 text-electric mx-auto mb-4 animate-spin" />
        <h2 className="font-outfit font-bold text-xl text-white mb-2">
          Connecting to GitHub...
        </h2>
        <p className="text-zinc-400">Please wait while we complete authentication</p>
      </motion.div>
    </div>
  );
}
