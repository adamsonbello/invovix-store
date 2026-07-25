import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger("invovix")

SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587


def _rest_key():
    return os.environ.get("BREVO_API_KEY", "").strip()


def _smtp_ready():
    return bool(os.environ.get("BREVO_SMTP_LOGIN", "").strip() and os.environ.get("BREVO_SMTP_KEY", "").strip())


def brevo_configured() -> bool:
    return bool(_rest_key()) or _smtp_ready()


def _build_content(to_name: str, order: dict, frontend_url: str):
    first = (order.get("items") or [{}])[0]
    product_id = first.get("product_id", "")
    base = frontend_url.rstrip("/")
    review_link = f"{base}/product/{product_id}" if product_id else f"{base}/account"
    order_ref = (order.get("id", "") or "")[:8].upper()
    subject = "Votre colis est arrivé — donnez votre avis ✦ Invovix"
    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto;color:#0a0a0a">
      <div style="background:#0a0a0a;color:#fff;padding:28px 24px">
        <h1 style="margin:0;font-size:26px;letter-spacing:-1px;text-transform:uppercase">INVOVIX</h1>
      </div>
      <div style="padding:28px 24px">
        <p>Bonjour {to_name},</p>
        <p>Votre commande <strong>#{order_ref}</strong> a bien été livrée. Nous espérons qu'elle vous ravit !</p>
        <p>Votre retour compte énormément. Prenez un instant pour noter <strong>le produit</strong> et <strong>la livraison / le transport</strong>.</p>
        <p style="margin:28px 0">
          <a href="{review_link}" style="background:#ff3300;color:#fff;text-decoration:none;padding:14px 26px;border-radius:999px;font-weight:bold">Laisser mon avis</a>
        </p>
        <hr style="border:none;border-top:1px solid #e5e5e5"/>
        <p style="font-size:13px;color:#777">Hello {to_name}, your order #{order_ref} has been delivered. We'd love your feedback on the product and delivery — <a href="{review_link}">leave a review</a>.</p>
      </div>
      <div style="padding:16px 24px;background:#f5f5f5;font-size:12px;color:#999">© Invovix · invovix.store</div>
    </div>
    """
    text = (
        f"Bonjour {to_name}, votre commande #{order_ref} a été livrée. "
        f"Donnez votre avis (produit + transport) : {review_link}"
    )
    return subject, html, text


def _send_email(to_email: str, to_name: str, subject: str, html: str, text: str) -> bool:
    if not to_email:
        logger.warning("Brevo: no recipient email; skipping")
        return False
    if not brevo_configured():
        logger.warning("Brevo not configured (need BREVO_API_KEY xkeysib OR BREVO_SMTP_LOGIN + key); skipping email")
        return False

    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "contact@invovix.store")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "Invovix")

    if _rest_key():
        try:
            r = httpx.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"accept": "application/json", "content-type": "application/json", "api-key": _rest_key()},
                json={
                    "sender": {"name": sender_name, "email": sender_email},
                    "to": [{"email": to_email, "name": to_name}],
                    "subject": subject,
                    "htmlContent": html,
                    "textContent": text,
                },
                timeout=20,
            )
            r.raise_for_status()
            logger.info(f"Brevo REST email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Brevo REST send failed: {e}")
            return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(os.environ["BREVO_SMTP_LOGIN"], os.environ["BREVO_SMTP_KEY"])
            s.sendmail(sender_email, [to_email], msg.as_string())
        logger.info(f"Brevo SMTP email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Brevo SMTP send failed: {e}")
        return False


def send_review_request(to_email: str, to_name: str, order: dict, frontend_url: str) -> bool:
    subject, html, text = _build_content(to_name, order, frontend_url)
    return _send_email(to_email, to_name, subject, html, text)


def send_contact_notification(admin_email: str, data: dict) -> bool:
    subject = f"Nouveau message de contact — {data.get('name','')}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#0a0a0a">
      <h2 style="text-transform:uppercase;letter-spacing:-0.5px">Nouveau message · Invovix</h2>
      <p><strong>Nom :</strong> {data.get('name','')}</p>
      <p><strong>Email :</strong> {data.get('email','')}</p>
      <p><strong>Sujet :</strong> {data.get('subject','')}</p>
      <p><strong>Message :</strong></p>
      <p style="background:#f5f5f5;padding:16px;border-left:3px solid #ff3300">{data.get('message','')}</p>
    </div>
    """
    text = f"Contact de {data.get('name','')} <{data.get('email','')}> — {data.get('subject','')}: {data.get('message','')}"
    return _send_email(admin_email, "Invovix Admin", subject, html, text)
