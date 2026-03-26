from datetime import datetime, timezone, timedelta
import secrets
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import JWT_SECRET, JWT_REFRESH_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_REFRESH_EXPIRATION_DAYS
from core.database import db
from models.schemas import User, UserResponse

security = HTTPBearer()


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
