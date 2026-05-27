"""
app/api/auth.py — JWT Authentication for ServicePulse
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import base64
import json
import logging

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# ── Secret key (in production, use env variable) ──────────
SECRET_KEY = "servicepulse-secret-key-2026-atlas-project"

# ── Default users (in production, store in database) ──────
USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password_hash": hashlib.sha256("admin@123".encode()).hexdigest(),
        "full_name": "System Administrator",
        "role": "superadmin",
        "email": "admin@atlas.in",
        "avatar": "SA",
        "permissions": ["dashboard", "sla", "workload", "teams", "tickets", "create", "connectors", "ai", "export", "admin"]
    },
    "manager": {
        "id": 2,
        "username": "manager",
        "password_hash": hashlib.sha256("manager@123".encode()).hexdigest(),
        "full_name": "Project Manager",
        "role": "manager",
        "email": "manager@atlas.in",
        "avatar": "PM",
        "permissions": ["dashboard", "sla", "workload", "teams", "tickets", "create", "connectors", "ai", "export"]
    },
    "viewer": {
        "id": 3,
        "username": "viewer",
        "password_hash": hashlib.sha256("viewer@123".encode()).hexdigest(),
        "full_name": "Leadership Viewer",
        "role": "viewer",
        "email": "viewer@atlas.in",
        "avatar": "LV",
        "permissions": ["dashboard", "sla", "workload", "teams", "tickets"]
    },
    "teamlead": {
        "id": 4,
        "username": "teamlead",
        "password_hash": hashlib.sha256("lead@123".encode()).hexdigest(),
        "full_name": "Team Lead",
        "role": "teamlead",
        "email": "teamlead@atlas.in",
        "avatar": "TL",
        "permissions": ["dashboard", "sla", "workload", "teams", "tickets", "create", "ai"]
    }
}


# ── Schemas ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    expires_in: int


# ── JWT (Simple implementation without PyJWT) ─────────────
def create_token(payload: dict, expires_hours: int = 8) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload["exp"] = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).timestamp()
    payload["iat"] = datetime.now(timezone.utc).timestamp()

    def b64encode(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()

    header_b64  = b64encode(header)
    payload_b64 = b64encode(payload)
    signature   = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b'=').decode()
        if not hmac.compare_digest(sig_b64, expected_b64):
            return None

        # Decode payload
        padding = 4 - len(payload_b64) % 4
        payload_b64 += '=' * (padding % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Check expiry
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None

        return payload
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        return None


# ── Auth dependency ───────────────────────────────────────
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = USERS.get(payload.get("username"))
    if not user:
        raise HTTPException(401, "User not found")
    return user


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Returns user if authenticated, None otherwise."""
    if not credentials:
        return None
    payload = verify_token(credentials.credentials)
    if not payload:
        return None
    return USERS.get(payload.get("username"))


# ── Endpoints ─────────────────────────────────────────────

@auth_router.post("/login")
def login(data: LoginRequest):
    """Authenticate user and return JWT token."""
    user = USERS.get(data.username.lower())
    if not user:
        raise HTTPException(401, "Invalid username or password")

    pwd_hash = hashlib.sha256(data.password.encode()).hexdigest()
    if not hmac.compare_digest(pwd_hash, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    expires_hours = 168 if data.remember_me else 8  # 7 days or 8 hours
    token = create_token({
        "username": user["username"],
        "role":     user["role"],
        "user_id":  user["id"]
    }, expires_hours)

    logger.info("User '%s' logged in successfully", data.username)

    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   expires_hours * 3600,
        "user": {
            "id":          user["id"],
            "username":    user["username"],
            "full_name":   user["full_name"],
            "role":        user["role"],
            "email":       user["email"],
            "avatar":      user["avatar"],
            "permissions": user["permissions"]
        }
    }


@auth_router.post("/logout")
def logout():
    """Logout — client should delete the token."""
    return {"message": "Logged out successfully"}


@auth_router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id":          current_user["id"],
        "username":    current_user["username"],
        "full_name":   current_user["full_name"],
        "role":        current_user["role"],
        "email":       current_user["email"],
        "avatar":      current_user["avatar"],
        "permissions": current_user["permissions"]
    }


@auth_router.get("/users")
def list_users(current_user: dict = Depends(get_current_user)):
    """List all users (admin only)."""
    if current_user["role"] != "superadmin":
        raise HTTPException(403, "Admin access required")
    return [
        {"id": u["id"], "username": u["username"], "full_name": u["full_name"],
         "role": u["role"], "email": u["email"]}
        for u in USERS.values()
    ]


@auth_router.post("/verify")
def verify_token_endpoint(authorization: str = Header(None)):
    """Verify if a token is valid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "No token provided")
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return {"valid": True, "username": payload.get("username"), "role": payload.get("role")}
