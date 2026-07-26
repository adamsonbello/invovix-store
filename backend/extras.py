import uuid
from datetime import datetime, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import db
from security import get_current_user, require_admin
import cj as cjmod

extras_router = APIRouter(prefix="/api")


# ----------------------------- Site settings -----------------------------
DEFAULT_SETTINGS = {
    "key": "site",
    "banner_enabled": True,
    "banner_text": "Livraison offerte dès 50€ · Paiement 100% sécurisé",
    "banner_text_en": "Free shipping over €50 · 100% secure checkout",
    "whatsapp_number": "",
    "whatsapp_enabled": False,
    # --- Identité légale (facturation / conformité) ---
    "company_name": "Invovix",
    "company_legal_form": "",          # ex: SAS, SASU, EI, micro-entreprise
    "siren": "",
    "siret": "",
    "vat_number": "",                  # TVA intracommunautaire
    "company_address": "",
    "vat_regime": "franchise",         # "franchise" (293 B, sans TVA) | "assujetti"
    "vat_rate": 20.0,
}


async def get_settings_doc() -> dict:
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0})
    if not doc:
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
        doc = dict(DEFAULT_SETTINGS)
    return doc


class SettingsInput(BaseModel):
    banner_enabled: bool = True
    banner_text: str = ""
    banner_text_en: str = ""
    whatsapp_number: str = ""
    whatsapp_enabled: bool = False
    company_name: str = "Invovix"
    company_legal_form: str = ""
    siren: str = ""
    siret: str = ""
    vat_number: str = ""
    company_address: str = ""
    vat_regime: str = "franchise"
    vat_rate: float = 20.0


@extras_router.get("/settings")
async def public_settings():
    return await get_settings_doc()


@extras_router.put("/admin/settings")
async def update_settings(body: SettingsInput, admin: dict = Depends(require_admin)):
    await db.settings.update_one({"key": "site"}, {"$set": {**body.model_dump(), "key": "site"}}, upsert=True)
    return await get_settings_doc()


# ----------------------------- Related products -----------------------------
@extras_router.get("/products/{product_id}/related")
async def related_products(product_id: str, limit: int = 4):
    p = await db.products.find_one({"id": product_id}, {"_id": 0, "category": 1})
    if not p:
        return {"items": []}
    cur = db.products.find(
        {"category": p.get("category"), "id": {"$ne": product_id}, "active": True}, {"_id": 0}
    ).limit(limit)
    items = await cur.to_list(limit)
    if len(items) < limit:
        exclude = [product_id] + [i["id"] for i in items]
        fill = await db.products.find(
            {"id": {"$nin": exclude}, "active": True}, {"_id": 0}
        ).limit(limit - len(items)).to_list(limit)
        items += fill
    return {"items": [cjmod.enrich_product(p) for p in items]}


# ----------------------------- Featured reviews -----------------------------
@extras_router.get("/reviews/featured")
async def featured_reviews(limit: int = 6):
    cur = db.reviews.find(
        {"rating": {"$gte": 4}, "comment": {"$nin": ["", None]}}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    revs = await cur.to_list(limit)
    out = []
    for r in revs:
        prod = await db.products.find_one(
            {"id": r["product_id"]}, {"_id": 0, "title": 1, "title_en": 1, "images": 1, "id": 1}
        )
        out.append({**r, "product": prod})
    return {"items": out}


# ----------------------------- Wishlist -----------------------------
@extras_router.get("/wishlist")
async def get_wishlist(user: dict = Depends(get_current_user)):
    doc = await db.wishlists.find_one({"user_id": user["id"]}, {"_id": 0})
    pids = doc["product_ids"] if doc else []
    items = await db.products.find({"id": {"$in": pids}, "active": True}, {"_id": 0}).to_list(200)
    order = {pid: i for i, pid in enumerate(pids)}
    items.sort(key=lambda x: order.get(x["id"], 0))
    return {"items": [cjmod.enrich_product(p) for p in items], "product_ids": pids}


@extras_router.post("/wishlist/{product_id}")
async def toggle_wishlist(product_id: str, user: dict = Depends(get_current_user)):
    doc = await db.wishlists.find_one({"user_id": user["id"]})
    pids = doc["product_ids"] if doc else []
    if product_id in pids:
        pids.remove(product_id)
        added = False
    else:
        pids.insert(0, product_id)
        added = True
    await db.wishlists.update_one({"user_id": user["id"]}, {"$set": {"product_ids": pids}}, upsert=True)
    return {"product_ids": pids, "added": added}


# ----------------------------- Promo codes -----------------------------
class PromoInput(BaseModel):
    code: str
    type: Literal["percent", "fixed"] = "percent"
    value: float
    min_subtotal: float = 0
    active: bool = True


async def validate_promo(code: str, subtotal: float) -> Optional[dict]:
    if not code:
        return None
    promo = await db.promos.find_one({"code": code.upper().strip(), "active": True}, {"_id": 0})
    if not promo:
        return None
    if subtotal < float(promo.get("min_subtotal", 0)):
        return None
    if promo["type"] == "percent":
        discount = round(subtotal * float(promo["value"]) / 100, 2)
    else:
        discount = min(round(float(promo["value"]), 2), subtotal)
    return {"code": promo["code"], "type": promo["type"], "value": promo["value"],
            "min_subtotal": promo.get("min_subtotal", 0), "discount": discount}


class PromoValidateInput(BaseModel):
    code: str
    subtotal: float


@extras_router.post("/promo/validate")
async def promo_validate(body: PromoValidateInput):
    res = await validate_promo(body.code, body.subtotal)
    if not res:
        raise HTTPException(400, "Code promo invalide ou non applicable.")
    return {"valid": True, **res}


@extras_router.get("/admin/promos")
async def list_promos(admin: dict = Depends(require_admin)):
    items = await db.promos.find({}, {"_id": 0}).sort("code", 1).to_list(500)
    return {"items": items}


@extras_router.post("/admin/promos")
async def create_promo(body: PromoInput, admin: dict = Depends(require_admin)):
    code = body.code.upper().strip()
    if not code:
        raise HTTPException(400, "Code requis")
    doc = {**body.model_dump(), "code": code, "id": str(uuid.uuid4()),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.promos.update_one({"code": code}, {"$set": doc}, upsert=True)
    return doc


@extras_router.delete("/admin/promos/{code}")
async def delete_promo(code: str, admin: dict = Depends(require_admin)):
    await db.promos.delete_one({"code": code.upper().strip()})
    return {"ok": True}


async def seed_extras():
    """Seed default settings and the WELCOME10 promo (idempotent)."""
    await get_settings_doc()
    existing = await db.promos.find_one({"code": "WELCOME10"})
    if not existing:
        await db.promos.insert_one({
            "id": str(uuid.uuid4()),
            "code": "WELCOME10",
            "type": "percent",
            "value": 10,
            "min_subtotal": 0,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
