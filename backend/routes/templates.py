from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from core.database import db
from core.security import get_current_user, project_to_response
from models.schemas import User, Project

router = APIRouter(tags=["templates"])

PROMPT_TEMPLATES = [
    {"id": "saas", "name": "SaaS Application", "category": "business", "icon": "layout",
     "prompt": "Build a complete SaaS application with user authentication (signup/login/OAuth), subscription billing with Stripe, user dashboard with analytics, admin panel, settings page, and a modern landing page with pricing section.",
     "tags": ["auth", "stripe", "dashboard", "admin"]},
    {"id": "ecommerce", "name": "E-Commerce Store", "category": "business", "icon": "shopping-cart",
     "prompt": "Build a modern e-commerce store with product catalog, shopping cart, checkout with Stripe payments, order management, user accounts, product search/filtering, responsive design, and an admin dashboard for managing products and orders.",
     "tags": ["payments", "catalog", "cart", "orders"]},
    {"id": "dashboard", "name": "Analytics Dashboard", "category": "data", "icon": "bar-chart",
     "prompt": "Build a real-time analytics dashboard with interactive charts (line, bar, pie), data tables with sorting/filtering, date range picker, export to CSV, dark theme, responsive grid layout, and a sidebar navigation.",
     "tags": ["charts", "tables", "real-time", "export"]},
    {"id": "chat", "name": "Chat Application", "category": "social", "icon": "message-circle",
     "prompt": "Build a real-time chat application with private messaging, group channels, message history, online/offline status, typing indicators, file sharing, emoji support, and a clean modern UI.",
     "tags": ["real-time", "messaging", "channels"]},
    {"id": "blog", "name": "Blog Platform", "category": "content", "icon": "file-text",
     "prompt": "Build a full-featured blog platform with markdown editor, image uploads, categories/tags, comments system, RSS feed, SEO optimization, author profiles, and a responsive reading experience.",
     "tags": ["markdown", "cms", "seo", "comments"]},
    {"id": "crm", "name": "CRM System", "category": "business", "icon": "users",
     "prompt": "Build a CRM (Customer Relationship Management) system with contact management, deal pipeline (kanban board), email integration, activity timeline, task management, reporting dashboard, and team collaboration features.",
     "tags": ["contacts", "pipeline", "tasks", "reports"]},
    {"id": "api", "name": "REST API Backend", "category": "developer", "icon": "server",
     "prompt": "Build a production-ready REST API with FastAPI including JWT authentication, CRUD operations, database models with relationships, pagination, filtering, rate limiting, API documentation (OpenAPI/Swagger), and comprehensive error handling.",
     "tags": ["fastapi", "jwt", "crud", "docs"]},
    {"id": "portfolio", "name": "Developer Portfolio", "category": "personal", "icon": "briefcase",
     "prompt": "Build a stunning developer portfolio website with hero section, project showcase with filtering, skills visualization, blog section, contact form, dark/light mode, smooth animations, and responsive design.",
     "tags": ["portfolio", "animations", "responsive"]},
]

PROJECT_TEMPLATES = [
    {
        "id": "saas-dashboard",
        "name": "SaaS Dashboard",
        "description": "Modern analytics dashboard with user auth, Stripe billing, team management, and responsive admin panel.",
        "category": "saas",
        "icon": "layout-dashboard",
        "gradient": "from-blue-600 to-cyan-500",
        "tech_stack": ["React", "FastAPI", "PostgreSQL", "Stripe", "TailwindCSS"],
        "prompt": "Build a modern SaaS dashboard application with: 1) User authentication with JWT and role-based access control, 2) Stripe subscription billing with multiple plans, 3) Analytics dashboard with charts showing revenue, users, and engagement metrics, 4) Team management with invite system, 5) Settings page with profile, billing, and notification preferences, 6) Responsive design with dark mode support. Use React with TailwindCSS for frontend and FastAPI with PostgreSQL for backend.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": True,
    },
    {
        "id": "ecommerce-store",
        "name": "E-Commerce Store",
        "description": "Full-stack online store with product catalog, cart, checkout, payments, and order tracking.",
        "category": "ecommerce",
        "icon": "shopping-cart",
        "gradient": "from-emerald-600 to-green-400",
        "tech_stack": ["React", "Node.js", "MongoDB", "Stripe", "TailwindCSS"],
        "prompt": "Build a full-stack e-commerce store with: 1) Product catalog with categories, search, and filtering, 2) Shopping cart with quantity management, 3) Secure checkout flow with Stripe payment processing, 4) User accounts with order history and tracking, 5) Admin panel for managing products, orders, and inventory, 6) Responsive mobile-first design with image optimization. Use React for frontend, Node.js/Express for backend, MongoDB for database.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": True,
    },
    {
        "id": "blog-platform",
        "name": "Blog Platform",
        "description": "Content publishing platform with markdown editor, categories, comments, and SEO optimization.",
        "category": "content",
        "icon": "file-text",
        "gradient": "from-purple-600 to-pink-500",
        "tech_stack": ["React", "FastAPI", "MongoDB", "Markdown", "TailwindCSS"],
        "prompt": "Build a blog platform with: 1) Rich markdown editor with live preview and image uploads, 2) Categories and tags for organizing posts, 3) Comment system with moderation, 4) SEO optimization with meta tags, sitemaps, and Open Graph, 5) Author profiles with bio and social links, 6) RSS feed generation, 7) Admin dashboard for managing posts and comments. Use React for frontend, FastAPI for backend, MongoDB for storage.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": False,
    },
    {
        "id": "api-backend",
        "name": "REST API Backend",
        "description": "Production-ready API with auth, rate limiting, docs, database models, and test suite.",
        "category": "backend",
        "icon": "server",
        "gradient": "from-orange-600 to-amber-500",
        "tech_stack": ["FastAPI", "PostgreSQL", "Redis", "Docker", "Pytest"],
        "prompt": "Build a production-ready REST API backend with: 1) JWT authentication with refresh tokens, 2) Rate limiting per user/plan, 3) Auto-generated OpenAPI/Swagger documentation, 4) Database models with migrations (Alembic), 5) Comprehensive test suite with pytest, 6) Docker and docker-compose setup, 7) CI/CD pipeline configuration, 8) Logging, error handling, and monitoring endpoints. Use FastAPI with PostgreSQL and Redis.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": False,
    },
    {
        "id": "portfolio-site",
        "name": "Portfolio Website",
        "description": "Stunning developer portfolio with project showcase, blog, contact form, and animations.",
        "category": "website",
        "icon": "briefcase",
        "gradient": "from-indigo-600 to-violet-500",
        "tech_stack": ["React", "Framer Motion", "TailwindCSS", "MDX"],
        "prompt": "Build a stunning developer portfolio website with: 1) Animated hero section with typing effect, 2) Project showcase gallery with filters and detail modals, 3) Skills section with visual progress indicators, 4) Blog section with MDX support, 5) Contact form with email integration, 6) Smooth scroll animations and page transitions using Framer Motion, 7) Dark/light theme toggle, 8) Fully responsive design. Use React with TailwindCSS and Framer Motion.",
        "complexity": "beginner",
        "estimated_credits": 2,
        "popular": True,
    },
    {
        "id": "realtime-chat",
        "name": "Real-Time Chat App",
        "description": "Live messaging with WebSocket, user presence, message history, and file sharing.",
        "category": "realtime",
        "icon": "message-circle",
        "gradient": "from-teal-600 to-emerald-400",
        "tech_stack": ["React", "FastAPI", "WebSocket", "MongoDB", "Redis"],
        "prompt": "Build a real-time chat application with: 1) WebSocket-based instant messaging, 2) User presence indicators (online/offline/typing), 3) Message history with infinite scroll, 4) File and image sharing with previews, 5) Group chat and direct messages, 6) Read receipts and message reactions, 7) Search through message history, 8) Push notification support. Use React for frontend, FastAPI with WebSocket for backend, MongoDB for storage, Redis for pub/sub.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": False,
    },
    {
        "id": "ai-assistant",
        "name": "AI Assistant",
        "description": "Conversational AI with NLP, context memory, chat history, and function calling.",
        "category": "ai",
        "icon": "bot",
        "gradient": "from-rose-600 to-pink-500",
        "tech_stack": ["React", "FastAPI", "OpenAI", "MongoDB", "TailwindCSS"],
        "prompt": "Build an AI-powered conversational assistant with: 1) Chat interface with streaming responses, 2) Context memory across conversations, 3) Conversation history with search, 4) Function calling for real-world actions (weather, search, calculations), 5) System prompt customization, 6) Multiple conversation threads, 7) Export chat history, 8) Token usage tracking. Use React for frontend, FastAPI for backend, OpenAI API for LLM, MongoDB for storage.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": True,
    },
    {
        "id": "mobile-app",
        "name": "Mobile App",
        "description": "Cross-platform mobile app with auth, push notifications, offline support, and sleek UI.",
        "category": "mobile",
        "icon": "smartphone",
        "gradient": "from-sky-600 to-blue-400",
        "tech_stack": ["React Native", "Expo", "FastAPI", "Firebase", "TypeScript"],
        "prompt": "Build a cross-platform mobile application with: 1) User authentication with biometric support, 2) Push notifications via Firebase, 3) Offline-first architecture with local storage sync, 4) Bottom tab navigation with smooth transitions, 5) Camera and photo library integration, 6) Dark/light theme with system preference detection, 7) App store ready configuration for iOS and Android. Use React Native with Expo, FastAPI for backend, Firebase for notifications.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": False,
    },
]


@router.get("/prompt-templates")
async def get_prompt_templates():
    return PROMPT_TEMPLATES


@router.get("/templates")
async def get_templates(category: Optional[str] = None):
    templates = PROJECT_TEMPLATES
    if category and category != "all":
        templates = [t for t in templates if t["category"] == category]
    categories = list(set(t["category"] for t in PROJECT_TEMPLATES))
    return {"templates": templates, "categories": categories}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    template = next((t for t in PROJECT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates/{template_id}/create")
async def create_project_from_template(template_id: str, user: User = Depends(get_current_user)):
    template = next((t for t in PROJECT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    project = Project(
        user_id=user.id, name=template["name"],
        description=template["description"],
        prompt=template["prompt"], status="draft",
        tech_stack=template["tech_stack"]
    )
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.projects.insert_one(doc)
    return project_to_response(project)
