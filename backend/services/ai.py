import re
import json
import asyncio
import logging
from typing import Dict
import httpx

from core.config import (
    XAI_API_KEY, XAI_BASE_URL, DEFAULT_XAI_MODEL,
    FAST_REASONING_MODEL, FAST_NON_REASONING_MODEL
)

logger = logging.getLogger(__name__)


def select_model(task_type: str) -> str:
    routing = {
        "architecture": DEFAULT_XAI_MODEL,
        "code_generation": FAST_REASONING_MODEL,
        "code_review": FAST_REASONING_MODEL,
        "documentation": FAST_NON_REASONING_MODEL,
        "simple_query": FAST_NON_REASONING_MODEL,
        "complex_reasoning": DEFAULT_XAI_MODEL,
    }
    return routing.get(task_type, FAST_REASONING_MODEL)


def calculate_credits(model: str, task_type: str) -> int:
    base_credits = {DEFAULT_XAI_MODEL: 3, FAST_REASONING_MODEL: 2, FAST_NON_REASONING_MODEL: 1}
    return base_credits.get(model, 2)


async def call_xai_api(prompt: str, model: str, system_message: str = None) -> str:
    if not XAI_API_KEY:
        return f"""```filename:App.jsx
import React, {{ useState }} from 'react';

export default function App() {{
  const [items, setItems] = useState([]);
  const [input, setInput] = useState('');

  const addItem = () => {{
    if (input.trim()) {{
      setItems([...items, {{ id: Date.now(), text: input, done: false }}]);
      setInput('');
    }}
  }};

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Generated App</h1>
        <p className="text-zinc-400 mb-8">Prompt: {prompt[:80]}...</p>
        <div className="flex gap-2 mb-6">
          <input value={{input}} onChange={{e => setInput(e.target.value)}}
            className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg border border-zinc-700"
            placeholder="Add an item..." />
          <button onClick={{addItem}} className="px-6 py-2 bg-blue-600 rounded-lg hover:bg-blue-700">Add</button>
        </div>
        <div className="space-y-2">
          {{items.map(item => (
            <div key={{item.id}} className="p-3 bg-zinc-900 rounded-lg border border-zinc-800 flex items-center justify-between">
              <span>{{item.text}}</span>
              <button onClick={{() => setItems(items.filter(i => i.id !== item.id))}} className="text-red-400 hover:text-red-300 text-sm">Remove</button>
            </div>
          ))}}
        </div>
      </div>
    </div>
  );
}}
```

```filename:api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

app = FastAPI()
items = []

class ItemCreate(BaseModel):
    text: str

class Item(BaseModel):
    id: str
    text: str
    done: bool = False

@app.get("/api/items")
def list_items():
    return items

@app.post("/api/items")
def create_item(data: ItemCreate):
    item = {{"id": str(uuid.uuid4()), "text": data.text, "done": False}}
    items.append(item)
    return item
```
"""

    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "max_tokens": 4096, "temperature": 0.7}

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(f"{XAI_BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def parse_files_from_response(text: str) -> Dict[str, str]:
    files = {}
    pattern = r'```(?:filename:)?([\w\-\.\/]+)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    for fname, content in matches:
        fname = fname.strip()
        if fname and not fname.startswith('//'):
            files[fname] = content.strip()
    if not files:
        code_pattern = r'```(\w+)\n(.*?)```'
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        ext_map = {"jsx": ".jsx", "javascript": ".js", "python": ".py", "typescript": ".tsx",
                    "css": ".css", "html": ".html", "json": ".json", "yaml": ".yml", "dockerfile": "Dockerfile"}
        for i, (lang, content) in enumerate(code_matches):
            ext = ext_map.get(lang.lower(), f".{lang.lower()}")
            fname = f"generated_{i}{ext}" if ext != "Dockerfile" else ext
            files[fname] = content.strip()
    return files


# ==================== AGENT CONFIGS ====================

AGENT_CONFIGS = [
    {"name": "architect", "label": "Architect Agent", "system": "You are a senior software architect at a top tech company. Given a user's application idea, design a complete system architecture. Output a clear markdown document with: 1) Project overview, 2) Tech stack recommendations, 3) Database schema (tables/collections with fields), 4) API endpoints list, 5) Component hierarchy for the frontend, 6) Security considerations. Be specific and practical - this will be used as a blueprint by other engineers."},
    {"name": "frontend", "label": "Frontend Agent", "system": "You are an expert frontend engineer. Given an architecture document and user requirements, generate production-ready React code. Output complete, working files with proper imports. Use React functional components, TailwindCSS for styling, and follow best practices. Output each file in this format:\n\n```filename:ComponentName.jsx\n// file content here\n```\n\nGenerate all necessary components, pages, and utility files."},
    {"name": "backend", "label": "Backend Agent", "system": "You are an expert backend engineer. Given an architecture document and user requirements, generate production-ready Python FastAPI code. Output complete, working files. Include: models, routes, authentication, database setup, and error handling. Output each file in this format:\n\n```filename:main.py\n# file content here\n```\n\nGenerate all necessary backend files."},
    {"name": "security", "label": "Security Agent", "system": "You are a senior cybersecurity engineer. Review the provided code for security vulnerabilities. Output a markdown security report with: 1) Critical issues found, 2) Warnings, 3) Recommendations, 4) Specific code fixes needed. Be thorough but practical."},
    {"name": "qa", "label": "QA Agent", "system": "You are a QA automation engineer. Given the application code, generate comprehensive test files. Include unit tests, integration tests, and API tests. Use pytest for backend and Jest/React Testing Library for frontend. Output each test file in this format:\n\n```filename:test_main.py\n# test content here\n```"},
    {"name": "devops", "label": "DevOps Agent", "system": "You are a DevOps engineer. Generate deployment configuration files for the application. Include: Dockerfile, docker-compose.yml, CI/CD pipeline (GitHub Actions), environment configuration, and deployment instructions. Output each file in this format:\n\n```filename:Dockerfile\n# content here\n```"},
]


# ==================== STREAMING ====================

async def stream_xai_api(prompt: str, model: str, system_message: str):
    if not XAI_API_KEY:
        demo_outputs = {
            "software architect": generate_demo_architecture(prompt),
            "frontend engineer": generate_demo_frontend(prompt),
            "backend engineer": generate_demo_backend(prompt),
            "cybersecurity engineer": generate_demo_security(prompt),
            "QA automation engineer": generate_demo_tests(prompt),
            "DevOps engineer": generate_demo_devops(prompt),
        }
        agent_type = next((k for k in demo_outputs if k in system_message.lower()), None)
        output = demo_outputs.get(agent_type, f"// Generated for: {prompt[:200]}")
        chunk_size = 40
        for i in range(0, len(output), chunk_size):
            yield output[i:i+chunk_size]
            await asyncio.sleep(0.02)
        return

    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    payload = {"model": model, "messages": messages, "max_tokens": 8192, "temperature": 0.5, "stream": True}

    async with httpx.AsyncClient(timeout=180.0) as http_client:
        async with http_client.stream("POST", f"{XAI_BASE_URL}/chat/completions", headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


# ==================== DEMO GENERATORS ====================

def _extract_app_name(prompt: str) -> str:
    words = prompt.lower().split()
    keywords = ["app", "application", "platform", "system", "tool", "dashboard", "store", "site"]
    for i, w in enumerate(words):
        if w in keywords and i > 0:
            return words[i-1].capitalize() + " " + w.capitalize()
    return "MyApp"


def generate_demo_architecture(prompt: str) -> str:
    app = _extract_app_name(prompt)
    return f"""# {app} - System Architecture

## Overview
{app} is a modern full-stack application built with React and FastAPI.

## Tech Stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, React Router
- **Backend:** FastAPI, MongoDB, JWT Authentication
- **Deployment:** Docker, Nginx, GitHub Actions CI/CD

## Database Schema

### Users Collection
```json
{{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "password_hash": "string",
  "role": "user | admin",
  "created_at": "datetime"
}}
```

### Items Collection
```json
{{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string",
  "status": "active | archived",
  "created_at": "datetime"
}}
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/signup | User registration |
| POST | /api/auth/login | User login |
| GET | /api/items | List user items |
| POST | /api/items | Create item |
| PUT | /api/items/:id | Update item |
| DELETE | /api/items/:id | Delete item |
| GET | /api/dashboard/stats | Dashboard analytics |

## Component Hierarchy
```
App
├── Layout (Navbar, Sidebar)
├── LandingPage
├── AuthPages (Login, Signup)
├── Dashboard
│   ├── StatsCards
│   ├── RecentItems
│   └── ActivityChart
├── ItemsPage
│   ├── ItemList
│   ├── ItemCard
│   └── CreateItemModal
└── SettingsPage
```

## Security
- JWT with refresh tokens
- bcrypt password hashing
- Rate limiting (100 req/min)
- Input validation (Pydantic)
- CORS whitelist
"""


def generate_demo_frontend(prompt: str) -> str:
    app = _extract_app_name(prompt)
    return f'''```filename:App.jsx
import {{ BrowserRouter, Routes, Route }} from "react-router-dom";
import Layout from "./components/Layout";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";

export default function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={{<LandingPage />}} />
        <Route path="/login" element={{<LoginPage />}} />
        <Route path="/dashboard" element={{<Layout><Dashboard /></Layout>}} />
      </Routes>
    </BrowserRouter>
  );
}}
```

```filename:pages/Dashboard.jsx
import {{ useState, useEffect }} from "react";
import {{ BarChart3, Users, TrendingUp, Plus }} from "lucide-react";
import api from "../lib/api";

export default function Dashboard() {{
  const [stats, setStats] = useState({{ items: 0, users: 0, growth: 0 }});
  const [items, setItems] = useState([]);

  useEffect(() => {{
    api.get("/dashboard/stats").then(r => setStats(r.data));
    api.get("/items").then(r => setItems(r.data));
  }}, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">{app} Dashboard</h1>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> New Item
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={{BarChart3}} label="Total Items" value={{stats.items}} />
        <StatCard icon={{Users}} label="Active Users" value={{stats.users}} />
        <StatCard icon={{TrendingUp}} label="Growth" value={{`${{stats.growth}}%`}} />
      </div>

      <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="font-semibold text-white">Recent Items</h2>
        </div>
        <div className="divide-y divide-zinc-800">
          {{items.map(item => (
            <div key={{item.id}} className="p-4 flex items-center justify-between hover:bg-zinc-800/50">
              <div>
                <p className="font-medium text-white">{{item.title}}</p>
                <p className="text-sm text-zinc-400">{{item.description}}</p>
              </div>
              <span className="px-2 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400">{{item.status}}</span>
            </div>
          ))}}
        </div>
      </div>
    </div>
  );
}}

function StatCard({{ icon: Icon, label, value }}) {{
  return (
    <div className="p-5 rounded-xl bg-zinc-900 border border-zinc-800">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <p className="text-sm text-zinc-400">{{label}}</p>
          <p className="text-xl font-bold text-white">{{value}}</p>
        </div>
      </div>
    </div>
  );
}}
```

```filename:components/Layout.jsx
import {{ Link, useLocation }} from "react-router-dom";
import {{ LayoutDashboard, Settings, LogOut }} from "lucide-react";

export default function Layout({{ children }}) {{
  const location = useLocation();
  const navItems = [
    {{ path: "/dashboard", icon: LayoutDashboard, label: "Dashboard" }},
    {{ path: "/settings", icon: Settings, label: "Settings" }},
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex">
      <aside className="w-64 bg-zinc-900 border-r border-zinc-800 p-4 flex flex-col">
        <h1 className="text-xl font-bold text-white mb-8">{app}</h1>
        <nav className="space-y-1 flex-1">
          {{navItems.map(item => (
            <Link key={{item.path}} to={{item.path}}
              className={{`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${{
                location.pathname === item.path ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              }}`}}>
              <item.icon className="w-4 h-4" /> {{item.label}}
            </Link>
          ))}}
        </nav>
        <button className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:text-white">
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </aside>
      <main className="flex-1 overflow-auto">{{children}}</main>
    </div>
  );
}}
```
'''


def generate_demo_backend(prompt: str) -> str:
    return '''```filename:main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

app = FastAPI(title="API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ItemCreate(BaseModel):
    title: str
    description: str = ""

class Item(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    status: str = "active"
    created_at: str

items_db = []

@app.get("/api/items")
async def list_items():
    return items_db

@app.post("/api/items")
async def create_item(data: ItemCreate):
    item = Item(
        id=str(uuid.uuid4()),
        user_id="demo-user",
        title=data.title,
        description=data.description,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    items_db.append(item.model_dump())
    return item.model_dump()

@app.put("/api/items/{item_id}")
async def update_item(item_id: str, data: ItemCreate):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db[i]["title"] = data.title
            items_db[i]["description"] = data.description
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {"message": "Deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    return {"items": len(items_db), "users": 1, "growth": 12.5}
```

```filename:models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```
'''


def generate_demo_security(prompt: str) -> str:
    return """# Security Audit Report

## Critical Issues
No critical vulnerabilities found.

## Warnings
1. **CORS Configuration** - Currently allows all origins (`*`). Restrict to specific domains in production.
2. **Rate Limiting** - No rate limiting configured. Add `slowapi` or similar middleware.
3. **Input Validation** - Ensure all user inputs are sanitized and validated with Pydantic.

## Recommendations
1. Add Helmet-style security headers (HSTS, CSP, X-Frame-Options)
2. Implement API key rotation mechanism
3. Add request logging for audit trail
4. Enable MongoDB authentication in production
5. Use environment variables for all secrets (never hardcode)
6. Add CSRF protection for cookie-based auth
7. Implement account lockout after failed login attempts

## Code Fixes Applied
- Added input length validation to all string fields
- Ensured password hashing uses bcrypt with proper salt rounds
- Added JWT token expiration checking
- Removed sensitive data from API responses

## Compliance Notes
- GDPR: Implement data export and deletion endpoints
- SOC 2: Audit logging recommended for all data mutations
- OWASP Top 10: No injection, XSS, or CSRF vulnerabilities detected
"""


def generate_demo_tests(prompt: str) -> str:
    return '''```filename:test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestItems:
    def test_list_items_empty(self):
        response = client.get("/api/items")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_item(self):
        response = client.post("/api/items", json={"title": "Test Item", "description": "A test"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Item"
        assert "id" in data

    def test_update_item(self):
        create = client.post("/api/items", json={"title": "Original"})
        item_id = create.json()["id"]
        response = client.put(f"/api/items/{item_id}", json={"title": "Updated"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_delete_item(self):
        create = client.post("/api/items", json={"title": "To Delete"})
        item_id = create.json()["id"]
        response = client.delete(f"/api/items/{item_id}")
        assert response.status_code == 200

    def test_delete_not_found(self):
        response = client.delete("/api/items/nonexistent")
        assert response.status_code == 404

    def test_dashboard_stats(self):
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "users" in data
```
'''


def generate_demo_devops(prompt: str) -> str:
    return '''```filename:Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```filename:docker-compose.yml
version: "3.8"
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - DB_NAME=myapp
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - mongo
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
volumes:
  mongo_data:
```

```filename:.github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: myapp/api:latest
```
'''
