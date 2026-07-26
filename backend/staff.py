"""Phase 4A : gestion du personnel (RBAC), journal des connexions, 2FA."""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from database import db
from security import (require_admin, get_current_user, hash_password,
                      STAFF_ROLES, ROLE_PERMISSIONS, permissions_for)
import twofa as twofamod

logger = logging.getLogger("invovix")
staff_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _public_staff(u: dict) -> dict:
    return {
        "id": u["id"], "email": u["email"], "name": u.get("name", ""),
        "role": u.get("role", "customer"), "created_at": u.get("created_at", ""),
        "twofa_enabled": bool(u.get("twofa_enabled")),
        "permissions": sorted(permissions_for(u.get("role", "customer"))),
    }


# ----------------------------- Permissions du user courant -----------------------------
@staff_router.get("/auth/permissions")
async def my_permissions(user: dict = Depends(get_current_user)):
    role = user.get("role", "customer")
    return {
        "role": role,
        "is_admin": role == "admin",
        "is_staff": role in STAFF_ROLES,
        "permissions": sorted(permissions_for(role)) if role != "admin" else "all",
        "twofa_enabled": bool(user.get("twofa_enabled")),
    }


# ----------------------------- Gestion du personnel (admin only) -----------------------------
class StaffInput(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "support"


class RoleInput(BaseModel):
    role: str


@staff_router.get("/admin/staff")
async def list_staff(admin: dict = Depends(require_admin)):
    users = await db.users.find({"role": {"$in": list(STAFF_ROLES)}}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return {"items": [_public_staff(u) for u in users], "roles": sorted(STAFF_ROLES),
            "role_permissions": {r: sorted(p) for r, p in ROLE_PERMISSIONS.items() if r in STAFF_ROLES}}


@staff_router.post("/admin/staff")
async def create_staff(body: StaffInput, admin: dict = Depends(require_admin)):
    if body.role not in STAFF_ROLES:
        raise HTTPException(400, "Rôle invalide")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Un compte existe déjà avec cet email")
    user = {
        "id": str(uuid.uuid4()), "email": email, "name": body.name,
        "password_hash": hash_password(body.password), "role": body.role,
        "created_at": _now(),
    }
    await db.users.insert_one(user)
    return _public_staff(user)


@staff_router.put("/admin/staff/{staff_id}/role")
async def update_staff_role(staff_id: str, body: RoleInput, admin: dict = Depends(require_admin)):
    if body.role not in STAFF_ROLES:
        raise HTTPException(400, "Rôle invalide")
    if staff_id == admin["id"]:
        raise HTTPException(400, "Impossible de modifier votre propre rôle")
    res = await db.users.update_one({"id": staff_id}, {"$set": {"role": body.role}})
    if res.matched_count == 0:
        raise HTTPException(404, "Membre introuvable")
    u = await db.users.find_one({"id": staff_id}, {"_id": 0})
    return _public_staff(u)


@staff_router.delete("/admin/staff/{staff_id}")
async def delete_staff(staff_id: str, admin: dict = Depends(require_admin)):
    if staff_id == admin["id"]:
        raise HTTPException(400, "Impossible de supprimer votre propre compte")
    u = await db.users.find_one({"id": staff_id}, {"_id": 0})
    if not u:
        raise HTTPException(404, "Membre introuvable")
    if u.get("role") not in STAFF_ROLES:
        raise HTTPException(400, "Cet utilisateur n'est pas un membre du personnel")
    await db.users.delete_one({"id": staff_id})
    return {"ok": True}


# ----------------------------- Journal des connexions -----------------------------
async def record_login(request: Request, email: str, success: bool, user_id: str = "", role: str = ""):
    try:
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
        await db.login_events.insert_one({
            "id": str(uuid.uuid4()), "email": email, "success": success,
            "user_id": user_id, "role": role, "ip": ip,
            "user_agent": request.headers.get("user-agent", "")[:300],
            "created_at": _now(),
        })
    except Exception as e:
        logger.error(f"login journal write failed: {e}")


@staff_router.get("/admin/login-journal")
async def login_journal(admin: dict = Depends(require_admin), limit: int = 100):
    items = await db.login_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 500))
    return {"items": items,
            "failed_24h": await db.login_events.count_documents({"success": False, "created_at": {"$gte": _cutoff_24h()}})}


def _cutoff_24h():
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()


# ----------------------------- 2FA (TOTP) -----------------------------
class CodeInput(BaseModel):
    code: str


@staff_router.post("/auth/2fa/setup")
async def twofa_setup(user: dict = Depends(get_current_user)):
    if user.get("role") not in STAFF_ROLES:
        raise HTTPException(403, "2FA réservée au personnel")
    secret = twofamod.new_secret()
    await db.users.update_one({"id": user["id"]}, {"$set": {"twofa_pending_secret": secret}})
    uri = twofamod.provisioning_uri(secret, user["email"])
    return {"secret": secret, "otpauth_uri": uri, "qr": twofamod.qr_data_url(uri)}


@staff_router.post("/auth/2fa/enable")
async def twofa_enable(body: CodeInput, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"id": user["id"]})
    secret = doc.get("twofa_pending_secret")
    if not secret:
        raise HTTPException(400, "Aucune configuration 2FA en cours")
    if not twofamod.verify_code(secret, body.code):
        raise HTTPException(400, "Code invalide")
    await db.users.update_one({"id": user["id"]}, {"$set": {"twofa_enabled": True, "twofa_secret": secret},
                                                    "$unset": {"twofa_pending_secret": ""}})
    return {"ok": True, "twofa_enabled": True}


@staff_router.post("/auth/2fa/disable")
async def twofa_disable(body: CodeInput, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"id": user["id"]})
    if not doc.get("twofa_enabled"):
        raise HTTPException(400, "2FA non activée")
    if not twofamod.verify_code(doc.get("twofa_secret", ""), body.code):
        raise HTTPException(400, "Code invalide")
    await db.users.update_one({"id": user["id"]}, {"$set": {"twofa_enabled": False},
                                                    "$unset": {"twofa_secret": "", "twofa_pending_secret": ""}})
    return {"ok": True, "twofa_enabled": False}
