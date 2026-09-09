import os
import re
import time
import uuid
import asyncio
import logging
import httpx
from urllib.parse import quote
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Query, Response, BackgroundTasks, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db, client
from security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, require_area,
    create_2fa_token, decode_2fa_token,
)
import cj as cjmod
import brevo as brevomod
import fulfillment as fulfillmod
from payments import payments_router
from extras import extras_router, validate_promo, seed_extras
from ops import ops_router
from ai import ai_router, optimize_product_core, translate_to_fr
from erp import erp_router, run_rules
from crm import crm_router, run_abandoned_recovery
import marketing as mktmod
from marketing import marketing_router
from notifications import notif_router
import staff as staffmod
from staff import staff_router
import storage as objstore
import twofa as twofamod
from publicapi import publicapi_router
from imports import imports_router
from documents import documents_router
from predict import predict_router
from stores import stores_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invovix")

app = FastAPI(title="Invovix API")
api = APIRouter(prefix="/api")


# ----------------------------- Anti-spam: rate limit + reCAPTCHA -----------------------------
_rate_store: dict = {}
RECAPTCHA_SECRET = os.environ.get("RECAPTCHA_SECRET_KEY", "")
RECAPTCHA_MIN_SCORE = float(os.environ.get("RECAPTCHA_MIN_SCORE", "0.5"))


def rate_limit(ip: str, key: str, max_calls: int, window_sec: int):
    now = time.time()
    k = f"{key}:{ip}"
    calls = [t for t in _rate_store.get(k, []) if now - t < window_sec]
    if len(calls) >= max_calls:
        raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
    calls.append(now)
    _rate_store[k] = calls


async def verify_recaptcha(token: str, expected_action: str, remote_ip: str = None):
    """Score-based check. Soft-fails (allows) when reCAPTCHA is not usable
    (no token / domain not yet whitelisted / network error) so forms keep
    working everywhere; honeypot + rate-limit remain the baseline protection.
    Enforces the score only when Google returns a successful verification."""
    if not RECAPTCHA_SECRET:
        return
    if not token:
        return  # domain likely not configured (e.g. preview) -> rely on honeypot + rate limit
    data = {"secret": RECAPTCHA_SECRET, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        payload = r.json()
    except Exception:
        return  # network issue -> do not block legitimate users
    if not payload.get("success"):
        return  # hostname-mismatch / expired etc. -> soft allow
    if payload.get("action") and payload.get("action") != expected_action:
        raise HTTPException(403, "Action anti-robot invalide.")
    if float(payload.get("score", 1)) < RECAPTCHA_MIN_SCORE:
        raise HTTPException(403, "Activité suspecte détectée.")


# ----------------------------- Models -----------------------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class TwoFALoginInput(BaseModel):
    temp_token: str
    code: str


class ProductInput(BaseModel):
    title: str
    title_en: Optional[str] = None
    description: str = ""
    description_en: Optional[str] = ""
    price: float
    compare_at_price: Optional[float] = 0.0
    currency: str = "EUR"
    category: str = "smart-home"
    subcategory: Optional[str] = ""
    brand: Optional[str] = ""
    sku: Optional[str] = ""
    ean: Optional[str] = ""
    buy_price: Optional[float] = 0.0
    weight: Optional[float] = 0.0
    dimensions: Optional[str] = ""
    supplier_id: Optional[str] = ""
    supplier_url: Optional[str] = ""
    video_url: Optional[str] = ""
    images: List[str] = []
    stock: int = 100
    featured: bool = False
    active: bool = True


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    variant_id: Optional[str] = ""


class ShippingAddress(BaseModel):
    full_name: str
    email: EmailStr
    address: str
    city: str
    postal_code: str
    country: str
    phone: Optional[str] = ""


class OrderInput(BaseModel):
    items: List[CartItem]
    shipping_address: ShippingAddress
    promo_code: Optional[str] = ""


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    delivery_rating: int = Field(ge=1, le=5)
    comment: str = ""


class NewsletterInput(BaseModel):
    email: EmailStr
    website: str = ""  # honeypot
    recaptcha_token: str = ""


class BulkImportInput(BaseModel):
    pids: List[str]
    margin: float = 60
    category: str = "smart-home"
    optimize: bool = False


class ContactInput(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str
    website: str = ""  # honeypot
    recaptcha_token: str = ""


class BlogInput(BaseModel):
    title: str
    excerpt: str = ""
    content: str = ""
    cover_image: str = ""
    tags: List[str] = []
    published: bool = True


class ProfileInput(BaseModel):
    name: str
    phone: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    postal_code: Optional[str] = ""
    country: Optional[str] = ""


class AccountMessageInput(BaseModel):
    subject: str = ""
    message: str = Field(min_length=2)


class ContactReplyInput(BaseModel):
    message: str = Field(min_length=1)


# ----------------------------- Auth -----------------------------
def _public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
            "twofa_enabled": bool(u.get("twofa_enabled"))}


@api.post("/auth/register")
async def register(body: RegisterInput):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Un compte existe déjà avec cet email")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "role": "customer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"], email, "customer")
    return {"token": token, "user": _public_user(user)}


@api.post("/auth/login")
async def login(body: LoginInput, request: Request):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await staffmod.record_login(request, email, False, user["id"] if user else "", user.get("role", "") if user else "")
        raise HTTPException(401, "Email ou mot de passe incorrect")
    # 2FA gate for staff accounts
    if user.get("twofa_enabled"):
        await staffmod.record_login(request, email, True, user["id"], user.get("role", ""))
        return {"twofa_required": True, "temp_token": create_2fa_token(user["id"])}
    await staffmod.record_login(request, email, True, user["id"], user.get("role", ""))
    token = create_access_token(user["id"], email, user["role"])
    return {"token": token, "user": _public_user(user)}


@api.post("/auth/2fa/login")
async def twofa_login(body: TwoFALoginInput, request: Request):
    user_id = decode_2fa_token(body.temp_token)
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    if not twofamod.verify_code(user.get("twofa_secret", ""), body.code):
        await staffmod.record_login(request, user["email"], False, user["id"], user.get("role", ""))
        raise HTTPException(400, "Code 2FA invalide")
    token = create_access_token(user["id"], user["email"], user["role"])
    return {"token": token, "user": _public_user(user)}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": _public_user(user)}


@api.get("/account/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "address": user.get("address", ""),
        "city": user.get("city", ""),
        "postal_code": user.get("postal_code", ""),
        "country": user.get("country", ""),
    }


@api.put("/account/profile")
async def update_profile(body: ProfileInput, user: dict = Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": body.model_dump()})
    fresh = await db.users.find_one({"id": user["id"]})
    return {"ok": True, "profile": {
        "name": fresh.get("name", ""), "email": fresh.get("email", ""), "phone": fresh.get("phone", ""),
        "address": fresh.get("address", ""), "city": fresh.get("city", ""),
        "postal_code": fresh.get("postal_code", ""), "country": fresh.get("country", ""),
    }}


@api.post("/account/message")
async def account_message(body: AccountMessageInput, user: dict = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    doc = {
        "id": str(uuid.uuid4()),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "subject": body.subject or "Message client",
        "message": body.message.strip(),
        "user_id": user["id"],
        "source": "client",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.contacts.insert_one(doc)
    if background_tasks:
        background_tasks.add_task(brevomod.send_contact_notification, os.environ.get("ADMIN_EMAIL", ""),
                                  {"name": doc["name"], "email": doc["email"], "subject": doc["subject"], "message": doc["message"]})
    return {"ok": True}


# ----------------------------- Products -----------------------------
@api.get("/products")
async def list_products(
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 24,
):
    query = {"active": True}
    if category:
        query["category"] = category
    if featured is not None:
        query["featured"] = featured
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"title_en": {"$regex": q, "$options": "i"}},
        ]
    total = await db.products.count_documents(query)
    cursor = db.products.find(query, {"_id": 0}).skip((page - 1) * size).limit(size)
    items = await cursor.to_list(size)
    items = [cjmod.enrich_product(p) for p in items]
    sales = await mktmod.get_active_flash_sales()
    if sales:
        items = [mktmod.apply_flash_to_product(p, sales) for p in items]
    return {"items": items, "total": total, "page": page, "size": size}


@api.get("/categories")
async def categories():
    cats = await db.products.distinct("category", {"active": True})
    return {"categories": cats}


@api.get("/products/{product_id}")
async def get_product(product_id: str):
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Produit introuvable")
    p = cjmod.enrich_product(p)
    sales = await mktmod.get_active_flash_sales()
    if sales:
        p = mktmod.apply_flash_to_product(p, sales)
    return p


@api.post("/admin/products")
async def create_product(body: ProductInput, admin: dict = Depends(require_area("catalog"))):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["title_en"] = doc.get("title_en") or doc["title"]
    doc["source"] = "manual"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/admin/products/{product_id}")
async def update_product(product_id: str, body: ProductInput, admin: dict = Depends(require_area("catalog"))):
    res = await db.products.update_one({"id": product_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Produit introuvable")
    return await db.products.find_one({"id": product_id}, {"_id": 0})


@api.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, admin: dict = Depends(require_area("catalog"))):
    await db.products.delete_one({"id": product_id})
    return {"ok": True}


# ----------------------------- Reviews & Ratings -----------------------------
async def _recompute_product_rating(product_id: str):
    reviews = await db.reviews.find({"product_id": product_id}, {"_id": 0, "rating": 1, "delivery_rating": 1}).to_list(5000)
    count = len(reviews)
    rating_avg = round(sum(r["rating"] for r in reviews) / count, 2) if count else 0.0
    delivery_avg = round(sum(r["delivery_rating"] for r in reviews) / count, 2) if count else 0.0
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"rating_avg": rating_avg, "rating_count": count, "delivery_avg": delivery_avg}},
    )


@api.get("/products/{product_id}/reviews")
async def list_reviews(product_id: str):
    items = await db.reviews.find({"product_id": product_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    count = len(items)
    rating_avg = round(sum(i["rating"] for i in items) / count, 2) if count else 0.0
    delivery_avg = round(sum(i["delivery_rating"] for i in items) / count, 2) if count else 0.0
    return {"items": items, "count": count, "rating_avg": rating_avg, "delivery_avg": delivery_avg}


@api.get("/products/{product_id}/can-review")
async def can_review(product_id: str, user: dict = Depends(get_current_user)):
    purchased = await db.orders.find_one({"user_id": user["id"], "payment_status": "paid", "items.product_id": product_id})
    already = await db.reviews.find_one({"product_id": product_id, "user_id": user["id"]})
    return {"can_review": bool(purchased) and not already, "purchased": bool(purchased), "already_reviewed": bool(already)}


@api.post("/products/{product_id}/reviews")
async def create_review(product_id: str, body: ReviewInput, user: dict = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    purchased = await db.orders.find_one({"user_id": user["id"], "payment_status": "paid", "items.product_id": product_id})
    if not purchased:
        raise HTTPException(403, "Seuls les acheteurs vérifiés de ce produit peuvent laisser un avis")
    if await db.reviews.find_one({"product_id": product_id, "user_id": user["id"]}):
        raise HTTPException(400, "Vous avez déjà laissé un avis pour ce produit")
    review = {
        "id": str(uuid.uuid4()),
        "product_id": product_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "rating": body.rating,
        "delivery_rating": body.delivery_rating,
        "comment": body.comment.strip(),
        "verified_purchase": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.reviews.insert_one(review)
    await _recompute_product_rating(product_id)
    review.pop("_id", None)
    return review


@api.post("/newsletter")
async def subscribe_newsletter(body: NewsletterInput, request: Request):
    ip = request.client.host if request.client else "?"
    rate_limit(ip, "newsletter", 10, 3600)
    if body.website:  # honeypot -> silently drop bots
        return {"ok": True}
    await verify_recaptcha(body.recaptcha_token, "newsletter", ip)
    email = body.email.lower()
    await db.newsletter.update_one(
        {"email": email},
        {"$setOnInsert": {"email": email, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True}


# ----------------------------- Contact -----------------------------
@api.post("/contact")
async def contact(body: ContactInput, request: Request, background_tasks: BackgroundTasks):
    ip = request.client.host if request.client else "?"
    rate_limit(ip, "contact", 5, 3600)
    if body.website:  # honeypot -> silently drop bots
        return {"ok": True}
    await verify_recaptcha(body.recaptcha_token, "contact", ip)
    clean = {"name": body.name, "email": body.email, "subject": body.subject, "message": body.message}
    doc = {"id": str(uuid.uuid4()), **clean, "created_at": datetime.now(timezone.utc).isoformat(), "read": False}
    await db.contacts.insert_one(doc)
    background_tasks.add_task(brevomod.send_contact_notification, os.environ.get("ADMIN_EMAIL", ""), clean)
    return {"ok": True}


@api.get("/admin/contacts")
async def list_contacts(admin: dict = Depends(require_area("support"))):
    items = await db.contacts.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@api.post("/admin/contacts/{contact_id}/reply")
async def reply_contact(contact_id: str, body: ContactReplyInput, admin: dict = Depends(require_area("support"))):
    contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    if not contact:
        raise HTTPException(404, "Message introuvable")
    to_email = contact.get("email")
    if not to_email:
        raise HTTPException(400, "Aucune adresse email pour ce contact")
    subject = f"Re: {contact.get('subject') or 'Votre message'} — Invovix"
    html = (
        f"<p>Bonjour {contact.get('name') or ''},</p>"
        f"<p>{body.message.strip().replace(chr(10), '<br>')}</p>"
        f"<hr><p style='color:#888;font-size:12px'>En réponse à votre message : « {(contact.get('message') or '')[:200]} »</p>"
        f"<p>L'équipe Invovix</p>"
    )
    sent = brevomod._send_email(to_email, contact.get("name") or "Client", subject, html, body.message.strip())
    reply = {"message": body.message.strip(), "by": admin.get("name", "Admin"), "at": datetime.now(timezone.utc).isoformat(), "sent": bool(sent)}
    await db.contacts.update_one({"id": contact_id}, {"$set": {"read": True}, "$push": {"replies": reply}})
    return {"ok": True, "sent": bool(sent), "brevo_configured": brevomod.brevo_configured()}


# ----------------------------- Blog -----------------------------
def _slugify(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] or uuid.uuid4().hex[:8]


BLOG_DIR = "/app/frontend/public/blog"


@api.post("/admin/upload")
async def upload_image(file: UploadFile = File(...), admin: dict = Depends(require_area("catalog"))):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png").lower()
    if ext not in ["png", "jpg", "jpeg", "webp", "gif"]:
        ext = "png"
    if not objstore.storage_configured():
        raise HTTPException(503, "Stockage objet non configuré (EMERGENT_LLM_KEY manquant)")
    content = await file.read()
    fid = uuid.uuid4().hex
    path = f"{objstore.APP_NAME}/blog/{fid}.{ext}"
    try:
        result = objstore.put_object(path, content, objstore.guess_content_type(f"x.{ext}", "image/png"))
    except Exception as e:
        raise HTTPException(502, f"Échec du téléversement: {e}")
    return {"url": f"/api/media/{result['path']}"}


@api.get("/media/{path:path}")
async def get_media(path: str):
    try:
        data, content_type = objstore.get_object(path)
    except Exception:
        raise HTTPException(404, "Média introuvable")
    return Response(content=data, media_type=content_type)


@api.get("/blog")
async def list_blog(tag: Optional[str] = None):
    q = {"published": True}
    if tag:
        q["tags"] = tag
    items = await db.blog_posts.find(q, {"_id": 0, "content": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@api.get("/blog/{slug}")
async def get_blog(slug: str):
    p = await db.blog_posts.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Article introuvable")
    return p


@api.get("/admin/blog")
async def admin_list_blog(admin: dict = Depends(require_area("content"))):
    items = await db.blog_posts.find({}, {"_id": 0, "content": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@api.get("/admin/blog/{post_id}")
async def admin_get_blog(post_id: str, admin: dict = Depends(require_area("content"))):
    p = await db.blog_posts.find_one({"id": post_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Article introuvable")
    return p


@api.post("/admin/blog")
async def create_blog(body: BlogInput, admin: dict = Depends(require_area("content"))):
    slug = _slugify(body.title)
    if await db.blog_posts.find_one({"slug": slug}):
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {"id": str(uuid.uuid4()), "slug": slug, **body.model_dump(), "author": admin["name"], "created_at": now, "updated_at": now}
    await db.blog_posts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/admin/blog/{post_id}")
async def update_blog(post_id: str, body: BlogInput, admin: dict = Depends(require_area("content"))):
    update = body.model_dump()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.blog_posts.update_one({"id": post_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Article introuvable")
    return await db.blog_posts.find_one({"id": post_id}, {"_id": 0})


@api.delete("/admin/blog/{post_id}")
async def delete_blog(post_id: str, admin: dict = Depends(require_area("content"))):
    await db.blog_posts.delete_one({"id": post_id})
    return {"ok": True}


@api.get("/sitemap.xml")
async def sitemap():
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    products = await db.products.find({"active": True}, {"_id": 0, "id": 1}).to_list(2000)
    posts = await db.blog_posts.find({"published": True}, {"_id": 0, "slug": 1}).to_list(500)
    static_paths = ["/", "/shop", "/shop?category=smart-home", "/shop?category=workspace",
                    "/shop?category=security", "/blog", "/contact", "/faq",
                    "/legal/mentions", "/legal/cgv", "/legal/confidentialite"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in static_paths:
        loc = f"{base}{p}".replace("&", "&amp;")
        lines.append(f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    for prod in products:
        lines.append(f"  <url><loc>{base}/product/{prod['id']}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>")
    for post in posts:
        lines.append(f"  <url><loc>{base}/blog/{post['slug']}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>")
    lines.append("</urlset>")
    return Response(content="\n".join(lines), media_type="application/xml")


@api.get("/img")
async def image_proxy(url: str):
    """Same-origin proxy for external images (e.g. CJDropshipping CDN) to bypass hotlink protection."""
    if not url.startswith("http"):
        raise HTTPException(400, "URL invalide")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
    except Exception:
        raise HTTPException(502, "Image indisponible")
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=604800"},
    )


# ----------------------------- Orders -----------------------------
async def _build_order(body: OrderInput, user: dict) -> dict:
    line_items = []
    subtotal = 0.0
    sales = await mktmod.get_active_flash_sales()
    for it in body.items:
        p = await db.products.find_one({"id": it.product_id}, {"_id": 0})
        if not p:
            raise HTTPException(400, f"Produit introuvable: {it.product_id}")
        variants = cjmod.serialize_variants(p)
        chosen = None
        if it.variant_id:
            chosen = next((v for v in variants if v["vid"] == it.variant_id), None)
        if not chosen and variants:
            chosen = variants[0]
        unit_price = chosen["price"] if chosen else p["price"]
        # Apply active flash sale discount to unit price
        disc = mktmod.flash_discount_for(p, sales) if sales else 0.0
        if disc > 0:
            unit_price = round(unit_price * (1 - disc / 100.0), 2)
        # Stock guard (only when stock is known/synced)
        if chosen and isinstance(chosen.get("stock"), int) and chosen["stock"] < it.quantity:
            raise HTTPException(400, f"Stock insuffisant pour « {p['title']} » (reste {chosen['stock']}).")
        line_total = round(unit_price * it.quantity, 2)
        subtotal += line_total
        line_items.append({
            "product_id": p["id"],
            "title": p["title"],
            "variant_id": chosen["vid"] if chosen else None,
            "variant_name": chosen["name"] if chosen and len(variants) > 1 else None,
            "price": unit_price,
            "quantity": it.quantity,
            "image": (chosen["image"] if chosen else None) or (p.get("images") or [None])[0],
            "line_total": line_total,
        })
    subtotal = round(subtotal, 2)
    shipping = 0.0 if subtotal >= 50 else 4.90
    discount = 0.0
    promo_code = None
    if getattr(body, "promo_code", ""):
        promo = await validate_promo(body.promo_code, subtotal)
        if promo:
            discount = promo["discount"]
            promo_code = promo["code"]
    total = round(subtotal + shipping - discount, 2)
    return {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user["email"],
        "items": line_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "promo_code": promo_code,
        "total": total,
        "currency": "EUR",
        "status": "pending",
        "payment_status": "pending",
        "payment_method": None,
        "shipping_address": body.shipping_address.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@api.post("/orders")
async def create_order(body: OrderInput, user: dict = Depends(get_current_user)):
    order = await _build_order(body, user)
    await db.orders.insert_one(order)
    order.pop("_id", None)
    return order


@api.get("/orders")
async def my_orders(user: dict = Depends(get_current_user)):
    items = await db.orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items}


@api.get("/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    o = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not o or (o["user_id"] != user["id"] and user["role"] != "admin"):
        raise HTTPException(404, "Commande introuvable")
    return o


@api.post("/admin/products/{product_id}/import-cj-reviews")
async def import_cj_reviews(product_id: str, admin: dict = Depends(require_area("catalog")), limit: int = 6, translate: bool = True):
    """Importe les vrais avis clients CJ d'un produit (traduits en FR), marqués achat vérifié."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    cj_pid = product.get("cj_pid")
    if not cj_pid:
        raise HTTPException(400, "Ce produit n'est pas lié à CJDropshipping (pas de cj_pid).")
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        comments = await cjmod.get_product_comments(cj_pid, page=1, size=max(limit * 3, 20))
    except Exception as e:
        raise HTTPException(502, f"Erreur CJDropshipping: {e}")
    # priorise les avis positifs (>=4) puis complète
    comments.sort(key=lambda c: int(c.get("score") or 0), reverse=True)
    imported = 0
    for c in comments:
        if imported >= limit:
            break
        cid = str(c.get("commentId") or "")
        if not cid:
            continue
        rid = f"cj-{cid}"
        if await db.reviews.find_one({"id": rid}):
            continue
        rating = max(1, min(int(c.get("score") or 5), 5))
        comment = (c.get("comment") or "").strip()
        if translate and comment:
            comment = await translate_to_fr(comment)
        review = {
            "id": rid,
            "product_id": product_id,
            "user_id": f"cj:{cid}",
            "user_name": c.get("commentUser") or "Client vérifié",
            "rating": rating,
            "delivery_rating": rating,
            "comment": comment,
            "images": [u for u in (c.get("commentUrls") or []) if u][:3],
            "country": c.get("countryCode") or "",
            "source": "cj",
            "verified_purchase": True,
            "created_at": (c.get("commentDate") or datetime.now(timezone.utc).isoformat()),
        }
        await db.reviews.insert_one(review)
        imported += 1
    await _recompute_product_rating(product_id)
    fresh = await db.products.find_one({"id": product_id}, {"_id": 0, "rating_avg": 1, "rating_count": 1})
    return {"imported": imported, "rating_avg": fresh.get("rating_avg"), "rating_count": fresh.get("rating_count")}


@api.post("/admin/products/{product_id}/sync-specs")
async def sync_product_specs(product_id: str, admin: dict = Depends(require_area("catalog"))):
    """Récupère/actualise les caractéristiques techniques depuis CJ pour un produit."""
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Produit introuvable")
    cj_pid = product.get("cj_pid")
    if not cj_pid:
        raise HTTPException(400, "Ce produit n'est pas lié à CJDropshipping (pas de cj_pid).")
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        data = await cjmod.cj_request("GET", "/product/query", params={"pid": cj_pid})
    except Exception as e:
        raise HTTPException(502, f"Erreur CJDropshipping: {e}")
    detail = data.get("data") or {}
    specs = cjmod.extract_specs(detail)
    await db.products.update_one({"id": product_id}, {"$set": {"specs": specs}})
    return {"ok": True, "specs": specs}


# ----------------------------- Admin -----------------------------
@api.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_area("analytics"))):
    total_orders = await db.orders.count_documents({})
    paid_orders = await db.orders.count_documents({"payment_status": "paid"})
    total_products = await db.products.count_documents({})
    total_users = await db.users.count_documents({"role": "customer"})
    cj_products = await db.products.count_documents({"source": "cjdropshipping"})
    revenue_cursor = db.orders.find({"payment_status": "paid"}, {"_id": 0, "total": 1})
    revenue = sum([o.get("total", 0) for o in await revenue_cursor.to_list(10000)])
    # stock total du catalogue (stock_total synchronisé CJ, sinon champ stock)
    prods = await db.products.find({}, {"_id": 0, "stock_total": 1, "stock": 1}).to_list(5000)
    total_stock = sum(int(p.get("stock_total") if isinstance(p.get("stock_total"), int) else (p.get("stock") or 0)) for p in prods)
    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "total_products": total_products,
        "total_users": total_users,
        "cj_products": cj_products,
        "total_stock": total_stock,
        "revenue": round(revenue, 2),
    }


@api.get("/admin/orders")
async def admin_orders(admin: dict = Depends(require_area("orders"))):
    items = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@api.put("/admin/orders/{order_id}/status")
async def admin_update_order(order_id: str, background_tasks: BackgroundTasks, status: str = Query(...), admin: dict = Depends(require_area("orders"))):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Commande introuvable")
    await db.orders.update_one({"id": order_id}, {"$set": {"status": status}})
    order["status"] = status
    email_queued = False
    addr = order.get("shipping_address") or {}
    to_email = addr.get("email") or order.get("user_email")
    to_name = addr.get("full_name") or "Client"

    if status == "shipped" and not order.get("shipping_email_sent"):
        background_tasks.add_task(brevomod.send_shipping_notification, to_email, to_name, order, os.environ.get("FRONTEND_URL", ""))
        await db.orders.update_one({"id": order_id}, {"$set": {"shipping_email_sent": True}})
        email_queued = True

    if status == "delivered" and not order.get("review_email_sent"):
        background_tasks.add_task(
            brevomod.send_review_request, to_email, to_name, order, os.environ.get("FRONTEND_URL", "")
        )
        await db.orders.update_one({"id": order_id}, {"$set": {"review_email_sent": True}})
        email_queued = True
    return {"ok": True, "email_queued": email_queued, "brevo_configured": brevomod.brevo_configured()}


@api.post("/admin/orders/{order_id}/fulfill")
async def admin_fulfill_order(order_id: str, admin: dict = Depends(require_area("orders"))):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Commande introuvable")
    await fulfillmod.handle_paid_order(order_id)
    refreshed = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return {
        "cj_order_id": refreshed.get("cj_order_id"),
        "fulfillment_status": refreshed.get("fulfillment_status"),
        "fulfillment_error": refreshed.get("fulfillment_error"),
    }


@api.post("/admin/orders/{order_id}/sync-cj")
async def admin_sync_cj(order_id: str, admin: dict = Depends(require_area("orders"))):
    return await fulfillmod.sync_cj_order(order_id)


# ----------------------------- CJ Dropshipping (admin) -----------------------------
@api.get("/admin/cj/status")
async def cj_status(admin: dict = Depends(require_area("cj"))):
    return {"configured": cjmod.cj_configured()}


@api.get("/admin/cj/search")
async def cj_search(q: str = "", page: int = 1, admin: dict = Depends(require_area("cj"))):
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        results = await cjmod.search_products(q, page=page, country_code="FR")
        return {"items": results}
    except Exception as e:
        raise HTTPException(502, f"Erreur CJDropshipping: {e}")


PUBLIC_PRODUCTS_DIR = "/app/frontend/public/products"


async def _localize_images(urls: list, pid: str) -> list:
    """Download external product images server-side into the frontend /public dir (served same-origin)."""
    os.makedirs(PUBLIC_PRODUCTS_DIR, exist_ok=True)
    local = []
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
        for i, u in enumerate(urls):
            try:
                r = await c.get(u, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                ext = "png" if "png" in r.headers.get("content-type", "") else "jpg"
                fname = f"cj_{pid}_{i}.{ext}"
                with open(os.path.join(PUBLIC_PRODUCTS_DIR, fname), "wb") as f:
                    f.write(r.content)
                local.append(f"/products/{fname}")
            except Exception:
                continue
    return local


async def _do_import(pid: str, margin: float, category: str, featured: bool = False) -> dict:
    product = await cjmod.import_product(pid)
    if await db.products.find_one({"cj_pid": product["cj_pid"]}):
        return {"pid": pid, "status": "skipped", "reason": "already imported"}
    cost = product.get("cost_price") or 0
    markup = 1 + (max(margin, 0) / 100.0)
    if cost:
        product["price"] = round(cost * markup, 2)
        product["compare_at_price"] = round(product["price"] * 1.35, 2)
    product["category"] = category or product.get("category", "smart-home")
    product["featured"] = featured
    product["images"] = await _localize_images(product.get("images", []), product["id"])
    await db.products.insert_one(product)
    return {"pid": pid, "status": "imported", "id": product["id"], "title": product["title"], "price": product["price"]}


@api.post("/admin/cj/import/{pid}")
async def cj_import(pid: str, admin: dict = Depends(require_area("cj")), margin: float = 60, category: str = "smart-home", featured: bool = False, optimize: bool = False):
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        res = await _do_import(pid, margin, category, featured)
    except Exception as e:
        raise HTTPException(502, f"Erreur import CJ: {e}")
    if res["status"] == "skipped":
        raise HTTPException(400, "Ce produit est déjà importé")
    if optimize and res.get("id"):
        try:
            opt = await optimize_product_core(res["id"], rewrite=True, image=False, score=True)
            res["optimized"] = opt.get("done", [])
        except Exception as e:
            logger.error(f"auto-optimize error: {e}")
            res["optimized"] = []
    return res


@api.post("/admin/cj/import-bulk")
async def cj_import_bulk(body: BulkImportInput, admin: dict = Depends(require_area("cj"))):
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    results = []
    for i, pid in enumerate(body.pids[:40]):
        if i > 0:
            await asyncio.sleep(1.2)
        try:
            r = await _do_import(pid, body.margin, body.category)
            if body.optimize and r.get("status") == "imported" and r.get("id"):
                try:
                    opt = await optimize_product_core(r["id"], rewrite=True, image=False, score=True)
                    r["optimized"] = opt.get("done", [])
                except Exception as oe:
                    logger.error(f"auto-optimize error: {oe}")
                    r["optimized"] = []
            results.append(r)
        except Exception as e:
            results.append({"pid": pid, "status": "error", "reason": str(e)})
    return {
        "imported": sum(1 for r in results if r["status"] == "imported"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }


# ----------------------------- Stripe webhook (Flow B path) -----------------------------
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{host_url}api/webhook/stripe")
    try:
        resp = await checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.error(f"stripe webhook error: {e}")
        raise HTTPException(400, "Invalid webhook")
    if resp.payment_status == "paid" and resp.session_id:
        await db.payment_transactions.update_one(
            {"session_id": resp.session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": "paid", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        oid = (resp.metadata or {}).get("order_id")
        if oid:
            await db.orders.update_one(
                {"id": oid, "payment_status": {"$ne": "paid"}},
                {"$set": {"payment_status": "paid", "status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            asyncio.create_task(fulfillmod.handle_paid_order(oid))
    return {"status": "ok"}


# ----------------------------- CJ tracking webhook (push updates) -----------------------------
@app.post("/api/webhook/cj")
async def cj_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    data = payload.get("data") or payload
    order_number = data.get("orderNumber") or data.get("orderNum")
    cj_order_id = data.get("orderId")
    order = None
    if order_number:
        order = await db.orders.find_one({"id": order_number}, {"_id": 0, "id": 1})
    if not order and cj_order_id:
        order = await db.orders.find_one({"cj_order_id": str(cj_order_id)}, {"_id": 0, "id": 1})
    if order:
        asyncio.create_task(fulfillmod.sync_cj_order(order["id"]))
    return {"status": "ok"}


@api.get("/")
async def root():
    return {"message": "Invovix API", "status": "ok"}


app.include_router(api)
app.include_router(payments_router)
app.include_router(extras_router)
app.include_router(ops_router)
app.include_router(ai_router)
app.include_router(erp_router)
app.include_router(crm_router)
app.include_router(marketing_router)
app.include_router(notif_router)
app.include_router(staff_router)
app.include_router(publicapi_router)
app.include_router(imports_router)
app.include_router(documents_router)
app.include_router(predict_router)
app.include_router(stores_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------- Startup -----------------------------
SAMPLE_PRODUCTS = [
    {
        "title": "Interrupteur Mural Connecté Aura", "title_en": "Aura Smart Wall Switch",
        "description": "Contrôlez l'éclairage de votre maison depuis votre smartphone ou votre voix. Compatible Alexa & Google Home.",
        "description_en": "Control your home lighting from your phone or voice. Works with Alexa & Google Home.",
        "price": 34.90, "compare_at_price": 49.90, "category": "smart-home", "featured": True,
        "images": ["/products/switch.jpg"],
    },
    {
        "title": "Caméra de Sécurité 360° Vigil", "title_en": "Vigil 360° Security Camera",
        "description": "Surveillance intérieure Full HD avec vision nocturne et détection de mouvement intelligente.",
        "description_en": "Full HD indoor monitoring with night vision and smart motion detection.",
        "price": 59.90, "compare_at_price": 89.90, "category": "security", "featured": True,
        "images": ["https://images.pexels.com/photos/29291981/pexels-photo-29291981.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"],
    },
    {
        "title": "Thermostat Intelligent Clima", "title_en": "Clima Smart Thermostat",
        "description": "Économisez jusqu'à 25% d'énergie grâce à la programmation intelligente de votre chauffage.",
        "description_en": "Save up to 25% energy with smart heating scheduling.",
        "price": 129.00, "compare_at_price": 179.00, "category": "smart-home", "featured": True,
        "images": ["/products/thermostat.jpg"],
    },
    {
        "title": "Chargeur Sans Fil Halo 15W", "title_en": "Halo 15W Wireless Charger",
        "description": "Recharge rapide sans fil pour un bureau épuré. Design minimaliste premium.",
        "description_en": "Fast wireless charging for a clutter-free desk. Premium minimalist design.",
        "price": 24.90, "compare_at_price": 39.90, "category": "workspace", "featured": True,
        "images": ["/products/charger.jpg"],
    },
    {
        "title": "Hub Domotique Central Nexus", "title_en": "Nexus Central Smart Hub",
        "description": "Le cerveau de votre maison connectée. Reliez tous vos appareils en un seul écosystème.",
        "description_en": "The brain of your connected home. Unify all your devices in one ecosystem.",
        "price": 89.00, "compare_at_price": 119.00, "category": "smart-home", "featured": False,
        "images": ["/products/hub.jpg"],
    },
    {
        "title": "Réveil Connecté Lumina", "title_en": "Lumina Smart Alarm",
        "description": "Réveil en douceur avec simulation d'aube et haut-parleur intégré.",
        "description_en": "Gentle wake-up with sunrise simulation and built-in speaker.",
        "price": 44.90, "compare_at_price": 59.90, "category": "smart-home", "featured": False,
        "images": ["/products/alarm.jpg"],
    },
    {
        "title": "Station de Travail Ergo Setup", "title_en": "Ergo Workspace Station",
        "description": "Optimisez votre télétravail avec un poste ergonomique connecté et modulaire.",
        "description_en": "Optimize remote work with a connected, modular ergonomic station.",
        "price": 149.00, "compare_at_price": 199.00, "category": "workspace", "featured": False,
        "images": ["/products/workstation.jpg"],
    },
    {
        "title": "Caméra Extérieure Sentinel", "title_en": "Sentinel Outdoor Camera",
        "description": "Protection extérieure résistante aux intempéries avec alertes en temps réel.",
        "description_en": "Weatherproof outdoor protection with real-time alerts.",
        "price": 79.90, "compare_at_price": 109.90, "category": "security", "featured": False,
        "images": ["/products/outdoorcam.jpg"],
    },
]


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@invovix.store").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Invovix Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin seeded")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}})


async def seed_products():
    if await db.products.count_documents({}) > 0:
        return
    for p in SAMPLE_PRODUCTS:
        doc = dict(p)
        doc["id"] = str(uuid.uuid4())
        doc["currency"] = "EUR"
        doc["stock"] = 100
        doc["active"] = True
        doc["source"] = "seed"
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.products.insert_one(doc)
    logger.info("Sample products seeded")


async def seed_audio():
    """Seed 3-4 produits Audio de démo (catégorie audio) — idempotent."""
    if await db.products.count_documents({"category": "audio"}) > 0:
        return
    audio = [
        {"title": "Casque Sans Fil Sonic Pro", "title_en": "Sonic Pro Wireless Headphones",
         "description": "Casque à réduction de bruit active, 40h d'autonomie et son haute fidélité pour une immersion totale.",
         "description_en": "Active noise-cancelling headphones with 40h battery and hi-fi sound for total immersion.",
         "price": 79.90, "compare_at_price": 119.90, "buy_price": 30.0,
         "images": ["https://images.pexels.com/photos/7772548/pexels-photo-7772548.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"], "featured": True},
        {"title": "Enceinte Connectée Aura Sound", "title_en": "Aura Sound Smart Speaker",
         "description": "Enceinte intelligente compatible Alexa & Google, son 360° riche et assistant vocal intégré.",
         "description_en": "Smart speaker compatible with Alexa & Google, rich 360° sound and built-in voice assistant.",
         "price": 49.90, "compare_at_price": 74.90, "buy_price": 19.0,
         "images": ["https://images.pexels.com/photos/1279365/pexels-photo-1279365.jpeg"], "featured": True},
        {"title": "Écouteurs True Wireless Beat", "title_en": "Beat True Wireless Earbuds",
         "description": "Écouteurs sans fil ultra-compacts, résistants à l'eau (IPX5) et boîtier de charge rapide.",
         "description_en": "Ultra-compact true wireless earbuds, water-resistant (IPX5) with fast-charge case.",
         "price": 39.90, "compare_at_price": 59.90, "buy_price": 14.0,
         "images": ["https://images.pexels.com/photos/3081173/pexels-photo-3081173.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"], "featured": False},
        {"title": "Mini Enceinte Nomade Pulse", "title_en": "Pulse Portable Mini Speaker",
         "description": "Enceinte Bluetooth portable, basses puissantes et 12h d'autonomie pour la maison ou l'extérieur.",
         "description_en": "Portable Bluetooth speaker with powerful bass and 12h battery for home or outdoor.",
         "price": 29.90, "compare_at_price": 44.90, "buy_price": 11.0,
         "images": ["https://images.pexels.com/photos/20323501/pexels-photo-20323501.jpeg"], "featured": False},
    ]
    for p in audio:
        doc = dict(p)
        doc["id"] = str(uuid.uuid4())
        doc["currency"] = "EUR"; doc["category"] = "audio"; doc["stock"] = 100
        doc["active"] = True; doc["source"] = "seed"
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.products.insert_one(doc)
    logger.info("Audio products seeded")


async def _stock_sync_loop():
    """Periodically refresh CJ stock for all imported products (default: daily)."""
    from ops import _sync_all_stock
    interval = int(os.environ.get("STOCK_SYNC_INTERVAL_HOURS", "24")) * 3600
    await asyncio.sleep(300)  # first run 5 min after boot
    while True:
        try:
            await _sync_all_stock()
            await run_rules()
        except Exception as e:
            logger.error(f"stock sync loop error: {e}")
        await asyncio.sleep(interval)


async def _tracking_sync_loop():
    """Periodically sync CJ tracking for open orders and email customers on shipment."""
    interval = int(os.environ.get("CJ_SYNC_INTERVAL_MIN", "60")) * 60
    await asyncio.sleep(120)  # let the app settle after boot
    while True:
        try:
            orders = await db.orders.find(
                {"cj_order_id": {"$ne": None}, "status": {"$in": ["processing", "shipped"]}},
                {"_id": 0, "id": 1},
            ).to_list(500)
            for o in orders:
                try:
                    await fulfillmod.sync_cj_order(o["id"])
                except Exception as e:
                    logger.error(f"auto sync failed {o['id']}: {e}")
                await asyncio.sleep(1.0)
            if orders:
                logger.info(f"auto tracking sync: {len(orders)} orders checked")
        except Exception as e:
            logger.error(f"tracking sync loop error: {e}")
        await asyncio.sleep(interval)


async def _abandoned_cart_loop():
    """Relance automatique des checkouts abandonnés (commandes en attente de paiement)."""
    interval = int(os.environ.get("ABANDONED_INTERVAL_MIN", "60")) * 60
    await asyncio.sleep(180)  # settle after boot
    while True:
        try:
            await run_abandoned_recovery()
        except Exception as e:
            logger.error(f"abandoned cart loop error: {e}")
        await asyncio.sleep(interval)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.products.create_index("id")
    await db.orders.create_index("id")
    await seed_admin()
    await seed_products()
    await seed_audio()
    await seed_extras()
    try:
        objstore.init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Object storage init failed: {e}")
    if os.environ.get("CJ_AUTO_SYNC", "true").lower() == "true":
        asyncio.create_task(_tracking_sync_loop())
    if os.environ.get("STOCK_AUTO_SYNC", "true").lower() == "true":
        asyncio.create_task(_stock_sync_loop())
    if os.environ.get("ABANDONED_CART_ENABLED", "true").lower() == "true":
        asyncio.create_task(_abandoned_cart_loop())


@app.on_event("shutdown")
async def shutdown():
    client.close()
