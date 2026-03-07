import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import api from "../lib/api";
import { CheckCircle2, ArrowLeft, Zap, Loader2 } from "lucide-react";
import Logo from "../components/Logo";
import { useState } from "react";

const PRICING_PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 0,
    period: "Free forever",
    credits: 10,
    features: ["10 AI credits/month", "1 project", "Subdomain deploy", "Community support"],
    cta: "Current Plan",
    popular: false,
    disabled: true,
  },
  {
    id: "standard",
    name: "Standard",
    price: 29,
    period: "/month",
    credits: 75,
    features: ["75 AI credits/month", "Full-stack & APIs", "Native + external deploy", "Version history", "Email support"],
    cta: "Get Standard",
    popular: false,
  },
  {
    id: "pro",
    name: "Pro",
    price: 59,
    period: "/month",
    credits: 150,
    features: ["150 AI credits/month", "SaaS & multi-tenant", "Advanced agents", "CI/CD integration", "Priority builds"],
    cta: "Get Pro",
    popular: true,
  },
  {
    id: "premier",
    name: "Premier",
    price: 199,
    period: "/month",
    credits: 600,
    features: ["600 AI credits/month", "Large SaaS apps", "Multi-org support", "Advanced security scans", "Priority support"],
    cta: "Get Premier",
    popular: false,
  },
  {
    id: "ultra",
    name: "Ultra",
    price: 499,
    period: "/month",
    credits: 2000,
    features: ["2,000 AI credits/month", "Unlimited projects", "Dedicated compute", "SLA guarantee", "Enterprise support"],
    cta: "Contact Sales",
    popular: false,
  },
];

export default function PricingPage() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [loadingPlan, setLoadingPlan] = useState(null);

  const handleSelectPlan = async (planId) => {
    if (!isAuthenticated) {
      navigate("/signup");
      return;
    }

    if (planId === "starter" || planId === user?.plan) {
      return;
    }

    setLoadingPlan(planId);
    try {
      // Send plan in POST body instead of query string
      const response = await api.post("/subscriptions/create-checkout", { plan: planId });

      if (response.data.demo) {
        toast.info("Demo mode - configure Stripe keys for real payments");
        setLoadingPlan(null);
        return;
      }

      window.location.href = response.data.url;
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Failed to start checkout";
      toast.error(message);
      setLoadingPlan(null);
    }
  };

  return (
    <div className="min-h-screen bg-void noise-bg">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/">
              <Logo size="default" />
            </Link>

            <div className="flex items-center gap-4">
              {isAuthenticated ? (
                <Button
                  onClick={() => navigate("/dashboard")}
                  variant="ghost"
                  className="text-zinc-400 hover:text-white"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Dashboard
                </Button>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    onClick={() => navigate("/login")}
                    className="text-zinc-400 hover:text-white"
                  >
                    Log in
                  </Button>
                  <Button
                    onClick={() => navigate("/signup")}
                    className="bg-electric hover:bg-electric/90 text-white"
                  >
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-electric/10 border border-electric/20 mb-6">
              <Zap className="w-4 h-4 text-electric" />
              <span className="text-sm text-electric font-medium">Simple, transparent pricing</span>
            </div>

            <h1 className="font-outfit font-bold text-4xl sm:text-5xl text-white mb-4">
              Choose your plan
            </h1>
            <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
              Start free, scale as you grow. All plans include access to our multi-agent AI system powered by xAI Grok.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6">
            {PRICING_PLANS.map((plan, index) => {
              const isCurrentPlan = user?.plan === plan.id;
              const isDisabled = plan.disabled || isCurrentPlan;

              return (
                <motion.div
                  key={plan.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`relative p-6 rounded-xl border ${
                    plan.popular ? "bg-electric/5 border-electric/30 shadow-glow" : "bg-void-paper/50 border-white/5"
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-electric text-xs font-medium text-white">
                      Most Popular
                    </div>
                  )}

                  {isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-emerald text-xs font-medium text-white">
                      Current Plan
                    </div>
                  )}

                  <h3 className="font-outfit font-semibold text-lg text-white mb-2">{plan.name}</h3>
                  <div className="flex items-baseline gap-1 mb-1">
                    <span className="text-3xl font-outfit font-bold text-white">${plan.price}</span>
                    <span className="text-sm text-zinc-500">{plan.period}</span>
                  </div>
                  <p className="text-sm text-zinc-400 mb-6">{plan.credits} AI credits/month</p>

                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <CheckCircle2 className="w-4 h-4 text-emerald shrink-0 mt-0.5" />
                        <span className="text-zinc-300">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    onClick={() => handleSelectPlan(plan.id)}
                    disabled={isDisabled || loadingPlan === plan.id}
                    className={`w-full ${
                      plan.popular
                        ? "bg-electric hover:bg-electric/90 text-white"
                        : isDisabled
                        ? "bg-white/5 text-zinc-500 cursor-not-allowed"
                        : "bg-white/5 hover:bg-white/10 text-white border border-white/10"
                    }`}
                  >
                    {loadingPlan === plan.id ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading...
                      </>
                    ) : isCurrentPlan ? (
                      "Current Plan"
                    ) : (
                      plan.cta
                    )}
                  </Button>
                </motion.div>
              );
            })}
          </div>

          {/* FAQ / Additional Info */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="mt-16 text-center">
            <p className="text-zinc-400">
              All plans include SSL certificates, 99.9% uptime SLA, and automatic backups.
            </p>
            <p className="text-zinc-500 text-sm mt-2">
              Need a custom plan?{" "}
              <a href="mailto:info@cursorcode.ai" className="text-electric hover:underline">
                Contact us
              </a>
            </p>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <Logo size="default" />
          <div className="text-sm text-zinc-500">© 2025 CursorCode AI. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}
