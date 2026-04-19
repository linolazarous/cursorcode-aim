# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI Grok models with multi-agent code generation.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI, Framer Motion
- **Backend:** FastAPI (modular), MongoDB (Motor), JWT Auth
- **Payments:** JengaHQ (Finserve Africa) — replaced Stripe
- **External APIs:** xAI Grok, JengaHQ, SendGrid, GitHub OAuth, Google OAuth

## Architecture
```
/app/backend/
├── server.py              # App init + router includes (68 lines)
├── core/
│   ├── config.py          # All env vars (JengaHQ, xAI, OAuth, SendGrid)
│   ├── database.py        # MongoDB connection
│   └── security.py        # JWT, auth helpers, get_current_user
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (signup, login, 2FA, OAuth, password reset)
│   ├── users.py           # User profile, onboarding, GitHub repos
│   ├── projects.py        # Project CRUD, share, export, snapshots, messages
│   ├── ai.py              # AI generation + SSE + rate limit + credit enforcement
│   ├── deployments.py     # Deployment routes (simulated)
│   ├── subscriptions.py   # JengaHQ checkout, IPN webhook, cancel, recurring billing, credits
│   ├── admin.py           # Admin stats/users/usage
│   ├── templates.py       # Prompt + project templates
│   └── shared.py          # Public shared project view
├── services/
│   ├── ai.py              # AI helpers, streaming, demo generators
│   ├── email.py           # SendGrid email helpers
│   ├── jenga.py           # JengaHQ API client (auth, payment, IPN verification)
│   └── stripe_service.py  # Billing plans + credit cost helpers (Stripe code removed)
├── ai_rate_limiter.py     # Plan-based rate limiting
└── ai_*.py                # Existing AI modules (to be wired in Phase 3)
```

## Subscription Tiers & Credits
| Tier | Price | Credits/mo | Key Features |
|------|-------|-----------|--------------|
| Starter | $0 | 10 | Basic chat/refactor |
| Standard | $29 | 75 | Full-stack & APIs |
| Pro | $59 | 150 | Autonomous debugging |
| Premier | $199 | 600 | Security scans |
| Ultra | $499 | 2,000 | Private sandboxes |

## Credit Costs per Operation
chat: 1, refactor: 2, code_generation: 2, architecture: 3, code_review: 2, documentation: 1, simple_query: 1, complex_reasoning: 3, multi_agent_build: 5, security_scan: 3, test_generation: 2, debug: 2, sandbox_execution: 4

## What's Been Implemented
- [x] Email/password auth with JWT + refresh tokens
- [x] GitHub OAuth + Standard Google OAuth2
- [x] Two-Factor Authentication (TOTP)
- [x] Password reset flow
- [x] Multi-agent AI code generation (SSE streaming, xAI Grok)
- [x] Project CRUD + file management
- [x] Project sharing, export, snapshots, activity timeline, messages
- [x] Prompt templates + project templates
- [x] Onboarding wizard + Legal pages
- [x] Cybersecurity-themed premium UI
- [x] **Backend modular refactoring** (server.py: 2500+ → 68 lines)
- [x] **JengaHQ payment integration** (Stripe fully replaced)
- [x] **Credit-based rate limiting** on all AI routes
- [x] **Recurring billing engine** (JengaHQ tokenization)
- [x] **`/api/user/credits`** endpoint
- [x] **`/api/ai/execute`** generic AI operation endpoint
- [x] **`/api/ai/credit-costs`** endpoint

## Prioritized Backlog

### P0 — In Progress
- **Phase 3: Wire existing AI modules** to routes (ai_sandbox, ai_guardrails, ai_validation_loop, ai_snapshot_manager, ai_context_pruning, ai_dependency_graph, ai_feedback_collector)

### P1
- Implement real file hosting for deployments (GCS integration)

### P2
- Enforce email verification flow

### P3/Future
- Custom prompt template creation/saving
- Team collaboration features
- Real-time multiplayer editing
- GCP deployment configuration (Cloud Run, Cloudflare DNS)

## Mocked Features
- **JengaHQ:** Demo mode when JENGA_API_KEY not set (auto-activates subscriptions)
- **AI generation:** Demo content when XAI_API_KEY not set
- **Deployment system:** Simulated (no real file hosting)
- **Contact form:** Simulated success

## Test Credentials
- Email: `test_refactor@example.com` / Password: `Test123456!`

## Testing History
- iteration_17: Backend refactoring — 42/42 passed
- iteration_18: JengaHQ migration + credit system — 31/31 passed
