# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI Grok models with multi-agent code generation.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI, Framer Motion
- **Backend:** FastAPI (modular), MongoDB (Motor), JWT Auth
- **Payments:** JengaHQ (Finserve Africa)
- **External APIs:** xAI Grok, JengaHQ, SendGrid, GitHub OAuth, Google OAuth

## Architecture
```
/app/backend/
├── server.py              # App init + router includes
├── core/
│   ├── config.py          # All env vars (Google OAuth, JengaHQ, xAI, SendGrid)
│   ├── database.py        # MongoDB connection
│   └── security.py        # JWT, auth, require_verified_email, get_admin_user
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (signup, login, 2FA, Google/GitHub OAuth, password reset, resend-verification)
│   ├── users.py           # User profile, onboarding, GitHub repos
│   ├── projects.py        # Project CRUD (create requires verified email)
│   ├── ai.py              # AI generation + SSE + rate limit + credit + verified email
│   ├── autonomous.py      # 18 endpoints: guardrails, sandbox, validation, snapshots, context, deps, feedback
│   ├── deployments.py     # Deployment routes (requires verified email)
│   ├── subscriptions.py   # JengaHQ checkout, IPN webhook, cancel, recurring billing
│   ├── admin.py           # Admin stats/users/usage
│   ├── templates.py       # Prompt + project templates
│   └── shared.py          # Public shared project view
├── services/
│   ├── ai.py, email.py, jenga.py, stripe_service.py (billing plans)
│   ├── guardrails.py, sandbox.py, validation_loop.py
│   ├── snapshot_manager.py, context_pruning.py, dependency_graph.py
│   └── feedback_collector.py
└── ai_*.py                # Supporting AI modules
```

## Email Verification Enforcement
**Protected (403 for unverified):** Create projects, AI generate, AI execute, sandbox, deploy
**Open (200 for all authenticated):** View projects, credits, plans, feedback stats, auth endpoints

## Google OAuth
- Client ID and Secret configured in `.env`
- Redirect URI: `https://grok-devops.preview.emergentagent.com/auth/google/callback`
- Flow: Frontend → `/api/auth/google` → Google → Frontend callback → `/api/auth/google/callback`

## What's Been Implemented
- [x] All auth flows (email, GitHub, Google OAuth, 2FA, password reset)
- [x] Multi-agent AI code generation (SSE streaming)
- [x] Project CRUD + share + export + snapshots + messages
- [x] Backend modular refactoring (server.py 2500+ -> 70 lines)
- [x] JengaHQ payment integration (Stripe fully replaced)
- [x] Credit-based rate limiting on all AI routes
- [x] 7 autonomous AI modules (guardrails, sandbox, validation_loop, snapshot_manager, context_pruning, dependency_graph, feedback_collector)
- [x] Cybersecurity-themed premium UI
- [x] **Email verification enforcement** on protected routes
- [x] **Google OAuth with real credentials**

## Prioritized Backlog
### P1
- Implement real file hosting for deployments (GCS integration)
### P2/Future
- Custom prompt template creation/saving
- Team collaboration features
- GCP deployment configuration (Cloud Run, Cloudflare DNS)

## Testing History
- iteration_17: Backend refactoring — 42/42 passed
- iteration_18: JengaHQ + credit system — 31/31 passed
- iteration_19: Autonomous AI modules — 53/53 passed
- iteration_20: Email verification + Google OAuth — 27/27 passed

## Test Credentials
- Verified: `test_refactor@example.com` / `Test123456!`
- Google OAuth: Configured with real keys
