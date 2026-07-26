import os
import uuid
import asyncio
import logging
from io import BytesIO
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import stripe

from database import db
from security import get_current_user, require_admin
import cj as cjmod
import brevo as brevomod

logger = logging.getLogger("invovix")
ops_router = APIRouter(prefix="/api")
stripe.api_key = os.environ.get("STRIPE_API_KEY", "")


def _today():
    return datetime.now(timezone.utc)


# ----------------------------- Analytics -----------------------------
@ops_router.post("/track/pageview")
async def track_pageview():
    day = _today().strftime("%Y-%m-%d")
    await db.analytics_visits.update_one({"date": day}, {"$inc": {"count": 1}}, upsert=True)
    return {"ok": True}


@ops_router.get("/admin/analytics")
async def analytics(admin: dict = Depends(require_admin)):
    paid = await db.orders.find({"payment_status": "paid"}, {"_id": 0}).to_list(20000)
    revenue = round(sum(o.get("total", 0) for o in paid), 2)
    paid_count = len(paid)
    aov = round(revenue / paid_count, 2) if paid_count else 0.0

    # status breakdown
    statuses = {}
    for s in ["pending", "processing", "shipped", "delivered", "cancelled"]:
        statuses[s] = await db.orders.count_documents({"status": s})

    # 30-day revenue series
    days = [( _today() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    rev_by_day = {d: 0.0 for d in days}
    for o in paid:
        d = (o.get("created_at") or "")[:10]
        if d in rev_by_day:
            rev_by_day[d] += o.get("total", 0)
    revenue_series = [{"date": d, "revenue": round(rev_by_day[d], 2)} for d in days]

    # top products
    counter = {}
    for o in paid:
        for it in o.get("items", []):
            key = it.get("product_id")
            if not key:
                continue
            entry = counter.setdefault(key, {"title": it.get("title", ""), "qty": 0, "revenue": 0.0})
            entry["qty"] += it.get("quantity", 0)
            entry["revenue"] += it.get("line_total", it.get("price", 0) * it.get("quantity", 0))
    top_products = sorted(counter.values(), key=lambda x: x["qty"], reverse=True)[:5]
    for t in top_products:
        t["revenue"] = round(t["revenue"], 2)

    # customers + visits + conversion (30d)
    since = ( _today() - timedelta(days=30)).isoformat()
    new_customers = await db.users.count_documents({"role": "customer", "created_at": {"$gte": since}})
    total_customers = await db.users.count_documents({"role": "customer"})
    visits_docs = await db.analytics_visits.find({"date": {"$in": days}}, {"_id": 0}).to_list(60)
    visits_30d = sum(v.get("count", 0) for v in visits_docs)
    orders_30d = sum(1 for o in paid if (o.get("created_at") or "")[:10] in rev_by_day)
    conversion = round((orders_30d / visits_30d) * 100, 2) if visits_30d else 0.0

    return {
        "revenue": revenue,
        "paid_orders": paid_count,
        "aov": aov,
        "total_orders": await db.orders.count_documents({}),
        "status_breakdown": statuses,
        "revenue_series": revenue_series,
        "top_products": top_products,
        "new_customers_30d": new_customers,
        "total_customers": total_customers,
        "visits_30d": visits_30d,
        "conversion_rate": conversion,
    }


# ----------------------------- Stock sync -----------------------------
@ops_router.post("/admin/products/{product_id}/sync-stock")
async def sync_stock(product_id: str, admin: dict = Depends(require_admin)):
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Produit introuvable")
    return await cjmod.sync_product_stock(p)


async def _sync_all_stock():
    products = await db.products.find({"source": "cjdropshipping"}, {"_id": 0}).to_list(2000)
    for p in products:
        try:
            await cjmod.sync_product_stock(p)
        except Exception as e:
            logger.error(f"stock sync failed {p.get('id')}: {e}")
        await asyncio.sleep(1.0)
    logger.info(f"stock sync-all done: {len(products)} products")


@ops_router.post("/admin/products/sync-stock-all")
async def sync_stock_all(admin: dict = Depends(require_admin)):
    count = await db.products.count_documents({"source": "cjdropshipping"})
    asyncio.create_task(_sync_all_stock())
    return {"ok": True, "queued": count}


# ----------------------------- Returns & refunds -----------------------------
class ReturnInput(BaseModel):
    order_id: str
    reason: str


class ReturnDecision(BaseModel):
    action: str  # approve | reject
    admin_note: str = ""


@ops_router.post("/returns")
async def create_return(body: ReturnInput, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": body.order_id, "user_id": user["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Commande introuvable")
    if order.get("payment_status") != "paid":
        raise HTTPException(400, "Cette commande n'est pas éligible à un retour.")
    if await db.returns.find_one({"order_id": body.order_id, "status": {"$in": ["requested", "approved", "refunded"]}}):
        raise HTTPException(400, "Une demande de retour existe déjà pour cette commande.")
    doc = {
        "id": str(uuid.uuid4()),
        "order_id": body.order_id,
        "user_id": user["id"],
        "user_email": order.get("user_email"),
        "order_ref": body.order_id[:8].upper(),
        "amount": order.get("total", 0),
        "reason": body.reason,
        "status": "requested",
        "admin_note": "",
        "created_at": _today().isoformat(),
    }
    await db.returns.insert_one(doc)
    await db.orders.update_one({"id": body.order_id}, {"$set": {"return_status": "requested"}})
    doc.pop("_id", None)
    return doc


@ops_router.get("/returns")
async def my_returns(user: dict = Depends(get_current_user)):
    items = await db.returns.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@ops_router.get("/admin/returns")
async def list_returns(admin: dict = Depends(require_admin)):
    items = await db.returns.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"items": items}


async def _stripe_refund(order_id: str, amount: float) -> dict:
    tx = await db.payment_transactions.find_one({"order_id": order_id, "provider": "stripe"}, {"_id": 0})
    if not tx or not tx.get("session_id") or not stripe.api_key:
        return {"refunded": False, "reason": "manual"}
    try:
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, tx["session_id"])
        pi = session.get("payment_intent")
        if not pi:
            return {"refunded": False, "reason": "no payment_intent"}
        refund = await asyncio.to_thread(stripe.Refund.create, payment_intent=pi)
        return {"refunded": refund.get("status") in ("succeeded", "pending"), "refund_id": refund.get("id")}
    except Exception as e:
        logger.error(f"stripe refund failed {order_id}: {e}")
        return {"refunded": False, "reason": str(e)}


@ops_router.put("/admin/returns/{return_id}")
async def decide_return(return_id: str, body: ReturnDecision, admin: dict = Depends(require_admin)):
    ret = await db.returns.find_one({"id": return_id}, {"_id": 0})
    if not ret:
        raise HTTPException(404, "Demande introuvable")
    if body.action == "reject":
        await db.returns.update_one({"id": return_id}, {"$set": {"status": "rejected", "admin_note": body.admin_note}})
        await db.orders.update_one({"id": ret["order_id"]}, {"$set": {"return_status": "rejected"}})
        return {"status": "rejected"}
    if body.action != "approve":
        raise HTTPException(400, "Action invalide")

    order = await db.orders.find_one({"id": ret["order_id"]}, {"_id": 0})
    refund_res = {"refunded": False, "reason": "manual"}
    if order and (order.get("payment_method") == "stripe" or True):
        refund_res = await _stripe_refund(ret["order_id"], ret.get("amount", 0))
    new_status = "refunded" if refund_res.get("refunded") else "approved"
    await db.returns.update_one(
        {"id": return_id},
        {"$set": {"status": new_status, "admin_note": body.admin_note, "refund": refund_res, "decided_at": _today().isoformat()}},
    )
    await db.orders.update_one(
        {"id": ret["order_id"]},
        {"$set": {"status": "cancelled", "return_status": new_status,
                  "payment_status": "refunded" if refund_res.get("refunded") else order.get("payment_status")}},
    )
    return {"status": new_status, "refund": refund_res}


# ----------------------------- Invoice PDF -----------------------------
def _build_invoice_pdf(order: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    ref = order["id"][:8].upper()
    y = h - 30 * mm

    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, y, "INVOVIX")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 20 * mm, y, "invovix.store")
    c.drawRightString(w - 20 * mm, y - 5 * mm, "contact@invovix.store")

    y -= 20 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, f"Facture #{ref}")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y - 6 * mm, f"Date : {(order.get('created_at') or '')[:10]}")

    addr = order.get("shipping_address") or {}
    c.drawString(20 * mm, y - 14 * mm, "Facturé à :")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y - 19 * mm, addr.get("full_name", ""))
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y - 24 * mm, f"{addr.get('address','')}")
    c.drawString(20 * mm, y - 29 * mm, f"{addr.get('postal_code','')} {addr.get('city','')} - {addr.get('country','')}")

    # table header
    y -= 42 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Produit")
    c.drawString(120 * mm, y, "Qté")
    c.drawString(140 * mm, y, "PU")
    c.drawRightString(w - 20 * mm, y, "Total")
    c.line(20 * mm, y - 2 * mm, w - 20 * mm, y - 2 * mm)
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    for it in order.get("items", []):
        name = it.get("title", "")[:60]
        if it.get("variant_name"):
            name += f" ({it['variant_name']})"
        c.drawString(20 * mm, y, name[:70])
        c.drawString(120 * mm, y, str(it.get("quantity", 1)))
        c.drawString(140 * mm, y, f"{it.get('price', 0):.2f}EUR")
        c.drawRightString(w - 20 * mm, y, f"{it.get('line_total', 0):.2f}EUR")
        y -= 6 * mm

    y -= 4 * mm
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 45 * mm, y, "Sous-total :")
    c.drawRightString(w - 20 * mm, y, f"{order.get('subtotal', 0):.2f}EUR")
    if order.get("discount"):
        y -= 5 * mm
        c.drawRightString(w - 45 * mm, y, f"Réduction {order.get('promo_code','') or ''} :")
        c.drawRightString(w - 20 * mm, y, f"-{order.get('discount', 0):.2f}EUR")
    y -= 5 * mm
    c.drawRightString(w - 45 * mm, y, "Livraison :")
    c.drawRightString(w - 20 * mm, y, "Offerte" if not order.get("shipping") else f"{order.get('shipping'):.2f}EUR")
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 45 * mm, y, "TOTAL TTC :")
    c.drawRightString(w - 20 * mm, y, f"{order.get('total', 0):.2f}EUR")

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(20 * mm, 20 * mm, "TVA non applicable / incluse selon régime. Document généré automatiquement par Invovix.")
    c.showPage()
    c.save()
    return buf.getvalue()


@ops_router.get("/orders/{order_id}/invoice")
async def order_invoice(order_id: str, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Commande introuvable")
    if user["role"] != "admin" and order.get("user_id") != user["id"]:
        raise HTTPException(403, "Accès refusé")
    if order.get("payment_status") != "paid":
        raise HTTPException(400, "Facture disponible uniquement pour les commandes payées.")
    pdf = _build_invoice_pdf(order)
    ref = order_id[:8].upper()
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Invovix-Facture-{ref}.pdf"'},
    )
