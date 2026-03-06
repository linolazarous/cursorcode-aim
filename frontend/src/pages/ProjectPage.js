import { useState, useEffect, useRef, useCallback } from "react";
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
  Bot,
  Zap,
  Copy,
  Check,
  FileCode,
  FileJson,
  FileText,
  File,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import Logo from "../components/Logo";
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
  { id: "grok-4-latest", name: "Grok 4 (Frontier)", description: "Deep reasoning", credits: 3 },
  { id: "grok-4-1-fast-reasoning", name: "Grok 4 Fast Reasoning", description: "Agentic workflows", credits: 2 },
  { id: "grok-4-1-fast-non-reasoning", name: "Grok 4 Fast", description: "High-throughput", credits: 1 },
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

  // Fetch project
  const fetchProject = useCallback(async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      setFiles(response.data.files || {});
      const fileKeys = Object.keys(response.data.files || {});
      if (fileKeys.length > 0) setSelectedFile(fileKeys[0]);
    } catch {
      toast.error("Failed to load project");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  }, [projectId, navigate]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [aiMessages]);

  // Generate AI code
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");

    const creditsRemaining = user?.credits - user?.credits_used || 0;
    const modelCredits = MODELS.find((m) => m.id === selectedModel)?.credits || 2;

    if (creditsRemaining < modelCredits) return toast.error("Insufficient credits");

    setGenerating(true);
    setAiMessages((prev) => [
      ...prev,
      { type: "user", content: prompt },
      { type: "system", content: "Generating code...", loading: true },
    ]);

    try {
      const response = await api.post("/ai/generate", {
        project_id: projectId,
        prompt,
        model: selectedModel,
        task_type: "code_generation",
      });

      const generatedCode = response.data.response;
      const newFiles = { ...files };
      if (!newFiles["App.jsx"]) newFiles["App.jsx"] = generatedCode;
      else newFiles[`generated_${Date.now()}.jsx`] = generatedCode;

      setFiles(newFiles);
      setSelectedFile(Object.keys(newFiles)[Object.keys(newFiles).length - 1]);
      await api.put(`/projects/${projectId}/files`, newFiles);

      setAiMessages((prev) => [
        ...prev.slice(0, -1),
        { type: "assistant", content: `Generated code using ${response.data.model_used}. Used ${response.data.credits_used} credit(s).` },
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
  }, [prompt, selectedModel, projectId, files, refreshUser, user]);

  // Deploy project
  const handleDeploy = useCallback(async () => {
    setDeploying(true);
    try {
      const response = await api.post(`/deploy/${projectId}`);
      setProject((prev) => ({ ...prev, deployed_url: response.data.deployed_url, status: "deployed" }));
      toast.success("Project deployed!");
    } catch {
      toast.error("Deployment failed");
    } finally {
      setDeploying(false);
    }
  }, [projectId]);

  // Save files
  const handleSaveFiles = useCallback(async () => {
    try {
      await api.put(`/projects/${projectId}/files`, files);
      toast.success("Files saved");
    } catch {
      toast.error("Failed to save files");
    }
  }, [files, projectId]);

  // Copy code
  const handleCopyCode = useCallback(() => {
    if (selectedFile && files[selectedFile]) {
      navigator.clipboard.writeText(files[selectedFile]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [selectedFile, files]);

  const getFileExtension = (filename) => filename.split(".").pop().toLowerCase();
  const getFileLanguage = (filename) => {
    const ext = getFileExtension(filename);
    const langMap = { js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", json: "json", css: "css", html: "html", md: "markdown", py: "python" };
    return langMap[ext] || "javascript";
  };

  if (loading) return <div className="min-h-screen bg-void flex items-center justify-center"><Loader2 className="w-8 h-8 text-electric animate-spin" /></div>;

  const creditsRemaining = user ? user.credits - user.credits_used : 0;

  return (
    <div className="min-h-screen bg-void flex flex-col">
      {/* Header and Main content unchanged */}
      {/* ... rest of JSX remains the same ... */}
    </div>
  );
}
