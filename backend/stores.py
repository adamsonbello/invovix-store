"""Module 19 — Multi-boutiques.
Gestion centralisée de plusieurs boutiques/domaines partageant le catalogue central.
La synchronisation = chaque boutique lit le catalogue unique filtré par ses catégories."""
import uuid
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from security import require_area
import cj as cjmod

logger = logging.getLogger("invovix")
stores_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _slugify(name: str) -> str:
    import re
    s = re.sub(r"[^\w\s-]", "", (name or "").lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:60] or uuid.uuid4().hex[:8]


class StoreInput(BaseModel):
    name: str
    domain: str = ""
    tagline: str = ""
    currency: str = "EUR"
    accent_color: str = "#FF3300"
    categories: List[str] = []          # filtre de synchro catalogue (vide = tout)
    featured_only: bool = False
    active: bool = True


async def _store_product_query(store: dict) -> dict:
    q = {"active": True}
    cats = store.get("categories") or []
    if cats:
        q["category"] = {"$in": cats}
    if store.get("featured_only"):
        q["featured"] = True
    return q


async def _catalog_count(store: dict) -> int:
    return await db.products.count_documents(await _store_product_query(store))


@stores_router.get("/admin/stores")
async def list_stores(admin: dict = Depends(require_area("operations"))):
    items = await db.stores.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for s in items:
        s["product_count"] = await _catalog_count(s)
    all_cats = await db.products.distinct("category", {"active": True})
    return {"items": items, "available_categories": all_cats}


@stores_router.post("/admin/stores")
async def create_store(body: StoreInput, admin: dict = Depends(require_area("operations"))):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["slug"] = _slugify(body.name)
    if await db.stores.find_one({"slug": doc["slug"]}):
        doc["slug"] = f"{doc['slug']}-{uuid.uuid4().hex[:5]}"
    doc["created_at"] = _now()
    await db.stores.insert_one(doc)
    doc.pop("_id", None)
    doc["product_count"] = await _catalog_count(doc)
    return doc


@stores_router.put("/admin/stores/{store_id}")
async def update_store(store_id: str, body: StoreInput, admin: dict = Depends(require_area("operations"))):
    res = await db.stores.update_one({"id": store_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Boutique introuvable")
    doc = await db.stores.find_one({"id": store_id}, {"_id": 0})
    doc["product_count"] = await _catalog_count(doc)
    return doc


@stores_router.delete("/admin/stores/{store_id}")
async def delete_store(store_id: str, admin: dict = Depends(require_area("operations"))):
    await db.stores.delete_one({"id": store_id})
    return {"ok": True}


@stores_router.get("/admin/stores/{store_id}/catalog")
async def store_catalog(store_id: str, admin: dict = Depends(require_area("operations"))):
    store = await db.stores.find_one({"id": store_id}, {"_id": 0})
    if not store:
        raise HTTPException(404, "Boutique introuvable")
    q = await _store_product_query(store)
    items = await db.products.find(q, {"_id": 0, "id": 1, "title": 1, "price": 1, "category": 1, "images": 1}).to_list(2000)
    return {"store": store, "count": len(items), "items": items}


# ----------------------------- Vitrine publique (par domaine/slug) -----------------------------
@stores_router.get("/public/stores/{slug}")
async def public_store(slug: str):
    store = await db.stores.find_one({"$or": [{"slug": slug}, {"domain": slug}], "active": True}, {"_id": 0})
    if not store:
        raise HTTPException(404, "Boutique introuvable")
    q = await _store_product_query(store)
    products = await db.products.find(q, {"_id": 0}).limit(200).to_list(200)
    products = [cjmod.enrich_product(p) for p in products]
    try:
        import marketing as mktmod
        sales = await mktmod.get_active_flash_sales()
        if sales:
            products = [mktmod.apply_flash_to_product(p, sales) for p in products]
    except Exception:
        pass
    return {
        "store": {k: store.get(k) for k in ("name", "slug", "domain", "tagline", "currency", "accent_color")},
        "products": products,
        "count": len(products),
    }
