// frontend/src/pages/DashboardPage.js
import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import Logo from "../components/Logo";
import Sidebar from "../components/Sidebar"; // Extracted Sidebar component
import CreditMeter from "../components/CreditMeter";
import {
  Plus,
  FolderOpen,
  Clock,
  Zap,
  Settings,
  LogOut,
  Code2,
  Cloud,
  LayoutDashboard,
  CreditCard,
  ChevronRight,
  Loader2,
  Search,
  MoreVertical,
  Trash2,
  ExternalLink,
  User,
  Github,
  AlertCircle,
  Star,
  GitFork,
  Import,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [githubRepos, setGithubRepos] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [importing, setImporting] = useState(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await api.get("/projects");
      setProjects(response.data);
    } catch (error) {
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      toast.error("Project name is required");
      return;
    }
    setCreating(true);
    try {
      const response = await api.post("/projects", {
        name: newProjectName,
        description: newProjectDescription,
      });
      setProjects([response.data, ...projects]);
      setCreateDialogOpen(false);
      setNewProjectName("");
      setNewProjectDescription("");
      toast.success("Project created!");
      navigate(`/project/${response.data.id}`);
    } catch (error) {
      toast.error("Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async (projectId) => {
    try {
      await api.delete(`/projects/${projectId}`);
      setProjects(projects.filter((p) => p.id !== projectId));
      toast.success("Project deleted");
    } catch (error) {
      toast.error("Failed to delete project");
    }
  };

  const handleConnectGitHub = async () => {
    try {
      const response = await api.get("/auth/github");
      window.location.href = response.data.url;
    } catch (error) {
      toast.error("Failed to connect GitHub");
    }
  };

  const handleFetchGitHubRepos = async () => {
    if (!user?.github_username) {
      toast.error("Please connect your GitHub account first");
      return;
    }
    setLoadingRepos(true);
    try {
      const response = await api.get("/github/repos");
      setGithubRepos(response.data);
      setImportDialogOpen(true);
    } catch (error) {
      toast.error("Failed to fetch repositories");
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleImportRepo = async (repoFullName) => {
    setImporting(repoFullName);
    try {
      const response = await api.post(`/github/import/${repoFullName}`);
      setProjects([response.data, ...projects]);
      setImportDialogOpen(false);
      toast.success("Repository imported!");
      navigate(`/project/${response.data.id}`);
    } catch (error) {
      toast.error("Failed to import repository");
    } finally {
      setImporting(null);
    }
  };

  const handleResendVerification = async () => {
    try {
      await api.post("/auth/resend-verification");
      toast.success("Verification email sent!");
    } catch (error) {
      toast.error("Failed to send verification email");
    }
  };

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const creditsRemaining = user ? user.credits - user.credits_used : 0;
  const creditsPercentage = user
    ? ((user.credits - user.credits_used) / user.credits) * 100
    : 0;

  return (
    <div className="min-h-screen bg-void flex">
      {/* Sidebar */}
      <Sidebar
        user={user}
        logout={logout}
        creditsRemaining={creditsRemaining}
        creditsPercentage={creditsPercentage}
        onUpgrade={() => navigate("/pricing")}
        onConnectGitHub={handleConnectGitHub}
        onImportGitHub={handleFetchGitHubRepos}
        githubLoading={loadingRepos}
      />

      {/* Main Content */}
      <main className="flex-1 ml-64">
        {/* Email Verification Banner */}
        {user && !user.email_verified && (
          <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-8 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-500" />
                <span className="text-yellow-400">
                  Please verify your email address to access all features.
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResendVerification}
                className="text-yellow-400 hover:text-yellow-300 hover:bg-yellow-500/10"
              >
                Resend Email
              </Button>
            </div>
          </div>
        )}

        {/* Header */}
        <header className="sticky top-0 z-30 bg-void/80 backdrop-blur-xl border-b border-white/5">
          <div className="flex items-center justify-between px-8 py-4">
            <div>
              <h1 className="font-outfit font-bold text-2xl text-white">
                Projects
              </h1>
              <p className="text-sm text-zinc-400">
                {projects.length} project{projects.length !== 1 ? "s" : ""}
              </p>
            </div>

            <div className="flex items-center gap-4">
              {user && (
                <CreditMeter
                  credits={user.credits}
                  creditsUsed={user.credits_used}
                  plan={user.plan}
                />
              )}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <Input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64 bg-void-subtle border-white/10 text-white placeholder:text-zinc-500 h-10"
                />
              </div>

              <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-electric hover:bg-electric/90 text-white shadow-glow">
                    <Plus className="w-4 h-4 mr-2" />
                    New Project
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-void-paper border-white/10">
                  <DialogHeader>
                    <DialogTitle className="font-outfit text-xl text-white">
                      Create New Project
                    </DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleCreateProject} className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <label className="text-sm text-white">Project Name</label>
                      <Input
                        placeholder="My Awesome App"
                        value={newProjectName}
                        onChange={(e) => setNewProjectName(e.target.value)}
                        className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-white">
                        Description (optional)
                      </label>
                      <Input
                        placeholder="A brief description of your project"
                        value={newProjectDescription}
                        onChange={(e) => setNewProjectDescription(e.target.value)}
                        className="bg-void-subtle border-white/10 text-white placeholder:text-zinc-500"
                      />
                    </div>
                    <Button
                      type="submit"
                      disabled={creating}
                      className="w-full bg-electric hover:bg-electric/90 text-white"
                    >
                      {creating ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4 mr-2" />
                          Create Project
                        </>
                      )}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </header>

        {/* Import GitHub Dialog */}
        <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
          <DialogContent className="bg-void-paper border-white/10 max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle className="font-outfit text-xl text-white flex items-center gap-2">
                <Github className="w-5 h-5" />
                Import from GitHub
              </DialogTitle>
            </DialogHeader>
            <div className="flex-1 overflow-y-auto mt-4 space-y-2">
              {githubRepos.length === 0 ? (
                <p className="text-zinc-400 text-center py-8">
                  No repositories found
                </p>
              ) : (
                githubRepos.map((repo) => (
                  <div
                    key={repo.id}
                    className="p-4 rounded-lg bg-void-subtle border border-white/5 hover:border-electric/30 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-white truncate">{repo.name}</h4>
                        <p className="text-sm text-zinc-400 truncate mt-1">
                          {repo.description || "No description"}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                          {repo.language && (
                            <span className="px-2 py-0.5 rounded bg-white/5">
                              {repo.language}
                            </span>
                          )}
                          <div className="flex items-center gap-1">
                            <Star className="w-3 h-3" />
                            {repo.stargazers_count}
                          </div>
                          <div className="flex items-center gap-1">
                            <GitFork className="w-3 h-3" />
                            {repo.forks_count}
                          </div>
                          {repo.private && <span className="text-yellow-500">Private</span>}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleImportRepo(repo.full_name)}
                        disabled={importing === repo.full_name}
                        className="ml-4 bg-electric hover:bg-electric/90 text-white"
                      >
                        {importing === repo.full_name ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <Import className="w-4 h-4 mr-1" />
                            Import
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </DialogContent>
        </Dialog>

        {/* Content */}
        <div className="p-8">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-electric animate-spin" />
            </div>
          ) : filteredProjects.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-20"
            >
              {searchQuery ? (
                <>
                  <Search className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                  <h3 className="font-outfit text-xl text-white mb-2">
                    No projects found
                  </h3>
                  <p className="text-zinc-400">No projects match "{searchQuery}"</p>
                </>
              ) : (
                <>
                  <FolderOpen className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                  <h3 className="font-outfit text-xl text-white mb-2">No projects yet</h3>
                  <p className="text-zinc-400 mb-6">
                    Create your first project or start from a template
                  </p>
                  <div className="flex items-center justify-center gap-4">
                    <Button
                      onClick={() => setCreateDialogOpen(true)}
                      className="bg-electric hover:bg-electric/90 text-white shadow-glow"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Create Project
                    </Button>
                    <Button
                      onClick={() => navigate("/templates")}
                      variant="outline"
                      className="border-white/10 text-white hover:bg-white/5"
                      data-testid="browse-templates-btn"
                    >
                      <Star className="w-4 h-4 mr-2" />
                      Browse Templates
                    </Button>
                    {user?.github_username && (
                      <Button
                        onClick={handleFetchGitHubRepos}
                        variant="outline"
                        className="border-white/10 text-white hover:bg-white/5"
                      >
                        <Github className="w-4 h-4 mr-2" />
                        Import from GitHub
                      </Button>
                    )}
                  </div>
                </>
              )}
            </motion.div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              <AnimatePresence>
                {filteredProjects.map((project, index) => (
                  <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: index * 0.05 }}
                    className="group relative p-6 rounded-xl bg-void-paper border border-white/5 hover:border-electric/30 transition-colors cursor-pointer"
                    onClick={() => navigate(`/project/${project.id}`)}
                  >
                    <div className="absolute inset-0 rounded-xl bg-electric/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                      <div className="flex items-start justify-between mb-4">
                        <div className="w-10 h-10 rounded-lg bg-electric/10 flex items-center justify-center">
                          {project.github_repo ? (
                            <Github className="w-5 h-5 text-white" />
                          ) : (
                            <Code2 className="w-5 h-5 text-electric" />
                          )}
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button className="p-2 rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-colors">
                              <MoreVertical className="w-4 h-4" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent
                            align="end"
                            className="bg-void-paper border-white/10"
                          >
                            {project.deployed_url && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  window.open(project.deployed_url, "_blank");
                                }}
                                className="text-zinc-300 focus:text-white focus:bg-white/5"
                              >
                                <ExternalLink className="w-4 h-4 mr-2" />
                                View Live
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteProject(project.id);
                              }}
                              className="text-red-400 focus:text-red-300 focus:bg-red-500/10"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      <h3 className="font-outfit font-semibold text-lg text-white mb-1 group-hover:text-electric transition-colors">
                        {project.name}
                      </h3>
                      <p className="text-sm text-zinc-400 line-clamp-2 mb-4">
                        {project.description || "No description"}
                      </p>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <Clock className="w-3 h-3" />
                          {new Date(project.updated_at).toLocaleDateString()}
                        </div>

                        {project.deployed_url ? (
                          <div className="flex items-center gap-1 text-xs text-emerald">
                            <Cloud className="w-3 h-3" />
                            Deployed
                          </div>
                        ) : project.status === "imported" ? (
                          <div className="flex items-center gap-1 text-xs text-purple-400">
                            <Github className="w-3 h-3" />
                            Imported
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-xs text-zinc-500">
                            <div className="w-2 h-2 rounded-full bg-yellow-500" />
                            Draft
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
