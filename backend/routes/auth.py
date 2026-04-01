import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode

from core.config import (
    FRONTEND_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI,
    GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_USERINFO_URL,
    JWT_REFRESH_SECRET, JWT_ALGORITHM
)
from core.database import db
from core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    generate_verification_token, get_current_user, user_to_response
)
from models.schemas import (
    UserCreate, UserLogin, User, UserResponse, TokenResponse,
    TwoFAVerifyRequest, TwoFALoginRequest, PasswordResetRequest,
    PasswordResetConfirm, GoogleCodeRequest
)
from services.email import send_email, send_verification_email, send_welcome_email
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
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


@router.get("/verify-email")
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


@router.post("/resend-verification")
async def resend_verification(user: User = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    new_token = generate_verification_token()
    await db.users.update_one({"id": user.id}, {"$set": {"verification_token": new_token}})
    background_tasks.add_task(send_verification_email, user.email, user.name, new_token)
    return {"message": "Verification email sent"}


@router.post("/login")
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


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user_to_response(user)


@router.post("/refresh", response_model=TokenResponse)
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


# ==================== 2FA ====================

@router.post("/2fa/enable")
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


@router.post("/2fa/verify")
async def verify_2fa(data: TwoFAVerifyRequest, user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    secret = user_doc.get("totp_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /auth/2fa/enable first.")
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    await db.users.update_one({"id": user.id}, {"$set": {"totp_enabled": True}})
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
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


@router.post("/login-2fa")
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

@router.post("/reset-password/request")
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


@router.post("/reset-password/confirm")
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
    refresh_tok = create_refresh_token({"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_tok, user=user_to_response(user))


# ==================== GITHUB OAUTH ====================

@router.get("/github")
async def github_login(redirect_uri: str = None):
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured. Set GITHUB_OAUTH_CLIENT_ID and GITHUB_OAUTH_CLIENT_SECRET in environment.")
    callback_url = redirect_uri or f"{FRONTEND_URL}/auth/github/callback"
    state = secrets.token_urlsafe(16)
    params = {"client_id": GITHUB_CLIENT_ID, "redirect_uri": callback_url, "scope": "user repo", "state": state}
    github_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=github_url)


@router.post("/github/callback")
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


# ==================== GOOGLE OAUTH ====================

@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment.")
    redirect_uri = GOOGLE_REDIRECT_URI or f"{FRONTEND_URL}/auth/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    google_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=google_url)


@router.post("/google/callback")
async def google_callback(data: GoogleCodeRequest, background_tasks: BackgroundTasks):
    redirect_uri = GOOGLE_REDIRECT_URI or f"{FRONTEND_URL}/auth/google/callback"
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not redirect_uri:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        token_resp = await http_client.post(GOOGLE_TOKEN_URL, data={
            "code": data.code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
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
    refresh_tok = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_tok,
        user=user_to_response(user)
    )
