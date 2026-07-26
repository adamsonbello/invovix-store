"""Module 3 — Import de produits par CSV / Excel / URL.
Alimente le catalogue central (products) réutilisé par toutes les boutiques."""
import os
import io
import re
import uuid
import logging
from datetime import datetime, timezone

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from database import db
from security import require_area

logger = logging.getLogger("invovix")
imports_router = APIRouter(prefix="/api")

PUBLIC_PRODUCTS_DIR = "/app/frontend/public/products"

# Mapping colonnes tolérant (minuscule -> champ produit)
COLUMN_ALIASES = {
    "title": "title", "titre": "title", "name": "title", "nom": "title",
    "title_en": "title_en", "titre_en": "title_en",
    "description": "description", "desc": "description",
    "description_en": "description_en",
    "price": "price", "prix": "price", "sale_price": "price", "prix_vente": "price",
    "buy_price": "buy_price", "cost": "buy_price", "cost_price": "buy_price",
    "prix_achat": "buy_price", "cout": "buy_price",
    "category": "category", "categorie": "category", "cat": "category",
    "subcategory": "subcategory", "sous_categorie": "subcategory",
    "brand": "brand", "marque": "brand",
    "sku": "sku", "ean": "ean", "gtin": "ean",
    "stock": "stock", "quantity": "stock", "quantite": "stock",
    "image": "images", "images": "images", "image_url": "images", "photo": "images",
    "video_url": "video_url", "video": "video_url",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _localize_images(urls: list, pid: str) -> list:
    os.makedirs(PUBLIC_PRODUCTS_DIR, exist_ok=True)
    local = []
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
        for i, u in enumerate(urls[:8]):
            u = (u or "").strip()
            if not u:
                continue
            if u.startswith("/"):  # déjà local
                local.append(u)
                continue
            if not u.startswith("http"):
                continue
            try:
                r = await c.get(u, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                ext = "png" if "png" in r.headers.get("content-type", "") else "jpg"
                fname = f"imp_{pid}_{i}.{ext}"
                with open(os.path.join(PUBLIC_PRODUCTS_DIR, fname), "wb") as f:
                    f.write(r.content)
                local.append(f"/products/{fname}")
            except Exception:
                continue
    return local


def _norm_row(row: dict) -> dict:
    out = {}
    for raw_key, val in row.items():
        key = COLUMN_ALIASES.get(str(raw_key).strip().lower())
        if not key:
            continue
        if val is None:
            continue
        sval = str(val).strip()
        if sval == "" or sval.lower() == "nan":
            continue
        out[key] = sval
    return out


def _to_float(v, default=0.0):
    if v is None:
        return default
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default


async def _create_from_norm(n: dict, margin: float, default_category: str) -> dict:
    title = n.get("title")
    if not title:
        return {"status": "error", "reason": "titre manquant"}
    pid = str(uuid.uuid4())
    price = _to_float(n.get("price"), 0.0)
    buy_price = _to_float(n.get("buy_price"), 0.0)
    if not price and buy_price:
        price = round(buy_price * (1 + max(margin, 0) / 100.0), 2)
    images_raw = re.split(r"[|,;\n]", n.get("images", "")) if n.get("images") else []
    images = await _localize_images([u for u in images_raw if u.strip()], pid)
    doc = {
        "id": pid,
        "title": title,
        "title_en": n.get("title_en") or title,
        "description": n.get("description", ""),
        "description_en": n.get("description_en", ""),
        "price": round(price, 2),
        "compare_at_price": round(price * 1.35, 2) if price else 0.0,
        "buy_price": round(buy_price, 2),
        "currency": "EUR",
        "category": n.get("category") or default_category,
        "subcategory": n.get("subcategory", ""),
        "brand": n.get("brand", ""),
        "sku": n.get("sku", ""),
        "ean": n.get("ean", ""),
        "video_url": n.get("video_url", ""),
        "images": images,
        "stock": int(_to_float(n.get("stock"), 100)),
        "featured": False,
        "active": True,
        "source": "import",
        "created_at": _now(),
    }
    await db.products.insert_one(doc)
    return {"status": "imported", "id": pid, "title": title, "price": doc["price"]}


@imports_router.post("/admin/import/file")
async def import_file(
    file: UploadFile = File(...),
    margin: float = Form(60.0),
    category: str = Form("smart-home"),
    admin: dict = Depends(require_area("catalog")),
):
    content = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            dfs = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            dfs = pd.read_csv(io.BytesIO(content), dtype=str, sep=None, engine="python")
    except Exception as e:
        raise HTTPException(400, f"Fichier illisible : {e}")
    dfs = dfs.where(pd.notnull(dfs), None)
    rows = dfs.to_dict(orient="records")
    if not rows:
        raise HTTPException(400, "Fichier vide")
    results = []
    for r in rows[:500]:
        n = _norm_row(r)
        if not n.get("title"):
            continue
        try:
            results.append(await _create_from_norm(n, margin, category))
        except Exception as e:
            results.append({"status": "error", "reason": str(e)})
    return {
        "imported": sum(1 for r in results if r["status"] == "imported"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "total_rows": len(rows),
        "results": results[:200],
    }


class UrlImportInput(BaseModel):
    url: str
    margin: float = 60.0
    category: str = "smart-home"


@imports_router.post("/admin/import/url")
async def import_url(body: UrlImportInput, admin: dict = Depends(require_area("catalog"))):
    if not body.url.startswith("http"):
        raise HTTPException(400, "URL invalide")
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
            r = await c.get(body.url, headers={"User-Agent": "Mozilla/5.0 (compatible; InvovixBot/1.0)"})
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
    except Exception as e:
        raise HTTPException(502, f"Impossible de récupérer la page : {e}")

    def meta(prop):
        el = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return el.get("content").strip() if el and el.get("content") else ""

    title = meta("og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    description = meta("og:description") or meta("description")
    image = meta("og:image")
    price = _to_float(meta("product:price:amount") or meta("og:price:amount"), 0.0)
    # tentative JSON-LD Product
    if not price or not image:
        import json as _json
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(s.string or "{}")
            except Exception:
                continue
            objs = data if isinstance(data, list) else [data]
            for o in objs:
                if isinstance(o, dict) and o.get("@type") in ("Product", ["Product"]):
                    title = title or o.get("name", "")
                    description = description or (o.get("description") or "")
                    offers = o.get("offers") or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = price or _to_float(offers.get("price"), 0.0)
                    img = o.get("image")
                    if not image and img:
                        image = img[0] if isinstance(img, list) else img
    if not title:
        raise HTTPException(422, "Aucune donnée produit détectée sur cette page")
    n = {
        "title": title[:120], "description": description[:2000],
        "price": str(price) if price else "", "images": image or "",
        "category": body.category,
    }
    res = await _create_from_norm(n, body.margin, body.category)
    product = await db.products.find_one({"id": res.get("id")}, {"_id": 0}) if res.get("id") else None
    return {"result": res, "product": product, "source_url": body.url}
