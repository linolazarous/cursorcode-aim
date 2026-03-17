# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications, powered by xAI's Grok models.

## Tech Stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Framer Motion, Lucide Icons, Monaco Editor, Recharts
- **Backend:** FastAPI, Motor (async MongoDB), JWT Auth, bcrypt, python-jose
- **Database:** MongoDB
- **3rd Party:** xAI Grok (AI generation), Stripe (payments), SendGrid (email), GitHub OAuth

## Architecture
```
/app/backend/
  server.py              - Main FastAPI app (all routes, auth, CRUD, templates, AI)
  ai_agents.py           - Multi-agent AI system (6 agents)
  orchestrator.py        - AI project orchestration pipeline
  ai_memory.py           - AI context memory (MongoDB-backed)
  ai_streaming.py        - SSE streaming for AI responses
  ai_metrics.py          - Usage tracking
  ai_rate_limiter.py     - Plan-based rate limiting
  ai_security.py, ai_file_manager.py, ai_repo_builder.py, ai_planner.py
  ai_task_graph.py, code_executor.py, ai_code_reviewer.py, ai_debugger.py
  ai_autofix_engine.py, ai_refactor_engine.py, ai_test_generator.py
  ai_project_architect.py, utils.py
/app/frontend/src/
  pages/                 - LandingPage, LoginPage, SignupPage, DashboardPage, ProjectPage,
                           SettingsPage, PricingPage, AdminPage, TemplatesPage, TemplatePreviewPage
  components/            - Logo, Sidebar, DemoVideoModal, ui/ (shadcn)
  components/mockups/    - SaaSMockup, EcommerceMockup, BlogMockup, ApiMockup,
                           PortfolioMockup, ChatMockup, AiMockup, MobileMockup
  context/               - AuthContext
  lib/                   - api.js (axios instance)
```

## Implemented Features (v2.1)

### Core Platform
- [x] Landing page with hero, features, pricing, testimonials
- [x] Watch Demo video modal (real 11MB MP4 uploaded)
- [x] Real logo.png (1.7MB uploaded)
- [x] JWT auth (signup, login, refresh), GitHub OAuth
- [x] User dashboard with sidebar navigation
- [x] Project CRUD with AI code generation workspace (Monaco editor)
- [x] Multi-agent AI build pipeline (6 agents)
- [x] 5 subscription plans with Stripe checkout
- [x] Credit system with rate limiting
- [x] Simulated deployments, Admin dashboard, Settings page

### Template System (v2.1)
- [x] 8 project templates: SaaS Dashboard, E-Commerce, Blog, REST API, Portfolio, Real-Time Chat, AI Assistant, Mobile App
- [x] Template Gallery page with search, category filters, complexity badges
- [x] **Template Preview Mode** - interactive mockups in browser chrome frame
- [x] Desktop/mobile viewport toggle
- [x] Template details sidebar with tech stack, features, credits info
- [x] One-click "Use Template" creates project with pre-filled AI prompt
- [x] 8 unique mockup components with realistic UI

### Mocked/Demo Mode
- AI generation returns demo responses (needs XAI_API_KEY)
- Stripe checkout returns demo URLs (needs STRIPE_SECRET_KEY)
- Email sending skipped (needs SENDGRID_API_KEY)
- GitHub OAuth (needs GITHUB_OAUTH_CLIENT_ID/SECRET)

## API Endpoints
- Auth: POST signup, login, refresh | GET me, verify-email, github
- User: PUT /api/users/me
- Projects: CRUD /api/projects
- Templates: GET /api/templates, GET /api/templates/:id, POST /api/templates/:id/create
- AI: POST generate, build | GET models, stream
- Deploy: POST /api/deploy/:id | GET/DELETE deployments
- Subscriptions: POST create-checkout, webhook | GET current
- Admin: GET stats, users, usage
- Health: GET /api/health

## Test Credentials
- email: test@cursorcode.ai, password: Test123456!

## Testing Status (March 17, 2026)
- Iteration 3: 16/16 core features (100%)
- Iteration 4: 17/17 templates gallery (100%)
- Iteration 5: 25/25 template preview mode (100%)

## Pending / Backlog
- Configure real API keys (xAI, Stripe, SendGrid, GitHub)
- Real file hosting for deployments
- Email verification blocking flow
- Community/user-submitted templates
