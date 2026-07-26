"""Phase 3C Notifications multi-canal : Discord & Slack (webhooks)."""
import logging
import httpx

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from security import require_admin
from extras import get_settings_doc

logger = logging.getLogger("invovix")
notif_router = APIRouter(prefix="/api")


async def notify_channels(text: str):
    """Envoie une notification texte sur les canaux configurés (Discord/Slack)."""
    settings = await get_settings_doc()
    if not settings.get("notify_new_order", False):
        return
    await _push(settings.get("discord_webhook_url", ""), settings.get("slack_webhook_url", ""), text)


async def _push(discord_url: str, slack_url: str, text: str):
    async with httpx.AsyncClient(timeout=10) as c:
        if discord_url:
            try:
                await c.post(discord_url, json={"content": text})
            except Exception as e:
                logger.error(f"discord notify failed: {e}")
        if slack_url:
            try:
                await c.post(slack_url, json={"text": text})
            except Exception as e:
                logger.error(f"slack notify failed: {e}")


class TestNotif(BaseModel):
    discord_webhook_url: str = ""
    slack_webhook_url: str = ""


@notif_router.post("/admin/notifications/test")
async def test_notification(body: TestNotif, admin: dict = Depends(require_admin)):
    if not body.discord_webhook_url and not body.slack_webhook_url:
        raise HTTPException(400, "Aucun webhook fourni")
    await _push(body.discord_webhook_url, body.slack_webhook_url, "🔔 Test de notification Invovix — la connexion fonctionne !")
    return {"ok": True}
