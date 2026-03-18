import { useState } from "react";
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

// ======================================================
// PRODUCTION BACKEND URL
// ======================================================
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function LoginPage() {
  const { login: authLogin } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);

  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

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
        toast.success("Welcome back!");
        navigate("/dashboard");
      } else {
        const result = await authLogin(email, password);
        if (result?.requires_2fa) {
          setRequires2FA(true);
          toast.info("Enter your 2FA code to continue");
        } else {
          toast.success("Welcome back!");
          navigate("/dashboard");
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

  // =====================================================
  // GITHUB LOGIN
  // =====================================================
  const handleGithubLogin = () => {
    if (githubLoading) return;

    setGithubLoading(true);

    window.location.href = `${BACKEND_URL}/api/auth/github`;
  };

  // =====================================================
  // GOOGLE LOGIN
  // =====================================================
  const handleGoogleLogin = () => {
    if (googleLoading) return;
    setGoogleLoading(true);
    window.location.href = `${BACKEND_URL}/api/auth/google`;
  };

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

          <Link to="/" className="flex lg:hidden mb-8">
            <Logo size="default" />
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>

          <h1 className="font-outfit font-bold text-3xl text-white mb-2">
            Welcome back
          </h1>

          <p className="text-zinc-400 mb-8">
            Sign in to your account to continue building
          </p>

          {/* GOOGLE LOGIN */}
          <Button
            onClick={handleGoogleLogin}
            disabled={googleLoading}
            className="w-full h-12 mb-4"
          >
            {googleLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              "Continue with Google"
            )}
          </Button>

          {/* GITHUB LOGIN */}
          <Button
            onClick={handleGithubLogin}
            disabled={githubLoading}
            variant="outline"
            className="w-full h-12 border-white/10 text-white hover:bg-white/5 mb-6"
          >
            {githubLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Github className="w-5 h-5 mr-2" />
                Continue with GitHub
              </>
            )}
          </Button>

          {/* EMAIL LOGIN FORM */}
          <form onSubmit={handleSubmit} className="space-y-6">

            {!requires2FA ? (
              <>
                <div>
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="login-email-input"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Label>Password</Label>
                    <Link to="/forgot-password" className="text-xs text-electric hover:underline">
                      Forgot password?
                    </Link>
                  </div>

                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      data-testid="login-password-input"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-3"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>

                </div>
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 rounded-lg bg-electric/10 border border-electric/20">
                  <ShieldCheck className="w-5 h-5 text-electric flex-shrink-0" />
                  <p className="text-sm text-zinc-300">
                    Two-factor authentication is enabled. Enter your 6-digit code from your authenticator app.
                  </p>
                </div>
                <div>
                  <Label>2FA Code</Label>
                  <Input
                    type="text"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                    className="text-center text-2xl tracking-[8px] font-mono"
                    required
                    autoFocus
                    data-testid="login-2fa-input"
                  />
                </div>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
              data-testid="login-submit-button"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {requires2FA ? "Verifying..." : "Signing in..."}
                </>
              ) : requires2FA ? (
                "Verify & Sign in"
              ) : (
                "Sign in"
              )}
            </Button>

            {requires2FA && (
              <button
                type="button"
                onClick={() => { setRequires2FA(false); setTotpCode(""); }}
                className="w-full text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Back to login
              </button>
            )}

          </form>

          <p className="text-center text-zinc-400 mt-8">
            Don't have an account?{" "}
            <Link to="/signup" className="text-electric hover:underline">
              Sign up for free
            </Link>
          </p>

        </motion.div>

      </div>
    </div>
  );
}
