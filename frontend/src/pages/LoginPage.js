import { useState, useEffect } from "react";           // ← added useEffect
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { ArrowLeft, Eye, EyeOff, Loader2, Github, ShieldCheck } from "lucide-react";
import Logo from "../components/Logo";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GoogleIcon = () => (
  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A11.96 11.96 0 0 0 1 12c0 1.94.46 3.77 1.18 5.07l3.66-2.84z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

export default function LoginPage() {
  const { login: authLogin, isAuthenticated } = useAuth();   // ← added isAuthenticated
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);

  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // 🔥 AUTO-REDIRECT WHEN AUTH STATE UPDATES (this fixes the race condition)
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // =====================================================
  // EMAIL LOGIN (with 2FA support)
  // =====================================================
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);

    try {
      if (requires2FA) {
        await authLogin(email, password, totpCode);
        toast.success("Welcome back! 2FA verified.");
        // No manual navigate here anymore – useEffect will catch it
      } else {
        const result = await authLogin(email, password);

        if (result?.requires_2fa) {
          setRequires2FA(true);
          setTotpCode("");
          toast.info("Enter your 2FA code to continue");
        } else {
          toast.success("Welcome back!");
          // No manual navigate here anymore – useEffect will catch it
        }
      }
    } catch (error) {
      console.error("Login error:", error);
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Invalid email or password";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  // GitHub & Google handlers stay exactly the same
  const handleGithubLogin = () => {
    if (githubLoading) return;
    setGithubLoading(true);
    window.location.href = `${BACKEND_URL}/api/auth/github`;
  };

  const handleGoogleLogin = () => {
    if (googleLoading) return;
    setGoogleLoading(true);
    window.location.href = `${BACKEND_URL}/api/auth/google`;
  };

  // ... rest of your JSX is unchanged (I kept it exactly the same)
  return (
    <div className="min-h-screen bg-void noise-bg flex">
      {/* LEFT PANEL */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-void-paper border-r border-white/5">
        <div className="absolute inset-0 bg-hero-glow" />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <Link to="/">
            <Logo size="large" />
          </Link>

          <div>
            <h2 className="font-outfit font-bold text-4xl text-white mb-4">
              Build Anything.
              <br />
              <span className="text-electric">Automatically.</span>
            </h2>

            <p className="text-zinc-400 text-lg max-w-md">
              The world's most powerful autonomous AI software engineering platform.
            </p>
          </div>

          <p className="text-sm text-zinc-500">
            © {new Date().getFullYear()} CursorCode AI
          </p>
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          {/* ... all your existing JSX (Google, GitHub, form, etc.) is unchanged ... */}
          {/* (I omitted it here for brevity – just keep everything from <Link to="/" ... down to the end) */}
        </motion.div>
      </div>
    </div>
  );
}
