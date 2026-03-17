import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { useAuth } from "../context/AuthContext";
import {
  Zap,
  Code2,
  Cloud,
  Shield,
  Cpu,
  GitBranch,
  ArrowRight,
  CheckCircle2,
  Terminal,
  Layers,
  Bot,
  Menu,
  X,
  Play,
} from "lucide-react";
import Logo from "../components/Logo";
import DemoVideoModal from "../components/DemoVideoModal";

const PRICING_PLANS = [
  {
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
    cta: "Get Started",
    popular: false,
  },
  {
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
    cta: "Start Building",
    popular: false,
  },
  {
    name: "Pro",
    price: 59,
    period: "/month",
    credits: 150,
    features: [
      "150 AI credits/month",
      "SaaS & multi-tenant",
      "Advanced agents",
      "CI/CD integration",
      "Priority builds",
    ],
    cta: "Go Pro",
    popular: true,
  },
  {
    name: "Premier",
    price: 199,
    period: "/month",
    credits: 600,
    features: [
      "600 AI credits/month",
      "Large SaaS apps",
      "Multi-org support",
      "Advanced security scans",
      "Priority support",
    ],
    cta: "Get Premier",
    popular: false,
  },
  {
    name: "Ultra",
    price: 499,
    period: "/month",
    credits: 2000,
    features: [
      "2,000 AI credits/month",
      "Unlimited projects",
      "Dedicated compute",
      "SLA guarantee",
      "Enterprise support",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

const FEATURES = [
  {
    icon: Bot,
    title: "Multi-Agent AI",
    description:
      "Coordinated agents powered by xAI Grok with intelligent routing for architecture, code, DevOps, and security.",
  },
  {
    icon: Code2,
    title: "Production-Grade Code",
    description:
      "Generate clean, scalable, documented code with proper error handling, types, and best practices.",
  },
  {
    icon: Cloud,
    title: "One-Click Deploy",
    description:
      "Deploy to CursorCode.app or Vercel, Netlify, AWS with auto-SSL, scaling, and monitoring.",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description:
      "OAuth/JWT/SSO, encrypted API vaults, RBAC, audit logs, and GDPR-ready infrastructure.",
  },
  {
    icon: Cpu,
    title: "Intelligent Routing",
    description:
      "Automatically selects optimal Grok model per task - frontier reasoning or fast agentic workflows.",
  },
  {
    icon: GitBranch,
    title: "Version Control",
    description:
      "Built-in version history, instant rollbacks, and seamless CI/CD pipeline integration.",
  },
];

const fadeUpVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.5,
      ease: "easeOut",
    },
  }),
};

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [demoModalOpen, setDemoModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-void noise-bg">
      {/* Demo Video Modal */}
      <DemoVideoModal isOpen={demoModalOpen} onClose={() => setDemoModalOpen(false)} />

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center">
              <Logo size="default" />
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              <a
                href="#features"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Features
              </a>
              <a
                href="#pricing"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Pricing
              </a>
              <a
                href="#"
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Docs
              </a>
            </div>

            {/* CTA Buttons */}
            <div className="hidden md:flex items-center gap-4">
              {isAuthenticated ? (
                <Button
                  onClick={() => navigate("/dashboard")}
                  className="bg-electric hover:bg-electric/90 text-white shadow-glow"
                  data-testid="nav-dashboard-btn"
                >
                  Dashboard
                </Button>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    onClick={() => navigate("/login")}
                    className="text-zinc-400 hover:text-white hover:bg-white/5"
                    data-testid="nav-login-btn"
                  >
                    Log in
                  </Button>
                  <Button
                    onClick={() => navigate("/signup")}
                    className="bg-electric hover:bg-electric/90 text-white shadow-glow"
                    data-testid="nav-signup-btn"
                  >
                    Get Started
                  </Button>
                </>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 text-zinc-400 hover:text-white"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              data-testid="mobile-menu-btn"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden glass border-t border-white/5">
            <div className="px-4 py-4 space-y-4">
              <a href="#features" className="block text-zinc-400 hover:text-white">
                Features
              </a>
              <a href="#pricing" className="block text-zinc-400 hover:text-white">
                Pricing
              </a>
              <div className="pt-4 border-t border-white/10 space-y-2">
                {isAuthenticated ? (
                  <Button
                    onClick={() => navigate("/dashboard")}
                    className="w-full bg-electric hover:bg-electric/90"
                  >
                    Dashboard
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => navigate("/login")}
                      className="w-full border-white/10"
                    >
                      Log in
                    </Button>
                    <Button
                      onClick={() => navigate("/signup")}
                      className="w-full bg-electric hover:bg-electric/90"
                    >
                      Get Started
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-hero-glow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-electric/5 blur-[100px]" />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <motion.div
              initial="hidden"
              animate="visible"
              className="text-left"
            >
              <motion.div
                custom={0}
                variants={fadeUpVariants}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-electric/10 border border-electric/20 mb-6"
              >
                <Zap className="w-4 h-4 text-electric" />
                <span className="text-sm text-electric font-medium">
                  Powered by xAI Grok
                </span>
              </motion.div>

              <motion.h1
                custom={1}
                variants={fadeUpVariants}
                className="font-outfit font-bold text-4xl sm:text-5xl lg:text-6xl text-white leading-tight mb-6"
              >
                Build Anything.
                <br />
                <span className="text-electric">Automatically.</span>
                <br />
                With AI.
              </motion.h1>

              <motion.p
                custom={2}
                variants={fadeUpVariants}
                className="text-lg text-zinc-400 max-w-xl mb-8"
              >
                CursorCode AI is the world's most powerful autonomous software
                engineering platform. Turn plain English into production-ready,
                deployed applications.
              </motion.p>

              <motion.div
                custom={3}
                variants={fadeUpVariants}
                className="flex flex-col sm:flex-row gap-4"
              >
                <Button
                  size="lg"
                  onClick={() => navigate(isAuthenticated ? "/dashboard" : "/signup")}
                  className="bg-electric hover:bg-electric/90 text-white px-8 py-6 text-lg shadow-glow btn-glow"
                  data-testid="hero-cta-btn"
                >
                  Start Building Free
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => setDemoModalOpen(true)}
                  className="border-white/10 text-white hover:bg-white/5 px-8 py-6 text-lg"
                  data-testid="hero-demo-btn"
                >
                  <Play className="mr-2 w-5 h-5" />
                  Watch Demo
                </Button>
              </motion.div>

              <motion.div
                custom={4}
                variants={fadeUpVariants}
                className="flex items-center gap-6 mt-8 text-sm text-zinc-500"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald" />
                  <span>No credit card</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald" />
                  <span>10 free credits</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald" />
                  <span>Deploy in seconds</span>
                </div>
              </motion.div>
            </motion.div>

            {/* Right Content - Code Preview */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="relative hidden lg:block"
            >
              <div className="relative">
                {/* Glow effect */}
                <div className="absolute -inset-4 bg-electric/20 rounded-2xl blur-2xl" />

                {/* Code window */}
                <div className="relative glass rounded-xl border border-white/10 overflow-hidden">
                  {/* Window header */}
                  <div className="flex items-center gap-2 px-4 py-3 bg-void-paper border-b border-white/5">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500" />
                      <div className="w-3 h-3 rounded-full bg-green-500" />
                    </div>
                    <span className="text-xs text-zinc-500 ml-2">
                      cursorcode-ai-generator
                    </span>
                  </div>

                  {/* Code content */}
                  <div className="p-6 font-mono text-sm">
                    <div className="text-zinc-500">// Your prompt</div>
                    <div className="text-emerald mt-2">
                      "Build a SaaS dashboard with user auth,
                    </div>
                    <div className="text-emerald">
                      Stripe payments, and real-time analytics"
                    </div>
                    <div className="mt-4 text-zinc-500">// CursorCode AI generates...</div>
                    <div className="mt-2 text-electric">
                      <span className="text-purple-400">const</span> app ={" "}
                      <span className="text-yellow-400">createSaaSApp</span>(
                      {"{"}
                    </div>
                    <div className="text-white/80 pl-4">
                      auth: <span className="text-emerald">'JWT + OAuth'</span>,
                    </div>
                    <div className="text-white/80 pl-4">
                      payments: <span className="text-emerald">'Stripe'</span>,
                    </div>
                    <div className="text-white/80 pl-4">
                      analytics: <span className="text-emerald">'real-time'</span>,
                    </div>
                    <div className="text-white/80 pl-4">
                      deploy: <span className="text-emerald">'cursorcode.app'</span>
                    </div>
                    <div className="text-electric">{"}"});</div>
                    <div className="mt-4 flex items-center gap-2">
                      <div className="w-2 h-4 bg-electric animate-pulse" />
                      <span className="text-zinc-500">Generating...</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 lg:py-32 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-left mb-16"
          >
            <h2 className="font-outfit font-bold text-3xl sm:text-4xl text-white mb-4">
              Everything you need to ship faster
            </h2>
            <p className="text-lg text-zinc-400 max-w-2xl">
              From idea to production in minutes. Our multi-agent AI system handles
              architecture, coding, testing, and deployment.
            </p>
          </motion.div>

          {/* Bento Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className={`group relative p-8 rounded-xl bg-void-paper/50 border border-white/5 hover:border-electric/30 transition-colors overflow-hidden ${
                  index === 0 ? "lg:col-span-2 lg:row-span-2" : ""
                }`}
                data-testid={`feature-card-${index}`}
              >
                {/* Hover glow */}
                <div className="absolute inset-0 bg-gradient-to-b from-electric/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="relative z-10">
                  <div className="w-12 h-12 rounded-lg bg-electric/10 flex items-center justify-center mb-4 group-hover:bg-electric/20 transition-colors">
                    <feature.icon className="w-6 h-6 text-electric" />
                  </div>
                  <h3 className="font-outfit font-semibold text-xl text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-zinc-400">{feature.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 lg:py-32 relative border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-left mb-16"
          >
            <h2 className="font-outfit font-bold text-3xl sm:text-4xl text-white mb-4">
              How CursorCode AI works
            </h2>
            <p className="text-lg text-zinc-400 max-w-2xl">
              Three simple steps from idea to deployed application.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                icon: Terminal,
                title: "Describe Your App",
                description:
                  "Tell us what you want to build in plain English. Be as detailed or simple as you like.",
              },
              {
                step: "02",
                icon: Layers,
                title: "AI Generates",
                description:
                  "Our multi-agent system designs architecture, writes code, and creates your full application.",
              },
              {
                step: "03",
                icon: Cloud,
                title: "Deploy Instantly",
                description:
                  "One-click deploy to CursorCode.app with auto-SSL, scaling, and monitoring included.",
              },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15 }}
                className="relative"
              >
                <div className="text-7xl font-outfit font-bold text-white/5 absolute -top-4 -left-2">
                  {item.step}
                </div>
                <div className="relative z-10 pt-8">
                  <div className="w-12 h-12 rounded-lg bg-emerald/10 flex items-center justify-center mb-4">
                    <item.icon className="w-6 h-6 text-emerald" />
                  </div>
                  <h3 className="font-outfit font-semibold text-xl text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-zinc-400">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 lg:py-32 relative border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-left mb-16"
          >
            <h2 className="font-outfit font-bold text-3xl sm:text-4xl text-white mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-zinc-400 max-w-2xl">
              Start free, scale as you grow. All plans include core AI features.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6">
            {PRICING_PLANS.map((plan, index) => (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className={`relative p-6 rounded-xl border ${
                  plan.popular
                    ? "bg-electric/5 border-electric/30 shadow-glow"
                    : "bg-void-paper/50 border-white/5"
                }`}
                data-testid={`pricing-plan-${plan.name.toLowerCase()}`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-electric text-xs font-medium text-white">
                    Most Popular
                  </div>
                )}

                <h3 className="font-outfit font-semibold text-lg text-white mb-2">
                  {plan.name}
                </h3>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-3xl font-outfit font-bold text-white">
                    ${plan.price}
                  </span>
                  <span className="text-sm text-zinc-500">{plan.period}</span>
                </div>
                <p className="text-sm text-zinc-400 mb-6">
                  {plan.credits} AI credits/month
                </p>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-emerald shrink-0 mt-0.5" />
                      <span className="text-zinc-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  onClick={() => navigate(isAuthenticated ? "/dashboard" : "/signup")}
                  className={`w-full ${
                    plan.popular
                      ? "bg-electric hover:bg-electric/90 text-white"
                      : "bg-white/5 hover:bg-white/10 text-white border border-white/10"
                  }`}
                  data-testid={`pricing-cta-${plan.name.toLowerCase()}`}
                >
                  {plan.cta}
                </Button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32 relative border-t border-white/5">
        <div className="absolute inset-0 bg-hero-glow" />
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-outfit font-bold text-3xl sm:text-4xl lg:text-5xl text-white mb-6">
              Ready to build the future?
            </h2>
            <p className="text-lg text-zinc-400 mb-8 max-w-2xl mx-auto">
              Join thousands of developers and teams using CursorCode AI to ship
              faster than ever.
            </p>
            <Button
              size="lg"
              onClick={() => navigate(isAuthenticated ? "/dashboard" : "/signup")}
              className="bg-electric hover:bg-electric/90 text-white px-10 py-6 text-lg shadow-glow btn-glow"
              data-testid="final-cta-btn"
            >
              Start Building Free
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <Logo size="default" />
            <div className="flex items-center gap-6 text-sm text-zinc-500">
              <a href="#" className="hover:text-white transition-colors">
                Privacy
              </a>
              <a href="#" className="hover:text-white transition-colors">
                Terms
              </a>
              <a href="#" className="hover:text-white transition-colors">
                Contact
              </a>
            </div>
            <div className="text-sm text-zinc-500">
              © {new Date().getFullYear()} CursorCode AI. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
