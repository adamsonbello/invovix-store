"""Phase 3A CRM : fiches clients, fidélité, relance panier/checkout abandonné."""
import os
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from security import get_current_user, require_admin
import brevo as brevomod

logger = logging.getLogger("invovix")
crm_router = APIRouter(prefix="/api")

# Fidélité : 1 point par euro dépensé ; paliers par total dépensé
TIERS = [
    {"name": "Bronze", "min": 0, "perk": "Bienvenue"},
    {"name": "Argent", "min": 150, "perk": "-5% permanent (à venir)"},
    {"name": "Or", "min": 400, "perk": "-10% + livraison prioritaire (à venir)"},
    {"name": "Platine", "min": 1000, "perk": "Accès VIP & offres exclusives"},
]


def _tier_for(total_spent: float) -> dict:
    t = TIERS[0]
    for tier in TIERS:
        if total_spent >= tier["min"]:
            t = tier
    return t


def _now():
    return datetime.now(timezone.utc)


async def accrue_loyalty(order: dict):
    """Attribue les points de fidélité à la validation du paiement (idempotent)."""
    if order.get("loyalty_awarded"):
        return
    uid = order.get("user_id")
    if not uid:
        return
    pts = int(order.get("total", 0) or 0)
    await db.users.update_one({"id": uid}, {"$inc": {"loyalty_points": pts}})
    await db.orders.update_one({"id": order["id"]}, {"$set": {"loyalty_awarded": True}})
    logger.info(f"loyalty +{pts} pts to {uid} for order {order['id']}")


# ----------------------------- Espace client : fidélité -----------------------------
@crm_router.get("/loyalty")
async def my_loyalty(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    paid = await db.orders.find({"user_id": user["id"], "payment_status": "paid"}, {"_id": 0, "total": 1}).to_list(1000)
    total_spent = round(sum(o.get("total", 0) for o in paid), 2)
    tier = _tier_for(total_spent)
    idx = TIERS.index(tier)
    nxt = TIERS[idx + 1] if idx + 1 < len(TIERS) else None
    return {
        "points": int(u.get("loyalty_points", 0)),
        "total_spent": total_spent,
        "tier": tier["name"],
        "perk": tier["perk"],
        "next_tier": nxt["name"] if nxt else None,
        "to_next": round(nxt["min"] - total_spent, 2) if nxt else 0,
    }


# ----------------------------- CRM admin -----------------------------
async def _customer_summary(u: dict) -> dict:
    uid = u["id"]
    orders = await db.orders.find({"user_id": uid}, {"_id": 0, "total": 1, "payment_status": 1, "created_at": 1}).to_list(2000)
    paid = [o for o in orders if o.get("payment_status") == "paid"]
    total_spent = round(sum(o.get("total", 0) for o in paid), 2)
    last = max((o.get("created_at", "") for o in orders), default="")
    returns_count = await db.returns.count_documents({"user_id": uid})
    tier = _tier_for(total_spent)
    status = "VIP" if total_spent >= 400 else ("actif" if paid else "nouveau")
    return {
        "id": uid,
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "created_at": u.get("created_at", ""),
        "orders_count": len(paid),
        "total_spent": total_spent,
        "aov": round(total_spent / len(paid), 2) if paid else 0.0,
        "last_order_at": last,
        "returns_count": returns_count,
        "loyalty_points": int(u.get("loyalty_points", 0)),
        "tier": tier["name"],
        "status": status,
    }


@crm_router.get("/admin/customers")
async def list_customers(admin: dict = Depends(require_admin), q: str = "", segment: str = ""):
    query = {"role": "customer"}
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]
    users = await db.users.find(query, {"_id": 0}).to_list(5000)
    items = [await _customer_summary(u) for u in users]
    if segment == "vip":
        items = [i for i in items if i["status"] == "VIP"]
    elif segment == "active":
        items = [i for i in items if i["status"] == "actif"]
    elif segment == "new":
        items = [i for i in items if i["status"] == "nouveau"]
    items.sort(key=lambda x: x["total_spent"], reverse=True)
    return {"items": items, "count": len(items)}


@crm_router.get("/admin/customers/{customer_id}")
async def customer_detail(customer_id: str, admin: dict = Depends(require_admin)):
    u = await db.users.find_one({"id": customer_id}, {"_id": 0})
    if not u:
        raise HTTPException(404, "Client introuvable")
    summary = await _customer_summary(u)
    orders = await db.orders.find({"user_id": customer_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    returns = await db.returns.find({"user_id": customer_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"customer": summary, "orders": orders, "returns": returns}


# ----------------------------- Relance panier / checkout abandonné -----------------------------
def _abandoned_window():
    """Renvoie (min_age, max_age) en heures : relance après X h, jusqu'à Y h."""
    return (
        float(os.environ.get("ABANDONED_MIN_HOURS", "1")),
        float(os.environ.get("ABANDONED_MAX_HOURS", "72")),
    )


async def _find_abandoned(all_pending: bool = False):
    """Commandes en attente de paiement = checkout abandonnés."""
    now = _now()
    min_h, max_h = _abandoned_window()
    q = {"payment_status": "pending"}
    orders = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    out = []
    for o in orders:
        try:
            created = datetime.fromisoformat(o.get("created_at"))
        except Exception:
            continue
        age_h = (now - created).total_seconds() / 3600
        if all_pending or (min_h <= age_h <= max_h):
            out.append(o)
    return out


async def send_abandoned_reminder(order: dict) -> bool:
    addr = order.get("shipping_address") or {}
    to_email = addr.get("email") or order.get("user_email") or ""
    to_name = addr.get("full_name") or "Client"
    if not to_email:
        return False
    promo = os.environ.get("ABANDONED_PROMO_CODE", "WELCOME10")
    ok = brevomod.send_abandoned_cart(to_email, to_name, order, os.environ.get("FRONTEND_URL", ""), promo)
    if ok:
        await db.orders.update_one({"id": order["id"]}, {"$set": {
            "abandoned_email_sent": True,
            "abandoned_email_at": _now().isoformat(),
        }})
    return ok


async def run_abandoned_recovery() -> dict:
    orders = await _find_abandoned()
    sent = 0
    for o in orders:
        if o.get("abandoned_email_sent"):
            continue
        try:
            if await send_abandoned_reminder(o):
                sent += 1
        except Exception as e:
            logger.error(f"abandoned reminder failed {o.get('id')}: {e}")
    logger.info(f"abandoned recovery: {sent} reminders sent ({len(orders)} candidates)")
    return {"candidates": len(orders), "sent": sent}


@crm_router.get("/admin/abandoned")
async def list_abandoned(admin: dict = Depends(require_admin)):
    orders = await _find_abandoned(all_pending=True)
    potential = round(sum(o.get("total", 0) for o in orders), 2)
    reminded = sum(1 for o in orders if o.get("abandoned_email_sent"))
    # récupérés : commandes payées qui avaient reçu une relance
    recovered = await db.orders.count_documents({"payment_status": "paid", "abandoned_email_sent": True})
    recovered_rev = 0.0
    for o in await db.orders.find({"payment_status": "paid", "abandoned_email_sent": True}, {"_id": 0, "total": 1}).to_list(2000):
        recovered_rev += o.get("total", 0)
    return {
        "items": orders,
        "count": len(orders),
        "potential_revenue": potential,
        "reminded": reminded,
        "recovered": recovered,
        "recovered_revenue": round(recovered_rev, 2),
    }


@crm_router.post("/admin/abandoned/{order_id}/remind")
async def remind_abandoned(order_id: str, admin: dict = Depends(require_admin)):
    o = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not o:
        raise HTTPException(404, "Commande introuvable")
    if o.get("payment_status") == "paid":
        raise HTTPException(400, "Commande déjà payée")
    ok = await send_abandoned_reminder(o)
    if not ok:
        raise HTTPException(502, "Envoi de l'email impossible (Brevo non configuré ou email manquant)")
    return {"ok": True}


@crm_router.post("/admin/abandoned/run")
async def run_abandoned_endpoint(admin: dict = Depends(require_admin)):
    return await run_abandoned_recovery()
