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
  ArrowLeft, Cloud, Save, Loader2, Code2, Terminal, Zap, Bot, Copy, Check,
  FileCode, FileJson, FileText, File, ExternalLink, Sparkles, ShieldCheck,
  TestTube, Server, LayoutDashboard, CheckCircle2, XCircle, Share2, Download,
  History, Clock, RotateCcw, Trash2, BookOpen, ChevronDown,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "../components/ui/resizable";
import CreditMeter from "../components/CreditMeter";

const FILE_ICONS = { js: FileCode, jsx: FileCode, ts: FileCode, tsx: FileCode, json: FileJson, css: FileText, html: File, md: FileText, py: FileCode, default: FileCode };
const MODELS = [
  { id: "grok-4-latest", name: "Grok 4 (Frontier)", credits: 3 },
  { id: "grok-4-1-fast-reasoning", name: "Grok 4 Fast Reasoning", credits: 2 },
  { id: "grok-4-1-fast-non-reasoning", name: "Grok 4 Fast", credits: 1 },
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
  const [buildMode, setBuildMode] = useState("multi");

  // Multi-agent
  const [agentStates, setAgentStates] = useState({});
  const [activeAgent, setActiveAgent] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [aiMessages, setAiMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // New features state
  const [showPromptTemplates, setShowPromptTemplates] = useState(false);
  const [promptTemplates, setPromptTemplates] = useState([]);
  const [showTimeline, setShowTimeline] = useState(false);
  const [activities, setActivities] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [showSnapshots, setShowSnapshots] = useState(false);

  useEffect(() => { fetchProject(); fetchMessages(); fetchPromptTemplates(); }, [projectId]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [aiMessages, streamingText]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      const pf = response.data.files || {};
      setFiles(pf);
      const fk = Object.keys(pf).filter(f => !f.startsWith("_docs/"));
      if (fk.length > 0 && !selectedFile) setSelectedFile(fk[0]);
    } catch { toast.error("Failed to load project"); navigate("/dashboard"); }
    finally { setLoading(false); }
  };

  const fetchMessages = async () => {
    try {
      const res = await api.get(`/projects/${projectId}/messages`);
      if (res.data.length > 0) setAiMessages(res.data.map(m => ({ type: m.type, content: m.content, agent: m.agent, label: m.label, status: m.status, filesCount: m.files_count })));
    } catch {}
  };

  const fetchPromptTemplates = async () => {
    try { const res = await api.get("/prompt-templates"); setPromptTemplates(res.data); } catch {}
  };

  const fetchActivity = async () => {
    try { const res = await api.get(`/projects/${projectId}/activity`); setActivities(res.data); } catch {}
  };

  const fetchSnapshots = async () => {
    try { const res = await api.get(`/projects/${projectId}/snapshots`); setSnapshots(res.data); } catch {}
  };

  const saveMessage = async (msg) => {
    try { await api.post(`/projects/${projectId}/messages`, msg); } catch {}
  };

  // === Quick Generate ===
  const handleQuickGenerate = async () => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");
    setGenerating(true);
    const userMsg = { type: "user", content: prompt };
    setAiMessages(prev => [...prev, userMsg, { type: "system", content: "Generating...", loading: true }]);
    saveMessage(userMsg);
    try {
      const response = await api.post("/ai/generate", { project_id: projectId, prompt, model: selectedModel, task_type: "code_generation" });
      const nf = { ...files, ...(response.data.files || {}) };
      if (!response.data.files || Object.keys(response.data.files).length === 0) nf[`generated_${Date.now()}.jsx`] = response.data.response;
      setFiles(nf);
      const cf = Object.keys(nf).filter(f => !f.startsWith("_docs/"));
      setSelectedFile(cf[cf.length - 1]);
      const assistMsg = { type: "assistant", content: `Generated with ${response.data.model_used}. ${response.data.credits_used} credit(s). ${Object.keys(response.data.files || {}).length} files.` };
      setAiMessages(prev => [...prev.slice(0, -1), assistMsg]);
      saveMessage(assistMsg);
      await refreshUser();
      setPrompt("");
      toast.success("Code generated!");
    } catch (error) {
      const m = error.response?.data?.detail || "Generation failed";
      toast.error(m);
      setAiMessages(prev => [...prev.slice(0, -1), { type: "error", content: m }]);
    } finally { setGenerating(false); }
  };

  // === Multi-Agent SSE ===
  const handleMultiAgentBuild = useCallback(() => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");
    if (eventSourceRef.current) eventSourceRef.current.close();
    setGenerating(true);
    setAgentStates({});
    setActiveAgent(null);
    setStreamingText("");
    const userMsg = { type: "user", content: prompt };
    setAiMessages(prev => [...prev, userMsg]);
    saveMessage(userMsg);

    const token = localStorage.getItem("access_token");
    const params = new URLSearchParams({ project_id: projectId, prompt, model: selectedModel, token });
    const es = new EventSource(`${BACKEND_URL}/api/ai/generate-stream?${params.toString()}`);
    eventSourceRef.current = es;
    let agentOutputs = {};

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "agent_start") {
          setActiveAgent(data.agent); setStreamingText("");
          agentOutputs[data.agent] = "";
          setAgentStates(prev => ({ ...prev, [data.agent]: "running" }));
          const statusMsg = { type: "agent_status", agent: data.agent, label: data.label, status: "running" };
          setAiMessages(prev => [...prev, statusMsg]);
          saveMessage(statusMsg);
        }
        if (data.type === "agent_chunk") {
          agentOutputs[data.agent] = (agentOutputs[data.agent] || "") + data.content;
          setStreamingText(agentOutputs[data.agent]);
        }
        if (data.type === "agent_complete") {
          setAgentStates(prev => ({ ...prev, [data.agent]: "done" }));
          setAiMessages(prev => {
            const u = [...prev];
            const idx = u.findLastIndex(m => m.agent === data.agent && m.type === "agent_status");
            if (idx !== -1) u[idx] = { ...u[idx], status: "done", filesCount: data.files_count };
            return u;
          });
        }
        if (data.type === "agent_error") { setAgentStates(prev => ({ ...prev, [data.agent]: "error" })); }
        if (data.type === "complete") {
          es.close(); setGenerating(false); setActiveAgent(null); setStreamingText("");
          fetchProject(); refreshUser(); setPrompt("");
          const doneMsg = { type: "assistant", content: `Build complete! ${data.files.filter(f => !f.startsWith("_docs/")).length} code files generated.` };
          setAiMessages(prev => [...prev, doneMsg]);
          saveMessage(doneMsg);
          toast.success(`Build complete! ${data.credits_used} credit(s) used.`);
        }
      } catch {}
    };
    es.onerror = () => { es.close(); setGenerating(false); setActiveAgent(null); toast.error("Connection lost"); };
  }, [prompt, projectId, selectedModel]);

  const handleGenerate = () => { buildMode === "multi" ? handleMultiAgentBuild() : handleQuickGenerate(); };

  const handleDeploy = async () => {
    setDeploying(true);
    try {
      const r = await api.post(`/deploy/${projectId}`);
      setProject(p => ({ ...p, deployed_url: r.data.deployed_url, status: "deployed" }));
      toast.success("Deployed!");
    } catch { toast.error("Deploy failed"); }
    finally { setDeploying(false); }
  };

  const handleShare = async () => {
    try {
      const r = await api.post(`/projects/${projectId}/share`);
      setProject(p => ({ ...p, is_public: r.data.is_public, share_id: r.data.share_id }));
      if (r.data.is_public) {
        const shareUrl = `${window.location.origin}/shared/${r.data.share_id}`;
        navigator.clipboard.writeText(shareUrl);
        toast.success("Share link copied!");
      } else { toast.info("Project set to private"); }
    } catch { toast.error("Failed to toggle sharing"); }
  };

  const handleExport = async () => {
    try {
      const r = await api.get(`/projects/${projectId}/export`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = url;
      a.download = `${project?.name?.replace(/\s+/g, "-").toLowerCase() || "project"}.zip`;
      a.click(); URL.revokeObjectURL(url);
      toast.success("Project downloaded!");
    } catch { toast.error("Export failed"); }
  };

  const handleSnapshot = async () => {
    try {
      const r = await api.post(`/projects/${projectId}/snapshots`, { label: `v${snapshots.length + 1}` });
      toast.success(`Snapshot "${r.data.label}" saved`);
      fetchSnapshots();
    } catch { toast.error("Snapshot failed"); }
  };

  const handleRestore = async (snapshotId, label) => {
    try {
      await api.post(`/projects/${projectId}/snapshots/${snapshotId}/restore`);
      toast.success(`Restored from "${label}"`);
      fetchProject(); fetchSnapshots();
    } catch { toast.error("Restore failed"); }
  };

  const handleCopyCode = () => {
    if (selectedFile && files[selectedFile]) { navigator.clipboard.writeText(files[selectedFile]); setCopied(true); setTimeout(() => setCopied(false), 2000); }
  };

  const getLang = (f) => {
    const ext = f.split(".").pop().toLowerCase();
    return { js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", json: "json", css: "css", html: "html", md: "markdown", py: "python", yml: "yaml", yaml: "yaml" }[ext] || "javascript";
  };

  if (loading) return <div className="min-h-screen bg-void flex items-center justify-center"><Loader2 className="w-8 h-8 text-electric animate-spin" /></div>;

  const codeFiles = Object.keys(files).filter(f => !f.startsWith("_docs/"));
  const docFiles = Object.keys(files).filter(f => f.startsWith("_docs/"));

  return (
    <div className="min-h-screen bg-void flex flex-col">
      {/* Header */}
      <header className="h-14 bg-void-paper border-b border-white/5 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="text-zinc-400 hover:text-white" data-testid="back-to-dashboard"><ArrowLeft className="w-4 h-4" /></Link>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-electric/20 flex items-center justify-center"><Code2 className="w-4 h-4 text-electric" /></div>
            <span className="font-outfit font-medium text-white">{project?.name}</span>
          </div>
          {project?.status === "deployed" && <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-emerald/10 text-emerald text-xs"><div className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse" /> Deployed</div>}
        </div>
        <div className="flex items-center gap-2">
          {user && <CreditMeter credits={user.credits} creditsUsed={user.credits_used} plan={user.plan} />}

          {/* Share */}
          <Button variant="outline" size="sm" onClick={handleShare} className={`border-white/10 ${project?.is_public ? "text-electric border-electric/30" : "text-white"}`} data-testid="share-btn">
            <Share2 className="w-4 h-4 mr-1" /> {project?.is_public ? "Shared" : "Share"}
          </Button>

          {/* Export */}
          <Button variant="outline" size="sm" onClick={handleExport} disabled={codeFiles.length === 0} className="border-white/10 text-white" data-testid="export-btn">
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>

          {/* Snapshots */}
          <Button variant="outline" size="sm" onClick={() => { fetchSnapshots(); setShowSnapshots(!showSnapshots); }} className="border-white/10 text-white" data-testid="snapshots-btn">
            <History className="w-4 h-4 mr-1" /> Versions
          </Button>

          {/* Activity */}
          <Button variant="outline" size="sm" onClick={() => { fetchActivity(); setShowTimeline(!showTimeline); }} className="border-white/10 text-white" data-testid="activity-btn">
            <Clock className="w-4 h-4 mr-1" /> Activity
          </Button>

          {/* Save */}
          <Button variant="outline" size="sm" onClick={async () => { await api.put(`/projects/${projectId}/files`, files); toast.success("Saved"); }} className="border-white/10 text-white" data-testid="save-files-btn">
            <Save className="w-4 h-4" />
          </Button>

          {/* Deploy */}
          <Button size="sm" onClick={handleDeploy} disabled={deploying || codeFiles.length === 0} className="bg-emerald hover:bg-emerald/90 text-white" data-testid="deploy-btn">
            {deploying ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Cloud className="w-4 h-4 mr-1" />} Deploy
          </Button>
        </div>
      </header>

      {/* Snapshots Drawer */}
      <AnimatePresence>
        {showSnapshots && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden bg-void-paper border-b border-white/5">
            <div className="p-4 max-h-48 overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium text-white">Version Snapshots</p>
                <Button size="sm" onClick={handleSnapshot} className="bg-electric/10 text-electric hover:bg-electric/20" data-testid="create-snapshot-btn"><Save className="w-3 h-3 mr-1" /> Save Snapshot</Button>
              </div>
              {snapshots.length === 0 ? <p className="text-xs text-zinc-500">No snapshots yet</p> : (
                <div className="space-y-2">
                  {snapshots.map(s => (
                    <div key={s.id} className="flex items-center justify-between p-2 rounded-lg bg-void border border-white/5 text-xs">
                      <div><span className="text-white font-medium">{s.label}</span><span className="text-zinc-500 ml-2">{s.file_count} files</span><span className="text-zinc-600 ml-2">{new Date(s.created_at).toLocaleString()}</span></div>
                      <Button size="sm" variant="ghost" onClick={() => handleRestore(s.id, s.label)} className="text-electric hover:text-white" data-testid={`restore-${s.id}`}><RotateCcw className="w-3 h-3 mr-1" /> Restore</Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Activity Drawer */}
      <AnimatePresence>
        {showTimeline && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden bg-void-paper border-b border-white/5">
            <div className="p-4 max-h-48 overflow-y-auto">
              <p className="text-sm font-medium text-white mb-3">Activity Timeline</p>
              {activities.length === 0 ? <p className="text-xs text-zinc-500">No activity yet</p> : (
                <div className="space-y-2">
                  {activities.map(a => (
                    <div key={a.id} className="flex items-center gap-3 text-xs">
                      <div className="w-1.5 h-1.5 rounded-full bg-electric shrink-0" />
                      <span className="text-zinc-300 flex-1">{a.detail || a.action}</span>
                      <span className="text-zinc-600 whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* AI Panel */}
          <ResizablePanel defaultSize={35} minSize={25}>
            <div className="h-full flex flex-col bg-void-paper border-r border-white/5">
              {/* Header */}
              <div className="p-4 border-b border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2"><Bot className="w-5 h-5 text-electric" /><span className="font-outfit font-medium text-white">AI Generator</span></div>
                  <div className="flex items-center bg-void rounded-lg p-0.5 border border-white/5">
                    <button onClick={() => setBuildMode("single")} className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${buildMode === "single" ? "bg-electric text-white" : "text-zinc-400"}`} data-testid="mode-single">Quick</button>
                    <button onClick={() => setBuildMode("multi")} className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${buildMode === "multi" ? "bg-electric text-white" : "text-zinc-400"}`} data-testid="mode-multi">Multi-Agent</button>
                  </div>
                </div>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger className="bg-void-subtle border-white/10 text-white" data-testid="model-selector"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-void-paper border-white/10">
                    {MODELS.map(m => (<SelectItem key={m.id} value={m.id} className="text-white focus:bg-white/5"><span>{m.name}</span><span className="text-xs text-zinc-500 ml-2">{m.credits}cr</span></SelectItem>))}
                  </SelectContent>
                </Select>
              </div>

              {/* Agent Status Bar */}
              {buildMode === "multi" && Object.keys(agentStates).length > 0 && (
                <div className="px-4 py-3 border-b border-white/5 space-y-1.5" data-testid="agent-status-bar">
                  {Object.entries(AGENT_META).map(([agent, meta]) => {
                    const state = agentStates[agent];
                    if (!state) return null;
                    const I = meta.icon;
                    return (<div key={agent} className={`flex items-center gap-2 px-2 py-1 rounded-md text-xs ${activeAgent === agent ? "bg-white/5" : ""}`}><div className={`w-5 h-5 rounded flex items-center justify-center ${meta.bg}`}><I className={`w-3 h-3 ${meta.color}`} /></div><span className="text-zinc-300 capitalize flex-1">{agent}</span>{state === "running" && <Loader2 className="w-3 h-3 text-electric animate-spin" />}{state === "done" && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}{state === "error" && <XCircle className="w-3 h-3 text-red-400" />}</div>);
                  })}
                </div>
              )}

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {aiMessages.length === 0 ? (
                  <div className="text-center py-8">
                    <Bot className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                    <p className="text-zinc-400 text-sm mb-3">{buildMode === "multi" ? "Describe your app. 6 agents will build it." : "Describe what you want."}</p>
                    <p className="text-zinc-600 text-xs mb-4">Powered by xAI Grok</p>
                    {/* Prompt Templates */}
                    <button onClick={() => setShowPromptTemplates(!showPromptTemplates)} className="text-electric text-xs hover:underline flex items-center gap-1 mx-auto" data-testid="show-templates-btn">
                      <BookOpen className="w-3 h-3" /> Browse Prompt Templates <ChevronDown className={`w-3 h-3 transition-transform ${showPromptTemplates ? "rotate-180" : ""}`} />
                    </button>
                    {showPromptTemplates && (
                      <div className="grid grid-cols-2 gap-2 mt-4 text-left">
                        {promptTemplates.map(t => (
                          <button key={t.id} onClick={() => { setPrompt(t.prompt); setShowPromptTemplates(false); }} className="p-3 rounded-lg border border-white/5 bg-void/50 hover:border-electric/30 transition-all text-left" data-testid={`prompt-template-${t.id}`}>
                            <p className="text-xs font-medium text-white">{t.name}</p>
                            <p className="text-[10px] text-zinc-500 mt-0.5 line-clamp-2">{t.prompt.slice(0, 60)}...</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  aiMessages.map((msg, i) => (
                    <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                      {msg.type === "agent_status" ? (
                        <AgentStatusMessage msg={msg} />
                      ) : (
                        <div className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
                          <div className={`max-w-[90%] rounded-lg p-3 text-sm ${msg.type === "user" ? "bg-electric text-white" : msg.type === "error" ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-void-subtle text-zinc-300 border border-white/5"}`}>
                            {msg.loading ? <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />{msg.content}</div> : <p className="whitespace-pre-wrap">{msg.content}</p>}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
                {activeAgent && streamingText && (
                  <div className="rounded-lg bg-void border border-white/5 p-3 text-xs font-mono text-zinc-400 max-h-40 overflow-y-auto" data-testid="streaming-output">
                    <div className="flex items-center gap-2 mb-2 text-electric text-[11px]"><Loader2 className="w-3 h-3 animate-spin" /><span className="capitalize">{activeAgent} generating...</span></div>
                    <pre className="whitespace-pre-wrap">{streamingText.slice(-800)}</pre>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-white/5">
                <Textarea placeholder={buildMode === "multi" ? "Describe your full app..." : "Describe what you want..."} value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleGenerate(); } }} className="min-h-[80px] bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 resize-none mb-3" data-testid="ai-prompt-input" />
                <Button onClick={handleGenerate} disabled={generating || !prompt.trim()} className="w-full bg-electric hover:bg-electric/90 text-white shadow-glow" data-testid="generate-btn">
                  {generating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />{buildMode === "multi" ? "Building..." : "Generating..."}</> : <><Sparkles className="w-4 h-4 mr-2" />{buildMode === "multi" ? "Build with 6 Agents" : "Generate Code"}</>}
                </Button>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle className="w-1 bg-white/5 hover:bg-electric/50 transition-colors" />

          {/* Editor */}
          <ResizablePanel defaultSize={65}>
            <div className="h-full flex flex-col">
              <div className="h-10 bg-void-paper border-b border-white/5 flex items-center px-2 overflow-x-auto gap-1">
                {codeFiles.map(f => {
                  const ext = f.split(".").pop().toLowerCase();
                  const Icon = FILE_ICONS[ext] || FILE_ICONS.default;
                  return (<button key={f} onClick={() => setSelectedFile(f)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs whitespace-nowrap transition-colors ${selectedFile === f ? "bg-electric/10 text-electric" : "text-zinc-400 hover:text-white hover:bg-white/5"}`} data-testid={`file-tab-${f}`}><Icon className="w-3.5 h-3.5" />{f}</button>);
                })}
                {docFiles.length > 0 && (<><div className="w-px h-5 bg-white/10 mx-1" />{docFiles.map(f => (<button key={f} onClick={() => setSelectedFile(f)} className={`flex items-center gap-1.5 px-2 py-1 rounded text-[11px] whitespace-nowrap transition-colors ${selectedFile === f ? "bg-amber-500/10 text-amber-400" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"}`}><FileText className="w-3 h-3" />{f.replace("_docs/", "")}</button>))}</>)}
                {Object.keys(files).length === 0 && <span className="text-zinc-500 text-sm px-3">No files - generate some code!</span>}
              </div>
              <div className="flex-1 relative">
                {selectedFile && files[selectedFile] ? (
                  <>
                    <button onClick={handleCopyCode} className="absolute top-3 right-3 z-10 p-2 rounded-lg bg-void-subtle border border-white/10 text-zinc-400 hover:text-white transition-colors" data-testid="copy-code-btn">
                      {copied ? <Check className="w-4 h-4 text-emerald" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <Editor height="100%" language={getLang(selectedFile)} value={files[selectedFile]} onChange={v => setFiles({ ...files, [selectedFile]: v || "" })} theme="vs-dark" options={{ fontSize: 14, fontFamily: "'JetBrains Mono', monospace", minimap: { enabled: false }, padding: { top: 16 }, scrollBeyondLastLine: false, smoothScrolling: true, cursorBlinking: "smooth", renderLineHighlight: "none" }} />
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center"><div className="text-center"><Code2 className="w-16 h-16 text-zinc-700 mx-auto mb-4" /><p className="text-zinc-400">Generate code to see it here</p></div></div>
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
  const I = meta.icon || Bot;
  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${msg.status === "done" ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/5 bg-void-subtle"}`}>
      <div className={`w-7 h-7 rounded-lg ${meta.bg || "bg-white/5"} flex items-center justify-center`}><I className={`w-4 h-4 ${meta.color || "text-zinc-400"}`} /></div>
      <div className="flex-1"><p className="text-xs font-medium text-white">{msg.label}</p>{msg.status === "done" && msg.filesCount > 0 && <p className="text-[11px] text-zinc-500">{msg.filesCount} files</p>}</div>
      {msg.status === "running" && <Loader2 className="w-4 h-4 text-electric animate-spin" />}
      {msg.status === "done" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
    </div>
  );
}
