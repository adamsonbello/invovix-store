import os
import logging
from datetime import datetime, timezone

from database import db
import cj as cjmod
import brevo as brevomod
import crm as crmmod
import notifications as notifmod
import publicapi as publicapimod

logger = logging.getLogger("invovix")


def _auto_fulfill() -> bool:
    return os.environ.get("CJ_AUTO_FULFILL", "true").lower() == "true"


def _recipient(order: dict):
    addr = order.get("shipping_address") or {}
    return (addr.get("email") or order.get("user_email") or "", addr.get("full_name") or "Client")


async def handle_paid_order(order_id: str):
    """Triggered when an order becomes paid: send confirmation email + create CJ order."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order or order.get("payment_status") != "paid":
        return
    frontend = os.environ.get("FRONTEND_URL", "")
    to_email, to_name = _recipient(order)

    # 1) Order confirmation email (idempotent)
    if not order.get("confirmation_email_sent") and to_email:
        try:
            if brevomod.send_order_confirmation(to_email, to_name, order, frontend):
                await db.orders.update_one({"id": order_id}, {"$set": {"confirmation_email_sent": True}})
        except Exception as e:
            logger.error(f"order confirmation email failed: {e}")

    # 1b) Loyalty points (idempotent)
    try:
        await crmmod.accrue_loyalty(order)
    except Exception as e:
        logger.error(f"loyalty accrual failed: {e}")

    # 1c) Multi-channel notification (Discord/Slack), once
    if not order.get("notify_sent"):
        try:
            total = float(order.get("total", 0) or 0)
            await notifmod.notify_channels(f"🛒 Nouvelle commande payée #{order_id[:8].upper()} — {total:.2f}€ ({to_name})")
            await db.orders.update_one({"id": order_id}, {"$set": {"notify_sent": True}})
        except Exception as e:
            logger.error(f"channel notify failed: {e}")

    # 2) CJ fulfillment (idempotent)
    if _auto_fulfill() and cjmod.cj_configured() and not order.get("cj_order_id"):
        try:
            res = await cjmod.create_cj_order(order)
            cj_order_id = res.get("orderId") or res.get("orderNum") or res.get("id")
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {
                    "cj_order_id": str(cj_order_id) if cj_order_id else None,
                    "fulfillment_status": "submitted",
                    "fulfillment_error": None,
                    "fulfilled_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            logger.info(f"CJ order created for {order_id}: {cj_order_id}")
        except Exception as e:
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {"fulfillment_status": "error", "fulfillment_error": str(e)}},
            )
            logger.error(f"CJ fulfillment failed for {order_id}: {e}")


async def sync_cj_order(order_id: str) -> dict:
    """Fetch CJ order detail, update tracking, and send shipping email when shipped."""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        return {"ok": False, "reason": "order not found"}
    cj_id = order.get("cj_order_id")
    if not cj_id:
        return {"ok": False, "reason": "no CJ order"}
    try:
        detail = await cjmod.get_cj_order(cj_id)
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    track = detail.get("trackNumber") or ""
    carrier = detail.get("logisticName") or ""
    track_url = detail.get("trackingUrl") or ""
    cj_status = detail.get("orderStatus") or ""

    update = {"cj_shipping_status": cj_status}
    if track:
        update["tracking_number"] = track
    if carrier:
        update["logistic_name"] = carrier
    if track_url:
        update["tracking_url"] = track_url

    shipped_now = False
    if track and order.get("status") not in ("shipped", "delivered"):
        update["status"] = "shipped"
        shipped_now = True

    await db.orders.update_one({"id": order_id}, {"$set": update})

    if shipped_now and not order.get("shipping_email_sent"):
        refreshed = await db.orders.find_one({"id": order_id}, {"_id": 0})
        to_email, to_name = _recipient(refreshed)
        try:
            if to_email and brevomod.send_shipping_notification(to_email, to_name, refreshed, os.environ.get("FRONTEND_URL", "")):
                await db.orders.update_one({"id": order_id}, {"$set": {"shipping_email_sent": True}})
        except Exception as e:
            logger.error(f"shipping email failed: {e}")

    return {"ok": True, "status": cj_status, "tracking_number": track, "carrier": carrier}
