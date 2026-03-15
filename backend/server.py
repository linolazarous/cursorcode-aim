"""
CursorCode AI - FastAPI Backend Server
Production-ready for Render deployment
Supports JWT auth, MongoDB, Stripe, SSE, GitHub & Google OAuth
"""

import os
import jwt
import stripe
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from passlib.context import CryptContext
from pymongo import MongoClient
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth

# Absolute import of orchestrator
from backend.orchestrator import orchestrate_project, stream_orchestration_sse
from backend.config import (
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    FRONTEND_URL
)

# =====================================================
# Load Environment
# =====================================================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cursorcode")

# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "cursorcode")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_key")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "refresh_secret")

XAI_API_KEY = os.getenv("XAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# =====================================================
# DATABASE CONNECTION
# =====================================================
try:
    client = MongoClient(MONGO_URL)
    client.admin.command("ping")
    logger.info("MongoDB connected successfully")
except Exception as e:
    logger.error("MongoDB connection failed")
    logger.error(e)
    raise e

db = client[DB_NAME]
users_collection = db["users"]
analytics_collection = db["analytics"]
usage_collection = db["ai_usage"]

# =====================================================
# PASSWORD HASHING
# =====================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================
# FASTAPI APPLICATION
# =====================================================
app = FastAPI(title="CursorCode AI", version="1.0", docs_url="/docs")

# =====================================================
# CORS CONFIGURATION
# =====================================================
origins = [
    FRONTEND_URL,
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# ROOT & HEALTH
# =====================================================
@app.get("/")
def root():
    return {
        "status": "CursorCode AI backend running",
        "version": "1.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# =====================================================
# REQUEST MODELS
# =====================================================
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# =====================================================
# AUTH HELPERS
# =====================================================
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=30)
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm="HS256")

def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user = users_collection.find_one({"email": payload["email"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# =====================================================
# EMAIL/PASSWORD AUTH
# =====================================================
@app.post("/api/auth/signup")
def signup(data: SignupRequest):
    if users_collection.find_one({"email": data.email}):
        raise HTTPException(400, "User already exists")
    hashed_password = hash_password(data.password)
    user = {
        "name": data.name,
        "email": data.email,
        "password": hashed_password,
        "created": datetime.utcnow(),
        "plan": "free"
    }
    users_collection.insert_one(user)
    access_token = create_access_token({"email": data.email})
    refresh_token = create_refresh_token({"email": data.email})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"name": data.name, "email": data.email}
    }

@app.post("/api/auth/login")
def login(data: LoginRequest):
    user = users_collection.find_one({"email": data.email})
    if not user or not user.get("password") or not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    access_token = create_access_token({"email": user["email"]})
    refresh_token = create_refresh_token({"email": user["email"]})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"name": user["name"], "email": user["email"]}
    }

@app.get("/api/auth/me")
def get_me(user=Depends(get_current_user)):
    return {"name": user["name"], "email": user["email"]}

# =====================================================
# OAUTH SETUP
# =====================================================
oauth = OAuth()

# GitHub OAuth
oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Google OAuth
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
)

# =====================================================
# OAUTH ROUTES
# =====================================================
# GitHub
@app.get("/api/auth/github/login")
async def github_login(request: Request):
    redirect_uri = f"{FRONTEND_URL}/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@app.get("/api/auth/github/callback")
async def github_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get('user', token=token)
    profile = resp.json()
    email = profile.get("email") or f"{profile['login']}@github.com"
    name = profile.get("name") or profile.get("login")
    user = users_collection.find_one({"email": email})
    if not user:
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": None,
            "created": datetime.utcnow(),
            "plan": "free"
        })
    access = create_access_token({"email": email})
    refresh = create_refresh_token({"email": email})
    return RedirectResponse(f"{FRONTEND_URL}/oauth-success?access={access}&refresh={refresh}")

# Google
@app.get("/api/auth/google/login")
async def google_login(request: Request):
    redirect_uri = f"{FRONTEND_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/api/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    resp = await oauth.google.get('userinfo', token=token)
    profile = resp.json()
    email = profile.get("email")
    name = profile.get("name") or email.split("@")[0]
    user = users_collection.find_one({"email": email})
    if not user:
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": None,
            "created": datetime.utcnow(),
            "plan": "free"
        })
    access = create_access_token({"email": email})
    refresh = create_refresh_token({"email": email})
    return RedirectResponse(f"{FRONTEND_URL}/oauth-success?access={access}&refresh={refresh}")

# =====================================================
# AI PROJECT DEPLOYMENT
# =====================================================
@app.post("/api/project/deploy")
async def deploy_project(prompt: str, user=Depends(get_current_user)):
    logger.info(f"User {user['email']} requested project deployment")
    try:
        project_result = await orchestrate_project(XAI_API_KEY, prompt, user["email"])
        preview_url = project_result.get("preview_url", "Deployment failed")
        return {"preview_url": preview_url, "details": project_result}
    except Exception as e:
        logger.error("Deployment error")
        logger.error(e)
        raise HTTPException(status_code=500, detail="Project deployment failed")

# =====================================================
# STREAMING ORCHESTRATION (SSE)
# =====================================================
@app.get("/api/project/stream")
async def project_stream(project_id: str = Query(...), prompt: str = Query(...), user=Depends(get_current_user)):
    logger.info(f"Streaming build for project {project_id}")
    try:
        event_source = await stream_orchestration_sse(project_id, prompt, XAI_API_KEY, user["email"])
        return event_source
    except Exception as e:
        logger.error("Streaming error")
        logger.error(e)
        raise HTTPException(status_code=500, detail="Streaming failed")
