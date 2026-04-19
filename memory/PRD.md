# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI Grok models with multi-agent code generation.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI, Framer Motion
- **Backend:** FastAPI (modular), MongoDB (Motor), JWT Auth
- **Payments:** JengaHQ (Finserve Africa)
- **Storage:** Emergent Object Storage (real file hosting)
- **External APIs:** xAI Grok, JengaHQ, SendGrid, GitHub OAuth, Google OAuth

## Architecture
```
/app/backend/
├── server.py              # App init + storage init at startup
├── core/
│   ├── config.py          # All env vars (Storage, JengaHQ, Google OAuth, xAI)
│   ├── database.py        # MongoDB connection
│   └── security.py        # JWT, auth, require_verified_email
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (signup, login, 2FA, Google/GitHub OAuth, password reset)
│   ├── users.py           # User profile, onboarding, GitHub repos
│   ├── projects.py        # Project CRUD (create requires verified email)
│   ├── ai.py              # AI generation + SSE + rate limit + credit + verified email
│   ├── autonomous.py      # 18 endpoints: guardrails, sandbox, validation, snapshots, context, deps, feedback
│   ├── deployments.py     # Real file hosting: upload to storage + preview serving
│   ├── subscriptions.py   # JengaHQ checkout, IPN webhook, cancel, recurring billing
│   ├── admin.py           # Admin stats/users/usage
│   ├── templates.py       # Prompt + project templates
│   └── shared.py          # Public shared project view
├── services/
│   ├── ai.py, email.py, jenga.py, stripe_service.py (billing plans)
│   ├── storage.py         # Emergent Object Storage wrapper
│   ├── guardrails.py, sandbox.py, validation_loop.py
│   ├── snapshot_manager.py, context_pruning.py, dependency_graph.py
│   └── feedback_collector.py
└── ai_*.py                # Supporting AI modules
```

## Deployment System (REAL)
- Files uploaded to Emergent Object Storage at `cursorcode/deployments/{deployment_id}/`
- Preview served via `GET /api/preview/{deployment_id}/{filepath}` (public, no auth)
- Correct MIME types: HTML, CSS, JS, JSON, images, etc.
- Auto-generates `index.html` with file listing if not present
- Falls back to simulation when `EMERGENT_LLM_KEY` not set

## What's Been Implemented
- [x] All auth flows (email, GitHub, Google OAuth, 2FA, password reset)
- [x] Multi-agent AI code generation (SSE streaming)
- [x] Project CRUD + share + export + snapshots + messages
- [x] Backend modular refactoring
- [x] JengaHQ payment integration (Stripe fully replaced)
- [x] Credit-based rate limiting on all AI routes
- [x] 7 autonomous AI modules
- [x] Email verification enforcement
- [x] Google OAuth with real credentials
- [x] **Real file hosting for deployments** (Emergent Object Storage)
- [x] Cybersecurity-themed premium UI

## Prioritized Backlog
### Future
- Custom prompt template creation/saving
- Team collaboration features
- GCP deployment configuration (Cloud Run, Cloudflare DNS)

## Testing History
- iteration_17: Backend refactoring — 42/42 passed
- iteration_18: JengaHQ + credit system — 31/31 passed
- iteration_19: Autonomous AI modules — 53/53 passed
- iteration_20: Email verification + Google OAuth — 27/27 passed
- iteration_21: Real file hosting — 18/18 passed

## Test Credentials
- Verified: `test_refactor@example.com` / `Test123456!`
