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
│   ├── config.py          # All env vars
│   ├── database.py        # MongoDB connection
│   └── security.py        # JWT, auth helpers
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (signup, login, 2FA, OAuth, password reset)
│   ├── users.py           # User profile, onboarding, GitHub repos
│   ├── projects.py        # Project CRUD, share, export, snapshots, messages
│   ├── ai.py              # AI generation + SSE + rate limit + credit enforcement
│   ├── autonomous.py      # 18 endpoints: guardrails, sandbox, validation, snapshots, context, deps, feedback
│   ├── deployments.py     # Deployment routes (simulated)
│   ├── subscriptions.py   # JengaHQ checkout, IPN webhook, cancel, recurring billing
│   ├── admin.py           # Admin stats/users/usage
│   ├── templates.py       # Prompt + project templates
│   └── shared.py          # Public shared project view
├── services/
│   ├── ai.py              # AI helpers, streaming, demo generators
│   ├── email.py           # SendGrid email helpers
│   ├── jenga.py           # JengaHQ API client
│   ├── stripe_service.py  # Billing plans + credit cost helpers (Stripe removed)
│   ├── guardrails.py      # Lazy code, credential leak, hallucinated lib detection
│   ├── sandbox.py         # Subprocess code execution wrapper
│   ├── validation_loop.py # Test gen -> execute -> debug cycle
│   ├── snapshot_manager.py# Pre-op snapshots, rollback, diff
│   ├── context_pruning.py # TF-IDF file relevance ranking
│   ├── dependency_graph.py# Cross-file import mapping
│   └── feedback_collector.py # User feedback storage + stats
├── ai_agents.py           # Multi-agent system (Grok)
├── ai_rate_limiter.py     # Plan-based rate limiting
├── ai_security.py         # Prompt/code security validation
├── code_executor.py       # Subprocess sandbox (Python/Node.js)
└── [other ai_*.py]        # Supporting AI modules
```

## Autonomous AI Modules (Phase 3 - COMPLETE)
| Module | Endpoints | Status |
|--------|-----------|--------|
| Guardrails | `/validate`, `/validate-project/{id}` | Working |
| Sandbox | `/execute`, `/run-tests/{id}` | Working |
| Validation Loop | `/validate-loop` | Working (demo mode) |
| Snapshot Manager | `/auto`, `/rollback`, `/diff`, list | Working |
| Context Pruning | `/rank/{id}`, `/prune/{id}` | Working |
| Dependency Graph | `/deps/{id}`, `/affected` | Working |
| Feedback Collector | `/feedback`, `/stats`, `/recent` | Working |

## What's Been Implemented
- [x] All auth flows (email, GitHub, Google OAuth, 2FA, password reset)
- [x] Multi-agent AI code generation (SSE streaming)
- [x] Project CRUD + share + export + snapshots + messages
- [x] Backend modular refactoring (server.py 2500+ -> 70 lines)
- [x] JengaHQ payment integration (Stripe fully replaced)
- [x] Credit-based rate limiting on all AI routes
- [x] Recurring billing engine
- [x] **7 autonomous AI modules** (guardrails, sandbox, validation_loop, snapshot_manager, context_pruning, dependency_graph, feedback_collector)
- [x] Cybersecurity-themed premium UI

## Prioritized Backlog
### P1
- Implement real file hosting for deployments (GCS integration)
### P2
- Enforce email verification flow
### P3/Future
- Custom prompt template creation/saving
- Team collaboration features
- GCP deployment configuration (Cloud Run, Cloudflare DNS)

## Testing History
- iteration_17: Backend refactoring — 42/42 passed
- iteration_18: JengaHQ + credit system — 31/31 passed
- iteration_19: Autonomous AI modules — 53/53 passed

## Test Credentials
- Email: `test_refactor@example.com` / Password: `Test123456!`
