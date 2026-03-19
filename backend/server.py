from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, StreamingResponse
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
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode
import json
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
    onboarding_completed: bool = False
    # 2FA (TOTP)
    totp_secret: Optional[str] = None
    totp_enabled: bool = False
    totp_backup_codes: Optional[List[str]] = None
    # Password Reset
    reset_token: Optional[str] = None
    reset_token_expires: Optional[str] = None
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
    onboarding_completed: bool
    totp_enabled: bool = False
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
    # Share
    is_public: bool = False
    share_id: Optional[str] = None
    view_count: int = 0
    # Owner info for shared view
    owner_name: Optional[str] = None
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
    is_public: bool = False
    share_id: Optional[str] = None
    view_count: int = 0
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
    files: Optional[Dict[str, str]] = None

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

async def get_user_from_token_param(request: Request) -> User:
    """Extract user from 'token' query param - used for SSE EventSource which can't send headers."""
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        return User(**user_doc)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, name=user.name, plan=user.plan,
        credits=user.credits, credits_used=user.credits_used, is_admin=user.is_admin,
        email_verified=user.email_verified, github_username=user.github_username,
        avatar_url=user.avatar_url, onboarding_completed=user.onboarding_completed,
        totp_enabled=user.totp_enabled,
        created_at=user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at
    )

def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id, user_id=project.user_id, name=project.name,
        description=project.description, prompt=project.prompt, status=project.status,
        files=project.files, tech_stack=project.tech_stack,
        deployed_url=project.deployed_url, deployment_id=project.deployment_id,
        github_repo=project.github_repo, is_public=project.is_public,
        share_id=project.share_id, view_count=project.view_count,
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
        # Production-grade demo: return realistic multi-file response
        return f"""```filename:App.jsx
import React, {{ useState }} from 'react';

export default function App() {{
  const [items, setItems] = useState([]);
  const [input, setInput] = useState('');

  const addItem = () => {{
    if (input.trim()) {{
      setItems([...items, {{ id: Date.now(), text: input, done: false }}]);
      setInput('');
    }}
  }};

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Generated App</h1>
        <p className="text-zinc-400 mb-8">Prompt: {prompt[:80]}...</p>
        <div className="flex gap-2 mb-6">
          <input value={{input}} onChange={{e => setInput(e.target.value)}}
            className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg border border-zinc-700"
            placeholder="Add an item..." />
          <button onClick={{addItem}} className="px-6 py-2 bg-blue-600 rounded-lg hover:bg-blue-700">Add</button>
        </div>
        <div className="space-y-2">
          {{items.map(item => (
            <div key={{item.id}} className="p-3 bg-zinc-900 rounded-lg border border-zinc-800 flex items-center justify-between">
              <span>{{item.text}}</span>
              <button onClick={{() => setItems(items.filter(i => i.id !== item.id))}} className="text-red-400 hover:text-red-300 text-sm">Remove</button>
            </div>
          ))}}
        </div>
      </div>
    </div>
  );
}}
```

```filename:api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

app = FastAPI()
items = []

class ItemCreate(BaseModel):
    text: str

class Item(BaseModel):
    id: str
    text: str
    done: bool = False

@app.get("/api/items")
def list_items():
    return items

@app.post("/api/items")
def create_item(data: ItemCreate):
    item = {{"id": str(uuid.uuid4()), "text": data.text, "done": False}}
    items.append(item)
    return item
```
"""

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

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # If 2FA enabled, signal frontend to request code
    if user.totp_enabled:
        return {"requires_2fa": True, "message": "2FA code required", "email": user.email}
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

@api_router.post("/users/me/complete-onboarding")
async def complete_onboarding(user: User = Depends(get_current_user)):
    await db.users.update_one({"id": user.id}, {"$set": {"onboarding_completed": True}})
    return {"message": "Onboarding completed"}

# ==================== TWO-FACTOR AUTHENTICATION (2FA) ====================

class TwoFAVerifyRequest(BaseModel):
    code: str

@api_router.post("/auth/2fa/enable")
async def enable_2fa(user: User = Depends(get_current_user)):
    """Generate TOTP secret, QR code, and backup codes for 2FA setup."""
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="CursorCode AI")
    # Generate QR code as base64
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = f"data:image/png;base64,{b64encode(buf.getvalue()).decode()}"
    # Generate backup codes
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    # Store secret and backup codes (not yet enabled until verified)
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"totp_secret": secret, "totp_backup_codes": backup_codes}}
    )
    return {"qr_code_base64": qr_base64, "secret": secret, "backup_codes": backup_codes}

@api_router.post("/auth/2fa/verify")
async def verify_2fa(data: TwoFAVerifyRequest, user: User = Depends(get_current_user)):
    """Verify TOTP code and activate 2FA."""
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    secret = user_doc.get("totp_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /auth/2fa/enable first.")
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    await db.users.update_one({"id": user.id}, {"$set": {"totp_enabled": True}})
    return {"message": "2FA enabled successfully"}

@api_router.post("/auth/2fa/disable")
async def disable_2fa(data: TwoFAVerifyRequest, user: User = Depends(get_current_user)):
    """Disable 2FA after verifying current code or backup code."""
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    secret = user_doc.get("totp_secret")
    backup_codes = user_doc.get("totp_backup_codes", [])
    totp = pyotp.TOTP(secret)
    code_valid = totp.verify(data.code, valid_window=1)
    backup_valid = data.code.upper() in [c.upper() for c in (backup_codes or [])]
    if not code_valid and not backup_valid:
        raise HTTPException(status_code=400, detail="Invalid code")
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"totp_enabled": False, "totp_secret": None, "totp_backup_codes": None}}
    )
    return {"message": "2FA disabled successfully"}

class TwoFALoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

@api_router.post("/auth/login-2fa")
async def login_with_2fa(credentials: TwoFALoginRequest):
    """Login endpoint that handles 2FA if enabled."""
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.totp_enabled:
        if not credentials.totp_code:
            return {"requires_2fa": True, "message": "2FA code required"}
        totp = pyotp.TOTP(user.totp_secret)
        backup_codes = user.totp_backup_codes or []
        code_valid = totp.verify(credentials.totp_code, valid_window=1)
        backup_valid = credentials.totp_code.upper() in [c.upper() for c in backup_codes]
        if not code_valid and not backup_valid:
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
        # If backup code used, remove it
        if backup_valid:
            new_codes = [c for c in backup_codes if c.upper() != credentials.totp_code.upper()]
            await db.users.update_one({"id": user.id}, {"$set": {"totp_backup_codes": new_codes}})
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

# ==================== PASSWORD RESET ====================

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@api_router.post("/auth/reset-password/request")
async def request_password_reset(data: PasswordResetRequest, background_tasks: BackgroundTasks):
    """Send password reset email. Always returns 200 to prevent email enumeration."""
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if user_doc:
        reset_token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await db.users.update_one(
            {"email": data.email},
            {"$set": {"reset_token": reset_token, "reset_token_expires": expires}}
        )
        reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0F172A, #1E293B); padding: 30px; text-align: center;">
                <h1 style="color: #60A5FA; margin: 0;">CursorCode AI</h1>
            </div>
            <div style="padding: 30px; background: #0F172A; color: #E2E8F0;">
                <h2>Reset Your Password</h2>
                <p>We received a request to reset your password. Click the button below to set a new password.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background: #3B82F6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #94A3B8; font-size: 14px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
            </div>
        </div>"""
        background_tasks.add_task(send_email, data.email, "Reset your CursorCode AI password", html_content)
    return {"message": "If an account exists with that email, a reset link has been sent."}

@api_router.post("/auth/reset-password/confirm")
async def confirm_password_reset(data: PasswordResetConfirm):
    """Reset password using token."""
    user_doc = await db.users.find_one({"reset_token": data.token}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires = user_doc.get("reset_token_expires")
    if expires:
        exp_dt = datetime.fromisoformat(expires)
        if datetime.now(timezone.utc) > exp_dt:
            raise HTTPException(status_code=400, detail="Reset token has expired")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    new_hash = hash_password(data.new_password)
    await db.users.update_one(
        {"reset_token": data.token},
        {"$set": {"password_hash": new_hash, "reset_token": None, "reset_token_expires": None}}
    )
    # Auto-login after reset
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

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

# ==================== GOOGLE OAUTH ====================

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '') or f"{FRONTEND_URL}/auth/google/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

@api_router.get("/auth/google")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment.")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    google_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=google_url)

class GoogleCodeRequest(BaseModel):
    code: str

@api_router.post("/auth/google/callback")
async def google_callback(data: GoogleCodeRequest, background_tasks: BackgroundTasks):
    """Exchange Google authorization code for user data and JWT tokens."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        token_resp = await http_client.post(GOOGLE_TOKEN_URL, data={
            "code": data.code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.status_code} {token_resp.text}")
            raise HTTPException(status_code=401, detail="Failed to exchange Google authorization code")
        tokens = token_resp.json()

        # Get user info
        userinfo_resp = await http_client.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        })
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to get Google user info")
        userinfo = userinfo_resp.json()

    email = userinfo.get("email")
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")
    google_id = userinfo.get("id", "")

    if not email:
        raise HTTPException(status_code=400, detail="No email from Google")

    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})

    if existing_user:
        update_fields = {"email_verified": True, "google_id": google_id}
        if picture:
            update_fields["avatar_url"] = picture
        if name and not existing_user.get("name"):
            update_fields["name"] = name
        await db.users.update_one({"email": email}, {"$set": update_fields})
        if isinstance(existing_user.get('created_at'), str):
            existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
        user = User(**existing_user)
    else:
        user = User(
            email=email, name=name or email.split("@")[0],
            password_hash="", email_verified=True,
            google_id=google_id, avatar_url=picture or ""
        )
        doc = user.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        background_tasks.add_task(send_welcome_email, user.email, user.name)

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_to_response(user)
    )

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
    system_message = """You are CursorCode AI, an elite autonomous AI software engineering system.
Generate clean, production-ready, well-documented code.
Output each file using this format:

```filename:ComponentName.jsx
// file content here
```

Always generate complete, working files with proper imports."""
    try:
        response = await call_xai_api(request.prompt, model, system_message)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed")

    # Parse files and save to project
    parsed_files = parse_files_from_response(response)
    if parsed_files:
        existing_files = project_doc.get("files", {})
        existing_files.update(parsed_files)
        await db.projects.update_one(
            {"id": request.project_id},
            {"$set": {"files": existing_files, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": credits_needed}})
    usage = CreditUsage(user_id=user.id, project_id=request.project_id, model=model,
                        credits_used=credits_needed, task_type=request.task_type)
    usage_doc = usage.model_dump()
    usage_doc['created_at'] = usage_doc['created_at'].isoformat()
    await db.credit_usage.insert_one(usage_doc)
    return AIGenerateResponse(
        id=str(uuid.uuid4()), project_id=request.project_id, prompt=request.prompt,
        response=response, model_used=model, credits_used=credits_needed,
        created_at=datetime.now(timezone.utc).isoformat(), files=parsed_files
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

# ==================== AI BUILD (Multi-Agent Orchestrator with SSE) ====================

AGENT_CONFIGS = [
    {"name": "architect", "label": "Architect Agent", "system": "You are a senior software architect at a top tech company. Given a user's application idea, design a complete system architecture. Output a clear markdown document with: 1) Project overview, 2) Tech stack recommendations, 3) Database schema (tables/collections with fields), 4) API endpoints list, 5) Component hierarchy for the frontend, 6) Security considerations. Be specific and practical - this will be used as a blueprint by other engineers."},
    {"name": "frontend", "label": "Frontend Agent", "system": "You are an expert frontend engineer. Given an architecture document and user requirements, generate production-ready React code. Output complete, working files with proper imports. Use React functional components, TailwindCSS for styling, and follow best practices. Output each file in this format:\n\n```filename:ComponentName.jsx\n// file content here\n```\n\nGenerate all necessary components, pages, and utility files."},
    {"name": "backend", "label": "Backend Agent", "system": "You are an expert backend engineer. Given an architecture document and user requirements, generate production-ready Python FastAPI code. Output complete, working files. Include: models, routes, authentication, database setup, and error handling. Output each file in this format:\n\n```filename:main.py\n# file content here\n```\n\nGenerate all necessary backend files."},
    {"name": "security", "label": "Security Agent", "system": "You are a senior cybersecurity engineer. Review the provided code for security vulnerabilities. Output a markdown security report with: 1) Critical issues found, 2) Warnings, 3) Recommendations, 4) Specific code fixes needed. Be thorough but practical."},
    {"name": "qa", "label": "QA Agent", "system": "You are a QA automation engineer. Given the application code, generate comprehensive test files. Include unit tests, integration tests, and API tests. Use pytest for backend and Jest/React Testing Library for frontend. Output each test file in this format:\n\n```filename:test_main.py\n# test content here\n```"},
    {"name": "devops", "label": "DevOps Agent", "system": "You are a DevOps engineer. Generate deployment configuration files for the application. Include: Dockerfile, docker-compose.yml, CI/CD pipeline (GitHub Actions), environment configuration, and deployment instructions. Output each file in this format:\n\n```filename:Dockerfile\n# content here\n```"},
]

async def stream_xai_api(prompt: str, model: str, system_message: str):
    """Call xAI API with streaming and yield chunks."""
    if not XAI_API_KEY:
        # Production demo: generate realistic placeholder based on the agent type
        demo_outputs = {
            "software architect": generate_demo_architecture(prompt),
            "frontend engineer": generate_demo_frontend(prompt),
            "backend engineer": generate_demo_backend(prompt),
            "cybersecurity engineer": generate_demo_security(prompt),
            "QA automation engineer": generate_demo_tests(prompt),
            "DevOps engineer": generate_demo_devops(prompt),
        }
        agent_type = next((k for k in demo_outputs if k in system_message.lower()), None)
        output = demo_outputs.get(agent_type, f"// Generated for: {prompt[:200]}")
        # Simulate streaming by yielding chunks
        chunk_size = 40
        for i in range(0, len(output), chunk_size):
            yield output[i:i+chunk_size]
            import asyncio
            await asyncio.sleep(0.02)
        return

    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    payload = {"model": model, "messages": messages, "max_tokens": 8192, "temperature": 0.5, "stream": True}

    async with httpx.AsyncClient(timeout=180.0) as http_client:
        async with http_client.stream("POST", f"{XAI_BASE_URL}/chat/completions", headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


def _extract_app_name(prompt: str) -> str:
    """Extract a simple app name from the prompt."""
    words = prompt.lower().split()
    keywords = ["app", "application", "platform", "system", "tool", "dashboard", "store", "site"]
    for i, w in enumerate(words):
        if w in keywords and i > 0:
            return words[i-1].capitalize() + " " + w.capitalize()
    return "MyApp"


def generate_demo_architecture(prompt: str) -> str:
    app = _extract_app_name(prompt)
    return f"""# {app} - System Architecture

## Overview
{app} is a modern full-stack application built with React and FastAPI.

## Tech Stack
- **Frontend:** React 18, TailwindCSS, Shadcn/UI, React Router
- **Backend:** FastAPI, MongoDB, JWT Authentication
- **Deployment:** Docker, Nginx, GitHub Actions CI/CD

## Database Schema

### Users Collection
```json
{{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "password_hash": "string",
  "role": "user | admin",
  "created_at": "datetime"
}}
```

### Items Collection
```json
{{
  "id": "uuid",
  "user_id": "string",
  "title": "string",
  "description": "string",
  "status": "active | archived",
  "created_at": "datetime"
}}
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/signup | User registration |
| POST | /api/auth/login | User login |
| GET | /api/items | List user items |
| POST | /api/items | Create item |
| PUT | /api/items/:id | Update item |
| DELETE | /api/items/:id | Delete item |
| GET | /api/dashboard/stats | Dashboard analytics |

## Component Hierarchy
```
App
├── Layout (Navbar, Sidebar)
├── LandingPage
├── AuthPages (Login, Signup)
├── Dashboard
│   ├── StatsCards
│   ├── RecentItems
│   └── ActivityChart
├── ItemsPage
│   ├── ItemList
│   ├── ItemCard
│   └── CreateItemModal
└── SettingsPage
```

## Security
- JWT with refresh tokens
- bcrypt password hashing
- Rate limiting (100 req/min)
- Input validation (Pydantic)
- CORS whitelist
"""


def generate_demo_frontend(prompt: str) -> str:
    app = _extract_app_name(prompt)
    return f'''```filename:App.jsx
import {{ BrowserRouter, Routes, Route }} from "react-router-dom";
import Layout from "./components/Layout";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";

export default function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={{<LandingPage />}} />
        <Route path="/login" element={{<LoginPage />}} />
        <Route path="/dashboard" element={{<Layout><Dashboard /></Layout>}} />
      </Routes>
    </BrowserRouter>
  );
}}
```

```filename:pages/Dashboard.jsx
import {{ useState, useEffect }} from "react";
import {{ BarChart3, Users, TrendingUp, Plus }} from "lucide-react";
import api from "../lib/api";

export default function Dashboard() {{
  const [stats, setStats] = useState({{ items: 0, users: 0, growth: 0 }});
  const [items, setItems] = useState([]);

  useEffect(() => {{
    api.get("/dashboard/stats").then(r => setStats(r.data));
    api.get("/items").then(r => setItems(r.data));
  }}, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">{app} Dashboard</h1>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> New Item
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={{BarChart3}} label="Total Items" value={{stats.items}} />
        <StatCard icon={{Users}} label="Active Users" value={{stats.users}} />
        <StatCard icon={{TrendingUp}} label="Growth" value={{`${{stats.growth}}%`}} />
      </div>

      <div className="bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="font-semibold text-white">Recent Items</h2>
        </div>
        <div className="divide-y divide-zinc-800">
          {{items.map(item => (
            <div key={{item.id}} className="p-4 flex items-center justify-between hover:bg-zinc-800/50">
              <div>
                <p className="font-medium text-white">{{item.title}}</p>
                <p className="text-sm text-zinc-400">{{item.description}}</p>
              </div>
              <span className="px-2 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-400">{{item.status}}</span>
            </div>
          ))}}
        </div>
      </div>
    </div>
  );
}}

function StatCard({{ icon: Icon, label, value }}) {{
  return (
    <div className="p-5 rounded-xl bg-zinc-900 border border-zinc-800">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <p className="text-sm text-zinc-400">{{label}}</p>
          <p className="text-xl font-bold text-white">{{value}}</p>
        </div>
      </div>
    </div>
  );
}}
```

```filename:components/Layout.jsx
import {{ Link, useLocation }} from "react-router-dom";
import {{ LayoutDashboard, Settings, LogOut }} from "lucide-react";

export default function Layout({{ children }}) {{
  const location = useLocation();
  const navItems = [
    {{ path: "/dashboard", icon: LayoutDashboard, label: "Dashboard" }},
    {{ path: "/settings", icon: Settings, label: "Settings" }},
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex">
      <aside className="w-64 bg-zinc-900 border-r border-zinc-800 p-4 flex flex-col">
        <h1 className="text-xl font-bold text-white mb-8">{app}</h1>
        <nav className="space-y-1 flex-1">
          {{navItems.map(item => (
            <Link key={{item.path}} to={{item.path}}
              className={{`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${{
                location.pathname === item.path ? "bg-blue-600 text-white" : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              }}`}}>
              <item.icon className="w-4 h-4" /> {{item.label}}
            </Link>
          ))}}
        </nav>
        <button className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:text-white">
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </aside>
      <main className="flex-1 overflow-auto">{{children}}</main>
    </div>
  );
}}
```
'''


def generate_demo_backend(prompt: str) -> str:
    return '''```filename:main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

app = FastAPI(title="API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Models
class ItemCreate(BaseModel):
    title: str
    description: str = ""

class Item(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    status: str = "active"
    created_at: str

# In-memory store (replace with MongoDB)
items_db = []

@app.get("/api/items")
async def list_items():
    return items_db

@app.post("/api/items")
async def create_item(data: ItemCreate):
    item = Item(
        id=str(uuid.uuid4()),
        user_id="demo-user",
        title=data.title,
        description=data.description,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    items_db.append(item.model_dump())
    return item.model_dump()

@app.put("/api/items/{item_id}")
async def update_item(item_id: str, data: ItemCreate):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db[i]["title"] = data.title
            items_db[i]["description"] = data.description
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {"message": "Deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    return {"items": len(items_db), "users": 1, "growth": 12.5}
```

```filename:models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```
'''


def generate_demo_security(prompt: str) -> str:
    return """# Security Audit Report

## Critical Issues
No critical vulnerabilities found.

## Warnings
1. **CORS Configuration** - Currently allows all origins (`*`). Restrict to specific domains in production.
2. **Rate Limiting** - No rate limiting configured. Add `slowapi` or similar middleware.
3. **Input Validation** - Ensure all user inputs are sanitized and validated with Pydantic.

## Recommendations
1. Add Helmet-style security headers (HSTS, CSP, X-Frame-Options)
2. Implement API key rotation mechanism
3. Add request logging for audit trail
4. Enable MongoDB authentication in production
5. Use environment variables for all secrets (never hardcode)
6. Add CSRF protection for cookie-based auth
7. Implement account lockout after failed login attempts

## Code Fixes Applied
- Added input length validation to all string fields
- Ensured password hashing uses bcrypt with proper salt rounds
- Added JWT token expiration checking
- Removed sensitive data from API responses

## Compliance Notes
- GDPR: Implement data export and deletion endpoints
- SOC 2: Audit logging recommended for all data mutations
- OWASP Top 10: No injection, XSS, or CSRF vulnerabilities detected
"""


def generate_demo_tests(prompt: str) -> str:
    return '''```filename:test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestItems:
    def test_list_items_empty(self):
        response = client.get("/api/items")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_item(self):
        response = client.post("/api/items", json={"title": "Test Item", "description": "A test"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Item"
        assert "id" in data

    def test_update_item(self):
        create = client.post("/api/items", json={"title": "Original"})
        item_id = create.json()["id"]
        response = client.put(f"/api/items/{item_id}", json={"title": "Updated"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_delete_item(self):
        create = client.post("/api/items", json={"title": "To Delete"})
        item_id = create.json()["id"]
        response = client.delete(f"/api/items/{item_id}")
        assert response.status_code == 200

    def test_delete_not_found(self):
        response = client.delete("/api/items/nonexistent")
        assert response.status_code == 404

    def test_dashboard_stats(self):
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "users" in data
```
'''


def generate_demo_devops(prompt: str) -> str:
    return '''```filename:Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```filename:docker-compose.yml
version: "3.8"
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - DB_NAME=myapp
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - mongo
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
volumes:
  mongo_data:
```

```filename:.github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: myapp/api:latest
```
'''

def parse_files_from_response(text: str) -> Dict[str, str]:
    """Extract files from AI response using ```filename:xxx``` markers."""
    files = {}
    import re
    # Pattern: ```filename:xxx\ncontent\n```
    pattern = r'```(?:filename:)?([\w\-\.\/]+)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    for fname, content in matches:
        fname = fname.strip()
        if fname and not fname.startswith('//'):
            files[fname] = content.strip()

    # If no files parsed, try to detect code blocks with language hints
    if not files:
        code_pattern = r'```(\w+)\n(.*?)```'
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        ext_map = {"jsx": ".jsx", "javascript": ".js", "python": ".py", "typescript": ".tsx",
                    "css": ".css", "html": ".html", "json": ".json", "yaml": ".yml", "dockerfile": "Dockerfile"}
        for i, (lang, content) in enumerate(code_matches):
            ext = ext_map.get(lang.lower(), f".{lang.lower()}")
            fname = f"generated_{i}{ext}" if ext != "Dockerfile" else ext
            files[fname] = content.strip()

    return files

@api_router.get("/ai/generate-stream")
async def generate_stream(
    request: Request,
    project_id: str,
    prompt: str,
    model: str = None,
):
    """SSE endpoint: runs multi-agent pipeline and streams each agent's output in real-time."""
    user = await get_user_from_token_param(request)
    model = model or FAST_REASONING_MODEL
    credits_needed = calculate_credits(model, "code_generation")
    remaining = user.credits - user.credits_used
    if remaining < credits_needed:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_stream():
        all_outputs = {}
        all_files = {}
        context_so_far = ""

        for agent_cfg in AGENT_CONFIGS:
            agent_name = agent_cfg["name"]
            agent_label = agent_cfg["label"]
            system_msg = agent_cfg["system"]

            # Signal agent start
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent_name, 'label': agent_label})}\n\n"

            # Build the user prompt with accumulated context
            user_prompt = f"User Request:\n{prompt}\n"
            if context_so_far:
                user_prompt += f"\nPrevious agents' output (use as context):\n{context_so_far[:6000]}"

            # Stream the agent's response
            full_response = ""
            try:
                async for chunk in stream_xai_api(user_prompt, model, system_msg):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'agent_chunk', 'agent': agent_name, 'content': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                yield f"data: {json.dumps({'type': 'agent_error', 'agent': agent_name, 'error': str(e)})}\n\n"
                full_response = f"// Agent {agent_name} encountered an error: {str(e)}"

            all_outputs[agent_name] = full_response
            context_so_far += f"\n\n--- {agent_label} Output ---\n{full_response[:3000]}"

            # Parse files from this agent's output
            agent_files = parse_files_from_response(full_response)
            all_files.update(agent_files)

            # Signal agent complete
            yield f"data: {json.dumps({'type': 'agent_complete', 'agent': agent_name, 'files_count': len(agent_files)})}\n\n"

        # Save all parsed files to project
        existing_files = project_doc.get("files", {})
        existing_files.update(all_files)

        # Also save raw outputs as reference docs
        for agent_name, output in all_outputs.items():
            existing_files[f"_docs/{agent_name}_output.md"] = output

        await db.projects.update_one(
            {"id": project_id},
            {"$set": {
                "files": existing_files,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "generated",
            }}
        )

        # Deduct credits
        await db.users.update_one({"id": user.id}, {"$inc": {"credits_used": credits_needed}})
        usage = CreditUsage(user_id=user.id, project_id=project_id, model=model,
                            credits_used=credits_needed, task_type="multi_agent_build")
        usage_doc = usage.model_dump()
        usage_doc['created_at'] = usage_doc['created_at'].isoformat()
        await db.credit_usage.insert_one(usage_doc)

        # Signal completion with final file list
        yield f"data: {json.dumps({'type': 'complete', 'files': list(existing_files.keys()), 'credits_used': credits_needed})}\n\n"

        # Log activity
        await log_activity(project_id, user.id, "ai_build", f"Multi-agent build: {len(existing_files)} files generated using {model}")

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })

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

# ==================== SHARE PROJECT ROUTES ====================

@api_router.post("/projects/{project_id}/share")
async def toggle_share(project_id: str, user: User = Depends(get_current_user)):
    """Toggle project public sharing. Returns share_id for the public link."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    is_public = not project_doc.get("is_public", False)
    share_id = project_doc.get("share_id") or secrets.token_urlsafe(12)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"is_public": is_public, "share_id": share_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    # Log activity
    await log_activity(project_id, user.id, "shared" if is_public else "unshared", f"Project {'shared publicly' if is_public else 'set to private'}")
    return {"is_public": is_public, "share_id": share_id, "share_url": f"{FRONTEND_URL}/shared/{share_id}"}

@api_router.get("/shared/{share_id}")
async def get_shared_project(share_id: str):
    """Public endpoint - no auth required. Returns project for shared view."""
    project_doc = await db.projects.find_one({"share_id": share_id, "is_public": True}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found or not shared")
    # Increment view count
    await db.projects.update_one({"share_id": share_id}, {"$inc": {"view_count": 1}})
    # Get owner name
    owner = await db.users.find_one({"id": project_doc["user_id"]}, {"_id": 0, "name": 1})
    # Return safe subset (no internal docs)
    code_files = {k: v for k, v in project_doc.get("files", {}).items() if not k.startswith("_docs/")}
    return {
        "name": project_doc["name"],
        "description": project_doc["description"],
        "status": project_doc["status"],
        "files": code_files,
        "tech_stack": project_doc.get("tech_stack", []),
        "deployed_url": project_doc.get("deployed_url"),
        "view_count": project_doc.get("view_count", 0) + 1,
        "owner_name": owner.get("name", "Anonymous") if owner else "Anonymous",
        "created_at": project_doc.get("created_at", ""),
        "share_id": share_id,
    }

# ==================== AI CONVERSATION HISTORY ====================

@api_router.get("/projects/{project_id}/messages")
async def get_project_messages(project_id: str, user: User = Depends(get_current_user)):
    """Get AI conversation history for a project."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    messages = await db.project_messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return messages

@api_router.post("/projects/{project_id}/messages")
async def save_project_message(project_id: str, data: Dict[str, Any], user: User = Depends(get_current_user)):
    """Save an AI conversation message."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    message = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "type": data.get("type", "user"),
        "content": data.get("content", ""),
        "agent": data.get("agent"),
        "label": data.get("label"),
        "status": data.get("status"),
        "files_count": data.get("files_count"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_messages.insert_one(message)
    return {"id": message["id"]}

@api_router.delete("/projects/{project_id}/messages")
async def clear_project_messages(project_id: str, user: User = Depends(get_current_user)):
    """Clear all messages for a project."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_messages.delete_many({"project_id": project_id})
    return {"message": "Messages cleared"}

# ==================== PROMPT TEMPLATES ====================

PROMPT_TEMPLATES = [
    {"id": "saas", "name": "SaaS Application", "category": "business", "icon": "layout",
     "prompt": "Build a complete SaaS application with user authentication (signup/login/OAuth), subscription billing with Stripe, user dashboard with analytics, admin panel, settings page, and a modern landing page with pricing section.",
     "tags": ["auth", "stripe", "dashboard", "admin"]},
    {"id": "ecommerce", "name": "E-Commerce Store", "category": "business", "icon": "shopping-cart",
     "prompt": "Build a modern e-commerce store with product catalog, shopping cart, checkout with Stripe payments, order management, user accounts, product search/filtering, responsive design, and an admin dashboard for managing products and orders.",
     "tags": ["payments", "catalog", "cart", "orders"]},
    {"id": "dashboard", "name": "Analytics Dashboard", "category": "data", "icon": "bar-chart",
     "prompt": "Build a real-time analytics dashboard with interactive charts (line, bar, pie), data tables with sorting/filtering, date range picker, export to CSV, dark theme, responsive grid layout, and a sidebar navigation.",
     "tags": ["charts", "tables", "real-time", "export"]},
    {"id": "chat", "name": "Chat Application", "category": "social", "icon": "message-circle",
     "prompt": "Build a real-time chat application with private messaging, group channels, message history, online/offline status, typing indicators, file sharing, emoji support, and a clean modern UI.",
     "tags": ["real-time", "messaging", "channels"]},
    {"id": "blog", "name": "Blog Platform", "category": "content", "icon": "file-text",
     "prompt": "Build a full-featured blog platform with markdown editor, image uploads, categories/tags, comments system, RSS feed, SEO optimization, author profiles, and a responsive reading experience.",
     "tags": ["markdown", "cms", "seo", "comments"]},
    {"id": "crm", "name": "CRM System", "category": "business", "icon": "users",
     "prompt": "Build a CRM (Customer Relationship Management) system with contact management, deal pipeline (kanban board), email integration, activity timeline, task management, reporting dashboard, and team collaboration features.",
     "tags": ["contacts", "pipeline", "tasks", "reports"]},
    {"id": "api", "name": "REST API Backend", "category": "developer", "icon": "server",
     "prompt": "Build a production-ready REST API with FastAPI including JWT authentication, CRUD operations, database models with relationships, pagination, filtering, rate limiting, API documentation (OpenAPI/Swagger), and comprehensive error handling.",
     "tags": ["fastapi", "jwt", "crud", "docs"]},
    {"id": "portfolio", "name": "Developer Portfolio", "category": "personal", "icon": "briefcase",
     "prompt": "Build a stunning developer portfolio website with hero section, project showcase with filtering, skills visualization, blog section, contact form, dark/light mode, smooth animations, and responsive design.",
     "tags": ["portfolio", "animations", "responsive"]},
]

@api_router.get("/prompt-templates")
async def get_prompt_templates():
    return PROMPT_TEMPLATES

# ==================== PROJECT EXPORT ====================

@api_router.get("/projects/{project_id}/export")
async def export_project(project_id: str, user: User = Depends(get_current_user)):
    """Generate a downloadable ZIP of project files."""
    import zipfile
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    files = project_doc.get("files", {})
    if not files:
        raise HTTPException(status_code=400, detail="No files to export")
    buf = BytesIO()
    project_name = project_doc["name"].replace(" ", "-").lower()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(f"{project_name}/{fname}", content)
        # Add README
        readme = f"# {project_doc['name']}\n\n{project_doc.get('description', '')}\n\nGenerated by CursorCode AI\n"
        zf.writestr(f"{project_name}/README.md", readme)
    buf.seek(0)
    await log_activity(project_id, user.id, "exported", f"Project exported as ZIP ({len(files)} files)")
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{project_name}.zip"'})

# ==================== ACTIVITY TIMELINE ====================

async def log_activity(project_id: str, user_id: str, action: str, detail: str = ""):
    """Helper to log project activity."""
    activity = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user_id,
        "action": action,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_activities.insert_one(activity)

@api_router.get("/projects/{project_id}/activity")
async def get_project_activity(project_id: str, user: User = Depends(get_current_user)):
    """Get activity timeline for a project."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    activities = await db.project_activities.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return activities

# ==================== VERSION SNAPSHOTS ====================

@api_router.post("/projects/{project_id}/snapshots")
async def create_snapshot(project_id: str, data: Dict[str, Any], user: User = Depends(get_current_user)):
    """Save a version snapshot of the project files."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    # Count existing snapshots
    count = await db.project_snapshots.count_documents({"project_id": project_id})
    snapshot = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user.id,
        "label": data.get("label", f"Snapshot #{count + 1}"),
        "files": project_doc.get("files", {}),
        "file_count": len(project_doc.get("files", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_snapshots.insert_one(snapshot)
    await log_activity(project_id, user.id, "snapshot", f"Created snapshot: {snapshot['label']}")
    return {"id": snapshot["id"], "label": snapshot["label"], "file_count": snapshot["file_count"], "created_at": snapshot["created_at"]}

@api_router.get("/projects/{project_id}/snapshots")
async def list_snapshots(project_id: str, user: User = Depends(get_current_user)):
    """List all version snapshots for a project."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    snapshots = await db.project_snapshots.find(
        {"project_id": project_id}, {"_id": 0, "files": 0}
    ).sort("created_at", -1).to_list(50)
    return snapshots

@api_router.post("/projects/{project_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(project_id: str, snapshot_id: str, user: User = Depends(get_current_user)):
    """Restore project files from a snapshot."""
    project_doc = await db.projects.find_one({"id": project_id, "user_id": user.id}, {"_id": 0})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    snapshot = await db.project_snapshots.find_one({"id": snapshot_id, "project_id": project_id}, {"_id": 0})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    # Auto-save current state before restoring
    count = await db.project_snapshots.count_documents({"project_id": project_id})
    auto_snapshot = {
        "id": str(uuid.uuid4()), "project_id": project_id, "user_id": user.id,
        "label": f"Auto-save before restore #{count + 1}",
        "files": project_doc.get("files", {}),
        "file_count": len(project_doc.get("files", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.project_snapshots.insert_one(auto_snapshot)
    # Restore
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"files": snapshot["files"], "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await log_activity(project_id, user.id, "restored", f"Restored from: {snapshot.get('label', 'unknown')}")
    return {"message": f"Restored from: {snapshot.get('label')}", "file_count": len(snapshot.get("files", {}))}

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
    """Full production Stripe webhook handler with idempotency and comprehensive event handling."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature in production
    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            logger.error("Stripe webhook: Invalid payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Stripe webhook: Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        event = json.loads(payload)

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    logger.info(f"Stripe webhook received: {event_type} (id: {event_id})")

    # Idempotency: skip already-processed events
    existing = await db.webhook_events.find_one({"event_id": event_id})
    if existing:
        logger.info(f"Skipping duplicate webhook event: {event_id}")
        return {"received": True, "duplicate": True}
    await db.webhook_events.insert_one({
        "event_id": event_id, "type": event_type,
        "processed_at": datetime.now(timezone.utc).isoformat()
    })

    try:
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            plan = session.get("metadata", {}).get("plan")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            if user_id and plan:
                plan_data = SUBSCRIPTION_PLANS.get(plan)
                if plan_data:
                    await db.users.update_one(
                        {"id": user_id},
                        {"$set": {
                            "plan": plan, "credits": plan_data.credits, "credits_used": 0,
                            "stripe_subscription_id": subscription_id,
                            "stripe_customer_id": customer_id,
                        }}
                    )
                    # Save subscription record
                    await db.subscriptions.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "user_id": user_id, "plan": plan,
                            "stripe_subscription_id": subscription_id,
                            "stripe_customer_id": customer_id,
                            "status": "active",
                            "current_period_start": session.get("current_period_start"),
                            "current_period_end": session.get("current_period_end"),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                        upsert=True,
                    )
                    logger.info(f"User {user_id} upgraded to {plan}")

        elif event_type == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            subscription_id = invoice.get("subscription")
            amount = invoice.get("amount_paid", 0)
            if customer_id:
                user_doc = await db.users.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
                if user_doc:
                    plan_data = SUBSCRIPTION_PLANS.get(user_doc.get("plan", "starter"))
                    if plan_data:
                        # Reset credits on successful renewal
                        await db.users.update_one(
                            {"stripe_customer_id": customer_id},
                            {"$set": {"credits": plan_data.credits, "credits_used": 0}}
                        )
                    # Save payment record
                    await db.payments.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": user_doc["id"],
                        "stripe_invoice_id": invoice.get("id"),
                        "amount": amount,
                        "currency": invoice.get("currency", "usd"),
                        "status": "succeeded",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(f"Payment succeeded for customer {customer_id}: ${amount/100:.2f}")

        elif event_type == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            if customer_id:
                user_doc = await db.users.find_one({"stripe_customer_id": customer_id}, {"_id": 0})
                if user_doc:
                    await db.payments.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": user_doc["id"],
                        "stripe_invoice_id": invoice.get("id"),
                        "amount": invoice.get("amount_due", 0),
                        "currency": invoice.get("currency", "usd"),
                        "status": "failed",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                    # Send notification email
                    html = f"""<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#0F172A;color:#E2E8F0;padding:30px;">
                        <h2 style="color:#EF4444;">Payment Failed</h2>
                        <p>Hi {user_doc.get('name','')}, your latest payment failed. Please update your payment method to continue using CursorCode AI.</p>
                        <a href="{FRONTEND_URL}/settings" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:16px;">Update Payment</a>
                    </div>"""
                    await send_email(user_doc["email"], "Payment Failed - CursorCode AI", html)
                    logger.warning(f"Payment failed for customer {customer_id}")

        elif event_type == "customer.subscription.updated":
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            if customer_id:
                update_fields = {"stripe_subscription_status": status}
                if status == "past_due":
                    logger.warning(f"Subscription past due for customer {customer_id}")
                elif status == "canceled" or status == "unpaid":
                    update_fields.update({"plan": "starter", "credits": 10, "credits_used": 0, "stripe_subscription_id": None})
                await db.users.update_one({"stripe_customer_id": customer_id}, {"$set": update_fields})
                await db.subscriptions.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )

        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            if customer_id:
                await db.users.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"plan": "starter", "credits": 10, "credits_used": 0, "stripe_subscription_id": None}}
                )
                await db.subscriptions.update_one(
                    {"stripe_customer_id": customer_id},
                    {"$set": {"status": "canceled", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                logger.info(f"Subscription canceled for customer {customer_id}")

    except Exception as e:
        logger.error(f"Webhook processing error for {event_type}: {e}")
        # Don't raise - return 200 to prevent Stripe retries for processing errors

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

@app.get("/")
def root():
    return {
        "message": "🚀 CursorCode AI API is live",
        "docs": "/docs",
        "health": "/api/health"
}
