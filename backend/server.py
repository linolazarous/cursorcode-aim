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
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from urllib.parse import urlencode
import re

# ==================== CONFIGURATION ====================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'cursorcode-secret-key-change-in-production')
JWT_REFRESH_SECRET = os.environ.get('JWT_REFRESH_SECRET', 'cursorcode-refresh-secret-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# xAI Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = os.environ.get('DEFAULT_XAI_MODEL', 'grok-4-latest')
FAST_REASONING_MODEL = os.environ.get('FAST_REASONING_MODEL', 'grok-4-fast-reasoning')
FAST_NON_REASONING_MODEL = os.environ.get('FAST_NON_REASONING_MODEL', 'grok-4-fast-non-reasoning')

# Stripe Configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'hello@cursorcode.app')

# OAuth Configuration
GITHUB_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.cursorcode.app')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '') or f"{FRONTEND_URL}/auth/google/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# ==================== APP INITIALIZATION ====================

app = FastAPI(title="CursorCode AI API", version="2.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.cursorcode.app",
        "https://cursorcode.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ==================== ROOT ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "message": "CursorCode AI API is running",
        "version": "2.0.0",
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mongodb": "connected" if mongo_url else "not configured",
        "stripe": "configured" if stripe.api_key else "not configured",
        "sendgrid": "configured" if SENDGRID_API_KEY else "not configured"
    }

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
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    onboarding_completed: bool = False
    totp_secret: Optional[str] = None
    totp_enabled: bool = False
    totp_backup_codes: Optional[List[str]] = None
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
    is_public: bool = False
    share_id: Optional[str] = None
    view_count: int = 0
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

class CreditUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    project_id: Optional[str] = None
    model: str
    credits_used: int
    task_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# ==================== HELPER FUNCTIONS ====================

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
        demo_response = f"""```filename:App.jsx
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
          ))}
        </div>
      </div>
    </div>
  );
}}
```"""
        return demo_response
    
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

# ==================== 2FA ROUTES ====================

class TwoFAVerifyRequest(BaseModel):
    code: str

@api_router.post("/auth/2fa/enable")
async def enable_2fa(user: User = Depends(get_current_user)):
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="CursorCode AI")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = f"data:image/png;base64,{b64encode(buf.getvalue()).decode()}"
    
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"totp_secret": secret, "totp_backup_codes": backup_codes}}
    )
    return {"qr_code_base64": qr_base64, "secret": secret, "backup_codes": backup_codes}

@api_router.post("/auth/2fa/verify")
async def verify_2fa(data: TwoFAVerifyRequest, user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    secret = user_doc.get("totp_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")
    
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    await db.users.update_one({"id": user.id}, {"$set": {"totp_enabled": True}})
    return {"message": "2FA enabled successfully"}

@api_router.post("/auth/2fa/disable")
async def disable_2fa(data: TwoFAVerifyRequest, user: User = Depends(get_current_user)):
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
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    user = User(**user_doc)
    
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

# ==================== GITHUB OAUTH ====================

@api_router.get("/auth/github")
async def github_login(redirect_uri: Optional[str] = None):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
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
                    {"$set": {
                        "github_id": github_user["id"],
                        "github_username": github_user["login"],
                        "github_access_token": github_token,
                        "avatar_url": github_user.get("avatar_url"),
                        "email_verified": True
                    }}
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

# ==================== GOOGLE OAUTH ====================

@api_router.get("/auth/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    
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
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    
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
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_to_response(user))

# ==================== PROJECT ROUTES ====================

@api_router.post("/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate, user: User = Depends(get_current_user)):
    project = Project(
        user_id=user.id,
        name=project_data.name,
        description=project_data.description or "",
        prompt=project_data.prompt or ""
    )
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
        "name": project_data.name,
        "description": project_data.description or "",
        "prompt": project_data.prompt or "",
        "updated_at": datetime.now(timezone.utc).isoformat()
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
```"""
    
    try:
        response = await call_xai_api(request.prompt, model, system_message)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed")
    
    files = {}
    pattern = r'```filename:([^\n]+)\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)
    for filename, content in matches:
        files[filename.strip()] = content.strip()
    
    if not files:
        alt_pattern = r'filename:\s*([^\n]+)\n```(?:[a-z]*)\n(.*?)```'
        matches = re.findall(alt_pattern, response, re.DOTALL)
        for filename, content in matches:
            files[filename.strip()] = content.strip()
    
    existing_files = project_doc.get('files', {})
    existing_files.update(files)
    await db.projects.update_one(
        {"id": request.project_id},
        {"$set": {"files": existing_files, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    credit_usage = CreditUsage(
        user_id=user.id, project_id=request.project_id,
        model=model, credits_used=credits_needed, task_type=request.task_type
    )
    usage_doc = credit_usage.model_dump()
    usage_doc['created_at'] = usage_doc['created_at'].isoformat()
    await db.credit_usage.insert_one(usage_doc)
    
    await db.users.update_one(
        {"id": user.id},
        {"$inc": {"credits_used": credits_needed}}
    )
    
    return AIGenerateResponse(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        prompt=request.prompt,
        response=response,
        model_used=model,
        credits_used=credits_needed,
        created_at=datetime.now(timezone.utc).isoformat(),
        files=files
    )

# ==================== STRIPE ROUTES ====================

@api_router.get("/stripe/plans")
async def get_plans():
    return {
        key: {
            "name": plan.name,
            "price": plan.price,
            "credits": plan.credits,
            "features": plan.features,
            "stripe_price_id": plan.stripe_price_id
        }
        for key, plan in SUBSCRIPTION_PLANS.items()
    }

@api_router.post("/stripe/create-checkout-session")
async def create_checkout_session(plan_id: str, user: User = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan or plan.price == 0:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="Plan not configured for payment")
    
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.id}
        )
        user.stripe_customer_id = customer.id
        await db.users.update_one(
            {"id": user.id},
            {"$set": {"stripe_customer_id": customer.id}}
        )
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": plan.stripe_price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/pricing",
            metadata={"user_id": user.id, "plan": plan_id}
        )
        return {"session_id": checkout_session.id, "url": checkout_session.url}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not stripe.api_key or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        plan_key = session["metadata"].get("plan")
        
        if user_id and plan_key:
            plan = SUBSCRIPTION_PLANS.get(plan_key)
            if plan:
                await db.users.update_one(
                    {"id": user_id},
                    {
                        "$set": {
                            "plan": plan_key,
                            "stripe_subscription_id": session.get("subscription"),
                            "credits": plan.credits,
                            "credits_used": 0
                        }
                    }
                )
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                price_id = subscription["items"]["data"][0]["price"]["id"]
                
                for plan_key, plan in SUBSCRIPTION_PLANS.items():
                    if plan.stripe_price_id == price_id:
                        user = await db.users.find_one({"stripe_subscription_id": subscription_id})
                        if user:
                            await db.users.update_one(
                                {"id": user["id"]},
                                {"$set": {"plan": plan_key, "credits": plan.credits}}
                            )
                        break
            except Exception as e:
                logger.error(f"Error processing invoice: {e}")
    
    return {"received": True}

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: User = Depends(get_current_user)):
    projects_count = await db.projects.count_documents({"user_id": user.id})
    usage_count = await db.credit_usage.count_documents({"user_id": user.id})
    deployments_count = await db.deployments.count_documents({"user_id": user.id}) if hasattr(db, 'deployments') else 0
    
    return {
        "projects": projects_count,
        "ai_calls": usage_count,
        "credits_remaining": user.credits - user.credits_used,
        "deployments": deployments_count,
        "plan": user.plan
    }

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

# ==================== MOUNT ROUTER & LIFECYCLE ====================

app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up CursorCode AI API...")
    await ensure_stripe_products()
    logger.info("CursorCode AI API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down CursorCode AI API...")
    client.close()
    logger.info("CursorCode AI API shutdown complete")
