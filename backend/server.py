import os
import jwt
import time
import stripe
import requests
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from passlib.context import CryptContext
from pymongo import MongoClient

from dotenv import load_dotenv
from openai import OpenAI

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# IMPORTANT: do NOT use backend.orchestrator
from orchestrator import stream_orchestration_sse

# =====================================================
# LOAD ENVIRONMENT
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

GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

XAI_API_KEY = os.getenv("XAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

# =====================================================
# DATABASE
# =====================================================
try:
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]

    users_collection = db["users"]
    analytics_collection = db["analytics"]
    usage_collection = db["ai_usage"]

    logger.info("MongoDB connected")

except Exception as e:
    logger.error("MongoDB connection failed")
    raise e

# =====================================================
# AI CLIENT (xAI Grok)
# =====================================================
ai_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

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
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# UTILS
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


def send_email(to_email, subject, content):
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid disabled")
        return

    try:
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=to_email,
            subject=subject,
            html_content=content,
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)

    except Exception as e:
        logger.error(f"Email error: {e}")

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


class CodeRequest(BaseModel):
    prompt: str
    language: str = "python"


class CodeInput(BaseModel):
    code: str

# =====================================================
# AUTH HELPERS
# =====================================================
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
# AUTH ROUTES
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
        "plan": "free",
    }

    users_collection.insert_one(user)

    access = create_access_token({"email": data.email})
    refresh = create_refresh_token({"email": data.email})

    send_email(data.email, "Welcome to CursorCode AI", "<h2>Welcome</h2>")

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {"name": data.name, "email": data.email},
    }


@app.post("/api/auth/login")
def login(data: LoginRequest):

    user = users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token({"email": data.email})
    refresh = create_refresh_token({"email": data.email})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {"name": user["name"], "email": user["email"]},
    }


@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return {"name": user["name"], "email": user["email"]}

# =====================================================
# GITHUB OAUTH
# =====================================================
@app.get("/api/auth/github")
def github_login():

    redirect = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={FRONTEND_URL}/github/callback"
    )

    return {"url": redirect}


@app.get("/api/auth/github/callback")
def github_callback(code: str):

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
    )

    token_json = token_res.json()

    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(400, "GitHub auth failed")

    user_res = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_data = user_res.json()

    email = f"{user_data['login']}@github.com"

    user = users_collection.find_one({"email": email})

    if not user:
        users_collection.insert_one(
            {"name": user_data["login"], "email": email, "created": datetime.utcnow()}
        )

    access = create_access_token({"email": email})
    refresh = create_refresh_token({"email": email})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {"name": user_data["login"], "email": email},
    }

# =====================================================
# AI CODE ENGINE
# =====================================================
@app.post("/api/ai/generate")
def generate_code(data: CodeRequest, user=Depends(get_current_user)):

    try:

        prompt = f"Generate production ready {data.language} code.\n\n{data.prompt}"

        response = ai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are an elite software engineer"},
                {"role": "user", "content": prompt},
            ],
        )

        code = response.choices[0].message.content

        usage_collection.insert_one(
            {"user": user["email"], "time": datetime.utcnow(), "type": "generate"}
        )

        return {"code": code}

    except Exception as e:

        logger.error(e)

        raise HTTPException(500, "AI generation failed")

# =====================================================
# STREAM PROJECT ORCHESTRATION
# =====================================================
@app.get("/api/project/stream")
async def project_stream(project_id: str, prompt: str):

    generator = stream_orchestration_sse(
        project_id=project_id,
        prompt=prompt,
        api_key=XAI_API_KEY,
    )

    return StreamingResponse(generator, media_type="text/event-stream")

# =====================================================
# STRIPE PAYMENTS
# =====================================================
@app.post("/api/payments/create-checkout")
def create_checkout(user=Depends(get_current_user)):

    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe not configured")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "CursorCode AI Pro"},
                    "unit_amount": 2000,
                },
                "quantity": 1,
            }
        ],
        success_url=f"{FRONTEND_URL}/success",
        cancel_url=f"{FRONTEND_URL}/cancel",
    )

    return {"url": session.url}

# =====================================================
# ANALYTICS
# =====================================================
@app.get("/api/analytics")
def analytics():

    total_users = users_collection.count_documents({})
    ai_calls = usage_collection.count_documents({})

    return {"total_users": total_users, "ai_requests": ai_calls}

# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "time": time.time(),
    }
