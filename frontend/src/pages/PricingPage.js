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
    features: [
      "10 AI credits/month",
      "1 project",
      "Subdomain deploy",
      "Community support",
    ],
    cta: "Current Plan",
    disabled: true,
  },
  {
    id: "standard",
    name: "Standard",
    price: 29,
    period: "/month",
    credits: 75,
    features: [
      "75 AI credits/month",
      "Full-stack & APIs",
      "Native + external deploy",
      "Version history",
      "Email support",
    ],
    cta: "Upgrade",
  },
  {
    id: "pro",
    name: "Pro",
    price: 59,
    period: "/month",
    credits: 150,
    popular: true,
    features: [
      "150 AI credits/month",
      "SaaS & multi-tenant",
      "Advanced AI agents",
      "CI/CD integration",
      "Priority builds",
    ],
    cta: "Upgrade",
  },
  {
    id: "premier",
    name: "Premier",
    price: 199,
    period: "/month",
    credits: 600,
    features: [
      "600 AI credits/month",
      "Large SaaS applications",
      "Multi-org support",
      "Security scans",
      "Priority support",
    ],
    cta: "Upgrade",
  },
  {
    id: "ultra",
    name: "Ultra",
    price: 499,
    period: "/month",
    credits: 2000,
    features: [
      "2,000 AI credits/month",
      "Unlimited projects",
      "Dedicated compute",
      "Enterprise SLA",
      "Dedicated support",
    ],
    cta: "Contact Sales",
    enterprise: true,
  },
];

export default function PricingPage() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  const [loadingPlan, setLoadingPlan] = useState(null);

  const handleSelectPlan = async (plan) => {
    if (!isAuthenticated) {
      toast.info("Create an account first");
      navigate("/signup");
      return;
    }

    if (plan.id === user?.plan) {
      toast.info("You are already on this plan");
      return;
    }

    if (plan.enterprise) {
      window.location.href = "mailto:info@cursorcode.ai";
      return;
    }

    if (loadingPlan) return;

    setLoadingPlan(plan.id);

    try {
      const res = await api.post("/subscriptions/create-checkout", {
        plan: plan.id,
      });

      if (res?.data?.demo) {
        toast.info("Demo mode enabled — Stripe keys not configured");
        setLoadingPlan(null);
        return;
      }

      if (!res?.data?.url) {
        throw new Error("Checkout session not returned");
      }

      window.location.href = res.data.url;

    } catch (error) {
      console.error(error);

      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Unable to start checkout";

      toast.error(message);
      setLoadingPlan(null);
    }
  };

  return (
    <div className="min-h-screen bg-void noise-bg">

      {/* NAVBAR */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">

            <Link to="/">
              <Logo size="default" />
            </Link>

            <div className="flex items-center gap-4">

              {isAuthenticated ? (
                <Button
                  variant="ghost"
                  onClick={() => navigate("/dashboard")}
                  className="text-zinc-400 hover:text-white"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    onClick={() => navigate("/login")}
                    className="text-zinc-400 hover:text-white"
                  >
                    Login
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

      {/* HERO */}
      <section className="pt-32 pb-14 text-center">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-electric/10 border border-electric/20 mb-6">
            <Zap className="w-4 h-4 text-electric" />
            <span className="text-sm text-electric font-medium">
              Transparent Pricing
            </span>
          </div>

          <h1 className="text-5xl font-bold text-white mb-4">
            Choose your plan
          </h1>

          <p className="text-zinc-400 max-w-2xl mx-auto">
            Build apps faster using AI agents powered by xAI Grok models.

          </p>

        </motion.div>
      </section>

      {/* PRICING */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-6">

          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6">

            {PRICING_PLANS.map((plan, i) => {
              const isCurrent = user?.plan === plan.id;

              return (
                <motion.div
                  key={plan.id}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className={`relative p-6 rounded-xl border ${
                    plan.popular
                      ? "bg-electric/5 border-electric/30 shadow-glow"
                      : "bg-void-paper border-white/5"
                  }`}
                >

                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-xs rounded-full bg-electric text-white">
                      Most Popular
                    </div>
                  )}

                  {isCurrent && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-xs rounded-full bg-emerald text-white">
                      Current Plan
                    </div>
                  )}

                  <h3 className="text-lg font-semibold text-white mb-2">
                    {plan.name}
                  </h3>

                  <div className="flex items-end gap-1 mb-2">
                    <span className="text-3xl font-bold text-white">
                      ${plan.price}
                    </span>
                    <span className="text-zinc-500 text-sm">
                      {plan.period}
                    </span>
                  </div>

                  <p className="text-sm text-zinc-400 mb-6">
                    {plan.credits} AI credits/month
                  </p>

                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2 text-sm"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald mt-0.5 shrink-0" />
                        <span className="text-zinc-300">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    onClick={() => handleSelectPlan(plan)}
                    disabled={loadingPlan === plan.id || isCurrent}
                    className={`w-full ${
                      plan.popular
                        ? "bg-electric hover:bg-electric/90 text-white"
                        : "bg-white/5 hover:bg-white/10 text-white border border-white/10"
                    }`}
                  >

                    {loadingPlan === plan.id ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing
                      </>
                    ) : isCurrent ? (
                      "Current Plan"
                    ) : (
                      plan.cta
                    )}

                  </Button>
                </motion.div>
              );
            })}

          </div>

          {/* INFO */}
          <div className="text-center mt-16 text-zinc-400">
            All plans include SSL certificates, global CDN, and 99.9% uptime.
          </div>

        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-12 border-t border-white/5 text-center text-sm text-zinc-500">
        © 2026 CursorCode AI — All rights reserved
      </footer>

    </div>
  );
}
