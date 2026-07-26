"""Phase 3C Notifications multi-canal : Discord, Slack, SMS & WhatsApp (Twilio)."""
import os
import re
import asyncio
import logging
import httpx

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from security import require_admin
from extras import get_settings_doc

logger = logging.getLogger("invovix")
notif_router = APIRouter(prefix="/api")

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM_NUMBER", "")
TWILIO_WA_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")


def format_e164(num: str, default_cc: str = "33") -> str:
    if not num:
        return ""
    n = num.strip().replace(" ", "").replace(".", "").replace("-", "")
    if n.startswith("+"):
        return n
    n = re.sub(r"\D", "", n)
    if n.startswith("00"):
        return "+" + n[2:]
    if n.startswith("0"):
        return "+" + default_cc + n[1:]
    return "+" + n


def twilio_configured() -> bool:
    return bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)


def _send_twilio_sync(to: str, body: str, whatsapp: bool = False) -> str:
    from twilio.rest import Client
    from twilio.http.http_client import TwilioHttpClient
    client = Client(TWILIO_SID, TWILIO_TOKEN, http_client=TwilioHttpClient(timeout=8))
    if whatsapp:
        frm = TWILIO_WA_FROM or ("whatsapp:" + TWILIO_FROM)
        to = "whatsapp:" + format_e164(to)
    else:
        frm = TWILIO_FROM
        to = format_e164(to)
    msg = client.messages.create(body=body, from_=frm, to=to)
    return msg.sid


async def send_sms(to: str, body: str, whatsapp: bool = False) -> str:
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        raise RuntimeError("Twilio non configuré")
    return await asyncio.wait_for(asyncio.to_thread(_send_twilio_sync, to, body, whatsapp), timeout=15)


async def notify_channels(text: str):
    """Notification sur les canaux configurés (Discord/Slack/SMS/WhatsApp)."""
    settings = await get_settings_doc()
    if not settings.get("notify_new_order", False):
        return
    await _push(settings.get("discord_webhook_url", ""), settings.get("slack_webhook_url", ""), text)
    to = settings.get("notify_sms_to", "")
    if to and twilio_configured():
        if settings.get("sms_enabled"):
            try:
                await send_sms(to, text)
            except Exception as e:
                logger.error(f"sms notify failed: {e}")
        if settings.get("whatsapp_enabled"):
            try:
                await send_sms(to, text, whatsapp=True)
            except Exception as e:
                logger.error(f"whatsapp notify failed: {e}")


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


class TestSms(BaseModel):
    to: str
    whatsapp: bool = False


@notif_router.post("/admin/notifications/test-sms")
async def test_sms(body: TestSms, admin: dict = Depends(require_admin)):
    if not twilio_configured():
        raise HTTPException(400, "Twilio non configuré (SID/Token/numéro expéditeur manquants)")
    if not body.to:
        raise HTTPException(400, "Numéro destinataire requis")
    try:
        sid = await send_sms(body.to, "🔔 Test Invovix : vos notifications SMS/WhatsApp fonctionnent !", whatsapp=body.whatsapp)
        return {"ok": True, "sid": sid}
    except Exception as e:
        raise HTTPException(400, f"Échec Twilio : {e}")


@notif_router.get("/admin/notifications/status")
async def notif_status(admin: dict = Depends(require_admin)):
    return {"twilio_configured": twilio_configured(), "from": TWILIO_FROM,
            "whatsapp_from": TWILIO_WA_FROM}

