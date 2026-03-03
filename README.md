# CursorCode AI

**Build Anything. Automatically. With AI.**

CursorCode AI is an autonomous AI software engineering platform powered by xAI's Grok family with intelligent multi-model routing. It replaces entire development teams by understanding user intent, automatically designing system architecture, writing production-grade code, designing UI/UX, and deploying to cloud with zero manual DevOps.

![CursorCode AI](./frontend/public/logo.png)

## Features

- **Multi-Agent AI System**: Coordinated agents powered by xAI Grok with intelligent routing
- **Production-Grade Code**: Generate clean, scalable, documented code
- **One-Click Deploy**: Deploy to cursorcode.app with auto-SSL and monitoring
- **GitHub Integration**: Import repos and enhance code with AI
- **Enterprise Security**: OAuth/JWT, RBAC, audit logs, GDPR-ready
- **Email Verification**: SendGrid-powered email verification flow
- **Stripe Billing**: Auto-created products/prices with subscription management

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: MongoDB with Motor async driver
- **Authentication**: JWT + GitHub OAuth
- **Payments**: Stripe (auto-created products/prices)
- **Email**: SendGrid
- **AI**: xAI Grok API (OpenAI-compatible)

### Frontend
- **Framework**: React 19 with React Router
- **Styling**: Tailwind CSS + Shadcn/UI
- **Animations**: Framer Motion
- **Code Editor**: Monaco Editor
- **Charts**: Recharts

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Yarn

### Environment Variables

#### Backend (`/backend/.env`)
```env
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=cursorcode

# Security
JWT_SECRET_KEY=your-secret-key
JWT_REFRESH_SECRET=your-refresh-secret

# xAI Grok API
XAI_API_KEY=your-xai-key
DEFAULT_XAI_MODEL=grok-4-latest
FAST_REASONING_MODEL=grok-4-1-fast-reasoning
FAST_NON_REASONING_MODEL=grok-4-1-fast-non-reasoning

# Stripe (auto-creates products if key provided)
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# SendGrid
SENDGRID_API_KEY=SG...
EMAIL_FROM=info@cursorcode.ai

# GitHub OAuth
GITHUB_OAUTH_CLIENT_ID=your-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-client-secret

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

#### Frontend (`/frontend/.env`)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Installation

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Frontend
cd frontend
yarn install
yarn start
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Create account (sends verification email) |
| POST | `/api/auth/login` | Login with email/password |
| GET | `/api/auth/github` | Initiate GitHub OAuth |
| POST | `/api/auth/github/callback` | Complete GitHub OAuth |
| GET | `/api/auth/verify-email` | Verify email with token |
| POST | `/api/auth/resend-verification` | Resend verification email |

### GitHub Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/github/repos` | List user's GitHub repos |
| POST | `/api/github/import/{repo}` | Import repo as project |

### Deployments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/deploy/{project_id}` | Deploy project |
| GET | `/api/deployments` | List deployments |
| GET | `/api/deployments/{id}` | Get deployment details |
| DELETE | `/api/deployments/{id}` | Delete deployment |

## Pricing Plans

| Plan | Price | Credits | Features |
|------|-------|---------|----------|
| Starter | Free | 10 | 1 project, subdomain |
| Standard | $29 | 75 | Full-stack, version history |
| Pro | $59 | 150 | SaaS, CI/CD, advanced agents |
| Premier | $199 | 600 | Multi-org, security scans |
| Ultra | $499 | 2,000 | Unlimited, dedicated compute |

## Deployment to Render

1. Create Web Service for backend:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`

2. Create Static Site for frontend:
   - Build: `cd frontend && yarn install && yarn build`
   - Publish: `frontend/build`

3. Set environment variables in Render dashboard

## License

Proprietary - 
<div className="text-sm text-zinc-500">
  © 2026 CursorCode AI. All rights reserved.
</div>
