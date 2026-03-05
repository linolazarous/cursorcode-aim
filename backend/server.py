import os
import jwt
import time
import stripe
import requests
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from passlib.context import CryptContext
from pymongo import MongoClient

from dotenv import load_dotenv

from openai import OpenAI

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cursorcode")


# =====================================================
# ENV VARIABLES
# =====================================================

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")

FRONTEND_URL = os.getenv("FRONTEND_URL", "*")

GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

XAI_API_KEY = os.getenv("XAI_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_XAI_MODEL", "grok-4-latest")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

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

def hash_password(password):
    return pwd_context.hash(password)


def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)


def create_access_token(data):

    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=2)

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(data):

    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=30)

    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm="HS256")


def send_email(to_email, subject, content):

    if not SENDGRID_API_KEY:
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

        logger.error(f"Email error {e}")


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
        raise HTTPException(status_code=401)

    token = auth_header.split(" ")[1]

    try:

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

        user = users_collection.find_one({"email": payload["email"]})

        if not user:
            raise HTTPException(status_code=401)

        return user

    except:

        raise HTTPException(status_code=401)


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

    send_email(
        data.email,
        "Welcome to CursorCode AI",
        "<h2>Welcome to CursorCode AI</h2>",
    )

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {"name": data.name, "email": data.email},
    }


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
        "user": {"name": user["name"], "email": user["email"]},
    }


@app.post("/api/auth/refresh")

def refresh_token(request: Request):

    token = request.headers.get("refresh-token")

    if not token:
        raise HTTPException(401)

    try:

        payload = jwt.decode(token, JWT_REFRESH_SECRET, algorithms=["HS256"])

        access = create_access_token({"email": payload["email"]})
        refresh = create_refresh_token({"email": payload["email"]})

        return {
            "access_token": access,
            "refresh_token": refresh,
        }

    except:

        raise HTTPException(401)


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

    access_token = token_res.json()["access_token"]

    user_res = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_data = user_res.json()

    email = f"{user_data['login']}@github.com"

    user = users_collection.find_one({"email": email})

    if not user:

        user = {
            "name": user_data["login"],
            "email": email,
            "created": datetime.utcnow(),
        }

        users_collection.insert_one(user)

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

    prompt = f"Generate production ready {data.language} code.\n\n{data.prompt}"

    response = ai_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "You are an elite software engineer"},
            {"role": "user", "content": prompt},
        ],
    )

    code = response.choices[0].message.content

    usage_collection.insert_one({
        "user": user["email"],
        "time": datetime.utcnow(),
        "type": "generate",
    })

    return {"code": code}


@app.post("/api/ai/explain")

def explain_code(data: CodeInput, user=Depends(get_current_user)):

    response = ai_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "Explain this code clearly"},
            {"role": "user", "content": data.code},
        ],
    )

    return {"explanation": response.choices[0].message.content}


@app.post("/api/ai/fix")

def fix_code(data: CodeInput, user=Depends(get_current_user)):

    response = ai_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "Fix bugs in this code"},
            {"role": "user", "content": data.code},
        ],
    )

    return {"fixed_code": response.choices[0].message.content}


# =====================================================
# STRIPE PAYMENTS
# =====================================================

@app.post("/api/payments/create-checkout")

def create_checkout(user=Depends(get_current_user)):

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "CursorCode AI Pro"},
                "unit_amount": 2000,
            },
            "quantity": 1,
        }],
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

    return {
        "total_users": total_users,
        "ai_requests": ai_calls,
    }


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/api/health")

def health():

    return {
        "status": "ok",
        "time": time.time(),
        }
