import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, Eye, EyeOff, Loader2, CheckCircle2, Github } from "lucide-react";
import Logo from "../components/Logo";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const passwordStrength = () => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    return strength;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await signup(name, email, password);
      toast.success("Account created! Please verify your email.");
      navigate("/dashboard");
    } catch (error) {
      const message = error.response?.data?.detail || "Signup failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Updated GitHub signup redirect
  const handleGitHubSignup = () => {
    setGithubLoading(true);
    const backendUrl = process.env.REACT_APP_BACKEND_URL; // Vercel env variable
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
              Start building
              <br />
              <span className="text-electric">in minutes</span>
            </h2>
            <p className="text-zinc-400 text-lg max-w-md mb-8">
              Get 10 free AI credits to create your first project. No credit card required.
            </p>

            <div className="space-y-4">
              {[
                "Multi-agent AI system powered by xAI Grok",
                "One-click deployment to CursorCode.app",
                "Full-stack applications from plain English",
              ].map((feature) => (
                <div key={feature} className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald" />
                  <span className="text-white">{feature}</span>
                </div>
              ))}
            </div>
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
          <Link to="/" className="flex lg:hidden mb-8">
            <Logo size="default" />
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>

          <h1 className="font-outfit font-bold text-3xl text-white mb-2">
            Create your account
          </h1>
          <p className="text-zinc-400 mb-8">
            Start building with 10 free AI credits
          </p>

          {/* GitHub OAuth Button */}
          <Button
            type="button"
            onClick={handleGitHubSignup}
            disabled={githubLoading}
            variant="outline"
            className="w-full h-12 border-white/10 text-white hover:bg-white/5 mb-6"
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
              <Label htmlFor="name" className="text-white">Full Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-12 focus:border-electric focus:ring-1 focus:ring-electric"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-white">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-12 focus:border-electric focus:ring-1 focus:ring-electric"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-white">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-12 pr-12 focus:border-electric focus:ring-1 focus:ring-electric"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              {password && (
                <div className="mt-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          passwordStrength() >= level
                            ? level <= 2 ? "bg-yellow-500" : "bg-emerald"
                            : "bg-white/10"
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    {passwordStrength() < 2 && "Weak password"}
                    {passwordStrength() === 2 && "Fair password"}
                    {passwordStrength() === 3 && "Good password"}
                    {passwordStrength() >= 4 && "Strong password"}
                  </p>
                </div>
              )}
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Create account"
              )}
            </Button>
          </form>

          <p className="text-center text-zinc-400 mt-8">
            Already have an account?{" "}
            <Link to="/login" className="text-electric hover:underline">Sign in</Link>
          </p>

          <p className="text-center text-xs text-zinc-500 mt-4">
            By signing up, you agree to our{" "}
            <a href="#" className="text-zinc-400 hover:text-white">Terms of Service</a>{" "}
            and{" "}
            <a href="#" className="text-zinc-400 hover:text-white">Privacy Policy</a>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
