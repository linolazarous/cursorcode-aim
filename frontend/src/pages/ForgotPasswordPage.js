import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { ArrowLeft, Loader2, CheckCircle2, Mail } from "lucide-react";
import Logo from "../components/Logo";
import api from "../lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  // =====================================================
  // FORGOT PASSWORD REQUEST – matches backend exactly
  // POST /api/auth/reset-password/request
  // Returns generic success message (security by obscurity)
  // =====================================================
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);

    try {
      await api.post("/auth/reset-password/request", { email });
      setSent(true);
      toast.success("If an account exists with that email, a reset link has been sent.");
    } catch (error) {
      // Network / server error only (backend never returns error for this endpoint)
      toast.error("Failed to send reset link. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void noise-bg flex">
      <div className="hidden lg:flex lg:w-1/2 relative bg-void-paper border-r border-white/5">
        <div className="absolute inset-0 bg-hero-glow" />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <Link to="/"><Logo size="large" /></Link>
          <div>
            <h2 className="font-outfit font-bold text-4xl text-white mb-4">
              Don't worry.<br />
              <span className="text-electric">We've got you.</span>
            </h2>
            <p className="text-zinc-400 text-lg max-w-md">
              Reset your password and get back to building.
            </p>
          </div>
          <p className="text-sm text-zinc-500">
            &copy; {new Date().getFullYear()} CursorCode AI
          </p>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <Link to="/" className="flex lg:hidden mb-8"><Logo size="default" /></Link>
          <Link to="/login" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white mb-8">
            <ArrowLeft className="w-4 h-4" /> Back to login
          </Link>

          {sent ? (
            <div className="text-center" data-testid="forgot-password-success">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              </div>
              <h1 className="font-outfit font-bold text-3xl text-white mb-3">Check Your Email</h1>
              <p className="text-zinc-400 mb-2">We've sent a password reset link to</p>
              <p className="text-white font-medium mb-8">{email}</p>
              <p className="text-zinc-500 text-sm mb-8">The link expires in 1 hour. Check your spam folder too.</p>
              <Link to="/login">
                <Button variant="outline" className="w-full h-12 border-white/10" data-testid="back-to-login-button">
                  Back to Sign In
                </Button>
              </Link>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 rounded-full bg-electric/10 flex items-center justify-center mb-6">
                <Mail className="w-7 h-7 text-electric" />
              </div>
              <h1 className="font-outfit font-bold text-3xl text-white mb-2">Forgot Password?</h1>
              <p className="text-zinc-400 mb-8">No worries. Enter your email and we'll send a reset link.</p>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <Label>Email Address</Label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoFocus
                    data-testid="forgot-email-input"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full h-12 bg-electric hover:bg-electric/90 text-white shadow-glow"
                  data-testid="forgot-submit-button"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Sending...</>
                  ) : (
                    "Send Reset Link"
                  )}
                </Button>
              </form>

              <p className="text-center text-zinc-400 mt-8">
                Remember your password?{" "}
                <Link to="/login" className="text-electric hover:underline">Sign in</Link>
              </p>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
