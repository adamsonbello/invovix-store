"""Phase 4B : API publique en lecture seule sécurisée par clé API (X-API-Key)."""
import uuid
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from database import db
from security import require_admin
import cj as cjmod

logger = logging.getLogger("invovix")
publicapi_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc).isoformat()


# ----------------------------- Gestion des clés (admin) -----------------------------
class ApiKeyInput(BaseModel):
    name: str


@publicapi_router.get("/admin/api-keys")
async def list_api_keys(admin: dict = Depends(require_admin)):
    items = await db.api_keys.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@publicapi_router.post("/admin/api-keys")
async def create_api_key(body: ApiKeyInput, admin: dict = Depends(require_admin)):
    doc = {
        "id": str(uuid.uuid4()), "name": body.name,
        "key": "ivx_" + secrets.token_urlsafe(24),
        "active": True, "last_used": None, "created_at": _now(),
    }
    await db.api_keys.insert_one(doc)
    doc.pop("_id", None)
    return doc


@publicapi_router.delete("/admin/api-keys/{key_id}")
async def delete_api_key(key_id: str, admin: dict = Depends(require_admin)):
    await db.api_keys.delete_one({"id": key_id})
    return {"ok": True}


@publicapi_router.put("/admin/api-keys/{key_id}/toggle")
async def toggle_api_key(key_id: str, admin: dict = Depends(require_admin)):
    doc = await db.api_keys.find_one({"id": key_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Clé introuvable")
    await db.api_keys.update_one({"id": key_id}, {"$set": {"active": not doc.get("active", True)}})
    return {"ok": True, "active": not doc.get("active", True)}


# ----------------------------- Dépendance clé API -----------------------------
async def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(401, "Clé API manquante (header X-API-Key)")
    doc = await db.api_keys.find_one({"key": x_api_key, "active": True})
    if not doc:
        raise HTTPException(401, "Clé API invalide ou désactivée")
    await db.api_keys.update_one({"id": doc["id"]}, {"$set": {"last_used": _now()}})
    return doc


# ----------------------------- Endpoints publics (lecture seule) -----------------------------
@publicapi_router.get("/public/products")
async def public_products(key=Depends(require_api_key), page: int = 1, size: int = 20, category: str = ""):
    size = min(size, 100)
    q = {"active": {"$ne": False}}
    if category:
        q["category"] = category
    total = await db.products.count_documents(q)
    items = await db.products.find(q, {"_id": 0}).skip((page - 1) * size).limit(size).to_list(size)
    items = [cjmod.enrich_product(p) for p in items]
    slim = [{"id": p["id"], "title": p.get("title"), "price": p.get("price"),
             "currency": p.get("currency", "EUR"), "category": p.get("category"),
             "in_stock": p.get("in_stock", True), "sku": p.get("sku", ""),
             "images": p.get("images", [])} for p in items]
    return {"items": slim, "total": total, "page": page, "size": size}


@publicapi_router.get("/public/products/{product_id}")
async def public_product(product_id: str, key=Depends(require_api_key)):
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Produit introuvable")
    p = cjmod.enrich_product(p)
    return {"id": p["id"], "title": p.get("title"), "description": p.get("description"),
            "price": p.get("price"), "currency": p.get("currency", "EUR"),
            "category": p.get("category"), "brand": p.get("brand", ""), "ean": p.get("ean", ""),
            "sku": p.get("sku", ""), "in_stock": p.get("in_stock", True), "images": p.get("images", [])}


@publicapi_router.get("/public/stats")
async def public_stats(key=Depends(require_api_key)):
    return {
        "products": await db.products.count_documents({"active": {"$ne": False}}),
        "categories": await db.products.distinct("category"),
    }


# ----------------------------- Webhooks sortants -----------------------------
WEBHOOK_EVENTS = {"order.paid", "order.shipped"}


class WebhookInput(BaseModel):
    url: str
    event: str = "order.paid"
    active: bool = True


@publicapi_router.get("/admin/webhooks")
async def list_webhooks(admin: dict = Depends(require_admin)):
    items = await db.webhooks.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items, "events": sorted(WEBHOOK_EVENTS)}


@publicapi_router.post("/admin/webhooks")
async def create_webhook(body: WebhookInput, admin: dict = Depends(require_admin)):
    if body.event not in WEBHOOK_EVENTS:
        raise HTTPException(400, "Événement invalide")
    if not body.url.startswith("http"):
        raise HTTPException(400, "URL invalide")
    doc = {"id": str(uuid.uuid4()), "url": body.url, "event": body.event,
           "active": body.active, "last_status": None, "created_at": _now()}
    await db.webhooks.insert_one(doc)
    doc.pop("_id", None)
    return doc


@publicapi_router.delete("/admin/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, admin: dict = Depends(require_admin)):
    await db.webhooks.delete_one({"id": webhook_id})
    return {"ok": True}


async def dispatch_event(event: str, payload: dict):
    """POST le payload à tous les webhooks actifs abonnés à l'événement."""
    hooks = await db.webhooks.find({"event": event, "active": True}, {"_id": 0}).to_list(100)
    if not hooks:
        return
    import httpx
    body = {"event": event, "data": payload, "sent_at": _now()}
    async with httpx.AsyncClient(timeout=10) as c:
        for h in hooks:
            try:
                r = await c.post(h["url"], json=body)
                await db.webhooks.update_one({"id": h["id"]}, {"$set": {"last_status": r.status_code, "last_sent": _now()}})
            except Exception as e:
                logger.error(f"webhook {h['id']} failed: {e}")
                await db.webhooks.update_one({"id": h["id"]}, {"$set": {"last_status": "error", "last_sent": _now()}})
