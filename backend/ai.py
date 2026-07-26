"""Cerveau IA d'Invovix — réécriture de fiches, génération d'images,
scoring de produits gagnants et assistant d'analyse décisionnelle.
Utilise la clé universelle Emergent (emergentintegrations)."""
import os
import re
import json
import uuid
import base64
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from database import db
from security import require_admin
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

logger = logging.getLogger("invovix")
ai_router = APIRouter(prefix="/api")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
TEXT_MODEL = os.environ.get("AI_TEXT_MODEL", "gpt-5.4")
IMAGE_MODEL = "gemini-3.1-flash-image-preview"
PUBLIC_PRODUCTS_DIR = "/app/frontend/public/products"

# provider inference from model name
def _provider_for(model: str) -> str:
    m = (model or "").lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "gemini"
    return "openai"


def _require_key():
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "Clé IA (EMERGENT_LLM_KEY) non configurée")


async def _llm_text(system: str, prompt: str, model: Optional[str] = None) -> str:
    _require_key()
    mdl = model or TEXT_MODEL
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"ai-{uuid.uuid4().hex[:12]}",
        system_message=system,
    ).with_model(_provider_for(mdl), mdl)
    return await chat.send_message(UserMessage(text=prompt))


def _parse_json(raw: str) -> dict:
    """Extrait un objet JSON d'une réponse LLM (tolère les blocs markdown)."""
    if not raw:
        return {}
    txt = raw.strip()
    txt = re.sub(r"^```(?:json)?", "", txt).strip()
    txt = re.sub(r"```$", "", txt).strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if m:
        txt = m.group(0)
    try:
        return json.loads(txt)
    except Exception:
        return {}


# ----------------------------- 1. Réécriture / optimisation de fiche -----------------------------
class RewriteInput(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    keywords_hint: str = ""
    model: Optional[str] = None


@ai_router.post("/admin/ai/rewrite-product")
async def rewrite_product(body: RewriteInput, admin: dict = Depends(require_admin)):
    system = (
        "Tu es un expert copywriting e-commerce et SEO pour une boutique de domotique "
        "et matériel de télétravail (marque Invovix). Tu écris un contenu premium, "
        "persuasif et optimisé pour la conversion. Réponds UNIQUEMENT en JSON valide, "
        "sans texte autour."
    )
    prompt = f"""Optimise cette fiche produit. Produit brut :
Titre: {body.title}
Description: {body.description or "(vide)"}
Catégorie: {body.category or "domotique"}
Mots-clés souhaités: {body.keywords_hint or "(aucun)"}

Renvoie STRICTEMENT ce JSON :
{{
  "title": "titre marketing FR optimisé (max 70 car.)",
  "title_en": "optimized EN marketing title (max 70 chars)",
  "description": "description FR riche en HTML simple (<p>, <ul>, <li>), 120-200 mots, bénéfices + usage",
  "description_en": "same in English HTML",
  "bullet_points": ["5 arguments de vente FR percutants"],
  "seo_title": "meta title FR (max 60 car.)",
  "seo_description": "meta description FR (max 155 car.)",
  "keywords": ["8 mots-clés SEO FR pertinents"],
  "faq": [{{"q": "question client FR", "a": "réponse FR"}}, "3 à 5 entrées"]
}}"""
    raw = await _llm_text(system, prompt, body.model)
    data = _parse_json(raw)
    if not data:
        raise HTTPException(502, "Réponse IA illisible, réessayez")
    return data


# ----------------------------- 2. Génération d'images IA (Nano Banana) -----------------------------
STYLE_PROMPTS = {
    "lifestyle": "Photo lifestyle premium et réaliste, dans un intérieur moderne et lumineux, ambiance chaleureuse, mise en scène du produit en situation d'usage, lumière naturelle douce, haute résolution, style publicité e-commerce haut de gamme.",
    "white": "Photo produit studio sur fond blanc pur (packshot e-commerce type Amazon), éclairage professionnel uniforme, ombre douce, très net, cadrage centré, haute résolution.",
    "infographic": "Infographie produit e-commerce moderne, mise en avant de 3 à 4 caractéristiques clés avec icônes et libellés courts, palette sobre et premium, fond clair, style marketing.",
    "thumbnail": "Miniature marketing accrocheuse pour réseaux sociaux, produit bien visible, couleurs vives et contrastées, composition dynamique, haute résolution.",
}


class GenImageInput(BaseModel):
    product_id: Optional[str] = None
    prompt: Optional[str] = ""
    style: str = "lifestyle"
    use_reference: bool = True


@ai_router.post("/admin/ai/generate-image")
async def generate_image(body: GenImageInput, admin: dict = Depends(require_admin)):
    _require_key()
    product = None
    if body.product_id:
        product = await db.products.find_one({"id": body.product_id}, {"_id": 0})
        if not product:
            raise HTTPException(404, "Produit introuvable")

    style_txt = STYLE_PROMPTS.get(body.style, STYLE_PROMPTS["lifestyle"])
    subject = body.prompt or (product.get("title") if product else "")
    if not subject:
        raise HTTPException(400, "Fournir un product_id ou un prompt")
    full_prompt = f"{style_txt}\n\nProduit : {subject}. Aucun texte artificiel ou watermark. Image seule."

    # référence image (édition) si dispo
    file_contents = None
    if body.use_reference and product and product.get("images"):
        ref = product["images"][0]
        local = None
        if ref.startswith("/products/"):
            local = os.path.join(PUBLIC_PRODUCTS_DIR, os.path.basename(ref))
        if local and os.path.exists(local):
            with open(local, "rb") as f:
                file_contents = [ImageContent(base64.b64encode(f.read()).decode("utf-8"))]

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"img-{uuid.uuid4().hex[:12]}",
        system_message="You are a product photography and marketing image generator.",
    ).with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])

    msg = UserMessage(text=full_prompt, file_contents=file_contents) if file_contents else UserMessage(text=full_prompt)
    try:
        _text, images = await chat.send_message_multimodal_response(msg)
    except Exception as e:
        logger.error(f"AI image error: {e}")
        raise HTTPException(502, f"Erreur génération image: {e}")
    if not images:
        raise HTTPException(502, "Aucune image générée")

    os.makedirs(PUBLIC_PRODUCTS_DIR, exist_ok=True)
    fname = f"ai_{uuid.uuid4().hex}.png"
    with open(os.path.join(PUBLIC_PRODUCTS_DIR, fname), "wb") as f:
        f.write(base64.b64decode(images[0]["data"]))
    url = f"/products/{fname}"

    if product and body.product_id:
        imgs = product.get("images") or []
        imgs.append(url)
        await db.products.update_one({"id": body.product_id}, {"$set": {"images": imgs}})
    return {"url": url, "style": body.style}


# ----------------------------- 3. Scoring produit gagnant -----------------------------
class ScoreInput(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    sell_price: float = 0.0
    cost_price: float = 0.0
    model: Optional[str] = None


@ai_router.post("/admin/ai/product-score")
async def product_score(body: ScoreInput, admin: dict = Depends(require_admin)):
    margin_pct = 0.0
    if body.sell_price and body.cost_price:
        margin_pct = round((body.sell_price - body.cost_price) / body.sell_price * 100, 1)
    system = (
        "Tu es un analyste e-commerce spécialisé dropshipping. Tu évalues le potentiel "
        "d'un produit gagnant sur les critères : demande/tendance, marge, saturation/concurrence, "
        "stabilité du prix fournisseur, effet 'wow'. Réponds UNIQUEMENT en JSON valide."
    )
    prompt = f"""Évalue ce produit pour du dropshipping (marché Europe, niche domotique/télétravail).
Titre: {body.title}
Description: {body.description or "(vide)"}
Catégorie: {body.category or "n/a"}
Prix de vente: {body.sell_price or "n/a"} EUR
Prix d'achat: {body.cost_price or "n/a"} EUR
Marge calculée: {margin_pct}%

Renvoie STRICTEMENT ce JSON :
{{
  "opportunity_score": 0-100,
  "demand": 0-100,
  "margin": 0-100,
  "competition": 0-100,
  "trend": "hausse|stable|baisse",
  "verdict": "gagnant|potentiel|à éviter",
  "reasons": ["3 à 5 justifications courtes FR"],
  "recommended_price": 0.0,
  "target_audience": "cible FR en une phrase"
}}"""
    raw = await _llm_text(system, prompt, body.model)
    data = _parse_json(raw)
    if not data:
        raise HTTPException(502, "Réponse IA illisible, réessayez")
    data["margin_pct"] = margin_pct
    return data


# ----------------------------- 4. Assistant d'analyse décisionnelle -----------------------------
async def _gather_business_context() -> dict:
    """Résumé compact des données business pour nourrir l'assistant IA."""
    now = datetime.now(timezone.utc)
    paid = await db.orders.find({"payment_status": "paid"}, {"_id": 0}).to_list(20000)
    revenue = round(sum(o.get("total", 0) for o in paid), 2)
    paid_count = len(paid)
    aov = round(revenue / paid_count, 2) if paid_count else 0.0

    # top produits
    counter = {}
    for o in paid:
        for it in o.get("items", []):
            t = it.get("title") or it.get("product_id")
            counter[t] = counter.get(t, 0) + it.get("quantity", 1)
    top = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:8]

    # 30j
    d30 = (now - timedelta(days=30)).isoformat()
    rev_30 = round(sum(o.get("total", 0) for o in paid if (o.get("created_at") or "") >= d30), 2)

    products = await db.products.find({}, {"_id": 0, "title": 1, "price": 1, "buy_price": 1, "stock_total": 1, "in_stock": 1, "category": 1, "rating_avg": 1}).to_list(2000)
    out_of_stock = [p["title"] for p in products if p.get("in_stock") is False][:20]
    to_ship = await db.orders.count_documents({"payment_status": "paid", "status": {"$in": ["processing", "paid"]}})
    customers = await db.users.count_documents({"role": "customer"})

    return {
        "revenue_total": revenue,
        "revenue_last_30d": rev_30,
        "orders_paid": paid_count,
        "average_order_value": aov,
        "customers": customers,
        "orders_to_ship": to_ship,
        "top_products": [{"title": t, "qty": q} for t, q in top],
        "out_of_stock": out_of_stock,
        "catalog_size": len(products),
        "products_sample": products[:40],
    }


class AnalyzeInput(BaseModel):
    question: str
    model: Optional[str] = None


@ai_router.post("/admin/ai/analyze")
async def analyze(body: AnalyzeInput, admin: dict = Depends(require_admin)):
    ctx = await _gather_business_context()
    system = (
        "Tu es l'analyste business IA d'Invovix, une boutique de dropshipping (domotique & "
        "télétravail, marché Europe). Tu réponds en FRANÇAIS, de façon concise, chiffrée et "
        "actionnable. Base-toi UNIQUEMENT sur les données fournies ; si une donnée manque, "
        "dis-le et propose comment l'obtenir. Termine par 2-3 recommandations concrètes."
    )
    prompt = f"""Données actuelles de la boutique (JSON) :
{json.dumps(ctx, ensure_ascii=False)}

Question de l'administrateur :
{body.question}"""
    answer = await _llm_text(system, prompt, body.model)
    return {"answer": answer, "context_used": {k: v for k, v in ctx.items() if k not in ("products_sample",)}}


@ai_router.get("/admin/ai/status")
async def ai_status(admin: dict = Depends(require_admin)):
    return {"configured": bool(EMERGENT_LLM_KEY), "text_model": TEXT_MODEL, "image_model": IMAGE_MODEL}
