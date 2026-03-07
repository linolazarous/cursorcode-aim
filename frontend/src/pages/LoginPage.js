import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { ArrowLeft, Eye, EyeOff, Loader2, Github } from "lucide-react";
import Logo from "../components/Logo";
import api from "../lib/api";

const BACKEND_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // =====================================================
  // EMAIL LOGIN
  // =====================================================
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.post("/auth/login", { email, password });

      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // GITHUB LOGIN
  // =====================================================
  const handleGithubLogin = () => {
    setGithubLoading(true);
    window.location.href = `${BACKEND_URL}/api/auth/github`;
  };

  // =====================================================
  // GOOGLE LOGIN
  // =====================================================
  const handleGoogleLogin = () => {
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

          <p className="text-sm text-zinc-500">© 2025 CursorCode AI</p>
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

          {/* EMAIL FORM */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <Label>Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
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

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
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
