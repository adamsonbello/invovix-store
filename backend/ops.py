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
from extras import get_settings_doc
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

    # --- Phase 2 : bénéfice, ROAS, opérations, série mensuelle ---
    prods = await db.products.find({}, {"_id": 0, "id": 1, "buy_price": 1, "cost_price": 1, "price": 1, "in_stock": 1, "stock_total": 1, "active": 1}).to_list(5000)
    cost_map = {p["id"]: float(p.get("buy_price") or p.get("cost_price") or 0) for p in prods}
    total_cost = 0.0
    revenue_30 = 0.0
    for o in paid:
        is_30 = (o.get("created_at") or "") >= since
        if is_30:
            revenue_30 += o.get("total", 0)
        for it in o.get("items", []):
            c = cost_map.get(it.get("product_id"), 0) * it.get("quantity", 0)
            total_cost += c
    gross_profit = round(revenue - total_cost, 2)

    settings = await get_settings_doc()
    ad_spend = float(settings.get("ad_spend_30d") or 0)
    net_profit_30d = round(revenue_30 - ad_spend, 2)
    roas = round(revenue_30 / ad_spend, 2) if ad_spend else 0.0
    roi = round((revenue_30 - ad_spend) / ad_spend * 100, 1) if ad_spend else 0.0

    out_of_stock = sum(1 for p in prods if p.get("in_stock") is False or p.get("stock_total") == 0)
    low_stock = sum(1 for p in prods if isinstance(p.get("stock_total"), (int, float)) and 0 < p.get("stock_total") <= 5)
    to_ship = await db.orders.count_documents({"payment_status": "paid", "status": {"$in": ["processing", "paid"]}})
    unresolved_alerts = await db.alerts.count_documents({"resolved": False})

    # 12-month revenue series
    months = []
    ref = _today().replace(day=1)
    for i in range(11, -1, -1):
        y = ref.year
        m = ref.month - i
        while m <= 0:
            m += 12; y -= 1
        months.append(f"{y}-{m:02d}")
    rev_by_month = {mo: 0.0 for mo in months}
    for o in paid:
        mo = (o.get("created_at") or "")[:7]
        if mo in rev_by_month:
            rev_by_month[mo] += o.get("total", 0)
    revenue_monthly = [{"month": mo, "revenue": round(rev_by_month[mo], 2)} for mo in months]

    return {
        "revenue": revenue,
        "paid_orders": paid_count,
        "aov": aov,
        "total_orders": await db.orders.count_documents({}),
        "status_breakdown": statuses,
        "revenue_series": revenue_series,
        "revenue_monthly": revenue_monthly,
        "top_products": top_products,
        "new_customers_30d": new_customers,
        "total_customers": total_customers,
        "visits_30d": visits_30d,
        "conversion_rate": conversion,
        "gross_profit": gross_profit,
        "revenue_30d": round(revenue_30, 2),
        "ad_spend_30d": ad_spend,
        "net_profit_30d": net_profit_30d,
        "roas": roas,
        "roi": roi,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "to_ship": to_ship,
        "unresolved_alerts": unresolved_alerts,
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
    # Attempt an automatic Stripe refund; falls back to manual for PayPal / missing tx.
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


# ----------------------------- Invoice PDF (compliant) -----------------------------
async def _next_invoice_number(order: dict) -> str:
    """Continuous sequential numbering (mandatory). Idempotent per order."""
    if order.get("invoice_number"):
        return order["invoice_number"]
    year = _today().year
    doc = await db.counters.find_one_and_update(
        {"id": f"invoice-{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = (doc or {}).get("seq", 1)
    number = f"INV-{year}-{seq:05d}"
    await db.orders.update_one(
        {"id": order["id"]},
        {"$set": {"invoice_number": number, "invoice_date": _today().isoformat()}},
    )
    return number


def _vat_breakdown(order: dict, settings: dict):
    """Returns (regime, rate, total_ht, total_tva, total_ttc, vat_note)."""
    total = float(order.get("total", 0) or 0)
    regime = settings.get("vat_regime", "franchise")
    rate = float(settings.get("vat_rate", 20.0) or 0)
    if regime == "assujetti" and rate > 0:
        ht = round(total / (1 + rate / 100), 2)
        tva = round(total - ht, 2)
        note = f"TVA {rate:.0f}% incluse."
        return regime, rate, ht, tva, total, note
    return regime, 0.0, total, 0.0, total, "TVA non applicable, art. 293 B du CGI."


def _build_invoice_pdf(order: dict, settings: dict, number: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    ref = order["id"][:8].upper()
    regime, rate, ht, tva, ttc, vat_note = _vat_breakdown(order, settings)
    y = h - 22 * mm

    # Header — seller legal identity (mandatory)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, y, settings.get("company_name") or "Invovix")
    c.setFont("Helvetica", 8)
    seller_lines = []
    if settings.get("company_legal_form"):
        seller_lines.append(settings["company_legal_form"])
    if settings.get("company_address"):
        seller_lines.append(settings["company_address"])
    ids = []
    if settings.get("siret"): ids.append(f"SIRET {settings['siret']}")
    elif settings.get("siren"): ids.append(f"SIREN {settings['siren']}")
    if settings.get("vat_number"): ids.append(f"TVA {settings['vat_number']}")
    if ids: seller_lines.append(" · ".join(ids))
    seller_lines.append("contact@invovix.store · invovix.store")
    yy = y - 6 * mm
    for ln in seller_lines:
        c.drawString(20 * mm, yy, ln[:95]); yy -= 4.2 * mm

    # Invoice title block
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(w - 20 * mm, y, "FACTURE")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 20 * mm, y - 6 * mm, f"N° {number}")
    c.drawRightString(w - 20 * mm, y - 11 * mm, f"Date : {(order.get('invoice_date') or order.get('created_at') or '')[:10]}")
    c.drawRightString(w - 20 * mm, y - 16 * mm, f"Commande : #{ref}")

    # Buyer + delivery
    addr = order.get("shipping_address") or {}
    y = yy - 8 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Client / Adresse de livraison :")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y - 5 * mm, addr.get("full_name", ""))
    c.drawString(20 * mm, y - 10 * mm, addr.get("address", ""))
    c.drawString(20 * mm, y - 15 * mm, f"{addr.get('postal_code','')} {addr.get('city','')} - {addr.get('country','')}")
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, y - 21 * mm, "Nature de l'opération : Livraison de biens")

    # Line items table
    y -= 32 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20 * mm, y, "Désignation")
    c.drawString(120 * mm, y, "Qté")
    c.drawString(135 * mm, y, "PU TTC")
    c.drawRightString(w - 20 * mm, y, "Total TTC")
    c.line(20 * mm, y - 2 * mm, w - 20 * mm, y - 2 * mm)
    y -= 8 * mm
    c.setFont("Helvetica", 8)
    for it in order.get("items", []):
        name = it.get("title", "")[:60]
        if it.get("variant_name"):
            name += f" ({it['variant_name']})"
        c.drawString(20 * mm, y, name[:72])
        c.drawString(120 * mm, y, str(it.get("quantity", 1)))
        c.drawString(135 * mm, y, f"{it.get('price', 0):.2f}")
        c.drawRightString(w - 20 * mm, y, f"{it.get('line_total', 0):.2f}EUR")
        y -= 5.5 * mm
        if y < 60 * mm:
            c.showPage(); y = h - 30 * mm; c.setFont("Helvetica", 8)

    # Totals
    y -= 3 * mm
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    if order.get("discount"):
        c.drawRightString(w - 45 * mm, y, f"Réduction {order.get('promo_code','') or ''} :")
        c.drawRightString(w - 20 * mm, y, f"-{order.get('discount', 0):.2f}EUR"); y -= 5 * mm
    c.drawRightString(w - 45 * mm, y, "Livraison :")
    c.drawRightString(w - 20 * mm, y, "Offerte" if not order.get("shipping") else f"{order.get('shipping'):.2f}EUR"); y -= 5 * mm
    c.drawRightString(w - 45 * mm, y, "Total HT :")
    c.drawRightString(w - 20 * mm, y, f"{ht:.2f}EUR"); y -= 5 * mm
    if tva > 0:
        c.drawRightString(w - 45 * mm, y, f"TVA ({rate:.0f}%) :")
        c.drawRightString(w - 20 * mm, y, f"{tva:.2f}EUR"); y -= 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 45 * mm, y, "Total TTC :")
    c.drawRightString(w - 20 * mm, y, f"{ttc:.2f}EUR")

    # Legal footer (mandatory mentions)
    c.setFont("Helvetica", 7)
    c.drawString(20 * mm, 26 * mm, vat_note)
    c.drawString(20 * mm, 22 * mm, "Paiement à réception. Pas d'escompte pour paiement anticipé. Pénalités de retard : 3x taux légal ; indemnité forfaitaire recouvrement : 40€.")
    c.drawString(20 * mm, 18 * mm, "Facture émise par Invovix — document conservé conformément aux obligations légales (durée 10 ans).")
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
    settings = await get_settings_doc()
    number = await _next_invoice_number(order)
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})  # reload with invoice_date
    pdf = _build_invoice_pdf(order, settings, number)
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )


# ----------------------------- e-reporting B2C (transmission des données) -----------------------------
@ops_router.get("/admin/ereporting")
async def ereporting(admin: dict = Depends(require_admin), days: int = 90, format: str = "json"):
    """Aggregated B2C transaction data (per day × VAT rate) for transmission to a PDP/PPF.
    Conforme à l'obligation de e-reporting des ventes aux particuliers."""
    settings = await get_settings_doc()
    regime = settings.get("vat_regime", "franchise")
    rate = float(settings.get("vat_rate", 20.0) or 0) if regime == "assujetti" else 0.0
    since = (_today() - timedelta(days=days)).isoformat()
    paid = await db.orders.find(
        {"payment_status": "paid", "created_at": {"$gte": since}}, {"_id": 0}
    ).to_list(50000)

    agg = {}
    for o in paid:
        day = (o.get("created_at") or "")[:10]
        ttc = float(o.get("total", 0) or 0)
        ht = round(ttc / (1 + rate / 100), 2) if rate else ttc
        tva = round(ttc - ht, 2)
        key = (day, rate)
        e = agg.setdefault(key, {"date": day, "vat_rate": rate, "count": 0, "total_ttc": 0.0, "total_ht": 0.0, "total_tva": 0.0})
        e["count"] += 1
        e["total_ttc"] = round(e["total_ttc"] + ttc, 2)
        e["total_ht"] = round(e["total_ht"] + ht, 2)
        e["total_tva"] = round(e["total_tva"] + tva, 2)
    rows = sorted(agg.values(), key=lambda x: x["date"])

    if format == "csv":
        lines = ["date;taux_tva;nb_operations;total_ht;total_tva;total_ttc;devise;type"]
        for r in rows:
            lines.append(f"{r['date']};{r['vat_rate']:.0f};{r['count']};{r['total_ht']:.2f};{r['total_tva']:.2f};{r['total_ttc']:.2f};EUR;B2C")
        csv = "\n".join(lines)
        return StreamingResponse(
            BytesIO(csv.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="ereporting-B2C-{_today().strftime("%Y%m%d")}.csv"'},
        )

    return {
        "regime": regime,
        "vat_rate": rate,
        "period_days": days,
        "operation_type": "B2C",
        "totals": {
            "count": sum(r["count"] for r in rows),
            "total_ttc": round(sum(r["total_ttc"] for r in rows), 2),
            "total_ht": round(sum(r["total_ht"] for r in rows), 2),
            "total_tva": round(sum(r["total_tva"] for r in rows), 2),
        },
        "rows": rows,
    }
