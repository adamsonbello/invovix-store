import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Query, Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db, client
from security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin,
)
import cj as cjmod
from payments import payments_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invovix")

app = FastAPI(title="Invovix API")
api = APIRouter(prefix="/api")


# ----------------------------- Models -----------------------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ProductInput(BaseModel):
    title: str
    title_en: Optional[str] = None
    description: str = ""
    description_en: Optional[str] = ""
    price: float
    compare_at_price: Optional[float] = 0.0
    currency: str = "EUR"
    category: str = "smart-home"
    images: List[str] = []
    stock: int = 100
    featured: bool = False
    active: bool = True


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


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


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    delivery_rating: int = Field(ge=1, le=5)
    comment: str = ""


class NewsletterInput(BaseModel):
    email: EmailStr


# ----------------------------- Auth -----------------------------
def _public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"]}


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
async def login(body: LoginInput):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    token = create_access_token(user["id"], email, user["role"])
    return {"token": token, "user": _public_user(user)}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": _public_user(user)}


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
    return p


@api.post("/admin/products")
async def create_product(body: ProductInput, admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["title_en"] = doc.get("title_en") or doc["title"]
    doc["source"] = "manual"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/admin/products/{product_id}")
async def update_product(product_id: str, body: ProductInput, admin: dict = Depends(require_admin)):
    res = await db.products.update_one({"id": product_id}, {"$set": body.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Produit introuvable")
    return await db.products.find_one({"id": product_id}, {"_id": 0})


@api.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, admin: dict = Depends(require_admin)):
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
async def subscribe_newsletter(body: NewsletterInput):
    email = body.email.lower()
    await db.newsletter.update_one(
        {"email": email},
        {"$setOnInsert": {"email": email, "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True}


@api.get("/sitemap.xml")
async def sitemap():
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    products = await db.products.find({"active": True}, {"_id": 0, "id": 1}).to_list(2000)
    static_paths = ["/", "/shop", "/shop?category=smart-home", "/shop?category=workspace", "/shop?category=security"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in static_paths:
        loc = f"{base}{p}".replace("&", "&amp;")
        lines.append(f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    for prod in products:
        lines.append(f"  <url><loc>{base}/product/{prod['id']}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>")
    lines.append("</urlset>")
    return Response(content="\n".join(lines), media_type="application/xml")


# ----------------------------- Orders -----------------------------
async def _build_order(body: OrderInput, user: dict) -> dict:
    line_items = []
    subtotal = 0.0
    for it in body.items:
        p = await db.products.find_one({"id": it.product_id}, {"_id": 0})
        if not p:
            raise HTTPException(400, f"Produit introuvable: {it.product_id}")
        line_total = round(p["price"] * it.quantity, 2)
        subtotal += line_total
        line_items.append({
            "product_id": p["id"],
            "title": p["title"],
            "price": p["price"],
            "quantity": it.quantity,
            "image": (p.get("images") or [None])[0],
            "line_total": line_total,
        })
    subtotal = round(subtotal, 2)
    shipping = 0.0 if subtotal >= 50 else 4.90
    total = round(subtotal + shipping, 2)
    return {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user["email"],
        "items": line_items,
        "subtotal": subtotal,
        "shipping": shipping,
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


# ----------------------------- Admin -----------------------------
@api.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    total_orders = await db.orders.count_documents({})
    paid_orders = await db.orders.count_documents({"payment_status": "paid"})
    total_products = await db.products.count_documents({})
    total_users = await db.users.count_documents({"role": "customer"})
    revenue_cursor = db.orders.find({"payment_status": "paid"}, {"_id": 0, "total": 1})
    revenue = sum([o.get("total", 0) for o in await revenue_cursor.to_list(10000)])
    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "total_products": total_products,
        "total_users": total_users,
        "revenue": round(revenue, 2),
    }


@api.get("/admin/orders")
async def admin_orders(admin: dict = Depends(require_admin)):
    items = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items}


@api.put("/admin/orders/{order_id}/status")
async def admin_update_order(order_id: str, status: str = Query(...), admin: dict = Depends(require_admin)):
    res = await db.orders.update_one({"id": order_id}, {"$set": {"status": status}})
    if res.matched_count == 0:
        raise HTTPException(404, "Commande introuvable")
    return {"ok": True}


# ----------------------------- CJ Dropshipping (admin) -----------------------------
@api.get("/admin/cj/status")
async def cj_status(admin: dict = Depends(require_admin)):
    return {"configured": cjmod.cj_configured()}


@api.get("/admin/cj/search")
async def cj_search(q: str = "", page: int = 1, admin: dict = Depends(require_admin)):
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        results = await cjmod.search_products(q, page=page, country_code="FR")
        return {"items": results}
    except Exception as e:
        raise HTTPException(502, f"Erreur CJDropshipping: {e}")


@api.post("/admin/cj/import/{pid}")
async def cj_import(pid: str, admin: dict = Depends(require_admin)):
    if not cjmod.cj_configured():
        raise HTTPException(503, "Clé API CJDropshipping non configurée")
    try:
        product = await cjmod.import_product(pid)
    except Exception as e:
        raise HTTPException(502, f"Erreur import CJ: {e}")
    existing = await db.products.find_one({"cj_pid": product["cj_pid"]})
    if existing:
        raise HTTPException(400, "Ce produit est déjà importé")
    await db.products.insert_one(product)
    product.pop("_id", None)
    return product


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
    return {"status": "ok"}


@api.get("/")
async def root():
    return {"message": "Invovix API", "status": "ok"}


app.include_router(api)
app.include_router(payments_router)

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


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.products.create_index("id")
    await db.orders.create_index("id")
    await seed_admin()
    await seed_products()


@app.on_event("shutdown")
async def shutdown():
    client.close()
