"""Phase 2 ERP : fournisseurs + comparateur, moteur de règles no-code, alertes."""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from database import db
from security import require_admin, require_area

logger = logging.getLogger("invovix")
erp_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc).isoformat()


def product_cost(p: dict) -> float:
    return float(p.get("buy_price") or p.get("cost_price") or 0)


def product_margin_pct(p: dict):
    price = float(p.get("price") or 0)
    cost = product_cost(p)
    if price and cost:
        return round((price - cost) / price * 100, 1)
    return None


# ----------------------------- Fournisseurs -----------------------------
class SupplierInput(BaseModel):
    name: str
    contact_email: str = ""
    contact_phone: str = ""
    website: str = ""
    country: str = ""
    avg_delay_days: float = 0.0
    quality_rating: float = 0.0        # 0-5
    shipping_cost: float = 0.0
    notes: str = ""


def _supplier_score(s: dict) -> float:
    """Score global 0-100 : qualité (max 60) - pénalité délai - pénalité port."""
    quality = min(max(s.get("quality_rating", 0), 0), 5) * 12  # 0..60
    delay = min(s.get("avg_delay_days", 0) or 0, 60)
    delay_pen = delay * 0.6            # jusqu'à -36
    ship_pen = min(s.get("shipping_cost", 0) or 0, 20) * 0.5   # jusqu'à -10
    return round(max(quality - delay_pen - ship_pen, 0), 1)


@erp_router.get("/admin/suppliers")
async def list_suppliers(admin: dict = Depends(require_area("operations"))):
    items = await db.suppliers.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for s in items:
        s["score"] = _supplier_score(s)
        s["product_count"] = await db.products.count_documents({"supplier_id": s["id"]})
    return {"items": items}


@erp_router.get("/admin/suppliers/compare")
async def compare_suppliers(admin: dict = Depends(require_area("operations"))):
    items = await db.suppliers.find({}, {"_id": 0}).to_list(1000)
    for s in items:
        s["score"] = _supplier_score(s)
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"items": items}


@erp_router.post("/admin/suppliers")
async def create_supplier(body: SupplierInput, admin: dict = Depends(require_area("operations"))):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = _now()
    await db.suppliers.insert_one(doc)
    doc.pop("_id", None)
    doc["score"] = _supplier_score(doc)
    return doc


@erp_router.put("/admin/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, body: SupplierInput, admin: dict = Depends(require_area("operations"))):
    res = await db.suppliers.update_one({"id": supplier_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Fournisseur introuvable")
    doc = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    doc["score"] = _supplier_score(doc)
    return doc


@erp_router.delete("/admin/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, admin: dict = Depends(require_area("operations"))):
    await db.suppliers.delete_one({"id": supplier_id})
    return {"ok": True}


# ----------------------------- Moteur de règles no-code -----------------------------
COND_TYPES = {"out_of_stock", "low_stock", "low_margin"}
ACTION_TYPES = {"hide", "alert", "set_margin"}


class RuleInput(BaseModel):
    name: str
    active: bool = True
    cond_type: str            # out_of_stock | low_stock | low_margin
    cond_value: float = 0.0   # seuil (stock ou %)
    action_type: str          # hide | alert | set_margin
    action_value: float = 0.0 # marge cible % pour set_margin


@erp_router.get("/admin/rules")
async def list_rules(admin: dict = Depends(require_area("operations"))):
    items = await db.rules.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"items": items}


@erp_router.post("/admin/rules")
async def create_rule(body: RuleInput, admin: dict = Depends(require_area("operations"))):
    if body.cond_type not in COND_TYPES:
        raise HTTPException(400, "Condition invalide")
    if body.action_type not in ACTION_TYPES:
        raise HTTPException(400, "Action invalide")
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = _now()
    await db.rules.insert_one(doc)
    doc.pop("_id", None)
    return doc


@erp_router.put("/admin/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleInput, admin: dict = Depends(require_area("operations"))):
    res = await db.rules.update_one({"id": rule_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Règle introuvable")
    return await db.rules.find_one({"id": rule_id}, {"_id": 0})


@erp_router.delete("/admin/rules/{rule_id}")
async def delete_rule(rule_id: str, admin: dict = Depends(require_area("operations"))):
    await db.rules.delete_one({"id": rule_id})
    return {"ok": True}


async def _add_alert(atype: str, message: str, product_id: str = "", rule_id: str = ""):
    """Crée une alerte non-résolue en évitant les doublons (même règle+produit)."""
    existing = await db.alerts.find_one({"rule_id": rule_id, "product_id": product_id, "resolved": False})
    if existing:
        return False
    await db.alerts.insert_one({
        "id": str(uuid.uuid4()), "type": atype, "message": message,
        "product_id": product_id, "rule_id": rule_id, "resolved": False, "created_at": _now(),
    })
    return True


def _matches(rule: dict, p: dict) -> bool:
    ct = rule["cond_type"]
    if ct == "out_of_stock":
        return p.get("in_stock") is False or (p.get("stock_total") is not None and p.get("stock_total") == 0)
    if ct == "low_stock":
        st = p.get("stock_total")
        return st is not None and st <= rule.get("cond_value", 0)
    if ct == "low_margin":
        m = product_margin_pct(p)
        return m is not None and m < rule.get("cond_value", 0)
    return False


async def run_rules() -> dict:
    """Évalue toutes les règles actives sur le catalogue et applique les actions."""
    rules = await db.rules.find({"active": True}, {"_id": 0}).to_list(1000)
    if not rules:
        return {"rules": 0, "matches": 0, "alerts": 0, "hidden": 0, "repriced": 0}
    products = await db.products.find({}, {"_id": 0}).to_list(5000)
    matches = alerts = hidden = repriced = 0
    for r in rules:
        for p in products:
            if not _matches(r, p):
                continue
            matches += 1
            at = r["action_type"]
            if at == "hide":
                if p.get("active", True):
                    await db.products.update_one({"id": p["id"]}, {"$set": {"active": False}})
                    hidden += 1
                    if await _add_alert("hide", f"« {p.get('title','')} » masqué automatiquement (règle {r['name']})", p["id"], r["id"]):
                        alerts += 1
            elif at == "set_margin":
                cost = product_cost(p)
                if cost:
                    new_price = round(cost * (1 + max(r.get("action_value", 0), 0) / 100.0), 2)
                    await db.products.update_one({"id": p["id"]}, {"$set": {"price": new_price}})
                    repriced += 1
                    if await _add_alert("reprice", f"Prix de « {p.get('title','')} » ajusté à {new_price}€ (règle {r['name']})", p["id"], r["id"]):
                        alerts += 1
            else:  # alert
                label = {"out_of_stock": "rupture de stock", "low_stock": "stock faible", "low_margin": "marge faible"}.get(r["cond_type"], r["cond_type"])
                if await _add_alert("alert", f"« {p.get('title','')} » : {label} (règle {r['name']})", p["id"], r["id"]):
                    alerts += 1
    logger.info(f"rules run: {matches} matches, {alerts} alerts, {hidden} hidden, {repriced} repriced")
    return {"rules": len(rules), "matches": matches, "alerts": alerts, "hidden": hidden, "repriced": repriced}


@erp_router.post("/admin/rules/run")
async def run_rules_endpoint(admin: dict = Depends(require_area("operations"))):
    return await run_rules()


# ----------------------------- Alertes -----------------------------
@erp_router.get("/admin/alerts")
async def list_alerts(admin: dict = Depends(require_area("operations")), include_resolved: bool = False):
    q = {} if include_resolved else {"resolved": False}
    items = await db.alerts.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items, "unresolved": await db.alerts.count_documents({"resolved": False})}


@erp_router.put("/admin/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, admin: dict = Depends(require_area("operations"))):
    await db.alerts.update_one({"id": alert_id}, {"$set": {"resolved": True, "resolved_at": _now()}})
    return {"ok": True}


@erp_router.post("/admin/alerts/clear")
async def clear_alerts(admin: dict = Depends(require_area("operations"))):
    await db.alerts.update_many({"resolved": False}, {"$set": {"resolved": True, "resolved_at": _now()}})
    return {"ok": True}
