"""
CursorCode AI - FastAPI Backend Server
Render-ready with absolute imports and SSE streaming
"""

import os
import jwt
import stripe
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from pymongo import MongoClient
from dotenv import load_dotenv

# Absolute import of orchestrator
from backend.orchestrator import orchestrate_project, stream_orchestration_sse

# =====================================================
# Load environment
# =====================================================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cursorcode")

# =====================================================
# ENV VARIABLES
# =====================================================
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "cursorcode")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "refresh_secret")

FRONTEND_URL = os.getenv("FRONTEND_URL", "*")

XAI_API_KEY = os.getenv("XAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

# =====================================================
# DATABASE
# =====================================================
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

users_collection = db["users"]
analytics_collection = db["analytics"]
usage_collection = db["ai_usage"]

# =====================================================
# PASSWORD HASHING
# =====================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================
# FASTAPI APP
# =====================================================
app = FastAPI(
    title="CursorCode AI",
    version="1.0",
    docs_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# ROOT HEALTH ENDPOINT (NEW)
# =====================================================
@app.get("/")
def root():
    return {
        "status": "CursorCode AI backend running",
        "version": "1.0",
        "docs": "/docs"
    }

# =====================================================
# MODELS
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

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user = users_collection.find_one({"email": payload["email"]})

        if not user:
            raise HTTPException(status_code=401)

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# =====================================================
# SIGNUP
# =====================================================
@app.post("/api/auth/signup")
def signup(data: SignupRequest):

    if users_collection.find_one({"email": data.email}):
        raise HTTPException(400, "User already exists")

    hashed = hash_password(data.password)

    user = {
        "name": data.name,
        "email": data.email,
        "password": hashed,
        "created": datetime.utcnow(),
        "plan": "free"
    }

    users_collection.insert_one(user)

    access = create_access_token({"email": data.email})
    refresh = create_refresh_token({"email": data.email})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "name": data.name,
            "email": data.email
        }
    }


# =====================================================
# LOGIN
# =====================================================
@app.post("/api/auth/login")
def login(data: LoginRequest):

    user = users_collection.find_one({"email": data.email})

    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token({"email": data.email})
    refresh = create_refresh_token({"email": data.email})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "name": user["name"],
            "email": user["email"]
        }
    }


# =====================================================
# CURRENT USER
# =====================================================
@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return {
        "name": user["name"],
        "email": user["email"]
    }


# =====================================================
# AI PROJECT DEPLOYMENT
# =====================================================
@app.post("/api/project/deploy")
async def deploy_project(prompt: str, user=Depends(get_current_user)):
    """
    Generate, build, and deploy the project.
    Returns live preview URL.
    """

    project_result = await orchestrate_project(
        XAI_API_KEY,
        prompt,
        user["email"]
    )

    preview_url = project_result.get("preview_url", "Deployment failed")

    return {
        "preview_url": preview_url,
        "details": project_result
    }


# =====================================================
# STREAMING ORCHESTRATION (SSE)
# =====================================================
@app.get("/api/project/stream")
async def project_stream(
    project_id: str = Query(...),
    prompt: str = Query(...),
    user=Depends(get_current_user)
):
    """
    Stream orchestration results using Server-Sent Events
    """

    event_source = await stream_orchestration_sse(
        project_id,
        prompt,
        XAI_API_KEY,
        user["email"]
    )

    return event_source
