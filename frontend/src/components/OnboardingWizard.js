import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import Logo from "./Logo";
import {
  ArrowRight,
  ArrowLeft,
  Loader2,
  Sparkles,
  Rocket,
  Check,
  Zap,
  LayoutDashboard,
  ShoppingCart,
  FileText,
  Server,
  Briefcase,
  MessageCircle,
  Bot,
  Smartphone,
  Wand2,
  Cloud,
  PartyPopper,
} from "lucide-react";

const ICON_MAP = {
  "layout-dashboard": LayoutDashboard,
  "shopping-cart": ShoppingCart,
  "file-text": FileText,
  server: Server,
  briefcase: Briefcase,
  "message-circle": MessageCircle,
  bot: Bot,
  smartphone: Smartphone,
};

const STEPS = [
  { id: "welcome", title: "Welcome" },
  { id: "template", title: "Pick Template" },
  { id: "customize", title: "Customize" },
  { id: "generate", title: "Generate" },
  { id: "complete", title: "Ready!" },
];

export default function OnboardingWizard({ onComplete }) {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [projectName, setProjectName] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generationPhase, setGenerationPhase] = useState(0);
  const [createdProject, setCreatedProject] = useState(null);

  useEffect(() => {
    api.get("/templates").then((res) => setTemplates(res.data.templates));
  }, []);

  useEffect(() => {
    if (selectedTemplate) {
      setProjectName(selectedTemplate.name);
      setCustomPrompt(selectedTemplate.prompt);
    }
  }, [selectedTemplate]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerationPhase(0);

    const phases = [
      "Analyzing requirements...",
      "Designing architecture...",
      "Generating frontend...",
      "Building backend...",
      "Running security audit...",
      "Writing tests...",
      "Preparing deployment...",
    ];

    // Simulate generation phases
    for (let i = 0; i < phases.length; i++) {
      setGenerationPhase(i);
      await new Promise((r) => setTimeout(r, 800));
    }

    // Create the project
    try {
      const res = await api.post(`/templates/${selectedTemplate.id}/create`);
      setCreatedProject(res.data);
      // Mark onboarding complete
      await api.post("/users/me/complete-onboarding");
      await refreshUser();
      setStep(4);
    } catch (err) {
      toast.error("Failed to create project");
    } finally {
      setGenerating(false);
    }
  };

  const handleFinish = () => {
    if (createdProject) {
      navigate(`/project/${createdProject.id}`);
    } else {
      onComplete();
    }
  };

  const handleSkip = async () => {
    try {
      await api.post("/users/me/complete-onboarding");
      await refreshUser();
    } catch (e) {
      // Silently handle
    }
    onComplete();
  };

  const GENERATION_PHASES = [
    "Analyzing requirements...",
    "Designing architecture...",
    "Generating frontend...",
    "Building backend...",
    "Running security audit...",
    "Writing tests...",
    "Preparing deployment...",
  ];

  return (
    <div
      className="fixed inset-0 z-50 bg-void flex items-center justify-center"
      data-testid="onboarding-wizard"
    >
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-electric/5 rounded-full blur-3xl animate-pulse" />
        <div
          className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-purple-500/5 rounded-full blur-3xl animate-pulse"
          style={{ animationDelay: "1.5s" }}
        />
      </div>

      <div className="relative z-10 w-full max-w-3xl mx-auto px-6">
        {/* Progress Bar */}
        <div className="flex items-center justify-between mb-8 px-4">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  i < step
                    ? "bg-electric text-white"
                    : i === step
                    ? "bg-electric/20 text-electric border-2 border-electric"
                    : "bg-white/5 text-zinc-600"
                }`}
              >
                {i < step ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`w-16 sm:w-24 h-0.5 mx-2 transition-all ${
                    i < step ? "bg-electric" : "bg-white/10"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="bg-void-paper border border-white/10 rounded-2xl overflow-hidden min-h-[440px] flex flex-col">
          <AnimatePresence mode="wait">
            {/* Step 0: Welcome */}
            {step === 0 && (
              <motion.div
                key="welcome"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex-1 flex flex-col items-center justify-center p-10 text-center"
              >
                <Logo size="large" className="justify-center mb-6" />
                <h1
                  className="font-outfit font-bold text-3xl text-white mb-3"
                  data-testid="welcome-title"
                >
                  Welcome, {user?.name}!
                </h1>
                <p className="text-zinc-400 max-w-md mb-2">
                  Let's build your first project in under a minute.
                </p>
                <p className="text-zinc-500 text-sm max-w-md mb-8">
                  Our AI agents will design, code, and deploy a full-stack
                  application from a single prompt.
                </p>
                <div className="flex items-center gap-6 text-sm text-zinc-500">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-electric" />
                    Pick a template
                  </div>
                  <div className="flex items-center gap-2">
                    <Wand2 className="w-4 h-4 text-purple-400" />
                    Customize it
                  </div>
                  <div className="flex items-center gap-2">
                    <Rocket className="w-4 h-4 text-emerald-400" />
                    Ship it
                  </div>
                </div>
              </motion.div>
            )}

            {/* Step 1: Pick Template */}
            {step === 1 && (
              <motion.div
                key="template"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex-1 p-6"
              >
                <h2 className="font-outfit font-bold text-xl text-white mb-1">
                  What do you want to build?
                </h2>
                <p className="text-sm text-zinc-400 mb-5">
                  Pick a starting point — you can always customize later.
                </p>
                <div
                  className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-h-[300px] overflow-y-auto pr-1"
                  data-testid="template-grid"
                >
                  {templates.map((t) => {
                    const Icon = ICON_MAP[t.icon] || Zap;
                    const isSelected = selectedTemplate?.id === t.id;
                    return (
                      <button
                        key={t.id}
                        onClick={() => setSelectedTemplate(t)}
                        data-testid={`onboard-template-${t.id}`}
                        className={`relative text-left p-4 rounded-xl border transition-all ${
                          isSelected
                            ? "border-electric bg-electric/10 shadow-glow"
                            : "border-white/5 bg-white/[0.02] hover:border-white/15"
                        }`}
                      >
                        {isSelected && (
                          <div className="absolute top-2 right-2">
                            <Check className="w-4 h-4 text-electric" />
                          </div>
                        )}
                        <div
                          className={`w-10 h-10 rounded-lg bg-gradient-to-br ${t.gradient} flex items-center justify-center mb-3`}
                        >
                          <Icon className="w-5 h-5 text-white" />
                        </div>
                        <p className="text-sm font-medium text-white leading-tight">
                          {t.name}
                        </p>
                        <p className="text-[10px] text-zinc-500 mt-1 line-clamp-2">
                          {t.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* Step 2: Customize */}
            {step === 2 && (
              <motion.div
                key="customize"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex-1 p-6"
              >
                <h2 className="font-outfit font-bold text-xl text-white mb-1">
                  Customize your project
                </h2>
                <p className="text-sm text-zinc-400 mb-6">
                  Fine-tune the name and prompt, or keep the defaults.
                </p>
                <div className="space-y-5">
                  <div>
                    <label className="text-sm text-zinc-300 mb-2 block">
                      Project Name
                    </label>
                    <Input
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                      className="bg-void border-white/10 text-white h-11"
                      placeholder="My Awesome App"
                      data-testid="onboard-project-name"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-zinc-300 mb-2 block">
                      AI Prompt
                    </label>
                    <textarea
                      value={customPrompt}
                      onChange={(e) => setCustomPrompt(e.target.value)}
                      className="w-full h-32 bg-void border border-white/10 rounded-lg text-white text-sm p-3 resize-none focus:border-electric/50 focus:outline-none transition-colors"
                      placeholder="Describe what you want to build..."
                      data-testid="onboard-prompt"
                    />
                    <p className="text-[10px] text-zinc-600 mt-1">
                      The AI agents will use this prompt to generate your full
                      project.
                    </p>
                  </div>
                  {selectedTemplate && (
                    <div className="flex items-center gap-2 flex-wrap">
                      {selectedTemplate.tech_stack.map((tech) => (
                        <span
                          key={tech}
                          className="px-2.5 py-1 rounded-md text-xs bg-white/5 text-zinc-400 border border-white/5"
                        >
                          {tech}
                        </span>
                      ))}
                      <span className="flex items-center gap-1 text-xs text-electric">
                        <Zap className="w-3 h-3" />~
                        {selectedTemplate.estimated_credits} credits
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Step 3: Generate */}
            {step === 3 && (
              <motion.div
                key="generate"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex-1 flex flex-col items-center justify-center p-10 text-center"
              >
                {generating ? (
                  <div data-testid="generating-state">
                    <div className="w-20 h-20 rounded-2xl bg-electric/10 flex items-center justify-center mx-auto mb-6 border border-electric/20">
                      <Loader2 className="w-10 h-10 text-electric animate-spin" />
                    </div>
                    <h2 className="font-outfit font-bold text-xl text-white mb-4">
                      Building your project...
                    </h2>
                    <div className="space-y-2 max-w-sm mx-auto">
                      {GENERATION_PHASES.map((phase, i) => (
                        <div
                          key={phase}
                          className={`flex items-center gap-3 text-sm transition-all ${
                            i < generationPhase
                              ? "text-emerald-400"
                              : i === generationPhase
                              ? "text-electric"
                              : "text-zinc-600"
                          }`}
                        >
                          {i < generationPhase ? (
                            <Check className="w-4 h-4 flex-shrink-0" />
                          ) : i === generationPhase ? (
                            <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border border-zinc-700 flex-shrink-0" />
                          )}
                          {phase}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div data-testid="pre-generate-state">
                    <div className="w-20 h-20 rounded-2xl bg-electric/10 flex items-center justify-center mx-auto mb-6 border border-electric/20">
                      <Sparkles className="w-10 h-10 text-electric" />
                    </div>
                    <h2 className="font-outfit font-bold text-xl text-white mb-2">
                      Ready to generate!
                    </h2>
                    <p className="text-zinc-400 text-sm max-w-md mb-6">
                      Our 6 AI agents (Architect, Frontend, Backend, Security,
                      QA, DevOps) will build{" "}
                      <span className="text-white font-medium">
                        {projectName}
                      </span>{" "}
                      for you.
                    </p>
                    <Button
                      onClick={handleGenerate}
                      className="bg-electric hover:bg-electric/90 text-white shadow-glow px-8 h-11"
                      data-testid="onboard-generate-btn"
                    >
                      <Rocket className="w-4 h-4 mr-2" />
                      Generate Project
                    </Button>
                  </div>
                )}
              </motion.div>
            )}

            {/* Step 4: Complete */}
            {step === 4 && (
              <motion.div
                key="complete"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex-1 flex flex-col items-center justify-center p-10 text-center"
              >
                <div className="w-20 h-20 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-6 border border-emerald-500/20">
                  <PartyPopper className="w-10 h-10 text-emerald-400" />
                </div>
                <h2
                  className="font-outfit font-bold text-2xl text-white mb-2"
                  data-testid="onboard-complete-title"
                >
                  Your project is ready!
                </h2>
                <p className="text-zinc-400 mb-2">
                  <span className="text-white font-medium">{projectName}</span>{" "}
                  has been created with a full AI-generated codebase.
                </p>
                <p className="text-zinc-500 text-sm mb-8">
                  Open it to explore the code, make edits, and deploy.
                </p>
                <div className="flex items-center gap-4">
                  <Button
                    onClick={handleFinish}
                    className="bg-electric hover:bg-electric/90 text-white shadow-glow px-6 h-11"
                    data-testid="onboard-open-project-btn"
                  >
                    Open Project
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  <Button
                    onClick={onComplete}
                    variant="ghost"
                    className="text-zinc-400 hover:text-white"
                    data-testid="onboard-go-dashboard-btn"
                  >
                    Go to Dashboard
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-white/5">
            <div>
              {step > 0 && step < 4 && !generating && (
                <Button
                  variant="ghost"
                  onClick={() => setStep(step - 1)}
                  className="text-zinc-400 hover:text-white"
                  data-testid="onboard-back-btn"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              )}
            </div>
            <div className="flex items-center gap-3">
              {step < 4 && (
                <Button
                  variant="ghost"
                  onClick={handleSkip}
                  className="text-zinc-500 hover:text-white text-sm"
                  data-testid="onboard-skip-btn"
                >
                  Skip for now
                </Button>
              )}
              {step < 3 && (
                <Button
                  onClick={() => setStep(step + 1)}
                  disabled={step === 1 && !selectedTemplate}
                  className="bg-electric hover:bg-electric/90 text-white"
                  data-testid="onboard-next-btn"
                >
                  {step === 0 ? "Get Started" : "Continue"}
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
