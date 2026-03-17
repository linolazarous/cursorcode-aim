import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import {
  User,
  CreditCard,
  Key,
  Shield,
  LayoutDashboard,
  Settings,
  LogOut,
  Loader2,
  Check,
  Copy,
  Eye,
  EyeOff,
  Zap,
} from "lucide-react";
import Logo from "../components/Logo";

export default function SettingsPage() {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [subscription, setSubscription] = useState(null);

  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");

  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);

  // ======================================================
  // SAFE API KEY GENERATION
  // ======================================================
  const demoApiKey = `cc_${btoa(user?.id || "demo")
    .replace(/=/g, "")
    .slice(0, 32)}`;

  // ======================================================
  // FETCH SUBSCRIPTION
  // ======================================================
  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const res = await api.get("/subscriptions/current");
        setSubscription(res.data);
      } catch (error) {
        console.warn("Subscription unavailable");
      }
    };

    fetchSubscription();
  }, []);

  // ======================================================
  // SAFE CREDIT CALCULATION
  // ======================================================
  const creditsRemaining = user
    ? Math.max(user.credits - user.credits_used, 0)
    : 0;

  const creditsPercentage = user?.credits
    ? (creditsRemaining / user.credits) * 100
    : 0;

  // ======================================================
  // COPY API KEY
  // ======================================================
  const handleCopyApiKey = async () => {
    try {
      await navigator.clipboard.writeText(demoApiKey);
      setApiKeyCopied(true);
      setTimeout(() => setApiKeyCopied(false), 2000);
      toast.success("API key copied");
    } catch {
      toast.error("Failed to copy");
    }
  };

  // ======================================================
  // UPDATE PROFILE
  // ======================================================
  const handleSaveProfile = async () => {
    setLoading(true);

    try {
      await api.put("/users/me", { name, email });

      await refreshUser();

      toast.success("Profile updated");

    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to update profile";

      toast.error(message);

    } finally {
      setLoading(false);
    }
  };

  // ======================================================
  // UPGRADE PLAN
  // ======================================================
  const handleUpgrade = async (plan) => {
    try {
      const res = await api.post("/subscriptions/create-checkout", { plan });

      if (res.data.demo) {
        toast.info("Demo mode - configure Stripe for real payments");
        return;
      }

      window.location.href = res.data.url;

    } catch (error) {
      toast.error(
        error?.response?.data?.message ||
          "Failed to start checkout"
      );
    }
  };

  return (
    <div className="min-h-screen bg-void flex">

      {/* SIDEBAR */}
      <aside className="fixed left-0 top-0 h-screen w-64 bg-void-paper border-r border-white/5 flex flex-col z-40">

        <div className="p-6 border-b border-white/5">
          <Link to="/">
            <Logo size="default" />
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1">

          <Link
            to="/dashboard"
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5"
          >
            <LayoutDashboard className="w-5 h-5" />
            Dashboard
          </Link>

          <Link
            to="/settings"
            className="flex items-center gap-3 px-4 py-3 rounded-lg bg-electric/10 text-electric"
          >
            <Settings className="w-5 h-5" />
            Settings
          </Link>

          {user?.is_admin && (
            <Link
              to="/admin"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5"
            >
              <Shield className="w-5 h-5" />
              Admin
            </Link>
          )}

        </nav>

        {/* CREDITS */}
        <div className="p-4 border-t border-white/5">

          <div className="p-4 rounded-lg bg-void-subtle border border-white/5">

            <div className="flex justify-between mb-2">
              <span className="text-sm text-zinc-400">
                AI Credits
              </span>
              <Zap className="w-4 h-4 text-electric" />
            </div>

            <div className="text-2xl font-bold text-white mb-2">
              {creditsRemaining}
              <span className="text-sm text-zinc-500">
                /{user?.credits || 0}
              </span>
            </div>

            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full bg-electric"
                style={{ width: `${creditsPercentage}%` }}
              />
            </div>

          </div>

        </div>

        {/* LOGOUT */}
        <div className="p-4 border-t border-white/5">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-400 hover:bg-red-500/10"
          >
            <LogOut className="w-5 h-5" />
            Log out
          </button>
        </div>

      </aside>

      {/* MAIN */}
      <main className="flex-1 ml-64">

        <header className="sticky top-0 bg-void/80 backdrop-blur border-b border-white/5">
          <div className="px-8 py-4">
            <h1 className="text-2xl font-bold text-white">
              Settings
            </h1>
            <p className="text-zinc-400 text-sm">
              Manage your account
            </p>
          </div>
        </header>

        <div className="p-8 max-w-4xl">

          <Tabs defaultValue="account" className="space-y-8">

            <TabsList className="bg-void-paper border border-white/5">

              <TabsTrigger value="account">
                <User className="w-4 h-4 mr-2" />
                Account
              </TabsTrigger>

              <TabsTrigger value="billing">
                <CreditCard className="w-4 h-4 mr-2" />
                Billing
              </TabsTrigger>

              <TabsTrigger value="api">
                <Key className="w-4 h-4 mr-2" />
                API Keys
              </TabsTrigger>

            </TabsList>

            {/* ACCOUNT */}
            <TabsContent value="account">

              <div className="p-6 rounded-xl bg-void-paper border border-white/5">

                <h3 className="text-lg font-semibold text-white mb-6">
                  Profile Information
                </h3>

                <div className="space-y-4">

                  <div>
                    <Label>Full Name</Label>
                    <Input
                      value={name}
                      onChange={(e) =>
                        setName(e.target.value)
                      }
                      className="max-w-md"
                    />
                  </div>

                  <div>
                    <Label>Email</Label>
                    <Input
                      type="email"
                      value={email}
                      onChange={(e) =>
                        setEmail(e.target.value)
                      }
                      className="max-w-md"
                    />
                  </div>

                  <Button
                    onClick={handleSaveProfile}
                    className="bg-electric text-white mt-4"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "Save Changes"
                    )}
                  </Button>

                </div>

              </div>

            </TabsContent>

            {/* BILLING */}
            <TabsContent value="billing">

              <div className="p-6 rounded-xl bg-void-paper border border-white/5">

                <h3 className="text-lg font-semibold text-white mb-6">
                  Current Plan
                </h3>

                <div className="flex justify-between items-center p-4 rounded-lg bg-void-subtle border border-white/5">

                  <div>
                    <p className="text-white font-semibold capitalize">
                      {subscription?.plan ||
                        user?.plan ||
                        "Starter"}{" "}
                      Plan
                    </p>

                    <p className="text-zinc-400 text-sm">
                      {subscription?.credits_remaining ||
                        creditsRemaining}{" "}
                      credits remaining
                    </p>
                  </div>

                  <Button
                    onClick={() =>
                      navigate("/pricing")
                    }
                    className="bg-electric text-white"
                  >
                    Upgrade
                  </Button>

                </div>

              </div>

            </TabsContent>

            {/* API */}
            <TabsContent value="api">

              <div className="p-6 rounded-xl bg-void-paper border border-white/5">

                <h3 className="text-lg font-semibold text-white mb-2">
                  API Access
                </h3>

                <p className="text-zinc-400 text-sm mb-6">
                  Use your API key to integrate
                  CursorCode AI
                </p>

                <div className="flex gap-4">

                  <div className="flex-1 relative">

                    <Input
                      type={
                        showApiKey ? "text" : "password"
                      }
                      value={demoApiKey}
                      readOnly
                      className="font-mono pr-24"
                    />

                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">

                      <button
                        onClick={() =>
                          setShowApiKey(!showApiKey)
                        }
                      >
                        {showApiKey ? (
                          <EyeOff size={16} />
                        ) : (
                          <Eye size={16} />
                        )}
                      </button>

                      <button
                        onClick={handleCopyApiKey}
                      >
                        {apiKeyCopied ? (
                          <Check
                            size={16}
                            className="text-emerald"
                          />
                        ) : (
                          <Copy size={16} />
                        )}
                      </button>

                    </div>

                  </div>

                </div>

              </div>

            </TabsContent>

          </Tabs>

        </div>

      </main>
    </div>
  );
}
