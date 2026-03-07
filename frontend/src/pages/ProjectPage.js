import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import api from "../lib/api";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const [project, setProject] = useState(null);
  const [files, setFiles] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [deploying, setDeploying] = useState(false);

  const fetchProject = useCallback(async () => {
    try {
      const res = await api.get("/project/stream", { params: { project_id: projectId } });
      setProject(res.data.project || {});
      setFiles(res.data.project?.files || {});
      const keys = Object.keys(res.data.project?.files || {});
      if (keys.length) setSelectedFile(keys[0]);
    } catch (err) {
      toast.error("Failed to load project");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  }, [projectId, navigate]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  // Generate AI code
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return toast.error("Please enter a prompt");

    const creditsRemaining = user?.credits - user?.credits_used || 0;
    if (creditsRemaining < 1) return toast.error("Insufficient credits");

    setGenerating(true);
    try {
      const res = await api.post("/project/deploy", { prompt, project_id: projectId });
      const newFiles = { ...files };
      newFiles[`generated_${Date.now()}.jsx`] = res.data.response || "// generated code";

      setFiles(newFiles);
      setSelectedFile(Object.keys(newFiles)[Object.keys(newFiles).length - 1]);
      toast.success("Code generated!");
      await refreshUser();
      setPrompt("");
    } catch (err) {
      const message = err.response?.data?.detail || "Generation failed";
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }, [prompt, projectId, files, refreshUser, user]);

  // Deploy project
  const handleDeploy = useCallback(async () => {
    setDeploying(true);
    try {
      const res = await api.post("/project/deploy", { project_id: projectId });
      setProject((prev) => ({ ...prev, deployed_url: res.data.deployed_url }));
      toast.success("Project deployed!");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Deployment failed");
    } finally {
      setDeploying(false);
    }
  }, [projectId]);

  // Save files
  const handleSaveFiles = useCallback(async () => {
    try {
      await api.put("/project/deploy", { project_id: projectId, files });
      toast.success("Files saved");
    } catch {
      toast.error("Failed to save files");
    }
  }, [projectId, files]);

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-void">
        <Loader2 className="w-8 h-8 text-electric animate-spin" />
      </div>
    );

  return (
    <div className="min-h-screen bg-void p-4">
      {/* Your UI here */}
      <Button onClick={handleGenerate} disabled={generating}>
        {generating ? "Generating..." : "Generate Code"}
      </Button>
      <Button onClick={handleDeploy} disabled={deploying}>
        {deploying ? "Deploying..." : "Deploy Project"}
      </Button>
      <Button onClick={handleSaveFiles}>Save Files</Button>
    </div>
  );
}
