import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import Editor from "@monaco-editor/react";
import {
  ArrowLeft,
  Play,
  Cloud,
  Save,
  Loader2,
  Code2,
  FolderTree,
  Terminal,
  Eye,
  Zap,
  Bot,
  Settings,
  Copy,
  Check,
  ChevronDown,
  FileCode,
  FileJson,
  FileText,
  File,
  RefreshCw,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import Logo from "../components/Logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
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

const FILE_ICONS = {
  js: FileCode,
  jsx: FileCode,
  ts: FileCode,
  tsx: FileCode,
  json: FileJson,
  css: FileText,
  html: File,
  md: FileText,
  py: FileCode,
  default: FileCode,
};

const MODELS = [
  {
    id: "grok-4-latest",
    name: "Grok 4 (Frontier)",
    description: "Deep reasoning",
    credits: 3,
  },
  {
    id: "grok-4-1-fast-reasoning",
    name: "Grok 4 Fast Reasoning",
    description: "Agentic workflows",
    credits: 2,
  },
  {
    id: "grok-4-1-fast-non-reasoning",
    name: "Grok 4 Fast",
    description: "High-throughput",
    credits: 1,
  },
];

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
  const [aiMessages, setAiMessages] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [aiMessages]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      setFiles(response.data.files || {});
      if (Object.keys(response.data.files || {}).length > 0) {
        setSelectedFile(Object.keys(response.data.files)[0]);
      }
    } catch (error) {
      toast.error("Failed to load project");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error("Please enter a prompt");
      return;
    }

    const creditsRemaining = user.credits - user.credits_used;
    const modelCredits = MODELS.find((m) => m.id === selectedModel)?.credits || 2;

    if (creditsRemaining < modelCredits) {
      toast.error("Insufficient credits");
      return;
    }

    setGenerating(true);
    setAiMessages((prev) => [
      ...prev,
      { type: "user", content: prompt },
      { type: "system", content: "Generating code...", loading: true },
    ]);

    try {
      const response = await api.post("/ai/generate", {
        project_id: projectId,
        prompt: prompt,
        model: selectedModel,
        task_type: "code_generation",
      });

      // Parse response and update files
      const generatedCode = response.data.response;

      // Simple file parsing - in production this would be more sophisticated
      const newFiles = { ...files };
      if (!newFiles["App.jsx"]) {
        newFiles["App.jsx"] = generatedCode;
      } else {
        newFiles[`generated_${Date.now()}.jsx`] = generatedCode;
      }

      setFiles(newFiles);
      setSelectedFile(Object.keys(newFiles)[Object.keys(newFiles).length - 1]);

      // Save files to project
      await api.put(`/projects/${projectId}/files`, newFiles);

      setAiMessages((prev) => [
        ...prev.slice(0, -1),
        {
          type: "assistant",
          content: `Generated code using ${response.data.model_used}. Used ${response.data.credits_used} credit(s).`,
        },
      ]);

      await refreshUser();
      setPrompt("");
      toast.success("Code generated!");
    } catch (error) {
      const message = error.response?.data?.detail || "Generation failed";
      toast.error(message);
      setAiMessages((prev) => [
        ...prev.slice(0, -1),
        { type: "error", content: message },
      ]);
    } finally {
      setGenerating(false);
    }
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

  const getFileExtension = (filename) => {
    return filename.split(".").pop().toLowerCase();
  };

  const getFileLanguage = (filename) => {
    const ext = getFileExtension(filename);
    const langMap = {
      js: "javascript",
      jsx: "javascript",
      ts: "typescript",
      tsx: "typescript",
      json: "json",
      css: "css",
      html: "html",
      md: "markdown",
      py: "python",
    };
    return langMap[ext] || "javascript";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-electric animate-spin" />
      </div>
    );
  }

  const creditsRemaining = user ? user.credits - user.credits_used : 0;

  return (
    <div className="min-h-screen bg-void flex flex-col">
      {/* Header */}
      <header className="h-14 bg-void-paper border-b border-white/5 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
            data-testid="back-to-dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-electric/20 flex items-center justify-center">
              <Code2 className="w-4 h-4 text-electric" />
            </div>
            <span className="font-outfit font-medium text-white">
              {project?.name}
            </span>
          </div>

          {project?.status === "deployed" && (
            <div className="flex items-center gap-2 px-2 py-1 rounded-full bg-emerald/10 text-emerald text-xs">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse" />
              Deployed
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Credits */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-void-subtle border border-white/5">
            <Zap className="w-4 h-4 text-electric" />
            <span className="text-sm text-white font-medium">
              {creditsRemaining}
            </span>
            <span className="text-xs text-zinc-500">credits</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleSaveFiles}
            className="border-white/10 text-white hover:bg-white/5"
            data-testid="save-files-btn"
          >
            <Save className="w-4 h-4 mr-2" />
            Save
          </Button>

          <Button
            size="sm"
            onClick={handleDeploy}
            disabled={deploying || Object.keys(files).length === 0}
            className="bg-emerald hover:bg-emerald/90 text-white shadow-glow-green"
            data-testid="deploy-btn"
          >
            {deploying ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Deploying...
              </>
            ) : (
              <>
                <Cloud className="w-4 h-4 mr-2" />
                Deploy
              </>
            )}
          </Button>

          {project?.deployed_url && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.open(project.deployed_url, "_blank")}
              className="text-zinc-400 hover:text-white"
              data-testid="view-live-btn"
            >
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
              <div className="p-4 border-b border-white/5">
                <div className="flex items-center gap-2 mb-3">
                  <Bot className="w-5 h-5 text-electric" />
                  <span className="font-outfit font-medium text-white">
                    AI Generator
                  </span>
                </div>

                {/* Model Selector */}
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger
                    className="bg-void-subtle border-white/10 text-white"
                    data-testid="model-selector"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-void-paper border-white/10">
                    {MODELS.map((model) => (
                      <SelectItem
                        key={model.id}
                        value={model.id}
                        className="text-white focus:bg-white/5"
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>{model.name}</span>
                          <span className="text-xs text-zinc-500 ml-2">
                            {model.credits} credit{model.credits > 1 ? "s" : ""}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {aiMessages.length === 0 ? (
                  <div className="text-center py-8">
                    <Bot className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                    <p className="text-zinc-400 text-sm">
                      Describe what you want to build and I'll generate the code
                    </p>
                  </div>
                ) : (
                  aiMessages.map((msg, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${
                        msg.type === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[90%] rounded-lg p-3 ${
                          msg.type === "user"
                            ? "bg-electric text-white"
                            : msg.type === "error"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-void-subtle text-zinc-300 border border-white/5"
                        }`}
                      >
                        {msg.loading ? (
                          <div className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>{msg.content}</span>
                          </div>
                        ) : (
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        )}
                      </div>
                    </motion.div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-white/5">
                <Textarea
                  placeholder="Describe what you want to build... (e.g., 'Create a todo app with React and local storage')"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleGenerate();
                    }
                  }}
                  className="min-h-[100px] bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 resize-none mb-3"
                  data-testid="ai-prompt-input"
                />
                <Button
                  onClick={handleGenerate}
                  disabled={generating || !prompt.trim()}
                  className="w-full bg-electric hover:bg-electric/90 text-white shadow-glow"
                  data-testid="generate-btn"
                >
                  {generating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Generate Code
                    </>
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
              <div className="h-10 bg-void-paper border-b border-white/5 flex items-center px-2 overflow-x-auto">
                {Object.keys(files).map((filename) => {
                  const ext = getFileExtension(filename);
                  const IconComponent = FILE_ICONS[ext] || FILE_ICONS.default;
                  return (
                    <button
                      key={filename}
                      onClick={() => setSelectedFile(filename)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm whitespace-nowrap transition-colors ${
                        selectedFile === filename
                          ? "bg-electric/10 text-electric"
                          : "text-zinc-400 hover:text-white hover:bg-white/5"
                      }`}
                      data-testid={`file-tab-${filename}`}
                    >
                      <IconComponent className="w-4 h-4" />
                      {filename}
                    </button>
                  );
                })}
                {Object.keys(files).length === 0 && (
                  <span className="text-zinc-500 text-sm px-3">
                    No files yet - generate some code!
                  </span>
                )}
              </div>

              {/* Editor */}
              <div className="flex-1 relative">
                {selectedFile && files[selectedFile] ? (
                  <>
                    {/* Copy button */}
                    <button
                      onClick={handleCopyCode}
                      className="absolute top-3 right-3 z-10 p-2 rounded-lg bg-void-subtle border border-white/10 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                      data-testid="copy-code-btn"
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-emerald" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>

                    <Editor
                      height="100%"
                      language={getFileLanguage(selectedFile)}
                      value={files[selectedFile]}
                      onChange={(value) =>
                        setFiles({ ...files, [selectedFile]: value || "" })
                      }
                      theme="vs-dark"
                      options={{
                        fontSize: 14,
                        fontFamily: "'JetBrains Mono', monospace",
                        minimap: { enabled: false },
                        padding: { top: 16 },
                        scrollBeyondLastLine: false,
                        smoothScrolling: true,
                        cursorBlinking: "smooth",
                        renderLineHighlight: "none",
                        overviewRulerBorder: false,
                        hideCursorInOverviewRuler: true,
                      }}
                    />
                  </>
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <Code2 className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                      <p className="text-zinc-400">
                        Generate code to see it here
                      </p>
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
