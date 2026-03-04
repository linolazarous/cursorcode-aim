import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Eye, EyeOff, Loader2, Github } from "lucide-react";
import Logo from "../components/Logo";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (error) {
      const message = error.response?.data?.detail || "Login failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  // Updated GitHub OAuth handler
  const handleGitHubLogin = () => {
    setGithubLoading(true);
    // Redirect directly to backend OAuth route
    // Replace YOUR_BACKEND_URL with your Render backend URL
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "https://your-backend.onrender.com";
    window.location.href = `${backendUrl}/auth/github`;
  };

  return (
    <div className="min-h-screen bg-void noise-bg flex">
      {/* Left Panel - Branding */}
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
            © 2025 CursorCode AI. All rights reserved.
          </p>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          {/* Mobile Logo */}
          <Link to="/" className="flex lg:hidden mb-8">
            <Logo size="default" />
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-8"
            data-testid="back-to-home-link"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>

          <h1 className="font-outfit font-bold text-3xl text-white mb-2">
            Welcome back
          </h1>
          <p className="text-zinc-400 mb-8">
            Sign in to your account to continue building
          </p>

          {/* GitHub OAuth Button */}
          <Button
            type="button"
            onClick={handleGitHubLogin}
            disabled={githubLoading}
            variant="outline"
            className="w-full h-12 border-white/10 text-white hover:bg-white/5 mb-6"
            data-testid="github-login-btn"
          >
            {githubLoading ? (
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
            ) : (
              <Github className="w-5 h-5 mr-2" />
            )}
            Continue with GitHub
          </Button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-void px-4 text-zinc-500">or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-12 focus:border-electric focus:ring-1 focus:ring-electric"
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-white">
                  Password
                </Label>
                <Link
                  to="/forgot-password"
                  className="text-sm text-electric hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-12 pr-12 focus:border-electric focus:ring-1 focus:ring-electric"
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                  data-testid="toggle-password-visibility"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
              data-testid="login-submit-btn"
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
            <Link
              to="/signup"
              className="text-electric hover:underline"
              data-testid="signup-link"
            >
              Sign up for free
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
