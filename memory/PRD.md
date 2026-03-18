# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI's Grok models.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn/UI, Framer Motion, React Router, Monaco Editor
- **Backend:** FastAPI, MongoDB (Motor), JWT Auth, httpx (xAI API), SSE Streaming, Stripe
- **AI:** xAI Grok (3 model tiers) with 6-agent multi-agent pipeline
- **3rd Party:** Stripe, SendGrid, GitHub OAuth, Google OAuth2 (standard)

## Design System
- **Theme:** Cybersecurity / deep-tech aesthetic
- **Background:** Deep navy #0a0e1a (void), #0d1425 (paper), #141f30 (subtle)
- **Accent:** Bright cyan-blue #00b4ff (electric), with glow effects
- **Typography:** Outfit (headings), Inter (body), JetBrains Mono (code)
- **Effects:** Glass-morphism, noise textures, cyber grid patterns, scan-line animations, pulse glows

## Completed Features (25+ features, 100% tested across 13 iterations)
1. User auth (signup, login, JWT, refresh tokens)
2. GitHub OAuth + Google OAuth2 (standard flow with colored SVG icons)
3. User/Admin dashboards with project CRUD
4. Project Templates Gallery (filterable)
5. Template Preview Mode (interactive mockups)
6. Pricing page with Stripe checkout
7. Settings page (profile, billing, API keys, security)
8. Demo Video Modal
9. Email verification flow
10. Two-Factor Authentication (2FA/TOTP)
11. Password Reset Flow (email-based)
12. Enhanced Landing Page (Architecture Graph, Deploy Terminal, Compliance)
13. Credit Meter Component
14. Security Tab in Settings
15. Guided Onboarding Wizard (4-step)
16. Real AI Code Generation with xAI Grok (SSE streaming, 6 agents)
17. Share Project (public preview links, view counter)
18. AI Conversation History (persistent per-project)
19. Prompt Templates Library (8 starters)
20. Project Export (ZIP download)
21. Activity Timeline (audit log)
22. Version Snapshots (save/restore with auto-backup)
23. Full Stripe Webhook (checkout, invoice, subscription events + idempotency)
24. Privacy, Terms, Contact pages (real content, real routing)
25. Production-grade Demo Mode (realistic multi-file AI output for all 6 agents)

## DB Collections
users, projects, project_messages, project_activities, project_snapshots, deployments, subscriptions, credit_usage, webhook_events, payments

## Production Environment
- **Backend:** Render (env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, STRIPE_SECRET_KEY, etc.)
- **Frontend:** Vercel (auto-deploys from GitHub)
- **Database:** MongoDB Atlas (production)

## Pending
- P1: Backend refactoring (server.py is 2500+ lines monolith → routes/, models/, services/)
- P2: Real deployment hosting, email verification enforcement, community templates
- Mocked: Deployment simulation, Contact form email, AI demo mode (until XAI_API_KEY set)
