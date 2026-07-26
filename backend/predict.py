"""Module — Tableaux prédictifs & moteur de prix IA.
Prévision de CA (régression linéaire + moyenne mobile) et recommandations de prix."""
import logging
from datetime import datetime, timezone, timedelta

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from security import require_area
from extras import get_settings_doc
import ai as aimod

logger = logging.getLogger("invovix")
predict_router = APIRouter(prefix="/api")


def _now():
    return datetime.now(timezone.utc)


@predict_router.get("/admin/predict/forecast")
async def forecast(admin: dict = Depends(require_area("analytics")), history_days: int = 90, horizon: int = 30):
    history_days = max(14, min(history_days, 180))
    horizon = max(7, min(horizon, 90))
    since = (_now() - timedelta(days=history_days)).isoformat()
    paid = await db.orders.find(
        {"payment_status": "paid", "created_at": {"$gte": since}}, {"_id": 0, "created_at": 1, "total": 1}
    ).to_list(50000)

    days = [(_now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(history_days - 1, -1, -1)]
    rev = {d: 0.0 for d in days}
    for o in paid:
        d = (o.get("created_at") or "")[:10]
        if d in rev:
            rev[d] += float(o.get("total", 0) or 0)
    y = np.array([rev[d] for d in days], dtype=float)

    # Régression linéaire sur la tendance
    x = np.arange(len(y))
    trend_slope = 0.0
    intercept = float(y.mean()) if len(y) else 0.0
    if len(y) >= 2 and y.any():
        trend_slope, intercept = np.polyfit(x, y, 1)
    # Moyenne mobile 7j pour lisser le niveau de base
    window = min(7, len(y)) or 1
    base_level = float(y[-window:].mean()) if len(y) else 0.0

    # Prévision : niveau lissé + pente projetée (bornée à >= 0)
    forecast_days = [(_now() + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(horizon)]
    fc = []
    for i in range(horizon):
        val = base_level + trend_slope * (i + 1) * 0.5
        fc.append({"date": forecast_days[i], "revenue": round(max(val, 0.0), 2)})

    hist = [{"date": d, "revenue": round(rev[d], 2)} for d in days]
    predicted_total = round(sum(f["revenue"] for f in fc), 2)
    recent_avg = float(y[-30:].mean()) if len(y) >= 1 else 0.0
    prev_avg = float(y[-60:-30].mean()) if len(y) >= 60 else recent_avg
    growth = round(((recent_avg - prev_avg) / prev_avg * 100), 1) if prev_avg else 0.0
    trend = "hausse" if trend_slope > 0.5 else ("baisse" if trend_slope < -0.5 else "stable")

    # Prévision de demande par produit (30j vs 30j précédents)
    d30 = (_now() - timedelta(days=30)).isoformat()
    d60 = (_now() - timedelta(days=60)).isoformat()
    orders_items = await db.orders.find(
        {"payment_status": "paid", "created_at": {"$gte": d60}}, {"_id": 0, "created_at": 1, "items": 1}
    ).to_list(50000)
    cur, prev = {}, {}
    for o in orders_items:
        recent = (o.get("created_at") or "") >= d30
        for it in o.get("items", []):
            t = it.get("title") or it.get("product_id")
            (cur if recent else prev)[t] = (cur if recent else prev).get(t, 0) + it.get("quantity", 1)
    demand = []
    for t, q in sorted(cur.items(), key=lambda x: x[1], reverse=True)[:10]:
        pq = prev.get(t, 0)
        g = round(((q - pq) / pq * 100), 0) if pq else (100.0 if q else 0.0)
        demand.append({"title": t, "qty_30d": q, "qty_prev_30d": pq, "growth": g})

    return {
        "history": hist,
        "forecast": fc,
        "predicted_total": predicted_total,
        "horizon": horizon,
        "trend": trend,
        "growth_30d": growth,
        "daily_avg_recent": round(recent_avg, 2),
        "demand": demand,
    }


@predict_router.get("/admin/predict/pricing")
async def pricing_suggestions(admin: dict = Depends(require_area("analytics")), target_margin: float = 0.0):
    settings = await get_settings_doc()
    default_target = target_margin or float(settings.get("target_margin") or 55.0)
    prods = await db.products.find({}, {"_id": 0}).to_list(5000)
    suggestions = []
    for p in prods:
        price = float(p.get("price") or 0)
        cost = float(p.get("buy_price") or p.get("cost_price") or 0)
        if not cost or not price:
            continue
        margin = round((price - cost) / price * 100, 1)
        ceiling = float(p.get("compare_at_price") or 0)
        target_price = round(cost / (1 - default_target / 100.0), 2) if default_target < 100 else price
        # borne : ne pas dépasser le prix barré si défini
        if ceiling and target_price > ceiling:
            target_price = ceiling
        delta = round(target_price - price, 2)
        if abs(delta) < 0.5:
            continue
        reason = ("Marge sous l'objectif → hausse conseillée" if delta > 0
                  else "Prix au-dessus de l'objectif → baisse possible pour la compétitivité")
        suggestions.append({
            "id": p["id"], "title": p.get("title", ""),
            "price": round(price, 2), "cost": round(cost, 2),
            "margin_pct": margin, "target_margin": default_target,
            "suggested_price": target_price, "delta": delta, "reason": reason,
        })
    suggestions.sort(key=lambda s: abs(s["delta"]), reverse=True)
    return {"target_margin": default_target, "items": suggestions[:100], "count": len(suggestions)}


class ApplyPriceInput(BaseModel):
    product_id: str
    price: float


@predict_router.post("/admin/predict/pricing/apply")
async def apply_price(body: ApplyPriceInput, admin: dict = Depends(require_area("catalog"))):
    res = await db.products.update_one({"id": body.product_id}, {"$set": {"price": round(body.price, 2)}})
    if res.matched_count == 0:
        raise HTTPException(404, "Produit introuvable")
    return {"ok": True, "product_id": body.product_id, "price": round(body.price, 2)}


@predict_router.post("/admin/predict/ai-price/{product_id}")
async def ai_price(product_id: str, admin: dict = Depends(require_area("ai"))):
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Produit introuvable")
    import re as _re
    plain = _re.sub(r"<[^>]+>", " ", p.get("description") or "")[:600]
    data = await aimod.run_score(
        p.get("title", ""), plain, p.get("category", ""),
        p.get("price", 0) or 0, p.get("buy_price", 0) or p.get("cost_price", 0) or 0,
    )
    if not data:
        raise HTTPException(502, "Réponse IA illisible")
    return {
        "product_id": product_id,
        "current_price": p.get("price", 0),
        "recommended_price": data.get("recommended_price"),
        "opportunity_score": data.get("opportunity_score"),
        "verdict": data.get("verdict"),
        "reasons": data.get("reasons", []),
    }
