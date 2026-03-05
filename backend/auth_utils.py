"""
CursorCode AI - Auth Helpers
JWT and OAuth utilities
"""

import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from passlib.context import CryptContext
from backend.db_models import Users
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=30)
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm="HS256")

def get_current_user(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user = Users.find_one({"email": payload["email"]})
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user
    except:
        raise HTTPException(status_code=401, detail="Unauthorized")
