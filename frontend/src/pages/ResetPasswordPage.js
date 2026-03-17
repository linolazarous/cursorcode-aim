import { useState, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { ArrowLeft, Eye, EyeOff, Loader2, CheckCircle2, Lock } from "lucide-react";
import Logo from "../components/Logo";
import api from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const { refreshUser } = useAuth();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const strength = useMemo(() => {
    if (!password) return { label: "", color: "bg-zinc-700", bars: 0 };
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    const map = [
      { label: "Very Weak", color: "bg-red-500", bars: 1 },
      { label: "Weak", color: "bg-orange-500", bars: 2 },
      { label: "Medium", color: "bg-yellow-500", bars: 3 },
      { label: "Strong", color: "bg-emerald-500", bars: 4 },
      { label: "Very Strong", color: "bg-green-500", bars: 5 },
    ];
    return map[Math.min(score - 1, 4)] || map[0];
  }, [password]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords don't match");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post("/auth/reset-password/confirm", { token, new_password: password });
      const { access_token, refresh_token } = res.data;
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      await refreshUser();
      setSuccess(true);
      toast.success("Password reset successfully!");
      setTimeout(() => navigate("/dashboard"), 2000);
    } catch (error) {
      const msg = error?.response?.data?.detail || "Failed to reset password";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-void noise-bg flex items-center justify-center p-8">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
          <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10 text-emerald-400" />
          </div>
          <h1 className="font-outfit font-bold text-3xl text-white mb-3">Password Reset!</h1>
          <p className="text-zinc-400 mb-6">Redirecting you to your dashboard...</p>
          <Loader2 className="w-6 h-6 animate-spin text-electric mx-auto" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-void noise-bg flex">
      <div className="hidden lg:flex lg:w-1/2 relative bg-void-paper border-r border-white/5">
        <div className="absolute inset-0 bg-hero-glow" />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <Link to="/"><Logo size="large" /></Link>
          <div>
            <h2 className="font-outfit font-bold text-4xl text-white mb-4">
              New password.<br /><span className="text-electric">Fresh start.</span>
            </h2>
            <p className="text-zinc-400 text-lg max-w-md">Set a strong password to protect your account.</p>
          </div>
          <p className="text-sm text-zinc-500">&copy; {new Date().getFullYear()} CursorCode AI</p>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
          <Link to="/" className="flex lg:hidden mb-8"><Logo size="default" /></Link>
          <Link to="/login" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white mb-8">
            <ArrowLeft className="w-4 h-4" /> Back to login
          </Link>

          {!token ? (
            <div className="text-center" data-testid="invalid-reset-token">
              <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-6">
                <Lock className="w-7 h-7 text-red-400" />
              </div>
              <h1 className="font-outfit font-bold text-3xl text-white mb-3">Invalid Link</h1>
              <p className="text-zinc-400 mb-6">This reset link is invalid or expired.</p>
              <Link to="/forgot-password">
                <Button className="bg-electric hover:bg-electric/90 text-white">Request a new link</Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 rounded-full bg-electric/10 flex items-center justify-center mb-6">
                <Lock className="w-7 h-7 text-electric" />
              </div>
              <h1 className="font-outfit font-bold text-3xl text-white mb-2">Reset Password</h1>
              <p className="text-zinc-400 mb-8">Choose a strong password for your account.</p>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <Label>New Password</Label>
                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 8 characters"
                      required
                      data-testid="reset-password-input"
                    />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-3 text-zinc-400 hover:text-white">
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {password && (
                    <div className="mt-2 space-y-1">
                      <div className="flex gap-1">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${i < strength.bars ? strength.color : "bg-zinc-800"}`} />
                        ))}
                      </div>
                      <p className="text-xs text-zinc-400">Strength: <span className="font-medium text-zinc-300">{strength.label}</span></p>
                    </div>
                  )}
                </div>
                <div>
                  <Label>Confirm Password</Label>
                  <Input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    required
                    data-testid="reset-confirm-password-input"
                  />
                  {confirmPassword && password !== confirmPassword && (
                    <p className="text-xs text-red-400 mt-1">Passwords don't match</p>
                  )}
                </div>
                <Button
                  type="submit"
                  disabled={loading || !token}
                  className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
                  data-testid="reset-submit-button"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Resetting...</>
                  ) : (
                    "Reset Password & Sign In"
                  )}
                </Button>
              </form>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
