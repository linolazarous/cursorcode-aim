# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI's Grok models.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn/UI, Framer Motion, React Router, Monaco Editor
- **Backend:** FastAPI, MongoDB (Motor), JWT Authentication, httpx (xAI API), SSE Streaming
- **AI:** xAI Grok (grok-4-latest, grok-4-1-fast-reasoning, grok-4-1-fast-non-reasoning)
- **3rd Party:** Stripe (billing), SendGrid (email), GitHub OAuth, Emergent Google Auth

## All Completed Features (21 features, tested 100%)
1. User auth (signup, login, JWT, refresh tokens)
2. GitHub OAuth + Emergent Google Auth
3. User/Admin dashboards with project CRUD
4. Project Templates Gallery with filterable categories
5. Template Preview Mode with interactive mockups
6. Pricing page with Stripe checkout
7. Settings page (profile, billing, API keys, security)
8. Demo Video Modal on landing page
9. Email verification flow
10. Two-Factor Authentication (2FA/TOTP)
11. Password Reset Flow with strength meter
12. Enhanced Landing Page (Architecture Graph, Deploy Terminal, Compliance)
13. Credit Meter Component
14. Security Tab in Settings (2FA management)
15. Guided Onboarding Wizard (4-step)
16. Real AI Code Generation with xAI Grok (SSE streaming, 6-agent pipeline)
17. **Share Project** — Public preview links with OG sharing, view counter
18. **AI Conversation History** — Persistent chat per project
19. **Prompt Templates Library** — 8 one-click starters
20. **Project Export** — ZIP download with proper folder structure
21. **Activity Timeline** — Full audit log of all actions
22. **Version Snapshots** — Save/restore project file states with auto-backup

## Key API Endpoints
- Auth: `/api/auth/signup`, `/api/auth/login`, `/api/auth/login-2fa`, `/api/auth/2fa/*`, `/api/auth/reset-password/*`
- Users: `/api/users/me`, `/api/users/me/complete-onboarding`
- Projects: `/api/projects` (CRUD), `/api/projects/:id/files`, `/api/projects/:id/share`, `/api/projects/:id/export`, `/api/projects/:id/messages`, `/api/projects/:id/activity`, `/api/projects/:id/snapshots`
- AI: `/api/ai/generate`, `/api/ai/generate-stream` (SSE), `/api/ai/models`
- Share: `/api/shared/:shareId` (public, no auth)
- Other: `/api/prompt-templates`, `/api/deploy/:id`, `/api/plans`, `/api/templates`, `/api/admin/stats`

## DB Collections
- users, projects, project_messages, project_activities, project_snapshots, deployments, subscriptions, credit_usage

## Pending
- **P1:** Full Stripe webhook (stub)
- **P2:** Real deployment hosting, email verification enforcement
- **Mocked:** Deployment (simulation), Stripe webhook (stub), AI demo mode when no XAI_API_KEY
