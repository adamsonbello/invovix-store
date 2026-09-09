"""Notifications Web Push (VAPID)."""
import os
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

from database import db
from security import get_current_user_optional, require_area

logger = logging.getLogger("invovix.push")
push_router = APIRouter(prefix="/api")

VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
VAPID_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:contact@invovix.store").strip()


def push_configured() -> bool:
    return bool(VAPID_PUBLIC and VAPID_PRIVATE)


class SubscriptionInput(BaseModel):
    endpoint: str
    keys: dict


class PushSendInput(BaseModel):
    title: str
    body: str
    url: str = "/"


@push_router.get("/push/vapid-public-key")
async def vapid_public_key():
    return {"public_key": VAPID_PUBLIC, "configured": push_configured()}


@push_router.post("/push/subscribe")
async def subscribe(body: SubscriptionInput, user: dict = Depends(get_current_user_optional)):
    if not push_configured():
        raise HTTPException(503, "Web Push non configuré (clés VAPID manquantes)")
    doc = {
        "endpoint": body.endpoint,
        "keys": body.keys,
        "user_id": user["id"] if user else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.push_subscriptions.update_one({"endpoint": body.endpoint}, {"$set": doc}, upsert=True)
    return {"ok": True}


@push_router.post("/push/unsubscribe")
async def unsubscribe(body: SubscriptionInput):
    await db.push_subscriptions.delete_one({"endpoint": body.endpoint})
    return {"ok": True}


async def send_push_to_all(title: str, body: str, url: str = "/") -> dict:
    """Envoie une notification à tous les abonnés. Purge les abonnements expirés."""
    if not push_configured():
        return {"sent": 0, "failed": 0, "reason": "not configured"}
    subs = await db.push_subscriptions.find({}, {"_id": 0}).to_list(5000)
    payload = json.dumps({"title": title, "body": body, "url": url})
    sent, failed, stale = 0, 0, []
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": s["keys"]},
                data=payload,
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims={"sub": VAPID_EMAIL},
            )
            sent += 1
        except WebPushException as e:
            failed += 1
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                stale.append(s["endpoint"])
        except Exception as e:
            failed += 1
            logger.error(f"push error: {e}")
    if stale:
        await db.push_subscriptions.delete_many({"endpoint": {"$in": stale}})
    return {"sent": sent, "failed": failed, "pruned": len(stale), "total": len(subs)}


@push_router.get("/admin/push/stats")
async def push_stats(admin: dict = Depends(require_area("marketing"))):
    count = await db.push_subscriptions.count_documents({})
    return {"subscribers": count, "configured": push_configured()}


@push_router.post("/admin/push/send")
async def admin_push_send(body: PushSendInput, admin: dict = Depends(require_area("marketing"))):
    res = await send_push_to_all(body.title, body.body, body.url)
    return res
