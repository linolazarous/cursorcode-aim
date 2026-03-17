import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import Editor from "@monaco-editor/react";
import {
  ArrowLeft,
  Cloud,
  Save,
  Loader2,
  Code2,
  Terminal,
  Zap,
  Bot,
  Copy,
  Check,
  FileCode,
  FileJson,
  FileText,
  File,
  ExternalLink,
  Sparkles,
  ShieldCheck,
  TestTube,
  Server,
  LayoutDashboard,
  CheckCircle2,
  XCircle,
  ChevronRight,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "../components/ui/resizable";
import CreditMeter from "../components/CreditMeter";

const FILE_ICONS = {
  js: FileCode, jsx: FileCode, ts: FileCode, tsx: FileCode,
  json: FileJson, css: FileText, html: File, md: FileText, py: FileCode,
  yml: FileText, yaml: FileText, default: FileCode,
};

const MODELS = [
  { id: "grok-4-latest", name: "Grok 4 (Frontier)", description: "Deep reasoning", credits: 3 },
  { id: "grok-4-1-fast-reasoning", name: "Grok 4 Fast Reasoning", description: "Agentic workflows", credits: 2 },
  { id: "grok-4-1-fast-non-reasoning", name: "Grok 4 Fast", description: "High-throughput", credits: 1 },
];

const AGENT_META = {
  architect: { icon: LayoutDashboard, color: "text-blue-400", bg: "bg-blue-500/10" },
  frontend: { icon: Code2, color: "text-purple-400", bg: "bg-purple-500/10" },
  backend: { icon: Server, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  security: { icon: ShieldCheck, color: "text-red-400", bg: "bg-red-500/10" },
  qa: { icon: TestTube, color: "text-teal-400", bg: "bg-teal-500/10" },
  devops: { icon: Terminal, color: "text-amber-400", bg: "bg-amber-500/10" },
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [selectedModel, setSelectedModel] = useState("grok-4-1-fast-reasoning");
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState({});
  const [copied, setCopied] = useState(false);
  const [buildMode, setBuildMode] = useState("multi"); // "single" or "multi"

  // Multi-agent streaming state
  const [agentStates, setAgentStates] = useState({});
  const [activeAgent, setActiveAgent] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [aiMessages, setAiMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  useEffect(() => { fetchProject(); }, [projectId]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [aiMessages, streamingText]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      const projectFiles = response.data.files || {};
      setFiles(projectFiles);
      const fileKeys = Object.keys(projectFiles).filter(f => !f.startsWith("_docs/"));
      if (fileKeys.length > 0) setSelectedFile(fileKeys[0]);
    } catch (error) {
      toast.error("Failed to load project");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  // === Single-agent generation (quick mode) ===
  const handleQuickGenerate = async () => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");
    setGenerating(true);
    setAiMessages(prev => [...prev, { type: "user", content: prompt }, { type: "system", content: "Generating code...", loading: true }]);
    try {
      const response = await api.post("/ai/generate", {
        project_id: projectId, prompt, model: selectedModel, task_type: "code_generation",
      });
      const newFiles = { ...files, ...(response.data.files || {}) };
      if (!response.data.files || Object.keys(response.data.files).length === 0) {
        newFiles[`generated_${Date.now()}.jsx`] = response.data.response;
      }
      setFiles(newFiles);
      const codeFiles = Object.keys(newFiles).filter(f => !f.startsWith("_docs/"));
      setSelectedFile(codeFiles[codeFiles.length - 1]);
      setAiMessages(prev => [...prev.slice(0, -1), {
        type: "assistant",
        content: `Generated code using ${response.data.model_used}. Used ${response.data.credits_used} credit(s). ${Object.keys(response.data.files || {}).length} files created.`,
      }]);
      await refreshUser();
      setPrompt("");
      toast.success("Code generated!");
    } catch (error) {
      const message = error.response?.data?.detail || "Generation failed";
      toast.error(message);
      setAiMessages(prev => [...prev.slice(0, -1), { type: "error", content: message }]);
    } finally {
      setGenerating(false);
    }
  };

  // === Multi-agent SSE streaming build ===
  const handleMultiAgentBuild = useCallback(() => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");
    if (eventSourceRef.current) eventSourceRef.current.close();

    setGenerating(true);
    setAgentStates({});
    setActiveAgent(null);
    setStreamingText("");
    setAiMessages(prev => [...prev, { type: "user", content: prompt }]);

    const token = localStorage.getItem("access_token");
    const params = new URLSearchParams({
      project_id: projectId,
      prompt: prompt,
      model: selectedModel,
      token: token,
    });
    const url = `${BACKEND_URL}/api/ai/generate-stream?${params.toString()}`;

    const es = new EventSource(url);
    eventSourceRef.current = es;
    let agentOutputs = {};

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "agent_start") {
          setActiveAgent(data.agent);
          setStreamingText("");
          agentOutputs[data.agent] = "";
          setAgentStates(prev => ({ ...prev, [data.agent]: "running" }));
          setAiMessages(prev => [...prev, {
            type: "agent_status", agent: data.agent, label: data.label, status: "running",
          }]);
        }

        if (data.type === "agent_chunk") {
          agentOutputs[data.agent] = (agentOutputs[data.agent] || "") + data.content;
          setStreamingText(agentOutputs[data.agent]);
        }

        if (data.type === "agent_complete") {
          setAgentStates(prev => ({ ...prev, [data.agent]: "done" }));
          setAiMessages(prev => {
            const updated = [...prev];
            const idx = updated.findLastIndex(m => m.agent === data.agent && m.type === "agent_status");
            if (idx !== -1) updated[idx] = { ...updated[idx], status: "done", filesCount: data.files_count };
            return updated;
          });
        }

        if (data.type === "agent_error") {
          setAgentStates(prev => ({ ...prev, [data.agent]: "error" }));
        }

        if (data.type === "complete") {
          es.close();
          setGenerating(false);
          setActiveAgent(null);
          setStreamingText("");
          // Reload project to get updated files
          fetchProject();
          refreshUser();
          setPrompt("");
          toast.success(`Build complete! ${data.files.length} files generated. ${data.credits_used} credit(s) used.`);
          setAiMessages(prev => [...prev, {
            type: "assistant",
            content: `Multi-agent build complete. ${data.files.filter(f => !f.startsWith("_docs/")).length} code files + ${data.files.filter(f => f.startsWith("_docs/")).length} docs generated.`,
          }]);
        }
      } catch (e) {
        console.error("SSE parse error:", e);
      }
    };

    es.onerror = () => {
      es.close();
      setGenerating(false);
      setActiveAgent(null);
      toast.error("Connection lost during build");
    };
  }, [prompt, projectId, selectedModel, fetchProject, refreshUser]);

  const handleGenerate = () => {
    if (buildMode === "multi") handleMultiAgentBuild();
    else handleQuickGenerate();
  };

  const handleDeploy = async () => {
    setDeploying(true);
    try {
      const response = await api.post(`/deploy/${projectId}`);
      setProject({ ...project, deployed_url: response.data.deployed_url, status: "deployed" });
      toast.success("Project deployed!");
    } catch (error) {
      toast.error("Deployment failed");
    } finally {
      setDeploying(false);
    }
  };

  const handleSaveFiles = async () => {
    try {
      await api.put(`/projects/${projectId}/files`, files);
      toast.success("Files saved");
    } catch (error) {
      toast.error("Failed to save files");
    }
  };

  const handleCopyCode = () => {
    if (selectedFile && files[selectedFile]) {
      navigator.clipboard.writeText(files[selectedFile]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getFileLanguage = (filename) => {
    const ext = filename.split(".").pop().toLowerCase();
    const langMap = { js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", json: "json", css: "css", html: "html", md: "markdown", py: "python", yml: "yaml", yaml: "yaml" };
    return langMap[ext] || "javascript";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-electric animate-spin" />
      </div>
    );
  }

  const codeFiles = Object.keys(files).filter(f => !f.startsWith("_docs/"));
  const docFiles = Object.keys(files).filter(f => f.startsWith("_docs/"));

  return (
    <div className="min-h-screen bg-void flex flex-col">
      {/* Header */}
      <header className="h-14 bg-void-paper border-b border-white/5 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors" data-testid="back-to-dashboard">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-electric/20 flex items-center justify-center">
              <Code2 className="w-4 h-4 text-electric" />
            </div>
            <span className="font-outfit font-medium text-white">{project?.name}</span>
          </div>
          {project?.status === "deployed" && (
            <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-emerald/10 text-emerald text-xs">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse" /> Deployed
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          {user && <CreditMeter credits={user.credits} creditsUsed={user.credits_used} plan={user.plan} />}
          <Button variant="outline" size="sm" onClick={handleSaveFiles} className="border-white/10 text-white hover:bg-white/5" data-testid="save-files-btn">
            <Save className="w-4 h-4 mr-2" /> Save
          </Button>
          <Button size="sm" onClick={handleDeploy} disabled={deploying || codeFiles.length === 0} className="bg-emerald hover:bg-emerald/90 text-white shadow-glow-green" data-testid="deploy-btn">
            {deploying ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Deploying...</> : <><Cloud className="w-4 h-4 mr-2" /> Deploy</>}
          </Button>
          {project?.deployed_url && (
            <Button variant="ghost" size="sm" onClick={() => window.open(project.deployed_url, "_blank")} className="text-zinc-400 hover:text-white" data-testid="view-live-btn">
              <ExternalLink className="w-4 h-4" />
            </Button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* AI Chat Panel */}
          <ResizablePanel defaultSize={35} minSize={25}>
            <div className="h-full flex flex-col bg-void-paper border-r border-white/5">
              {/* Chat Header */}
              <div className="p-4 border-b border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-electric" />
                    <span className="font-outfit font-medium text-white">AI Generator</span>
                  </div>
                  {/* Build mode toggle */}
                  <div className="flex items-center bg-void rounded-lg p-0.5 border border-white/5">
                    <button
                      onClick={() => setBuildMode("single")}
                      className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${buildMode === "single" ? "bg-electric text-white" : "text-zinc-400 hover:text-white"}`}
                      data-testid="mode-single"
                    >
                      Quick
                    </button>
                    <button
                      onClick={() => setBuildMode("multi")}
                      className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${buildMode === "multi" ? "bg-electric text-white" : "text-zinc-400 hover:text-white"}`}
                      data-testid="mode-multi"
                    >
                      Multi-Agent
                    </button>
                  </div>
                </div>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger className="bg-void-subtle border-white/10 text-white" data-testid="model-selector">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-void-paper border-white/10">
                    {MODELS.map((model) => (
                      <SelectItem key={model.id} value={model.id} className="text-white focus:bg-white/5">
                        <div className="flex items-center justify-between w-full">
                          <span>{model.name}</span>
                          <span className="text-xs text-zinc-500 ml-2">{model.credits} cr</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Agent Status Bar (multi-agent mode) */}
              {buildMode === "multi" && Object.keys(agentStates).length > 0 && (
                <div className="px-4 py-3 border-b border-white/5 space-y-1.5" data-testid="agent-status-bar">
                  {Object.entries(AGENT_META).map(([agent, meta]) => {
                    const state = agentStates[agent];
                    if (!state) return null;
                    const IconComp = meta.icon;
                    return (
                      <div key={agent} className={`flex items-center gap-2 px-2 py-1 rounded-md text-xs ${activeAgent === agent ? "bg-white/5" : ""}`}>
                        <div className={`w-5 h-5 rounded flex items-center justify-center ${meta.bg}`}>
                          <IconComp className={`w-3 h-3 ${meta.color}`} />
                        </div>
                        <span className="text-zinc-300 capitalize flex-1">{agent}</span>
                        {state === "running" && <Loader2 className="w-3 h-3 text-electric animate-spin" />}
                        {state === "done" && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                        {state === "error" && <XCircle className="w-3 h-3 text-red-400" />}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {aiMessages.length === 0 ? (
                  <div className="text-center py-8">
                    <Bot className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                    <p className="text-zinc-400 text-sm mb-1">
                      {buildMode === "multi"
                        ? "Describe your app. 6 AI agents will architect, code, secure, test, and deploy it."
                        : "Describe what you want to build and I'll generate the code."}
                    </p>
                    <p className="text-zinc-600 text-xs">Powered by xAI Grok</p>
                  </div>
                ) : (
                  aiMessages.map((msg, index) => (
                    <motion.div key={index} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                      {msg.type === "agent_status" ? (
                        <AgentStatusMessage msg={msg} />
                      ) : (
                        <div className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
                          <div className={`max-w-[90%] rounded-lg p-3 text-sm ${
                            msg.type === "user" ? "bg-electric text-white"
                              : msg.type === "error" ? "bg-red-500/10 text-red-400 border border-red-500/20"
                              : "bg-void-subtle text-zinc-300 border border-white/5"
                          }`}>
                            {msg.loading ? (
                              <div className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" /> <span>{msg.content}</span>
                              </div>
                            ) : (
                              <p className="whitespace-pre-wrap">{msg.content}</p>
                            )}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))
                )}

                {/* Live streaming text */}
                {activeAgent && streamingText && (
                  <div className="rounded-lg bg-void border border-white/5 p-3 text-xs font-mono text-zinc-400 max-h-40 overflow-y-auto" data-testid="streaming-output">
                    <div className="flex items-center gap-2 mb-2 text-electric text-[11px]">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span className="capitalize">{activeAgent} agent generating...</span>
                    </div>
                    <pre className="whitespace-pre-wrap">{streamingText.slice(-800)}</pre>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-white/5">
                <Textarea
                  placeholder={buildMode === "multi"
                    ? "Describe your full app... (e.g., 'Build a project management tool with kanban boards, team collaboration, and Stripe billing')"
                    : "Describe what you want... (e.g., 'Create a todo app with local storage')"}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleGenerate(); } }}
                  className="min-h-[80px] bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 resize-none mb-3"
                  data-testid="ai-prompt-input"
                />
                <Button
                  onClick={handleGenerate}
                  disabled={generating || !prompt.trim()}
                  className="w-full bg-electric hover:bg-electric/90 text-white shadow-glow"
                  data-testid="generate-btn"
                >
                  {generating ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> {buildMode === "multi" ? "Building..." : "Generating..."}</>
                  ) : (
                    <><Sparkles className="w-4 h-4 mr-2" /> {buildMode === "multi" ? "Build with 6 Agents" : "Generate Code"}</>
                  )}
                </Button>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle className="w-1 bg-white/5 hover:bg-electric/50 transition-colors" />

          {/* Code Editor Panel */}
          <ResizablePanel defaultSize={65}>
            <div className="h-full flex flex-col">
              {/* File Tabs */}
              <div className="h-10 bg-void-paper border-b border-white/5 flex items-center px-2 overflow-x-auto gap-1">
                {codeFiles.map((filename) => {
                  const ext = filename.split(".").pop().toLowerCase();
                  const IconComponent = FILE_ICONS[ext] || FILE_ICONS.default;
                  return (
                    <button
                      key={filename}
                      onClick={() => setSelectedFile(filename)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs whitespace-nowrap transition-colors ${
                        selectedFile === filename ? "bg-electric/10 text-electric" : "text-zinc-400 hover:text-white hover:bg-white/5"
                      }`}
                      data-testid={`file-tab-${filename}`}
                    >
                      <IconComponent className="w-3.5 h-3.5" /> {filename}
                    </button>
                  );
                })}
                {docFiles.length > 0 && (
                  <>
                    <div className="w-px h-5 bg-white/10 mx-1" />
                    {docFiles.map((filename) => (
                      <button
                        key={filename}
                        onClick={() => setSelectedFile(filename)}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded text-[11px] whitespace-nowrap transition-colors ${
                          selectedFile === filename ? "bg-amber-500/10 text-amber-400" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
                        }`}
                      >
                        <FileText className="w-3 h-3" /> {filename.replace("_docs/", "")}
                      </button>
                    ))}
                  </>
                )}
                {Object.keys(files).length === 0 && (
                  <span className="text-zinc-500 text-sm px-3">No files yet - generate some code!</span>
                )}
              </div>

              {/* Editor */}
              <div className="flex-1 relative">
                {selectedFile && files[selectedFile] ? (
                  <>
                    <button
                      onClick={handleCopyCode}
                      className="absolute top-3 right-3 z-10 p-2 rounded-lg bg-void-subtle border border-white/10 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                      data-testid="copy-code-btn"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <Editor
                      height="100%"
                      language={getFileLanguage(selectedFile)}
                      value={files[selectedFile]}
                      onChange={(value) => setFiles({ ...files, [selectedFile]: value || "" })}
                      theme="vs-dark"
                      options={{
                        fontSize: 14, fontFamily: "'JetBrains Mono', monospace",
                        minimap: { enabled: false }, padding: { top: 16 },
                        scrollBeyondLastLine: false, smoothScrolling: true,
                        cursorBlinking: "smooth", renderLineHighlight: "none",
                        overviewRulerBorder: false, hideCursorInOverviewRuler: true,
                      }}
                    />
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <Code2 className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                      <p className="text-zinc-400">Generate code to see it here</p>
                      <p className="text-zinc-600 text-sm mt-1">Use Multi-Agent mode for full-stack generation</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}

function AgentStatusMessage({ msg }) {
  const meta = AGENT_META[msg.agent] || {};
  const IconComp = meta.icon || Bot;
  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${
      msg.status === "done" ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/5 bg-void-subtle"
    }`}>
      <div className={`w-7 h-7 rounded-lg ${meta.bg || "bg-white/5"} flex items-center justify-center`}>
        <IconComp className={`w-4 h-4 ${meta.color || "text-zinc-400"}`} />
      </div>
      <div className="flex-1">
        <p className="text-xs font-medium text-white">{msg.label}</p>
        {msg.status === "done" && msg.filesCount > 0 && (
          <p className="text-[11px] text-zinc-500">{msg.filesCount} files generated</p>
        )}
      </div>
      {msg.status === "running" && <Loader2 className="w-4 h-4 text-electric animate-spin" />}
      {msg.status === "done" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
    </div>
  );
}
