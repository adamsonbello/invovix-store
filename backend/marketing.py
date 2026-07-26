"""Phase 3B Marketing : campagnes email, bundles (packs), ventes flash."""
import os
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from database import db
from security import require_admin, require_area
import brevo as brevomod

logger = logging.getLogger("invovix")
marketing_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc)


def _iso():
    return _now().isoformat()


# ----------------------------- Campagnes email -----------------------------
class CampaignInput(BaseModel):
    subject: str
    body_html: str
    segment: str = "newsletter"   # newsletter | customers | vip | all


async def _recipients(segment: str) -> list:
    emails = {}
    if segment in ("newsletter", "all"):
        for n in await db.newsletter.find({}, {"_id": 0, "email": 1}).to_list(20000):
            if n.get("email"):
                emails[n["email"]] = n.get("name", "")
    if segment in ("customers", "all", "vip"):
        for u in await db.users.find({"role": "customer"}, {"_id": 0, "email": 1, "name": 1, "id": 1}).to_list(20000):
            if segment == "vip":
                paid = await db.orders.find({"user_id": u["id"], "payment_status": "paid"}, {"_id": 0, "total": 1}).to_list(2000)
                if sum(o.get("total", 0) for o in paid) < 400:
                    continue
            emails[u["email"]] = u.get("name", "")
    return [{"email": e, "name": n} for e, n in emails.items()]


async def _send_campaign(campaign_id: str, subject: str, body_html: str, recipients: list):
    frontend = os.environ.get("FRONTEND_URL", "")
    sent = 0
    for r in recipients[:2000]:
        try:
            if brevomod.send_campaign_email(r["email"], r.get("name") or "Client", subject, body_html, frontend):
                sent += 1
        except Exception as e:
            logger.error(f"campaign send failed to {r['email']}: {e}")
    await db.campaigns.update_one({"id": campaign_id}, {"$set": {"sent": sent, "status": "sent", "sent_at": _iso()}})
    logger.info(f"campaign {campaign_id}: {sent}/{len(recipients)} emails sent")


@marketing_router.get("/admin/campaigns")
async def list_campaigns(admin: dict = Depends(require_area("marketing"))):
    items = await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@marketing_router.post("/admin/campaigns")
async def create_campaign(body: CampaignInput, background_tasks: BackgroundTasks, admin: dict = Depends(require_area("marketing"))):
    if body.segment not in ("newsletter", "customers", "vip", "all"):
        raise HTTPException(400, "Segment invalide")
    recipients = await _recipients(body.segment)
    campaign = {
        "id": str(uuid.uuid4()), "subject": body.subject, "body_html": body.body_html,
        "segment": body.segment, "recipients": len(recipients), "sent": 0,
        "status": "sending" if recipients else "empty", "created_at": _iso(),
    }
    await db.campaigns.insert_one(campaign)
    campaign.pop("_id", None)
    if recipients:
        background_tasks.add_task(_send_campaign, campaign["id"], body.subject, body.body_html, recipients)
    return campaign


@marketing_router.get("/admin/segments/count")
async def segment_counts(admin: dict = Depends(require_area("marketing"))):
    return {s: len(await _recipients(s)) for s in ("newsletter", "customers", "vip", "all")}


# ----------------------------- Bundles (packs) -----------------------------
class BundleInput(BaseModel):
    title: str
    description: str = ""
    product_ids: List[str] = []
    bundle_price: float
    image: str = ""
    active: bool = True


async def _resolve_bundle(b: dict) -> dict:
    prods = await db.products.find({"id": {"$in": b.get("product_ids", [])}}, {"_id": 0, "id": 1, "title": 1, "price": 1, "images": 1}).to_list(50)
    normal = round(sum(p.get("price", 0) for p in prods), 2)
    b = dict(b)
    b["products"] = prods
    b["normal_price"] = normal
    b["savings"] = round(max(normal - b.get("bundle_price", 0), 0), 2)
    b["savings_pct"] = round(b["savings"] / normal * 100, 0) if normal else 0
    if not b.get("image") and prods:
        b["image"] = (prods[0].get("images") or [""])[0]
    return b


@marketing_router.get("/bundles")
async def public_bundles():
    items = await db.bundles.find({"active": True}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": [await _resolve_bundle(b) for b in items]}


@marketing_router.get("/admin/bundles")
async def list_bundles(admin: dict = Depends(require_area("marketing"))):
    items = await db.bundles.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": [await _resolve_bundle(b) for b in items]}


@marketing_router.post("/admin/bundles")
async def create_bundle(body: BundleInput, admin: dict = Depends(require_area("marketing"))):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = _iso()
    await db.bundles.insert_one(doc)
    doc.pop("_id", None)
    return await _resolve_bundle(doc)


@marketing_router.put("/admin/bundles/{bundle_id}")
async def update_bundle(bundle_id: str, body: BundleInput, admin: dict = Depends(require_area("marketing"))):
    res = await db.bundles.update_one({"id": bundle_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Bundle introuvable")
    doc = await db.bundles.find_one({"id": bundle_id}, {"_id": 0})
    return await _resolve_bundle(doc)


@marketing_router.delete("/admin/bundles/{bundle_id}")
async def delete_bundle(bundle_id: str, admin: dict = Depends(require_area("marketing"))):
    await db.bundles.delete_one({"id": bundle_id})
    return {"ok": True}


# ----------------------------- Ventes flash -----------------------------
class FlashInput(BaseModel):
    title: str
    scope: str = "category"        # category | product | all
    target: str = ""               # category name or product_id (ignoré si all)
    discount_percent: float = 10.0
    ends_at: str                   # ISO datetime
    active: bool = True


async def get_active_flash_sales() -> list:
    now = _iso()
    sales = await db.flash_sales.find({"active": True}, {"_id": 0}).to_list(100)
    return [s for s in sales if (s.get("ends_at") or "") > now]


def flash_discount_for(product: dict, sales: list) -> float:
    """Renvoie le meilleur % de réduction flash applicable au produit (0 si aucun)."""
    best = 0.0
    for s in sales:
        scope = s.get("scope")
        if scope == "all" or (scope == "category" and product.get("category") == s.get("target")) or (scope == "product" and product.get("id") == s.get("target")):
            best = max(best, float(s.get("discount_percent", 0)))
    return best


def apply_flash_to_product(product: dict, sales: list) -> dict:
    disc = flash_discount_for(product, sales)
    if disc > 0 and product.get("price"):
        original = product["price"]
        product["original_price"] = original
        product["price"] = round(original * (1 - disc / 100.0), 2)
        product["flash_discount"] = disc
        # borne de fin la plus proche parmi les ventes applicables
        ends = [s.get("ends_at") for s in sales if flash_discount_for(product, [s]) == disc and disc > 0]
        product["flash_ends_at"] = min([e for e in ends if e], default=None)
    return product


@marketing_router.get("/flash-sales/active")
async def active_flash():
    return {"items": await get_active_flash_sales()}


@marketing_router.get("/admin/flash-sales")
async def list_flash(admin: dict = Depends(require_area("marketing"))):
    items = await db.flash_sales.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    now = _iso()
    for s in items:
        s["is_active"] = bool(s.get("active") and (s.get("ends_at") or "") > now)
    return {"items": items}


@marketing_router.post("/admin/flash-sales")
async def create_flash(body: FlashInput, admin: dict = Depends(require_area("marketing"))):
    if body.scope not in ("category", "product", "all"):
        raise HTTPException(400, "Scope invalide")
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = _iso()
    await db.flash_sales.insert_one(doc)
    doc.pop("_id", None)
    return doc


@marketing_router.put("/admin/flash-sales/{sale_id}")
async def update_flash(sale_id: str, body: FlashInput, admin: dict = Depends(require_area("marketing"))):
    res = await db.flash_sales.update_one({"id": sale_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Vente flash introuvable")
    return await db.flash_sales.find_one({"id": sale_id}, {"_id": 0})


@marketing_router.delete("/admin/flash-sales/{sale_id}")
async def delete_flash(sale_id: str, admin: dict = Depends(require_area("marketing"))):
    await db.flash_sales.delete_one({"id": sale_id})
    return {"ok": True}
