"""
CursorCode AI - Central Config
Holds constants and central environment config
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Database
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

# Frontend
FRONTEND_URL = os.getenv("FRONTEND_URL")

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")

# OAuth
GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# AI
XAI_API_KEY = os.getenv("XAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL")

# Email
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
