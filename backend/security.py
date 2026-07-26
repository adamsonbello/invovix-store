import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends

from database import db

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_DAYS = 7


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_2fa_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "2fa",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_2fa_token(token: str) -> str:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Jeton 2FA invalide ou expiré")
    if payload.get("type") != "2fa":
        raise HTTPException(status_code=401, detail="Type de jeton invalide")
    return payload["sub"]


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ----------------------------- RBAC (Phase 4) -----------------------------
STAFF_ROLES = {"admin", "manager", "marketing", "support", "accounting"}
ALL_AREAS = {"analytics", "catalog", "orders", "content", "marketing",
             "operations", "ai", "cj", "settings", "support", "staff"}

# Zones autorisées par rôle (admin = toutes)
ROLE_PERMISSIONS = {
    "admin": set(ALL_AREAS),
    "manager": {"analytics", "catalog", "orders", "content", "marketing", "operations", "ai", "cj", "support"},
    "marketing": {"analytics", "marketing", "content", "ai", "catalog"},
    "support": {"orders", "support", "marketing"},
    "accounting": {"analytics", "orders", "settings"},
    "customer": set(),
}


def permissions_for(role: str) -> set:
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user: dict, area: str) -> bool:
    if user.get("role") == "admin":
        return True
    return area in permissions_for(user.get("role", "customer"))


def require_area(area: str):
    """Dépendance : autorise l'admin, ou un staff dont le rôle couvre la zone."""
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not has_permission(user, area):
            raise HTTPException(status_code=403, detail="Permission refusée pour cette zone")
        return user
    return _dep


async def require_staff(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé au personnel")
    return user

