from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import os

# ==================== USER MODELS ====================

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

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

# ==================== PROJECT MODELS ====================

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

# ==================== AI MODELS ====================

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

# ==================== DEPLOYMENT MODELS ====================

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

# ==================== GITHUB MODELS ====================

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

# ==================== STRIPE MODELS ====================

class SubscriptionPlan(BaseModel):
    name: str
    price: int
    credits: int
    features: List[str]
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None

class CheckoutRequest(BaseModel):
    plan: str

# ==================== AUTH MODELS ====================

class TwoFAVerifyRequest(BaseModel):
    code: str

class TwoFALoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class GoogleCodeRequest(BaseModel):
    code: str

# ==================== SUBSCRIPTION PLANS ====================

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
