import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import Editor from "@monaco-editor/react";
import {
  Code2, FileCode, FileJson, FileText, File, Eye, User, Calendar,
  ExternalLink, Copy, Check, ArrowLeft, Loader2, Share2,
} from "lucide-react";
import Logo from "../components/Logo";

const API_URL = process.env.REACT_APP_BACKEND_URL;
const FILE_ICONS = { js: FileCode, jsx: FileCode, ts: FileCode, tsx: FileCode, json: FileJson, css: FileText, html: File, md: FileText, py: FileCode, default: FileCode };

export default function SharedProjectPage() {
  const { shareId } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [copied, setCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/shared/${shareId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => { setProject(d); const keys = Object.keys(d.files || {}); if (keys.length) setSelectedFile(keys[0]); })
      .catch(() => setProject(null))
      .finally(() => setLoading(false));
  }, [shareId]);

  const copyCode = () => {
    if (selectedFile && project?.files[selectedFile]) {
      navigator.clipboard.writeText(project.files[selectedFile]);
      setCopied(true); setTimeout(() => setCopied(false), 2000);
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setLinkCopied(true); setTimeout(() => setLinkCopied(false), 2000);
  };

  const getLang = (f) => {
    const ext = f.split(".").pop().toLowerCase();
    return { js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", json: "json", css: "css", html: "html", md: "markdown", py: "python" }[ext] || "javascript";
  };

  if (loading) return <div className="min-h-screen bg-void flex items-center justify-center"><Loader2 className="w-8 h-8 text-electric animate-spin" /></div>;

  if (!project) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center" data-testid="shared-not-found">
        <div className="text-center"><Code2 className="w-16 h-16 text-zinc-600 mx-auto mb-4" /><h1 className="text-2xl font-bold text-white mb-2">Project Not Found</h1><p className="text-zinc-400 mb-6">This shared link may have expired or the project was set to private.</p><Link to="/"><Button className="bg-electric hover:bg-electric/90 text-white">Go Home</Button></Link></div>
      </div>
    );
  }

  const files = Object.keys(project.files || {});
  return (
    <div className="min-h-screen bg-void flex flex-col" data-testid="shared-project-page">
      {/* Header */}
      <header className="h-14 bg-void-paper border-b border-white/5 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/"><Logo size="default" /></Link>
          <div className="w-px h-6 bg-white/10" />
          <div>
            <h1 className="font-outfit font-medium text-white text-sm" data-testid="shared-project-name">{project.name}</h1>
            <div className="flex items-center gap-3 text-[11px] text-zinc-500">
              <span className="flex items-center gap-1"><User className="w-3 h-3" /> {project.owner_name}</span>
              <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {project.view_count} views</span>
              <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={copyLink} className="border-white/10 text-white" data-testid="copy-share-link-btn">
            {linkCopied ? <><Check className="w-4 h-4 mr-1 text-emerald" /> Copied!</> : <><Share2 className="w-4 h-4 mr-1" /> Share</>}
          </Button>
          {project.deployed_url && (
            <Button size="sm" onClick={() => window.open(project.deployed_url, "_blank")} className="bg-emerald hover:bg-emerald/90 text-white" data-testid="view-live-btn">
              <ExternalLink className="w-4 h-4 mr-1" /> View Live
            </Button>
          )}
          <Link to="/signup"><Button size="sm" className="bg-electric hover:bg-electric/90 text-white" data-testid="try-cursorcode-btn">Try CursorCode AI</Button></Link>
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 flex overflow-hidden">
        {/* File sidebar */}
        <div className="w-56 bg-void-paper border-r border-white/5 overflow-y-auto p-3 shrink-0">
          <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 px-2">Files ({files.length})</p>
          {files.map(f => {
            const ext = f.split(".").pop().toLowerCase();
            const Icon = FILE_ICONS[ext] || FILE_ICONS.default;
            return (
              <button key={f} onClick={() => setSelectedFile(f)} className={`flex items-center gap-2 w-full px-2 py-1.5 rounded text-xs text-left transition-colors ${selectedFile === f ? "bg-electric/10 text-electric" : "text-zinc-400 hover:text-white hover:bg-white/5"}`} data-testid={`shared-file-${f}`}>
                <Icon className="w-3.5 h-3.5 shrink-0" /> <span className="truncate">{f}</span>
              </button>
            );
          })}
          {files.length === 0 && <p className="text-zinc-600 text-xs px-2">No files generated yet</p>}
        </div>

        {/* Editor (read-only) */}
        <div className="flex-1 relative">
          {selectedFile && project.files[selectedFile] ? (
            <>
              <button onClick={copyCode} className="absolute top-3 right-3 z-10 p-2 rounded-lg bg-void-subtle border border-white/10 text-zinc-400 hover:text-white transition-colors" data-testid="copy-code-btn">
                {copied ? <Check className="w-4 h-4 text-emerald" /> : <Copy className="w-4 h-4" />}
              </button>
              <Editor
                height="100%" language={getLang(selectedFile)} value={project.files[selectedFile]}
                theme="vs-dark" options={{ readOnly: true, fontSize: 14, fontFamily: "'JetBrains Mono', monospace", minimap: { enabled: false }, padding: { top: 16 }, scrollBeyondLastLine: false }}
              />
            </>
          ) : (
            <div className="h-full flex items-center justify-center"><div className="text-center"><Code2 className="w-16 h-16 text-zinc-700 mx-auto mb-4" /><p className="text-zinc-400">Select a file to view</p></div></div>
          )}
        </div>
      </div>
    </div>
  );
}
