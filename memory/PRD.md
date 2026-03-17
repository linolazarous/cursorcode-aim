# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications, powered by xAI's Grok models.

## Tech Stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, Framer Motion, Lucide Icons, Monaco Editor, Recharts
- **Backend:** FastAPI, Motor (async MongoDB), JWT Auth, bcrypt, python-jose
- **Database:** MongoDB
- **3rd Party:** xAI Grok (AI), Stripe (payments), SendGrid (email), GitHub OAuth, Emergent Google Auth

## Implemented Features (v2.2)

### Core Platform
- [x] Landing page with hero, features, pricing, testimonials
- [x] Watch Demo video modal (real 11MB MP4)
- [x] Real logo.png
- [x] JWT auth (signup, login, refresh)
- [x] **Google OAuth** via Emergent-managed Auth (auth.emergentagent.com)
- [x] **GitHub OAuth** with proper redirect flow (needs user's keys)
- [x] User dashboard with sidebar navigation
- [x] Project CRUD with AI workspace (Monaco editor)
- [x] Multi-agent AI build pipeline (6 agents)
- [x] 5 subscription plans with Stripe checkout
- [x] Credit system with rate limiting
- [x] Simulated deployments, Admin dashboard, Settings page

### Template System
- [x] 8 project templates (SaaS, E-Commerce, Blog, API, Portfolio, Chat, AI Assistant, Mobile)
- [x] Template Gallery with search, category filters, complexity badges
- [x] **Template Preview Mode** - interactive mockups in browser chrome frame
- [x] Desktop/mobile viewport toggle
- [x] One-click "Use Template" creates project with pre-filled prompt

### Auth System
- [x] Email/password signup & login with JWT
- [x] Google OAuth via Emergent Auth (session exchange → JWT)
- [x] GitHub OAuth (redirect → callback → JWT) - needs user's CLIENT_ID/SECRET
- [x] Token refresh
- [x] Email verification flow

### Mocked/Demo Mode
- AI generation: demo responses (needs XAI_API_KEY)
- Stripe: demo URLs (needs STRIPE_SECRET_KEY)
- SendGrid: skipped (needs SENDGRID_API_KEY)
- GitHub OAuth: error msg (needs CLIENT_ID/SECRET)

## API Endpoints
- Auth: POST signup, login, refresh, google/session, github/callback | GET me, verify-email, github
- User: PUT /api/users/me
- Projects: CRUD /api/projects
- Templates: GET /api/templates, /api/templates/:id, POST /api/templates/:id/create
- AI: POST generate, build | GET models, stream
- Deploy: POST /api/deploy/:id | GET/DELETE deployments
- Subscriptions: POST create-checkout, webhook | GET current
- Admin: GET stats, users, usage

## Test Credentials
- email: test@cursorcode.ai, password: Test123456!

## Testing Status (March 17, 2026)
- Iteration 3: 16/16 core features (100%)
- Iteration 4: 17/17 templates gallery (100%)
- Iteration 5: 25/25 template preview (100%)
- Iteration 6: 11/11 OAuth auth (100%)

## Pending / Backlog
- Configure xAI API key for real AI generation
- Configure Stripe keys for real payments
- Configure SendGrid for real emails
- Configure GitHub OAuth keys
- Real file hosting for deployments
- Community templates
