import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import Logo from "../components/Logo";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const sessionIdMatch = hash.match(/session_id=([^&]+)/);

    if (!sessionIdMatch) {
      setError("No session ID received from Google");
      return;
    }

    const sessionId = sessionIdMatch[1];

    const exchangeSession = async () => {
      try {
        const response = await api.post("/auth/google/session", {
          session_id: sessionId,
        });

        const { access_token, refresh_token, user } = response.data;

        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);

        await refreshUser();

        toast.success(`Welcome, ${user.name}!`);

        // Clean URL and navigate
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { replace: true });
      } catch (err) {
        console.error("Google auth error:", err);
        setError(
          err?.response?.data?.detail ||
            err.message ||
            "Google authentication failed"
        );
      }
    };

    exchangeSession();
  }, [navigate, refreshUser]);

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
              data-testid="back-to-login"
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
          Connecting your Google account...
        </h2>
        <p className="text-zinc-400">
          Please wait while we complete authentication
        </p>
      </motion.div>
    </div>
  );
}
