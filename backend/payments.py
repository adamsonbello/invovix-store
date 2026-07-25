import os
import uuid
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

from database import db
from security import get_current_user

payments_router = APIRouter(prefix="/api/payments")

PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
PAYPAL_BASE = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"


def paypal_configured() -> bool:
    return bool(os.environ.get("PAYPAL_CLIENT_ID", "").strip() and os.environ.get("PAYPAL_SECRET", "").strip())


async def _order_total(order: dict) -> float:
    return round(float(order["total"]), 2)


class CheckoutRequest(BaseModel):
    order_id: str
    origin_url: str


# ---------------- STRIPE (Flow B, dynamic amount) ----------------
@payments_router.post("/stripe/checkout")
async def stripe_checkout(body: CheckoutRequest, request: Request, user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": body.order_id}, {"_id": 0})
    if not order or order["user_id"] != user["id"]:
        raise HTTPException(404, "Order not found")

    amount = await _order_total(order)
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)

    success_url = f"{body.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{body.origin_url}/payment/cancel"
    req = CheckoutSessionRequest(
        amount=amount,
        currency="eur",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": order["id"], "user_id": user["id"]},
    )
    session = await checkout.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "order_id": order["id"],
        "user_id": user["id"],
        "amount": amount,
        "currency": "eur",
        "provider": "stripe",
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.orders.update_one({"id": order["id"]}, {"$set": {"payment_method": "stripe", "stripe_session_id": session.session_id}})
    return {"checkout_url": session.url, "session_id": session.session_id}


@payments_router.get("/status/{session_id}")
async def payment_status(session_id: str, request: Request):
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Transaction not found")

    if record.get("payment_status") != "paid":
        host_url = str(request.base_url)
        checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{host_url}api/webhook/stripe")
        try:
            status = await checkout.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": datetime.now(timezone.utc).isoformat()}},
                )
                await db.orders.update_one(
                    {"id": record["order_id"], "payment_status": {"$ne": "paid"}},
                    {"$set": {"payment_status": "paid", "status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}},
                )
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception:
            pass
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"], "order_id": record["order_id"]}


# ---------------- PAYPAL (REST Orders v2, dynamic amount) ----------------
async def _paypal_access_token() -> str:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{PAYPAL_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_SECRET"]),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()["access_token"]


@payments_router.post("/paypal/create/{order_id}")
async def paypal_create(order_id: str, user: dict = Depends(get_current_user)):
    if not paypal_configured():
        raise HTTPException(503, "PayPal not configured")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order or order["user_id"] != user["id"]:
        raise HTTPException(404, "Order not found")
    amount = await _order_total(order)
    token = await _paypal_access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{PAYPAL_BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": order_id,
                    "amount": {"currency_code": "EUR", "value": f"{amount:.2f}"},
                }],
            },
        )
        r.raise_for_status()
        pp = r.json()
    await db.orders.update_one({"id": order_id}, {"$set": {"payment_method": "paypal", "paypal_order_id": pp["id"]}})
    return {"paypal_order_id": pp["id"]}


@payments_router.post("/paypal/capture/{paypal_order_id}")
async def paypal_capture(paypal_order_id: str, user: dict = Depends(get_current_user)):
    if not paypal_configured():
        raise HTTPException(503, "PayPal not configured")
    token = await _paypal_access_token()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{PAYPAL_BASE}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        r.raise_for_status()
        cap = r.json()
    ref_id = cap["purchase_units"][0]["reference_id"]
    paid = cap.get("status") == "COMPLETED"
    if paid:
        await db.orders.update_one(
            {"id": ref_id},
            {"$set": {"payment_status": "paid", "status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    return {"status": cap.get("status"), "order_id": ref_id, "paid": paid}


@payments_router.get("/config")
async def payments_config():
    return {"paypal": paypal_configured(), "stripe": True}
