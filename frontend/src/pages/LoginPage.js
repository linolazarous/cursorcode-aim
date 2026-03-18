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
            variant="outline"
            className="w-full h-12 mb-3 bg-white/[0.03] border-white/10 text-white hover:bg-white/[0.07] hover:border-white/20 transition-all"
            data-testid="login-google-btn"
          >
            {googleLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <GoogleIcon />
                Continue with Google
              </>
            )}
          </Button>

          {/* GITHUB LOGIN */}
          <Button
            onClick={handleGithubLogin}
            disabled={githubLoading}
            variant="outline"
            className="w-full h-12 bg-white/[0.03] border-white/10 text-white hover:bg-white/[0.07] hover:border-white/20 transition-all mb-6"
            data-testid="login-github-btn"
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

          {/* Divider */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-xs text-zinc-500 uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

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
