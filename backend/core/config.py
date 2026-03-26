import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# JWT
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'cursorcode-secret-key-change-in-production')
JWT_REFRESH_SECRET = os.environ.get('JWT_REFRESH_SECRET', 'cursorcode-refresh-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# xAI
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = os.environ.get('DEFAULT_XAI_MODEL', 'grok-4-latest')
FAST_REASONING_MODEL = os.environ.get('FAST_REASONING_MODEL', 'grok-4-1-fast-reasoning')
FAST_NON_REASONING_MODEL = os.environ.get('FAST_NON_REASONING_MODEL', 'grok-4-1-fast-non-reasoning')

# Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# SendGrid
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'info@cursorcode.ai')

# GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', '')

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# URLs
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '') or f"{FRONTEND_URL}/auth/google/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
