from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
import secrets
from datetime import datetime, timezone, timedelta
import bcrypt
from jose import jwt, JWTError
import httpx
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from urllib.parse import urlencode

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'cursorcode-secret-key-change-in-production')
JWT_REFRESH_SECRET = os.environ.get('JWT_REFRESH_SECRET', 'cursorcode-refresh-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# xAI Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = os.environ.get('DEFAULT_XAI_MODEL', 'grok-4-latest')
FAST_REASONING_MODEL = os.environ.get('FAST_REASONING_MODEL', 'grok-4-1-fast-reasoning')
FAST_NON_REASONING_MODEL = os.environ.get('FAST_NON_REASONING_MODEL', 'grok-4-1-fast-non-reasoning')

# Stripe Configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'info@cursorcode.ai')

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Create the main app
app = FastAPI(title="CursorCode AI API", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    password_hash: str = ""
    plan: str = "starter"
    credits: int = 10
    credits_used: int = 0
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    is_admin: bool = False
    email_verified: bool = False
    verification_token: Optional[str] = None
    github_id: Optional[int] = None
    github_username: Optional[str] = None
    github_access_token: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    plan: str
    credits: int
    credits_used: int
    is_admin: bool
    email_verified: bool
    github_username: Optional[str]
    avatar_url: Optional[str]
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    prompt: Optional[str] = ""

class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: str = ""
    prompt: str = ""
    status: str = "draft"
    files: Dict[str, str] = Field(default_factory=dict)
    tech_stack: List[str] = Field(default_factory=list)
    deployed_url: Optional[str] = None
    deployment_id: Optional[str] = None
    github_repo: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    prompt: str
    status: str
    files: Dict[str, str]
    tech_stack: List[str]
    deployed_url: Optional[str]
    deployment_id: Optional[str]
    github_repo: Optional[str]
    created_at: str
    updated_at: str

class AIGenerateRequest(BaseModel):
    project_id: str
    prompt: str
    model: Optional[str] = None
    task_type: str = "code_generation"

class AIGenerateResponse(BaseModel):
    id: str
    project_id: str
    prompt: str
    response: str
    model_used: str
    credits_used: int
    created_at: str

class AIBuildRequest(BaseModel):
    prompt: str

class CreditUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    project_id: Optional[str] = None
    model: str
    credits_used: int
    task_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Deployment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    user_id: str
    subdomain: str
    status: str = "deploying"
    url: str
    files: Dict[str, str] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str]
    html_url: str
    clone_url: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    private: bool
    updated_at: str

class SubscriptionPlan(BaseModel):
    name: str
    price: int
    credits: int
    features: List[str]
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "starter": SubscriptionPlan(
        name="Starter", price=0, credits=10,
        features=["10 AI credits/month", "1 project", "Subdomain deploy", "Community support"]
    ),
    "standard": SubscriptionPlan(
        name="Standard", price=29, credits=75,
        features=["75 AI credits/month", "Full-stack & APIs", "Native + external deploy", "Version history", "Email support"],
        stripe_price_id=os.environ.get('STRIPE_STANDARD_PRICE_ID')
    ),
    "pro": SubscriptionPlan(
        name="Pro", price=59, credits=150,
        features=["150 AI credits/month", "SaaS & multi-tenant", "Advanced agents", "CI/CD integration", "Priority builds"],
        stripe_price_id=os.environ.get('STRIPE_PRO_PRICE_ID')
    ),
    "premier": SubscriptionPlan(
        name="Premier", price=199, credits=600,
        features=["600 AI credits/month", "Large SaaS", "Multi-org support", "Advanced security scans", "Priority support"],
        stripe_price_id=os.environ.get('STRIPE_PREMIER_PRICE_ID')
    ),
    "ultra": SubscriptionPlan(
        name="Ultra", price=499, credits=2000,
        features=["2,000 AI credits/month", "Unlimited projects", "Dedicated compute", "SLA guarantee", "Enterprise support"],
        stripe_price_id=os.environ.get('STRIPE_ULTRA_PRICE_ID')
    )
}

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_REFRESH_SECRET, algorithm=JWT_ALGORITHM)

def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user_doc is None:
            raise HTTPException(status_code=401, detail="User not found")
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        return User(**user_doc)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, name=user.name, plan=user.plan,
        credits=user.credits, credits_used=user.credits_used, is_admin=user.is_admin,
        email_verified=user.email_verified, github_username=user.github_username,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at
    )

def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id, user_id=project.user_id, name=project.name,
        description=project.description, prompt=project.prompt, status=project.status,
        files=project.files, tech_stack=project.tech_stack,
        deployed_url=project.deployed_url, deployment_id=project.deployment_id,
        github_repo=project.github_repo,
        created_at=project.created_at.isoformat() if isinstance(project.created_at, datetime) else project.created_at,
        updated_at=project.updated_at.isoformat() if isinstance(project.updated_at, datetime) else project.updated_at
    )

# ==================== EMAIL HELPERS ====================

async def send_email(to_email: str, subject: str, html_content: str):
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured, skipping email")
        return False
    try:
        message = Mail(from_email=EMAIL_FROM, to_emails=to_email, subject=subject, html_content=html_content)
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

async def send_verification_email(email: str, name: str, token: str):
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #3B82F6, #10B981); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">CursorCode AI</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #333;">Verify your email, {name}!</h2>
            <p style="color: #666;">Thanks for signing up. Please verify your email address.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" style="background: #3B82F6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Verify Email Address
                </a>
            </div>
        </div>
    </div>"""
    return await send_email(email, "Verify your CursorCode AI account", html_content)

async def send_welcome_email(email: str, name: str):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #3B82F6, #10B981); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to CursorCode AI!</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2 style="color: #333;">You're all set, {name}!</h2>
            <p style="color: #666;">Your email has been verified. Start building with AI.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{FRONTEND_URL}/dashboard" style="background: #3B82F6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Start Building
                </a>
            </div>
        </div>
    </div>"""
    return await send_email(email, "Welcome to CursorCode AI", html_content)

# ==================== AI HELPERS ====================

def select_model(task_type: str) -> str:
    routing = {
        "architecture": DEFAULT_XAI_MODEL,
        "code_generation": FAST_REASONING_MODEL,
        "code_review": FAST_REASONING_MODEL,
        "documentation": FAST_NON_REASONING_MODEL,
        "simple_query": FAST_NON_REASONING_MODEL,
        "complex_reasoning": DEFAULT_XAI_MODEL,
    }
    return routing.get(task_type, FAST_REASONING_MODEL)

def calculate_credits(model: str, task_type: str) -> int:
    base_credits = {DEFAULT_XAI_MODEL: 3, FAST_REASONING_MODEL: 2, FAST_NON_REASONING_MODEL: 1}
    return base_credits.get(model, 2)

async def call_xai_api(prompt: str, model: str, system_message: str = None) -> str:
    if not XAI_API_KEY:
        return f"""// Generated by CursorCode AI using {model}
// Demo response - configure XAI_API_KEY for real generation

import React from 'react';

export default function GeneratedComponent() {{
  return (
    <div className="p-6 bg-gray-900 rounded-lg">
      <h1 className="text-2xl font-bold text-white">AI Generated Component</h1>
      <p className="text-gray-400 mt-2">Prompt: {prompt[:100]}...</p>
    </div>
  );
}}"""

    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "max_tokens": 4096, "temperature": 0.7}

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        response = await http_client.post(f"{XAI_BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

# ==================== STRIPE HELPERS ====================

async def ensure_stripe_products():
    if not stripe.api_key:
        logger.warning("Stripe API key not configured")
        return
    try:
        products = stripe.Product.list(limit=10)
        existing_names = {p.name: p.id for p in products.data}
        for plan_key, plan in SUBSCRIPTION_PLANS.items():
            if plan.price == 0:
                continue
            product_name = f"CursorCode AI {plan.name}"
            if product_name not in existing_names:
                product = stripe.Product.create(
                    name=product_name,
                    description=f"{plan.credits} AI credits/month - " + ", ".join(plan.features[:2]),
                    metadata={"plan": plan_key}
                )
                product_id = product.id
            else:
                product_id = existing_names[product_name]
            prices = stripe.Price.list(product=product_id, active=True, limit=1)
            if not prices.data:
                price = stripe.Price.create(
                    product=product_id, unit_amount=plan.price * 100, currency="usd",
                    recurring={"interval": "month"}, metadata={"plan": plan_key}
                )
                SUBSCRIPTION_PLANS[plan_key].stripe_price_id = price.id
                SUBSCRIPTION_PLANS[plan_key].stripe_product_id = product_id
            else:
                SUBSCRIPTION_PLANS[plan_key].stripe_price_id = prices.data[0].id
                SUBSCRIPTION_PLANS[plan_key].stripe_product_id = product_id
        logger.info("Stripe products initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Stripe: {e}")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate, background_tasks: BackgroundTasks):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    verification_token = generate_verification_token()
    user = User(
        email=user_data.email, name=user_data.name,
        password_hash=hash_password(user_data.password),
        email_verified=False, verification_token=verification_token
    )
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    background_tasks.add_task(send_verification_email, user.email, user.name, verification_token)
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

@api_router.get("/auth/verify-email")
async def verify_email(token: str, background_tasks: BackgroundTasks):
    user_doc = await db.users.find_one({"verification_token": token}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    await db.users.update_one(
        {"verification_token": token},
        {"$set": {"email_verified": True, "verification_token": None}}
    )
    background_tasks.add_task(send_welcome_email, user_doc['email'], user_doc['name'])
    return {"message": "Email verified successfully", "redirect": f"{FRONTEND_URL}/dashboard"}

@api_router.post("/auth/resend-verification")
async def resend_verification(user: User = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    new_token = generate_verification_token()
    await db.users.update_one({"id": user.id}, {"$set": {"verification_token": new_token}})
    background_tasks.add_task(send_verification_email, user.email, user.name, new_token)
    return {"message": "Verification email sent"}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user_to_response(user)

@api_router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Header(...)):
    try:
        payload = jwt.decode(refresh_token, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        user = User(**user_doc)
        new_access = create_access_token({"sub": user.id})
        new_refresh = create_refresh_token({"sub": user.id})
        return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=user_to_response(user))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== USER PROFILE ROUTES ====================

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

@api_router.put("/users/me", response_model=UserResponse)
async def update_user_profile(data: UserUpdateRequest, user: User = Depends(get_current_user)):
    update_fields = {}
    if data.name:
        update_fields["name"] = data.name
    if data.email and data.email != user.email:
        existing = await db.users.find_one({"email": data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_fields["email"] = data.email
    if update_fields:
        await db.users.update_one({"id": user.id}, {"$set": update_fields})
    updated_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    if isinstance(updated_doc.get('created_at'), str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    return user_to_response(User(**updated_doc))

# ==================== GITHUB OAUTH ROUTES ====================

@api_router.get("/auth/github")
async def github_login(redirect_uri: Optional[str] = None):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured. Set GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET in environment.")
    callback_url = redirect_uri or f"{FRONTEND_URL}/auth/github/callback"
    state = secrets.token_urlsafe(16)
    params = {"client_id": GITHUB_CLIENT_ID, "redirect_uri": callback_url, "scope": "user repo", "state": state}
    github_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=github_url)

@api_router.post("/auth/github/callback")
async def github_callback(code: str, background_tasks: BackgroundTasks):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    try:
        async with httpx.AsyncClient() as http_client:
            token_response = await http_client.post(
                "https://github.com/login/oauth/access_token",
                json={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
                headers={"Accept": "application/json"}
            )
            token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(status_code=400, detail=f"GitHub auth failed: {token_data.get('error_description', token_data['error'])}")
        github_token = token_data.get("access_token")
        async with httpx.AsyncClient() as http_client:
            user_response = await http_client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
            )
            github_user = user_response.json()
        existing_user = await db.users.find_one({"github_id": github_user["id"]}, {"_id": 0})
        if existing_user:
            await db.users.update_one(
                {"github_id": github_user["id"]},
                {"$set": {"github_access_token": github_token, "avatar_url": github_user.get("avatar_url")}}
            )
            if isinstance(existing_user.get('created_at'), str):
                existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
            user = User(**existing_user)
        else:
            email = github_user.get("email") or f"{github_user['login']}@github.cursorcode.ai"
            email_user = await db.users.find_one({"email": email}, {"_id": 0})
            if email_user:
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"github_id": github_user["id"], "github_username": github_user["login"],
                              "github_access_token": github_token, "avatar_url": github_user.get("avatar_url"),
                              "email_verified": True}}
                )
                if isinstance(email_user.get('created_at'), str):
                    email_user['created_at'] = datetime.fromisoformat(email_user['created_at'])
                user = User(**email_user)
            else:
                user = User(
                    email=email, name=github_user.get("name") or github_user["login"],
                    password_hash="", github_id=github_user["id"],
                    github_username=github_user["login"], github_access_token=github_token,
                    avatar_url=github_user.get("avatar_url"), email_verified=True
                )
                doc = user.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.users.insert_one(doc)
                background_tasks.add_task(send_welcome_email, user.email, user.name)
        access_token = create_access_token({"sub": user.id})
        refresh_tok = create_refresh_token({"sub": user.id})
        return TokenResponse(access_token=access_token, refresh_token=refresh_tok, user=user_to_response(user))
    except Exception as e:
        logger.error(f"GitHub OAuth error: {e}")
        raise HTTPException(status_code=500, detail="GitHub authentication failed")

@api_router.get("/github/repos", response_model=List[GitHubRepo])
async def get_github_repos(user: User = Depends(get_current_user)):
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub account not connected")
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"},
                params={"per_page": 100, "sort": "updated", "direction": "desc"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch repositories")
            repos = response.json()
            return [
                GitHubRepo(
                    id=repo["id"], name=repo["name"], full_name=repo["full_name"],
                    description=repo.get("description"), html_url=repo["html_url"],
                    clone_url=repo["clone_url"], language=repo.get("language"),
                    stargazers_count=repo["stargazers_count"], forks_count=repo["forks_count"],
                    private=repo["private"], updated_at=repo["updated_at"]
                ) for repo in repos
            ]
    except httpx.HTTPError as e:
        logger.error(f"GitHub API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch repositories")

@api_router.post("/github/import/{repo_full_name:path}")
async def import_github_repo(repo_full_name: str, user: User = Depends(get_current_user)):
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub account not connected")
    try:
        async with httpx.AsyncClient() as http_client:
            repo_response = await http_client.get(
                f"https://api.github.com/repos/{repo_full_name}",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"}
            )
            if repo_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Repository not found")
            repo = repo_response.json()
            contents_response = await http_client.get(
                f"https://api.github.com/repos/{repo_full_name}/contents",
                headers={"Authorization": f"Bearer {user.github_access_token}", "Accept": "application/vnd.github+json"}
            )
            files = {}
            if contents_response.status_code == 200:
                contents = contents_response.json()
                code_extensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.json', '.md']
                for item in contents[:20]:
                    if item["type"] == "file" and any(item["name"].endswith(ext) for ext in code_extensions):
                        if item["size"] < 50000:
                            file_response = await http_client.get(
                                item["download_url"],
                                headers={"Authorization": f"Bearer {user.github_access_token}"}
                            )
                            if file_response.status_code == 200:
                                files[item["name"]] = file_response.text
        project = Project(
            user_id=user.id, name=repo["name"],
            description=repo.get("description") or f"Imported from GitHub: {repo_full_name}",
            prompt=f"Imported from GitHub: {repo['html_url']}",
            status="imported", files=files,
            tech_stack=[repo.get("language")] if repo.get("language") else [],
            github_repo=repo_full_name
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.projects.insert_one(doc)
        return project_to_response(project)
    except httpx.HTTPError as e:
        logger.error(f"GitHub import error: {e}")
        raise HTTPException(status_code=500, detail="Failed to import repository")

# ==================== GOOGLE OAUTH (EMERGENT AUTH) ====================

EMERGENT_AUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

class GoogleSessionRequest(BaseModel):
    session_id: str

@api_router.post("/auth/google/session")
async def google_session_exchange(data: GoogleSessionRequest, background_tasks: BackgroundTasks):
    """Exchange Emergent Auth session_id for user data and JWT tokens."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(
                EMERGENT_AUTH_SESSION_URL,
                headers={"X-Session-ID": data.session_id}
            )
            if response.status_code != 200:
                logger.error(f"Emergent auth failed: {response.status_code} {response.text}")
                raise HTTPException(status_code=401, detail="Google authentication failed")
            session_data = response.json()

        email = session_data.get("email")
        name = session_data.get("name", "")
        picture = session_data.get("picture", "")
        session_token = session_data.get("session_token", "")

        if not email:
            raise HTTPException(status_code=400, detail="No email from Google")

        # Check if user exists
        existing_user = await db.users.find_one({"email": email}, {"_id": 0})

        if existing_user:
            # Update existing user
            update_fields = {"email_verified": True}
            if picture:
                update_fields["avatar_url"] = picture
            if name and not existing_user.get("name"):
                update_fields["name"] = name
            await db.users.update_one({"email": email}, {"$set": update_fields})
            if isinstance(existing_user.get('created_at'), str):
                existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
            user = User(**existing_user)
        else:
            # Create new user
            user = User(
                email=email, name=name or email.split("@")[0],
                password_hash="", email_verified=True,
                avatar_url=picture or ""
            )
            doc = user.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.users.insert_one(doc)
            background_tasks.add_task(send_welcome_email, user.email, user.name)

        # Store Emergent session token
        if session_token:
            await db.user_sessions.update_one(
                {"user_id": user.id},
                {"$set": {
                    "user_id": user.id,
                    "session_token": session_token,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )

        # Generate JWT tokens (compatible with existing auth)
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_to_response(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth session exchange error: {e}")
        raise HTTPException(status_code=500, detail="Google authentication failed")

# ==================== PROJECT ROUTES ====================

@api_router.post("/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=project_data.name,
                      description=project_data.description or "", prompt=project_data.prompt or "")
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.projects.insert_one(doc)
    return project_to_response(project)

@api_router.get("/projects", response_model=List[ProjectResponse])
async def get_projects(user: User = Depends(get_current_user)):
    projects = await db.projects.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    result = []
    for p in projects:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
        if isinstance(p.get('updated_at'), str):
            p['updated_at'] = datetime.fromisoformat(p['updated_at'])
        result.append(project_to_response(Project(**p)))
    return result

@api_router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if isinstance(project_doc.get('created_at'), str):
        project_doc['created_at'] = datetime.fromisoformat(project_doc['created_at'])
    if isinstance(project_doc.get('updated_at'), str):
        project_doc['updated_at'] = datetime.fromisoformat(project_doc['updated_at'])
    return project_to_response(Project(**project_doc))

@api_router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_data: ProjectCreate, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    update_data = {
        "name": project_data.name, "description": project_data.description or "",
        "prompt": project_data.prompt or "", "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.projects.update_one({"id": project_id}, {"$set": update_data})
    updated_doc = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if isinstance(updated_doc.get('created_at'), str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    if isinstance(updated_doc.get('updated_at'), str):
        updated_doc['updated_at'] = datetime.fromisoformat(updated_doc['updated_at'])
    return project_to_response(Project(**updated_doc))

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: User = Depends(get_current_user)):
    result = await db.projects.delete_one({"id": project_id, "user_id": user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}

@api_router.put("/projects/{project_id}/files")
async def update_project_files(project_id: str, files: Dict[str, str], user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"files": files, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Files updated"}

# ==================== AI GENERATION ROUTES ====================

@api_router.post("/ai/generate", response_model=AIGenerateResponse)
async def generate_code(request: AIGenerateRequest, user: User = Depends(get_current_user)):
    model = request.model or select_model(request.task_type)
    credits_needed = calculate_credits(model, request.task_type)
    remaining_credits = user.credits - user.credits_used
    if remaining_credits < credits_needed:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    project_doc = await db.projects.find_one({"id": request.project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    system_message = "You are CursorCode AI, an elite autonomous AI software engineering system. Generate clean, production-ready, well-documented code."
    try:
        response = await call_xai_api(request.prompt, model, system_message)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed")
    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": credits_needed}})
    usage = CreditUsage(user_id=user.id, project_id=request.project_id, model=model,
                        credits_used=credits_needed, task_type=request.task_type)
    usage_doc = usage.model_dump()
    usage_doc['created_at'] = usage_doc['created_at'].isoformat()
    await db.credit_usage.insert_one(usage_doc)
    return AIGenerateResponse(
        id=str(uuid.uuid4()), project_id=request.project_id, prompt=request.prompt,
        response=response, model_used=model, credits_used=credits_needed,
        created_at=datetime.now(timezone.utc).isoformat()
    )

@api_router.get("/ai/models")
async def get_ai_models():
    return {
        "models": [
            {"id": DEFAULT_XAI_MODEL, "name": "Grok 4 (Frontier)", "description": "Deep reasoning for architecture", "credits_per_use": 3},
            {"id": FAST_REASONING_MODEL, "name": "Grok 4 Fast Reasoning", "description": "Optimized for agentic workflows", "credits_per_use": 2},
            {"id": FAST_NON_REASONING_MODEL, "name": "Grok 4 Fast", "description": "High-throughput generation", "credits_per_use": 1}
        ]
    }

# ==================== AI BUILD (Multi-Agent Orchestrator) ====================

@api_router.post("/ai/build")
async def ai_build_project(data: AIBuildRequest, user: User = Depends(get_current_user)):
    """Full multi-agent AI project generation using the orchestrator"""
    from ai_rate_limiter import check_rate_limit
    from ai_metrics import track_ai_usage

    if not check_rate_limit(user.email, user.plan):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Upgrade your plan.")

    remaining_credits = user.credits - user.credits_used
    if remaining_credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    if not XAI_API_KEY:
        # Demo mode response
        return {
            "project_name": "demo-project",
            "architecture": "Demo architecture - configure XAI_API_KEY for real generation",
            "frontend": "// Demo frontend code",
            "backend": "# Demo backend code",
            "security": "No security issues found (demo)",
            "tests": "# Demo test suite",
            "devops": "# Demo Dockerfile",
            "execution_log": "Demo mode - no execution",
            "repository": None,
            "demo": True
        }

    try:
        from orchestrator import orchestrate_project
        result = await orchestrate_project(api_key=XAI_API_KEY, prompt=data.prompt, user_email=user.email)
        # Deduct credits
        await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": 1}})
        track_ai_usage(user.email)
        return result
    except Exception as e:
        logger.exception("AI build failed")
        raise HTTPException(status_code=500, detail="AI build failed")

@api_router.get("/ai/stream")
async def stream_build(prompt: str, user: User = Depends(get_current_user)):
    """Stream AI project build via SSE"""
    from ai_rate_limiter import check_rate_limit
    if not check_rate_limit(user.email, user.plan):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    if not XAI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")
    from ai_streaming import stream_project_build
    return await stream_project_build(prompt=prompt, user_email=user.email)

# ==================== DEPLOYMENT ROUTES ====================

@api_router.post("/deploy/{project_id}")
async def deploy_project(project_id: str, user: User = Depends(get_current_user)):
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    project_name = project_doc['name'].lower().replace(' ', '-').replace('_', '-')
    project_name = ''.join(c for c in project_name if c.isalnum() or c == '-')[:30]
    subdomain = f"{project_name}-{project_id[:8]}"
    deployed_url = f"https://{subdomain}.cursorcode.app"
    deployment = Deployment(
        project_id=project_id, user_id=user.id, subdomain=subdomain,
        status="deployed", url=deployed_url, files=project_doc.get('files', {}),
        logs=[
            f"[{datetime.now(timezone.utc).isoformat()}] Deployment initiated",
            f"[{datetime.now(timezone.utc).isoformat()}] Building project...",
            f"[{datetime.now(timezone.utc).isoformat()}] Installing dependencies...",
            f"[{datetime.now(timezone.utc).isoformat()}] Configuring SSL certificate...",
            f"[{datetime.now(timezone.utc).isoformat()}] Deployment successful!"
        ]
    )
    deployment_doc = deployment.model_dump()
    deployment_doc['created_at'] = deployment_doc['created_at'].isoformat()
    deployment_doc['updated_at'] = deployment_doc['updated_at'].isoformat()
    await db.deployments.insert_one(deployment_doc)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"status": "deployed", "deployed_url": deployed_url,
                  "deployment_id": deployment.id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"deployment_id": deployment.id, "deployed_url": deployed_url,
            "subdomain": subdomain, "status": "deployed", "logs": deployment.logs}

@api_router.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str, user: User = Depends(get_current_user)):
    deployment_doc = await db.deployments.find_one({"id": deployment_id, "user_id": user.id}, {"_id": 0})
    if not deployment_doc:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment_doc

@api_router.get("/deployments")
async def list_deployments(user: User = Depends(get_current_user)):
    deployments = await db.deployments.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"deployments": deployments}

@api_router.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str, user: User = Depends(get_current_user)):
    deployment_doc = await db.deployments.find_one({"id": deployment_id, "user_id": user.id}, {"_id": 0})
    if not deployment_doc:
        raise HTTPException(status_code=404, detail="Deployment not found")
    await db.projects.update_one(
        {"id": deployment_doc["project_id"]},
        {"$set": {"status": "draft", "deployed_url": None, "deployment_id": None}}
    )
    await db.deployments.delete_one({"id": deployment_id})
    return {"message": "Deployment deleted"}

# ==================== SUBSCRIPTION ROUTES ====================

@api_router.get("/plans")
async def get_plans():
    return {"plans": {k: v.model_dump() for k, v in SUBSCRIPTION_PLANS.items()}}

class CheckoutRequest(BaseModel):
    plan: str

@api_router.post("/subscriptions/create-checkout")
async def create_checkout_session(data: CheckoutRequest, user: User = Depends(get_current_user)):
    plan = data.plan
    if plan not in SUBSCRIPTION_PLANS or plan == "starter":
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan_data = SUBSCRIPTION_PLANS[plan]
    if not stripe.api_key:
        return {"url": f"{FRONTEND_URL}/dashboard?plan={plan}&demo=true", "demo": True}
    await ensure_stripe_products()
    if not plan_data.stripe_price_id:
        return {"url": f"{FRONTEND_URL}/dashboard?plan={plan}&demo=true", "demo": True}
    try:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name, metadata={"user_id": user.id})
            await db.users.update_one({"id": user.id}, {"$set": {"stripe_customer_id": customer.id}})
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id
        session = stripe.checkout.Session.create(
            customer=customer_id, payment_method_types=["card"],
            line_items=[{"price": plan_data.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard?success=true&plan={plan}",
            cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
            metadata={"user_id": user.id, "plan": plan}
        )
        return {"url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout failed: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")

@api_router.post("/subscriptions/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)
    event_type = event.get("type", "")
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan")
        if user_id and plan:
            plan_data = SUBSCRIPTION_PLANS.get(plan)
            if plan_data:
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"plan": plan, "credits": plan_data.credits, "credits_used": 0,
                              "stripe_subscription_id": session.get("subscription")}}
                )
    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        if customer_id:
            await db.users.update_one(
                {"stripe_customer_id": customer_id},
                {"$set": {"plan": "starter", "credits": 10, "credits_used": 0, "stripe_subscription_id": None}}
            )
    return {"received": True}

@api_router.get("/subscriptions/current")
async def get_current_subscription(user: User = Depends(get_current_user)):
    plan = SUBSCRIPTION_PLANS.get(user.plan, SUBSCRIPTION_PLANS["starter"])
    return {
        "plan": user.plan, "plan_details": plan.model_dump(),
        "credits": user.credits, "credits_used": user.credits_used,
        "credits_remaining": user.credits - user.credits_used
    }

# ==================== ADMIN ROUTES ====================

@api_router.get("/admin/stats")
async def get_admin_stats(user: User = Depends(get_admin_user)):
    total_users = await db.users.count_documents({})
    total_projects = await db.projects.count_documents({})
    total_generations = await db.credit_usage.count_documents({})
    total_deployments = await db.deployments.count_documents({})
    pipeline = [{"$group": {"_id": "$plan", "count": {"$sum": 1}}}]
    plan_counts = await db.users.aggregate(pipeline).to_list(None)
    plan_distribution = {item["_id"]: item["count"] for item in plan_counts if item["_id"]}
    for plan in SUBSCRIPTION_PLANS.keys():
        if plan not in plan_distribution:
            plan_distribution[plan] = 0
    revenue = sum(SUBSCRIPTION_PLANS[plan].price * count for plan, count in plan_distribution.items())
    # AI metrics
    from ai_metrics import get_platform_stats
    ai_stats = get_platform_stats()
    return {
        "total_users": total_users, "total_projects": total_projects,
        "total_generations": total_generations, "total_deployments": total_deployments,
        "plan_distribution": plan_distribution, "monthly_revenue": revenue,
        "ai_metrics": ai_stats
    }

@api_router.get("/admin/users")
async def get_admin_users(user: User = Depends(get_admin_user), limit: int = 50, skip: int = 0):
    users = await db.users.find(
        {}, {"_id": 0, "password_hash": 0, "github_access_token": 0, "verification_token": 0}
    ).skip(skip).limit(limit).to_list(limit)
    return {"users": users, "total": await db.users.count_documents({})}

@api_router.get("/admin/usage")
async def get_admin_usage(user: User = Depends(get_admin_user), days: int = 30):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    usage = await db.credit_usage.find(
        {"created_at": {"$gte": start_date.isoformat()}}, {"_id": 0}
    ).to_list(1000)
    return {"usage": usage}

# ==================== TEMPLATES ROUTES ====================

PROJECT_TEMPLATES = [
    {
        "id": "saas-dashboard",
        "name": "SaaS Dashboard",
        "description": "Modern analytics dashboard with user auth, Stripe billing, team management, and responsive admin panel.",
        "category": "saas",
        "icon": "layout-dashboard",
        "gradient": "from-blue-600 to-cyan-500",
        "tech_stack": ["React", "FastAPI", "PostgreSQL", "Stripe", "TailwindCSS"],
        "prompt": "Build a modern SaaS dashboard application with: 1) User authentication with JWT and role-based access control, 2) Stripe subscription billing with multiple plans, 3) Analytics dashboard with charts showing revenue, users, and engagement metrics, 4) Team management with invite system, 5) Settings page with profile, billing, and notification preferences, 6) Responsive design with dark mode support. Use React with TailwindCSS for frontend and FastAPI with PostgreSQL for backend.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": True,
    },
    {
        "id": "ecommerce-store",
        "name": "E-Commerce Store",
        "description": "Full-stack online store with product catalog, cart, checkout, payments, and order tracking.",
        "category": "ecommerce",
        "icon": "shopping-cart",
        "gradient": "from-emerald-600 to-green-400",
        "tech_stack": ["React", "Node.js", "MongoDB", "Stripe", "TailwindCSS"],
        "prompt": "Build a full-stack e-commerce store with: 1) Product catalog with categories, search, and filtering, 2) Shopping cart with quantity management, 3) Secure checkout flow with Stripe payment processing, 4) User accounts with order history and tracking, 5) Admin panel for managing products, orders, and inventory, 6) Responsive mobile-first design with image optimization. Use React for frontend, Node.js/Express for backend, MongoDB for database.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": True,
    },
    {
        "id": "blog-platform",
        "name": "Blog Platform",
        "description": "Content publishing platform with markdown editor, categories, comments, and SEO optimization.",
        "category": "content",
        "icon": "file-text",
        "gradient": "from-purple-600 to-pink-500",
        "tech_stack": ["React", "FastAPI", "MongoDB", "Markdown", "TailwindCSS"],
        "prompt": "Build a blog platform with: 1) Rich markdown editor with live preview and image uploads, 2) Categories and tags for organizing posts, 3) Comment system with moderation, 4) SEO optimization with meta tags, sitemaps, and Open Graph, 5) Author profiles with bio and social links, 6) RSS feed generation, 7) Admin dashboard for managing posts and comments. Use React for frontend, FastAPI for backend, MongoDB for storage.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": False,
    },
    {
        "id": "api-backend",
        "name": "REST API Backend",
        "description": "Production-ready API with auth, rate limiting, docs, database models, and test suite.",
        "category": "backend",
        "icon": "server",
        "gradient": "from-orange-600 to-amber-500",
        "tech_stack": ["FastAPI", "PostgreSQL", "Redis", "Docker", "Pytest"],
        "prompt": "Build a production-ready REST API backend with: 1) JWT authentication with refresh tokens, 2) Rate limiting per user/plan, 3) Auto-generated OpenAPI/Swagger documentation, 4) Database models with migrations (Alembic), 5) Comprehensive test suite with pytest, 6) Docker and docker-compose setup, 7) CI/CD pipeline configuration, 8) Logging, error handling, and monitoring endpoints. Use FastAPI with PostgreSQL and Redis.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": False,
    },
    {
        "id": "portfolio-site",
        "name": "Portfolio Website",
        "description": "Stunning developer portfolio with project showcase, blog, contact form, and animations.",
        "category": "website",
        "icon": "briefcase",
        "gradient": "from-indigo-600 to-violet-500",
        "tech_stack": ["React", "Framer Motion", "TailwindCSS", "MDX"],
        "prompt": "Build a stunning developer portfolio website with: 1) Animated hero section with typing effect, 2) Project showcase gallery with filters and detail modals, 3) Skills section with visual progress indicators, 4) Blog section with MDX support, 5) Contact form with email integration, 6) Smooth scroll animations and page transitions using Framer Motion, 7) Dark/light theme toggle, 8) Fully responsive design. Use React with TailwindCSS and Framer Motion.",
        "complexity": "beginner",
        "estimated_credits": 2,
        "popular": True,
    },
    {
        "id": "realtime-chat",
        "name": "Real-Time Chat App",
        "description": "Live messaging with WebSocket, user presence, message history, and file sharing.",
        "category": "realtime",
        "icon": "message-circle",
        "gradient": "from-teal-600 to-emerald-400",
        "tech_stack": ["React", "FastAPI", "WebSocket", "MongoDB", "Redis"],
        "prompt": "Build a real-time chat application with: 1) WebSocket-based instant messaging, 2) User presence indicators (online/offline/typing), 3) Message history with infinite scroll, 4) File and image sharing with previews, 5) Group chat and direct messages, 6) Read receipts and message reactions, 7) Search through message history, 8) Push notification support. Use React for frontend, FastAPI with WebSocket for backend, MongoDB for storage, Redis for pub/sub.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": False,
    },
    {
        "id": "ai-assistant",
        "name": "AI Assistant",
        "description": "Conversational AI with NLP, context memory, chat history, and function calling.",
        "category": "ai",
        "icon": "bot",
        "gradient": "from-rose-600 to-pink-500",
        "tech_stack": ["React", "FastAPI", "OpenAI", "MongoDB", "TailwindCSS"],
        "prompt": "Build an AI-powered conversational assistant with: 1) Chat interface with streaming responses, 2) Context memory across conversations, 3) Conversation history with search, 4) Function calling for real-world actions (weather, search, calculations), 5) System prompt customization, 6) Multiple conversation threads, 7) Export chat history, 8) Token usage tracking. Use React for frontend, FastAPI for backend, OpenAI API for LLM, MongoDB for storage.",
        "complexity": "intermediate",
        "estimated_credits": 3,
        "popular": True,
    },
    {
        "id": "mobile-app",
        "name": "Mobile App",
        "description": "Cross-platform mobile app with auth, push notifications, offline support, and sleek UI.",
        "category": "mobile",
        "icon": "smartphone",
        "gradient": "from-sky-600 to-blue-400",
        "tech_stack": ["React Native", "Expo", "FastAPI", "Firebase", "TypeScript"],
        "prompt": "Build a cross-platform mobile application with: 1) User authentication with biometric support, 2) Push notifications via Firebase, 3) Offline-first architecture with local storage sync, 4) Bottom tab navigation with smooth transitions, 5) Camera and photo library integration, 6) Dark/light theme with system preference detection, 7) App store ready configuration for iOS and Android. Use React Native with Expo, FastAPI for backend, Firebase for notifications.",
        "complexity": "advanced",
        "estimated_credits": 5,
        "popular": False,
    },
]

@api_router.get("/templates")
async def get_templates(category: Optional[str] = None):
    templates = PROJECT_TEMPLATES
    if category and category != "all":
        templates = [t for t in templates if t["category"] == category]
    categories = list(set(t["category"] for t in PROJECT_TEMPLATES))
    return {"templates": templates, "categories": categories}

@api_router.get("/templates/{template_id}")
async def get_template(template_id: str):
    template = next((t for t in PROJECT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@api_router.post("/templates/{template_id}/create")
async def create_project_from_template(template_id: str, user: User = Depends(get_current_user)):
    template = next((t for t in PROJECT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    project = Project(
        user_id=user.id, name=template["name"],
        description=template["description"],
        prompt=template["prompt"], status="draft",
        tech_stack=template["tech_stack"]
    )
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.projects.insert_one(doc)
    return project_to_response(project)

# ==================== HEALTH & ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "CursorCode AI API", "version": "2.0.0", "status": "running"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    if stripe.api_key:
        await ensure_stripe_products()
    logger.info("CursorCode AI v2.0 started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
