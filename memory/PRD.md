# CursorCode AI - Product Requirements Document

## Original Problem Statement
Build an autonomous AI software engineering platform called "CursorCode AI" that takes natural language prompts to design, build, deploy, and maintain full-stack applications. Powered by xAI's Grok models.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn/UI, Framer Motion, React Router
- **Backend:** FastAPI, MongoDB (Motor), JWT Authentication
- **3rd Party:** Stripe (billing), SendGrid (email), GitHub OAuth, Emergent Google Auth

## Architecture
```
/app/
├── backend/
│   ├── server.py             # Main FastAPI entry (all routes)
│   ├── ai_modules/           # AI logic (builder, orchestrator)
│   ├── auth_modules/         # Auth helpers
│   ├── db/                   # MongoDB connection (Motor)
│   ├── models/               # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main routing
│   │   ├── components/       # TwoFactorSetup, CreditMeter, OnboardingWizard, Sidebar, Logo, DemoVideoModal
│   │   ├── context/          # AuthContext
│   │   ├── lib/              # API client (axios)
│   │   ├── pages/            # All pages including ForgotPassword, ResetPassword
│   │   └── mockups/          # Template previews
│   └── package.json
```

## Key DB Schema
- **users:** `{email, hashed_password, name, credits, plan, credits_used, stripe_customer_id, github_id, google_id, is_verified, is_admin, onboarding_completed, totp_secret, totp_enabled, totp_backup_codes, reset_token, reset_token_expires}`
- **projects:** `{user_id, name, description, status, preview_url}`
- **subscriptions:** `{user_id, stripe_subscription_id, plan, status}`

## Completed Features (All Tested - 100% Pass)
1. User authentication (signup, login, JWT, refresh tokens)
2. GitHub OAuth + Emergent Google Auth
3. User/Admin dashboards with project CRUD
4. Project Templates Gallery with filterable categories
5. Template Preview Mode with interactive mockups
6. Pricing page with Stripe checkout integration
7. Settings page (profile, billing, API keys, security)
8. Demo Video Modal on landing page
9. Email verification flow
10. **Two-Factor Authentication (2FA/TOTP)** - Enable, verify, disable, login with 2FA
11. **Password Reset Flow** - Email-based reset with token expiration + password strength meter
12. **Enhanced Landing Page** - Architecture Graph (7 agents), Deploy Terminal animation, Enterprise Compliance (SOC 2, GDPR, Security-First)
13. **Credit Meter Component** - Visual credit tracking on Dashboard header
14. **Security Tab in Settings** - Full 2FA management UI
15. **Guided Onboarding Wizard** - 4-step wizard (Welcome, Use Case, Features, Ready) for new users

## Key API Endpoints
- `/api/auth/signup`, `/api/auth/login`, `/api/auth/login-2fa`
- `/api/auth/2fa/enable`, `/api/auth/2fa/verify`, `/api/auth/2fa/disable`
- `/api/auth/reset-password/request`, `/api/auth/reset-password/confirm`
- `/api/auth/github`, `/api/auth/google/session`
- `/api/users/me` (GET/PUT), `/api/users/me/complete-onboarding`
- `/api/projects` (CRUD)
- `/api/stripe/create-checkout-session`, `/api/stripe/webhook` (stub)
- `/api/templates`, `/api/admin/stats`

## Pending Tasks (Prioritized)
### P1
- Stripe Webhook - full implementation for checkout.session.completed

### P2
- Real file hosting for deployments (object storage)
- Email verification enforcement on protected routes
- Community templates

### Mocked/Simulated
- Project deployment feature (simulation with fake preview URLs)
- Stripe webhook (stub endpoint)
- SendGrid emails (requires API key configuration)

## Download
Project zip available at `/app/cursorcode-ai-project.zip` (1.9MB, excludes demo-video.mp4)
