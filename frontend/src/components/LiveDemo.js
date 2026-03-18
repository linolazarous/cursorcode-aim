import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import {
  ArrowRight, Play, LayoutDashboard, Code2, Server,
  ShieldCheck, TestTube, Terminal, CheckCircle2, Loader2,
  Sparkles, FileCode, FileJson, FileText, File,
} from "lucide-react";

const EXAMPLE_PROMPTS = [
  "Build a project management app with Kanban boards, team chat, and Stripe billing",
  "Create a real-time crypto portfolio tracker with price alerts and chart analytics",
  "Build a healthcare appointment scheduler with patient records and video consultations",
];

const AGENTS = [
  { id: "architect", name: "Architect", icon: LayoutDashboard, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
  { id: "frontend", name: "Frontend", icon: Code2, color: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/20" },
  { id: "backend", name: "Backend", icon: Server, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  { id: "security", name: "Security", icon: ShieldCheck, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
  { id: "qa", name: "QA", icon: TestTube, color: "text-teal-400", bg: "bg-teal-500/10", border: "border-teal-500/20" },
  { id: "devops", name: "DevOps", icon: Terminal, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
];

const FILE_ICON_MAP = { js: FileCode, jsx: FileCode, ts: FileCode, tsx: FileCode, json: FileJson, css: FileText, py: FileCode, html: FileText, md: FileText };
const getFileIcon = (name) => FILE_ICON_MAP[name.split(".").pop()] || File;

const DEMO_FILES = {
  "src/App.tsx": `import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import KanbanBoard from './pages/KanbanBoard';
import TeamChat from './pages/TeamChat';
import Settings from './pages/Settings';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/login" element={<Login />} />
          <Route path="/board/:id" element={<KanbanBoard />} />
          <Route path="/chat" element={<TeamChat />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}`,
  "src/pages/Dashboard.tsx": `import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import ProjectCard from '../components/ProjectCard';
import StatsWidget from '../components/StatsWidget';

export default function Dashboard() {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <h1>Welcome back, {user.name}</h1>
      <StatsWidget projects={projects} />
      <div className="grid grid-cols-3 gap-6 mt-8">
        {projects.map(p => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>
    </div>
  );
}`,
  "server/routes/projects.py": `from fastapi import APIRouter, Depends
from models.project import Project
from auth.middleware import get_current_user
from database import db

router = APIRouter(prefix="/api/projects")

@router.get("/")
async def list_projects(user=Depends(get_current_user)):
    projects = await db.projects.find(
        {"team_id": user.team_id}
    ).to_list(100)
    return {"projects": projects}

@router.post("/")
async def create_project(data: Project, user=Depends(get_current_user)):
    data.owner_id = user.id
    result = await db.projects.insert_one(data.dict())
    return {"id": str(result.inserted_id)}`,
  "server/routes/billing.py": `import stripe
from fastapi import APIRouter, Request
from config import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY
router = APIRouter(prefix="/api/billing")

@router.post("/checkout")
async def create_checkout(request: Request):
    data = await request.json()
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": data["price_id"],
            "quantity": 1,
        }],
        mode="subscription",
        success_url=data["success_url"],
    )
    return {"url": session.url}`,
  "server/middleware/security.py": `from fastapi import Request, HTTPException
from jose import jwt, JWTError
import rate_limiter

async def verify_token(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")

async def rate_limit(request: Request):
    client_ip = request.client.host
    if rate_limiter.is_exceeded(client_ip):
        raise HTTPException(429, "Rate limit exceeded")`,
  "tests/test_projects.py": `import pytest
from httpx import AsyncClient
from server.main import app

@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(app=app) as client:
        response = await client.post("/api/projects/", json={
            "name": "Test Project",
            "description": "A test project"
        }, headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data`,
  "docker-compose.yml": `version: '3.8'
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - REACT_APP_API_URL=http://api:8000

  api:
    build: ./server
    ports: ["8000:8000"]
    environment:
      - MONGO_URL=mongodb://db:27017/app
      - STRIPE_SECRET_KEY=\${STRIPE_SECRET_KEY}
    depends_on: [db]

  db:
    image: mongo:7
    volumes: ["mongo_data:/data/db"]

volumes:
  mongo_data:`,
};

const AGENT_MESSAGES = [
  { agent: "architect", message: "Analyzing requirements... Designing system architecture with 6 microservices" },
  { agent: "architect", message: "Database schema: users, projects, boards, tasks, messages, subscriptions" },
  { agent: "frontend", message: "Scaffolding React app with TypeScript, Tailwind CSS, and React Router" },
  { agent: "frontend", message: "Building Dashboard, KanbanBoard, TeamChat, and Settings pages" },
  { agent: "backend", message: "Creating FastAPI server with project CRUD and Stripe billing routes" },
  { agent: "backend", message: "Setting up WebSocket server for real-time team chat" },
  { agent: "security", message: "Implementing JWT auth with refresh tokens and rate limiting middleware" },
  { agent: "security", message: "Adding CORS, input validation, SQL injection prevention, and XSS guards" },
  { agent: "qa", message: "Writing 24 test cases across unit, integration, and e2e coverage" },
  { agent: "qa", message: "All tests passing. Code coverage: 94.2%" },
  { agent: "devops", message: "Generating Docker Compose config with frontend, API, and MongoDB services" },
  { agent: "devops", message: "Build complete. Ready to deploy at https://your-app.cursorcode.app" },
];

export default function LiveDemo() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | generating | complete
  const [activeAgent, setActiveAgent] = useState(null);
  const [completedAgents, setCompletedAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [visibleCode, setVisibleCode] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [visibleFiles, setVisibleFiles] = useState([]);
  const [progress, setProgress] = useState(0);
  const codeRef = useRef(null);
  const cancelRef = useRef(false);

  const fileNames = Object.keys(DEMO_FILES);

  const streamCode = useCallback(async (code) => {
    const chars = code.split("");
    let result = "";
    for (let i = 0; i < chars.length; i++) {
      if (cancelRef.current) return;
      result += chars[i];
      if (i % 3 === 0) {
        setVisibleCode(result);
        await new Promise((r) => setTimeout(r, 8));
      }
    }
    setVisibleCode(result);
  }, []);

  const runDemo = useCallback(async (inputPrompt) => {
    cancelRef.current = false;
    setPhase("generating");
    setMessages([]);
    setCompletedAgents([]);
    setVisibleFiles([]);
    setVisibleCode("");
    setSelectedFile(null);
    setProgress(0);

    const fileOrder = [...fileNames];
    const totalSteps = AGENT_MESSAGES.length;

    for (let i = 0; i < totalSteps; i++) {
      if (cancelRef.current) return;
      const msg = AGENT_MESSAGES[i];
      setActiveAgent(msg.agent);
      setMessages((prev) => [...prev, msg]);
      setProgress(((i + 1) / totalSteps) * 100);

      // Reveal files at certain milestones
      if (i === 2 && fileOrder[0]) { setVisibleFiles((p) => [...p, fileOrder[0]]); setSelectedFile(fileOrder[0]); await streamCode(DEMO_FILES[fileOrder[0]]); }
      if (i === 3 && fileOrder[1]) { setVisibleFiles((p) => [...p, fileOrder[1]]); setSelectedFile(fileOrder[1]); await streamCode(DEMO_FILES[fileOrder[1]]); }
      if (i === 4 && fileOrder[2]) { setVisibleFiles((p) => [...p, fileOrder[2]]); setSelectedFile(fileOrder[2]); await streamCode(DEMO_FILES[fileOrder[2]]); }
      if (i === 5 && fileOrder[3]) { setVisibleFiles((p) => [...p, fileOrder[3]]); setSelectedFile(fileOrder[3]); await streamCode(DEMO_FILES[fileOrder[3]]); }
      if (i === 6 && fileOrder[4]) { setVisibleFiles((p) => [...p, fileOrder[4]]); setSelectedFile(fileOrder[4]); await streamCode(DEMO_FILES[fileOrder[4]]); }
      if (i === 8 && fileOrder[5]) { setVisibleFiles((p) => [...p, fileOrder[5]]); setSelectedFile(fileOrder[5]); await streamCode(DEMO_FILES[fileOrder[5]]); }
      if (i === 10 && fileOrder[6]) { setVisibleFiles((p) => [...p, fileOrder[6]]); setSelectedFile(fileOrder[6]); await streamCode(DEMO_FILES[fileOrder[6]]); }

      // Mark agent complete on their last message
      if (i + 1 >= totalSteps || AGENT_MESSAGES[i + 1]?.agent !== msg.agent) {
        setCompletedAgents((prev) => [...prev, msg.agent]);
      }

      if (![2, 3, 4, 5, 6, 8, 10].includes(i)) {
        await new Promise((r) => setTimeout(r, 800));
      }
    }

    setActiveAgent(null);
    setPhase("complete");
  }, [fileNames, streamCode]);

  const handleFileClick = (file) => {
    setSelectedFile(file);
    setVisibleCode(DEMO_FILES[file]);
  };

  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [visibleCode]);

  const handleReset = () => {
    cancelRef.current = true;
    setPhase("idle");
    setPrompt("");
    setMessages([]);
    setCompletedAgents([]);
    setVisibleFiles([]);
    setVisibleCode("");
    setSelectedFile(null);
    setActiveAgent(null);
    setProgress(0);
  };

  return (
    <section className="py-20 lg:py-32 relative border-t border-white/5" id="demo" data-testid="live-demo-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-electric/10 border border-electric/20 mb-6">
            <Sparkles className="w-4 h-4 text-electric" />
            <span className="text-sm text-electric font-medium">Interactive Demo</span>
          </div>
          <h2 className="font-outfit font-bold text-3xl sm:text-4xl text-white mb-4">
            See it in action — <span className="text-electric">no signup required</span>
          </h2>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto">
            Type a prompt or pick an example below. Watch 7 AI agents build your app in real-time.
          </p>
        </motion.div>

        {/* Prompt Input */}
        {phase === "idle" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl mx-auto mb-8"
          >
            <div className="relative">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && prompt.trim()) runDemo(prompt);
                }}
                placeholder="Describe the app you want to build..."
                className="w-full h-14 px-6 pr-32 rounded-xl bg-void-paper border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:border-electric/50 focus:ring-1 focus:ring-electric/30 font-inter text-base"
                data-testid="demo-prompt-input"
              />
              <Button
                onClick={() => prompt.trim() && runDemo(prompt)}
                disabled={!prompt.trim()}
                className="absolute right-2 top-2 bg-electric hover:bg-electric/90 text-white h-10 px-5"
                data-testid="demo-run-btn"
              >
                <Play className="w-4 h-4 mr-2" />
                Generate
              </Button>
            </div>

            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              {EXAMPLE_PROMPTS.map((ep, i) => (
                <button
                  key={i}
                  onClick={() => { setPrompt(ep); runDemo(ep); }}
                  className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/8 text-zinc-400 hover:text-white hover:border-electric/30 hover:bg-electric/5 transition-all"
                  data-testid={`demo-example-${i}`}
                >
                  {ep.length > 60 ? ep.substring(0, 60) + "..." : ep}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Generation View */}
        {phase !== "idle" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-6xl mx-auto"
          >
            {/* Prompt display + progress */}
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <Sparkles className="w-4 h-4 text-electric shrink-0" />
                <p className="text-sm text-zinc-400 truncate">{prompt || EXAMPLE_PROMPTS[0]}</p>
              </div>
              <button
                onClick={handleReset}
                className="text-xs text-zinc-500 hover:text-white ml-4 shrink-0"
                data-testid="demo-reset-btn"
              >
                Try another
              </button>
            </div>

            {/* Progress bar */}
            <div className="h-1 bg-void-paper rounded-full mb-6 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-electric to-emerald rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>

            {/* Agent Status Bar */}
            <div className="flex gap-2 mb-4 flex-wrap">
              {AGENTS.map((agent) => {
                const isActive = activeAgent === agent.id;
                const isComplete = completedAgents.includes(agent.id);
                const Icon = agent.icon;
                return (
                  <div
                    key={agent.id}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      isActive
                        ? `${agent.bg} ${agent.color} ${agent.border} shadow-md`
                        : isComplete
                        ? "bg-emerald/10 text-emerald border-emerald/20"
                        : "bg-void-paper/50 text-zinc-600 border-white/5"
                    }`}
                    data-testid={`demo-agent-${agent.id}`}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : isActive ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                    {agent.name}
                  </div>
                );
              })}
            </div>

            {/* Main content: File tree + Code + Agent log */}
            <div className="grid grid-cols-12 gap-0 rounded-xl border border-white/10 overflow-hidden bg-void-paper/50" style={{ height: 420 }}>
              {/* File tree */}
              <div className="col-span-3 border-r border-white/5 overflow-y-auto">
                <div className="px-3 py-2 border-b border-white/5">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Files</span>
                </div>
                <div className="p-1">
                  <AnimatePresence>
                    {visibleFiles.map((file) => {
                      const Icon = getFileIcon(file);
                      return (
                        <motion.button
                          key={file}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          onClick={() => handleFileClick(file)}
                          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-left transition-colors ${
                            selectedFile === file
                              ? "bg-electric/10 text-electric"
                              : "text-zinc-400 hover:bg-white/5 hover:text-white"
                          }`}
                          data-testid={`demo-file-${file.replace(/[/.]/g, "-")}`}
                        >
                          <Icon className="w-3.5 h-3.5 shrink-0" />
                          <span className="truncate">{file}</span>
                        </motion.button>
                      );
                    })}
                  </AnimatePresence>
                  {visibleFiles.length === 0 && (
                    <div className="px-2 py-4 text-xs text-zinc-600 text-center">
                      Files will appear here...
                    </div>
                  )}
                </div>
              </div>

              {/* Code viewer */}
              <div className="col-span-5 border-r border-white/5 flex flex-col">
                <div className="flex items-center gap-2 px-4 py-2 bg-void/50 border-b border-white/5">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
                  </div>
                  <span className="text-xs text-zinc-500 ml-1 truncate">
                    {selectedFile || "waiting..."}
                  </span>
                </div>
                <div
                  ref={codeRef}
                  className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed"
                  data-testid="demo-code-viewer"
                >
                  {visibleCode ? (
                    <pre className="text-zinc-300 whitespace-pre-wrap">
                      {visibleCode.split("\n").map((line, i) => (
                        <div key={i} className="flex">
                          <span className="text-zinc-600 select-none w-8 text-right mr-4 shrink-0">{i + 1}</span>
                          <span>{colorize(line)}</span>
                        </div>
                      ))}
                      {phase === "generating" && (
                        <span className="inline-block w-2 h-4 bg-electric animate-pulse ml-0.5" />
                      )}
                    </pre>
                  ) : (
                    <div className="h-full flex items-center justify-center text-zinc-600 text-sm">
                      {phase === "generating" ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin text-electric" />
                          <span>Initializing agents...</span>
                        </div>
                      ) : (
                        "Code will stream here..."
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Agent activity log */}
              <div className="col-span-4 flex flex-col">
                <div className="px-4 py-2 bg-void/50 border-b border-white/5">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Agent Activity</span>
                </div>
                <div className="flex-1 overflow-y-auto p-3 space-y-2" data-testid="demo-agent-log">
                  <AnimatePresence>
                    {messages.map((msg, i) => {
                      const agent = AGENTS.find((a) => a.id === msg.agent);
                      if (!agent) return null;
                      const Icon = agent.icon;
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="flex gap-2 items-start"
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center shrink-0 mt-0.5 ${agent.bg}`}>
                            <Icon className={`w-3 h-3 ${agent.color}`} />
                          </div>
                          <div>
                            <span className={`text-xs font-medium ${agent.color}`}>{agent.name}</span>
                            <p className="text-xs text-zinc-400 mt-0.5">{msg.message}</p>
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                  {messages.length === 0 && (
                    <div className="text-xs text-zinc-600 text-center py-4">
                      Agent logs will stream here...
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Complete CTA */}
            <AnimatePresence>
              {phase === "complete" && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-8 text-center"
                >
                  <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald/10 border border-emerald/20 text-emerald text-sm font-medium mb-4">
                    <CheckCircle2 className="w-4 h-4" />
                    Generation complete — 7 files, 6 agents, under 60 seconds
                  </div>
                  <p className="text-zinc-400 mb-6">
                    This was a simulation. Sign up free to generate <span className="text-white">real, deployable code</span> from your prompts.
                  </p>
                  <Button
                    onClick={() => navigate("/signup")}
                    className="bg-electric hover:bg-electric/90 text-white px-8 py-5 text-base shadow-glow"
                    data-testid="demo-signup-cta"
                  >
                    Start Building for Free
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </section>
  );
}

function colorize(line) {
  const trimmed = line.trim();
  if (trimmed.startsWith("//") || trimmed.startsWith("#")) {
    return <span className="text-zinc-600">{line}</span>;
  }
  if (trimmed.startsWith("import ") || trimmed.startsWith("from ") || trimmed.startsWith("export ")) {
    return <span className="text-purple-400">{line}</span>;
  }
  if (trimmed.startsWith("@") || trimmed.startsWith("async ") || trimmed.startsWith("def ") || trimmed.startsWith("class ")) {
    return <span className="text-blue-400">{line}</span>;
  }
  if (trimmed.includes("return ") || trimmed.startsWith("const ") || trimmed.startsWith("let ") || trimmed.startsWith("var ")) {
    return <span className="text-electric">{line}</span>;
  }
  return line;
}
