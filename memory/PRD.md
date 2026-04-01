# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI Grok models with multi-agent code generation.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI, Framer Motion
- **Backend:** FastAPI (modular), MongoDB (Motor), JWT Auth
- **External APIs:** xAI Grok, Stripe, SendGrid, GitHub OAuth, Google OAuth

## Core Requirements
1. User authentication (email/password, GitHub OAuth, Google OAuth, 2FA/TOTP)
2. AI code generation workspace with multi-agent SSE streaming
3. Subscription billing (Stripe webhooks)
4. Project management (CRUD, share, export, snapshots, activity timeline)
5. Deployment simulation
6. Admin dashboard
7. Cybersecurity-themed premium UI

## Architecture (Post-Refactor)
```
/app/backend/
├── server.py              # App init + router includes (75 lines)
├── core/
│   ├── config.py          # All env vars and constants
│   ├── database.py        # MongoDB connection
│   └── security.py        # JWT, auth helpers, get_current_user
├── models/
│   └── schemas.py         # All Pydantic models
├── routes/
│   ├── auth.py            # Auth (signup, login, 2FA, OAuth, password reset)
│   ├── users.py           # User profile, onboarding, GitHub repos
│   ├── projects.py        # Project CRUD, share, export, snapshots, messages
│   ├── ai.py              # AI generation + SSE streaming
│   ├── deployments.py     # Deployment routes
│   ├── subscriptions.py   # Billing, Stripe webhook
│   ├── admin.py           # Admin stats/users/usage
│   ├── templates.py       # Prompt + project templates
│   └── shared.py          # Public shared project view
├── services/
│   ├── ai.py              # AI helpers, streaming, demo generators
│   ├── email.py           # SendGrid email helpers
│   └── stripe_service.py  # Stripe products, SUBSCRIPTION_PLANS
└── tests/                 # Test files
```

## What's Been Implemented
- [x] Email/password auth with JWT + refresh tokens
- [x] GitHub OAuth
- [x] Standard Google OAuth2
- [x] Two-Factor Authentication (TOTP)
- [x] Password reset flow
- [x] Multi-agent AI code generation (SSE streaming, xAI Grok)
- [x] Project CRUD + file management
- [x] Project sharing via public links
- [x] Project export as ZIP
- [x] Version snapshots (create/restore)
- [x] Activity timeline
- [x] Conversation history (messages)
- [x] Prompt templates + project templates
- [x] Stripe subscription billing + webhook
- [x] Deployment simulation
- [x] Admin dashboard (stats, users, usage)
- [x] Onboarding wizard
- [x] Legal pages (Privacy, Terms, Contact)
- [x] Cybersecurity-themed premium UI (NeuralBackground, AnimatedCounter, RotatingText, LiveDemo)
- [x] **Backend refactoring** (server.py: 2500+ → 75 lines, 16 modules)

## Prioritized Backlog
### P1
- Implement real file hosting for deployments (S3/GCS)

### P2
- Enforce email verification flow (restrict unverified users)

### P3/Future
- Custom prompt template creation/saving
- Team collaboration features
- Real-time multiplayer editing

## Mocked Features
- **LiveDemo** on landing page: Simulated AI generation stream
- **Deployment system**: Creates records but doesn't host real files
- **Contact form**: Simulates success without sending email
- **AI generation**: Returns demo content when XAI_API_KEY not set
- **Stripe checkout**: Returns demo URL when STRIPE_SECRET_KEY not set

## Test Credentials
- Email: `test_refactor@example.com` / Password: `Test123456!`

## Testing History
- iteration_12 through iteration_17: All passed
- iteration_17: Backend refactoring verification - 42/42 tests passed (100%)
