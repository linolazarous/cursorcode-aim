import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "./ui/button";
import api from "../lib/api";
import { toast } from "sonner";
import {
  Sparkles,
  Code2,
  ShieldCheck,
  Rocket,
  Layers,
  Zap,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Terminal,
  CreditCard,
  LayoutDashboard,
  ShoppingCart,
  Smartphone,
  BarChart3,
  Server,
} from "lucide-react";

const USE_CASES = [
  { id: "saas", label: "SaaS Application", icon: LayoutDashboard, desc: "User auth, billing, dashboards" },
  { id: "ecommerce", label: "E-Commerce", icon: ShoppingCart, desc: "Product catalog, cart, payments" },
  { id: "dashboard", label: "Analytics Dashboard", icon: BarChart3, desc: "Charts, data tables, reports" },
  { id: "api", label: "Backend API", icon: Server, desc: "REST/GraphQL, auth, database" },
  { id: "mobile", label: "Mobile App", icon: Smartphone, desc: "React Native, cross-platform" },
  { id: "other", label: "Something Else", icon: Sparkles, desc: "Tell the AI what you need" },
];

const FEATURES = [
  {
    icon: Code2,
    title: "AI Code Generation",
    desc: "Describe what you want in plain English. Our multi-agent system architects, codes, and tests your entire application.",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: Layers,
    title: "Project Templates",
    desc: "Start from battle-tested templates for SaaS, e-commerce, dashboards, and more. Preview before you use.",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise Security",
    desc: "Two-factor authentication, audit logging, RBAC, and SOC 2-ready architecture built in from day one.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Rocket,
    title: "One-Click Deploy",
    desc: "Deploy to CursorCode Cloud instantly. Get a live preview URL for every project, no DevOps required.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
];

const STEP_COUNT = 4;

export default function OnboardingWizard({ user, onComplete }) {
  const [step, setStep] = useState(0);
  const [selectedUseCase, setSelectedUseCase] = useState(null);
  const [completing, setCompleting] = useState(false);

  const handleComplete = async () => {
    setCompleting(true);
    try {
      await api.post("/users/me/complete-onboarding");
      toast.success("You're all set! Let's build something amazing.");
      onComplete?.();
    } catch {
      toast.error("Something went wrong");
    } finally {
      setCompleting(false);
    }
  };

  const next = () => setStep((s) => Math.min(s + 1, STEP_COUNT - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="onboarding-wizard">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative w-full max-w-2xl mx-4 rounded-2xl border border-white/10 bg-void-paper shadow-2xl overflow-hidden"
      >
        {/* Progress Bar */}
        <div className="h-1 bg-zinc-800">
          <motion.div
            className="h-full bg-electric"
            animate={{ width: `${((step + 1) / STEP_COUNT) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        <div className="p-8 min-h-[420px] flex flex-col">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <StepWrapper key="welcome">
                <div className="text-center flex-1 flex flex-col items-center justify-center">
                  <div className="w-20 h-20 rounded-full bg-electric/10 flex items-center justify-center mb-6">
                    <Sparkles className="w-10 h-10 text-electric" />
                  </div>
                  <h2 className="font-outfit font-bold text-3xl text-white mb-3" data-testid="onboarding-welcome-title">
                    Welcome, {user?.name?.split(" ")[0] || "there"}!
                  </h2>
                  <p className="text-zinc-400 text-lg max-w-md mb-2">
                    You're about to experience the future of software engineering.
                  </p>
                  <p className="text-zinc-500 text-sm max-w-md">
                    Let's get you set up in under 60 seconds.
                  </p>
                  <div className="flex items-center gap-6 mt-8 text-sm text-zinc-500">
                    <span className="flex items-center gap-2"><Zap className="w-4 h-4 text-electric" /> 10 free credits</span>
                    <span className="flex items-center gap-2"><Terminal className="w-4 h-4 text-emerald-400" /> AI-powered</span>
                    <span className="flex items-center gap-2"><CreditCard className="w-4 h-4 text-purple-400" /> No card needed</span>
                  </div>
                </div>
              </StepWrapper>
            )}

            {step === 1 && (
              <StepWrapper key="usecase">
                <div className="flex-1">
                  <h2 className="font-outfit font-bold text-2xl text-white mb-2" data-testid="onboarding-usecase-title">
                    What are you building?
                  </h2>
                  <p className="text-zinc-400 mb-6">This helps our AI tailor recommendations for you.</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {USE_CASES.map((uc) => (
                      <button
                        key={uc.id}
                        onClick={() => setSelectedUseCase(uc.id)}
                        className={`p-4 rounded-xl border text-left transition-all ${
                          selectedUseCase === uc.id
                            ? "border-electric bg-electric/10 shadow-glow"
                            : "border-white/10 bg-void hover:border-white/20"
                        }`}
                        data-testid={`usecase-${uc.id}`}
                      >
                        <uc.icon className={`w-5 h-5 mb-2 ${selectedUseCase === uc.id ? "text-electric" : "text-zinc-400"}`} />
                        <p className="font-medium text-white text-sm">{uc.label}</p>
                        <p className="text-xs text-zinc-500 mt-0.5">{uc.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </StepWrapper>
            )}

            {step === 2 && (
              <StepWrapper key="features">
                <div className="flex-1">
                  <h2 className="font-outfit font-bold text-2xl text-white mb-2" data-testid="onboarding-features-title">
                    Your Toolkit
                  </h2>
                  <p className="text-zinc-400 mb-6">Everything you need to go from idea to production.</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {FEATURES.map((feat, i) => (
                      <motion.div
                        key={feat.title}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="p-4 rounded-xl border border-white/5 bg-void/50"
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-9 h-9 rounded-lg ${feat.bg} flex items-center justify-center flex-shrink-0`}>
                            <feat.icon className={`w-5 h-5 ${feat.color}`} />
                          </div>
                          <div>
                            <p className="font-medium text-white text-sm">{feat.title}</p>
                            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{feat.desc}</p>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </StepWrapper>
            )}

            {step === 3 && (
              <StepWrapper key="complete">
                <div className="text-center flex-1 flex flex-col items-center justify-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", duration: 0.5 }}
                    className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6"
                  >
                    <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                  </motion.div>
                  <h2 className="font-outfit font-bold text-3xl text-white mb-3" data-testid="onboarding-complete-title">
                    You're Ready!
                  </h2>
                  <p className="text-zinc-400 text-lg max-w-md mb-2">
                    Your workspace is set up and your AI agents are standing by.
                  </p>
                  <p className="text-zinc-500 text-sm max-w-sm">
                    Create your first project or explore templates to get started.
                  </p>
                  <div className="flex flex-col sm:flex-row items-center gap-3 mt-8">
                    <Button
                      onClick={handleComplete}
                      disabled={completing}
                      className="bg-electric hover:bg-electric/90 text-white shadow-glow px-8 h-12 text-base"
                      data-testid="onboarding-finish-button"
                    >
                      {completing ? "Setting up..." : "Start Building"}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                </div>
              </StepWrapper>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="px-8 py-4 border-t border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Array.from({ length: STEP_COUNT }).map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === step ? "bg-electric w-6" : i < step ? "bg-electric/40" : "bg-zinc-700"
                }`}
              />
            ))}
          </div>
          <div className="flex items-center gap-3">
            {step > 0 && step < STEP_COUNT - 1 && (
              <Button variant="ghost" size="sm" onClick={prev} className="text-zinc-400" data-testid="onboarding-prev-button">
                <ArrowLeft className="w-4 h-4 mr-1" /> Back
              </Button>
            )}
            {step < STEP_COUNT - 1 && (
              <Button onClick={next} size="sm" className="bg-electric hover:bg-electric/90 text-white" data-testid="onboarding-next-button">
                {step === 0 ? "Let's Go" : "Continue"} <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            )}
            {step === 0 && (
              <button onClick={handleComplete} className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors ml-2" data-testid="onboarding-skip-button">
                Skip
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function StepWrapper({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.2 }}
      className="flex-1 flex flex-col"
    >
      {children}
    </motion.div>
  );
}
