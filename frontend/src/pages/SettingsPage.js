import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
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

  // Form state
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");

  // API key state
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);
  const demoApiKey = `cc_${btoa(user?.id || "demo").slice(0, 32)}`;

  // Fetch subscription on mount
  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await api.get("/subscriptions/current");
        setSubscription(response.data);
      } catch (error) {
        console.error("Failed to fetch subscription:", error);
      }
    };
    fetchSubscription();
  }, []);

  const creditsRemaining = user ? user.credits - user.credits_used : 0;
  const creditsPercentage = user ? (creditsRemaining / user.credits) * 100 : 0;

  // Copy API key
  const handleCopyApiKey = () => {
    navigator.clipboard.writeText(demoApiKey);
    setApiKeyCopied(true);
    setTimeout(() => setApiKeyCopied(false), 2000);
    toast.success("API key copied");
  };

  // Update profile
  const handleSaveProfile = async () => {
    setLoading(true);
    try {
      await api.put("/users/me", { name, email });
      await refreshUser();
      toast.success("Profile updated successfully");
    } catch (error) {
      const message =
        error?.response?.data?.detail || error?.response?.data?.message || "Failed to update profile";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  // Upgrade subscription
  const handleUpgrade = async (plan) => {
    try {
      const response = await api.post("/subscriptions/create-checkout", { plan });
      if (response.data.demo) {
        toast.info("Demo mode - configure Stripe for real payments");
        return;
      }
      window.location.href = response.data.url;
    } catch (error) {
      const message = error?.response?.data?.message || "Failed to start checkout";
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen bg-void flex">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-64 bg-void-paper border-r border-white/5 flex flex-col z-40">
        <div className="p-6 border-b border-white/5">
          <Link to="/">
            <Logo size="default" />
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          <Link
            to="/dashboard"
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <LayoutDashboard className="w-5 h-5" />
            <span>Dashboard</span>
          </Link>

          <Link
            to="/settings"
            className="flex items-center gap-3 px-4 py-3 rounded-lg bg-electric/10 text-electric"
          >
            <Settings className="w-5 h-5" />
            <span className="font-medium">Settings</span>
          </Link>

          {user?.is_admin && (
            <Link
              to="/admin"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <Shield className="w-5 h-5" />
              <span>Admin</span>
            </Link>
          )}
        </nav>

        {/* Credits Card */}
        <div className="p-4 border-t border-white/5">
          <div className="p-4 rounded-lg bg-void-subtle border border-white/5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-400">AI Credits</span>
              <Zap className="w-4 h-4 text-electric" />
            </div>
            <div className="text-2xl font-outfit font-bold text-white mb-2">
              {creditsRemaining}
              <span className="text-sm font-normal text-zinc-500">/{user?.credits}</span>
            </div>
            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full bg-electric transition-all"
                style={{ width: `${creditsPercentage}%` }}
              />
            </div>
          </div>
        </div>

        {/* User Menu */}
        <div className="p-4 border-t border-white/5">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Log out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        <header className="sticky top-0 z-30 bg-void/80 backdrop-blur-xl border-b border-white/5">
          <div className="px-8 py-4">
            <h1 className="font-outfit font-bold text-2xl text-white">Settings</h1>
            <p className="text-sm text-zinc-400">Manage your account and preferences</p>
          </div>
        </header>

        <div className="p-8 max-w-4xl">
          <Tabs defaultValue="account" className="space-y-8">
            <TabsList className="bg-void-paper border border-white/5">
              <TabsTrigger value="account" className="data-[state=active]:bg-electric/10 data-[state=active]:text-electric">
                <User className="w-4 h-4 mr-2" /> Account
              </TabsTrigger>
              <TabsTrigger value="billing" className="data-[state=active]:bg-electric/10 data-[state=active]:text-electric">
                <CreditCard className="w-4 h-4 mr-2" /> Billing
              </TabsTrigger>
              <TabsTrigger value="api" className="data-[state=active]:bg-electric/10 data-[state=active]:text-electric">
                <Key className="w-4 h-4 mr-2" /> API Keys
              </TabsTrigger>
            </TabsList>

            {/* Account Tab */}
            <TabsContent value="account" className="space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-6 rounded-xl bg-void-paper border border-white/5">
                <h3 className="font-outfit font-semibold text-lg text-white mb-6">Profile Information</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-white">Full Name</Label>
                    <Input id="name" value={name} onChange={(e) => setName(e.target.value)} className="bg-void-subtle border-white/10 text-white max-w-md" />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-white">Email Address</Label>
                    <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-void-subtle border-white/10 text-white max-w-md" />
                  </div>

                  <Button onClick={handleSaveProfile} className="bg-electric hover:bg-electric/90 text-white mt-4">
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : "Save Changes"}
                  </Button>
                </div>
              </motion.div>
            </TabsContent>

            {/* Billing Tab */}
            <TabsContent value="billing" className="space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-6 rounded-xl bg-void-paper border border-white/5">
                <h3 className="font-outfit font-semibold text-lg text-white mb-6">Current Plan</h3>
                <div className="flex items-center justify-between p-4 rounded-lg bg-void-subtle border border-white/5">
                  <div>
                    <p className="font-outfit font-semibold text-white capitalize">{subscription?.plan || user?.plan || "Starter"} Plan</p>
                    <p className="text-sm text-zinc-400">{subscription?.credits_remaining || creditsRemaining} credits remaining this month</p>
                  </div>
                  <Button onClick={() => navigate("/pricing")} className="bg-electric hover:bg-electric/90 text-white">Upgrade Plan</Button>
                </div>
              </motion.div>
            </TabsContent>

            {/* API Tab */}
            <TabsContent value="api" className="space-y-6">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-6 rounded-xl bg-void-paper border border-white/5">
                <h3 className="font-outfit font-semibold text-lg text-white mb-2">API Access</h3>
                <p className="text-sm text-zinc-400 mb-6">Use your API key to integrate CursorCode AI into your workflows.</p>

                <div className="flex items-center gap-4">
                  <div className="flex-1 relative">
                    <Input type={showApiKey ? "text" : "password"} value={demoApiKey} readOnly className="bg-void-subtle border-white/10 text-white pr-24 font-mono" />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button onClick={() => setShowApiKey(!showApiKey)} className="p-1.5 rounded hover:bg-white/5 text-zinc-500 hover:text-white transition-colors">
                        {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                      <button onClick={handleCopyApiKey} className="p-1.5 rounded hover:bg-white/5 text-zinc-500 hover:text-white transition-colors">
                        {apiKeyCopied ? <Check className="w-4 h-4 text-emerald" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
