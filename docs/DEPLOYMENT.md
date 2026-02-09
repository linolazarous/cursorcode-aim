# Deployment Guide

## Quick Deploy to Render

### Backend Service (Web Service)
1. Create new **Web Service** → Connect GitHub repo
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. **Environment**: Python 3.11

### Frontend Service (Static Site)
1. Create new **Static Site** → Connect GitHub repo  
2. **Root Directory**: `frontend`
3. **Build Command**: `yarn install && yarn build`
4. **Publish Directory**: `build`

### Required Environment Variables (Backend)

```env
# Database (MongoDB Atlas recommended)
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=cursorcode

# CORS - Set to your frontend domain
CORS_ORIGINS=https://your-frontend.onrender.com,https://cursorcode.ai

# Security (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-256-bit-secret
JWT_REFRESH_SECRET=your-256-bit-refresh-secret

# xAI Grok API (from x.ai)
XAI_API_KEY=xai-your-key
DEFAULT_XAI_MODEL=grok-4-latest
FAST_REASONING_MODEL=grok-4-1-fast-reasoning
FAST_NON_REASONING_MODEL=grok-4-1-fast-non-reasoning

# Stripe (from stripe.com/dashboard)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# SendGrid (from sendgrid.com)
SENDGRID_API_KEY=SG...
EMAIL_FROM=info@cursorcode.ai

# GitHub OAuth (from github.com/settings/developers)
GITHUB_OAUTH_CLIENT_ID=your-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-client-secret

# Frontend URL (your deployed frontend)
FRONTEND_URL=https://your-frontend.onrender.com
```

### Required Environment Variables (Frontend)

```env
REACT_APP_BACKEND_URL=https://your-backend.onrender.com
```

## GitHub OAuth Setup

1. Go to https://github.com/settings/developers
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: CursorCode AI
   - **Homepage URL**: https://your-frontend.onrender.com
   - **Authorization callback URL**: https://your-frontend.onrender.com/auth/github/callback
4. Copy **Client ID** and generate **Client Secret**
5. Add to Render environment variables

## Stripe Webhook Setup

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-backend.onrender.com/api/subscriptions/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy **Signing secret** → Add as `STRIPE_WEBHOOK_SECRET`

## MongoDB Atlas Setup

1. Create free cluster at mongodb.com/cloud/atlas
2. Create database user
3. Whitelist all IPs (0.0.0.0/0) or Render IPs
4. Get connection string → Add as `MONGO_URL`

## Troubleshooting

### Backend won't start
- Check `MONGO_URL` is correct and accessible
- Ensure all required env vars are set
- Check Render logs for specific errors

### Frontend shows blank page
- Verify `REACT_APP_BACKEND_URL` points to backend
- Check browser console for errors
- Ensure CORS_ORIGINS includes frontend URL

### GitHub OAuth fails
- Verify callback URL matches exactly
- Check GITHUB_OAUTH_CLIENT_ID and SECRET are set
- Ensure FRONTEND_URL is correct

### Stripe checkout fails
- Verify STRIPE_SECRET_KEY is correct
- Check webhook endpoint is accessible
- Ensure products are created (auto-created on first request)
