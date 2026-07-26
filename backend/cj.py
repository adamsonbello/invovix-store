import os
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote
import httpx

from database import db

CJ_BASE_URL = os.environ.get("CJ_BASE_URL", "https://developers.cjdropshipping.com/api2.0/v1")
TOKEN_DOC_ID = "cj_token"


def cj_configured() -> bool:
    return bool(os.environ.get("CJ_API_KEY", "").strip())


async def _get_tokens():
    return await db.cj_tokens.find_one({"id": TOKEN_DOC_ID}) or {}


async def _save_tokens(payload: dict):
    payload["id"] = TOKEN_DOC_ID
    payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.cj_tokens.replace_one({"id": TOKEN_DOC_ID}, payload, upsert=True)


async def _ensure_access_token() -> str:
    if not cj_configured():
        raise RuntimeError("CJ_API_KEY_MISSING")
    tok = await _get_tokens()
    if tok.get("accessToken"):
        return tok["accessToken"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{CJ_BASE_URL}/authentication/getAccessToken",
            json={"apiKey": os.environ["CJ_API_KEY"]},
        )
        r.raise_for_status()
        data = r.json()
    if not data.get("result"):
        raise RuntimeError(data.get("message", "CJ token request failed"))
    await _save_tokens(data["data"])
    return data["data"]["accessToken"]


async def cj_request(method: str, path: str, *, params=None, json=None):
    token = await _ensure_access_token()
    headers = {"CJ-Access-Token": token, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.request(method, f"{CJ_BASE_URL}{path}", headers=headers, params=params, json=json)
        if r.status_code >= 400:
            raise RuntimeError(f"CJ HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
    if not data.get("result"):
        tok = await _get_tokens()
        if tok.get("refreshToken"):
            async with httpx.AsyncClient(timeout=30) as c:
                rr = await c.post(
                    f"{CJ_BASE_URL}/authentication/refreshAccessToken",
                    json={"refreshToken": tok["refreshToken"]},
                )
                rd = rr.json()
            if rd.get("result"):
                await _save_tokens(rd["data"])
                return await cj_request(method, path, params=params, json=json)
        raise RuntimeError(data.get("message", "CJ API request failed"))
    return data


async def search_products(keyword: str, page: int = 1, size: int = 20, country_code: str = None):
    params = {"pageNum": page, "pageSize": size}
    if keyword:
        params["productNameEn"] = keyword
    if country_code:
        params["countryCode"] = country_code
    data = await cj_request("GET", "/product/list", params=params)
    payload = data.get("data") or {}
    return payload.get("list") or []


def normalize_cj_product(cj: dict) -> dict:
    """Map a CJ product detail payload into an Invovix product document."""
    variants = cj.get("variants") or []
    base_price = 0.0
    if variants:
        try:
            base_price = float(variants[0].get("variantSellPrice") or 0)
        except (TypeError, ValueError):
            base_price = 0.0
    if not base_price:
        try:
            sp = cj.get("sellPrice") or cj.get("productSellPrice") or 0
            base_price = float(str(sp).split("-")[0]) if sp else 0.0
        except (TypeError, ValueError):
            base_price = 0.0

    images = cj.get("productImageSet") or cj.get("productImage") or []
    if isinstance(images, str):
        images = [images]
    raw_imgs = [u for u in images[:6] if u]

    raw_desc = cj.get("description") or ""
    clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
    clean_desc = re.sub(r"&[a-zA-Z]+;", " ", clean_desc)
    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

    return {
        "id": str(uuid.uuid4()),
        "title": cj.get("productNameEn") or cj.get("productName") or "Untitled",
        "title_en": cj.get("productNameEn") or cj.get("productName") or "Untitled",
        "description": clean_desc,
        "description_en": clean_desc,
        "price": round(base_price * 1.6, 2) if base_price else 0.0,
        "cost_price": base_price,
        "compare_at_price": round(base_price * 2.2, 2) if base_price else 0.0,
        "currency": "EUR",
        "category": "smart-home",
        "images": raw_imgs,
        "stock": 100,
        "featured": False,
        "active": True,
        "source": "cjdropshipping",
        "cj_pid": cj.get("pid") or cj.get("productId"),
        "cj_variants": variants,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def import_product(pid: str) -> dict:
    data = await cj_request("GET", "/product/query", params={"pid": pid})
    detail = data.get("data") or {}
    return normalize_cj_product(detail)


# ----------------------------- Variants & stock -----------------------------
def product_margin_ratio(p: dict) -> float:
    cost = p.get("cost_price") or 0
    price = p.get("price") or 0
    try:
        if cost and price:
            return float(price) / float(cost)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return 1.6


def serialize_variants(p: dict) -> list:
    ratio = product_margin_ratio(p)
    out = []
    for v in (p.get("cj_variants") or []):
        try:
            cost = float(v.get("variantSellPrice") or 0)
        except (TypeError, ValueError):
            cost = 0.0
        price = round(cost * ratio, 2) if cost else float(p.get("price", 0) or 0)
        stock = v.get("stock")  # populated by sync_product_stock; None = unknown
        out.append({
            "vid": str(v.get("vid") or ""),
            "name": v.get("variantNameEn") or v.get("variantName") or v.get("variantKey") or "Standard",
            "sku": v.get("variantSku") or "",
            "price": price,
            "image": v.get("variantImage") or (p.get("images") or [None])[0],
            "stock": stock,
        })
    return out


def product_stock_total(p: dict):
    """Returns int stock if known, else None (unknown -> treat as available)."""
    vs = p.get("cj_variants") or []
    if vs:
        known = [v.get("stock") for v in vs if isinstance(v.get("stock"), int)]
        if known:
            return sum(known)
        return None  # not synced yet
    return int(p.get("stock", 0) or 0)


def enrich_product(p: dict) -> dict:
    variants = serialize_variants(p)
    stock_total = product_stock_total(p)
    p = dict(p)
    p["variants"] = variants
    p["has_variants"] = len(variants) > 1
    p["stock_total"] = stock_total
    p["in_stock"] = True if stock_total is None else stock_total > 0
    p.pop("cj_variants", None)  # keep response light / hide raw supplier data
    return p


async def query_vid_stock(vid: str) -> int:
    try:
        data = await cj_request("GET", "/product/stock/queryByVid", params={"vid": vid})
        rows = data.get("data") or []
        total = 0
        for r in rows:
            total += int(r.get("totalInventoryNum") or r.get("cjInventoryNum") or r.get("storageNum") or 0)
        return total
    except Exception:
        return -1  # error sentinel


async def sync_product_stock(product: dict) -> dict:
    """Query live CJ stock for each variant and persist it on the product."""
    variants = product.get("cj_variants") or []
    if not variants:
        return {"ok": False, "reason": "no CJ variants"}
    total = 0
    updated = []
    for v in variants:
        vid = str(v.get("vid") or "")
        s = await query_vid_stock(vid) if vid else -1
        v = dict(v)
        v["stock"] = None if s < 0 else s
        if isinstance(v["stock"], int):
            total += v["stock"]
        updated.append(v)
    await db.products.update_one(
        {"id": product["id"]},
        {"$set": {"cj_variants": updated, "stock_total": total, "stock_synced_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "stock_total": total, "variants": len(updated)}


# ----------------------------- Order fulfillment -----------------------------
EUROZONE_CODES = {
    "france": "FR", "belgique": "BE", "belgium": "BE", "allemagne": "DE", "germany": "DE",
    "espagne": "ES", "spain": "ES", "italie": "IT", "italy": "IT", "pays-bas": "NL",
    "netherlands": "NL", "portugal": "PT", "irlande": "IE", "ireland": "IE",
    "autriche": "AT", "austria": "AT", "finlande": "FI", "finland": "FI",
    "grèce": "GR", "grece": "GR", "greece": "GR", "luxembourg": "LU",
    "slovaquie": "SK", "slovakia": "SK", "slovénie": "SI", "slovenia": "SI",
    "estonie": "EE", "estonia": "EE", "lettonie": "LV", "latvia": "LV",
    "lituanie": "LT", "lithuania": "LT", "chypre": "CY", "cyprus": "CY",
    "malte": "MT", "malta": "MT", "croatie": "HR", "croatia": "HR",
}


def country_to_code(name: str) -> str:
    if not name:
        return "FR"
    n = name.strip()
    if len(n) == 2:
        return n.upper()
    return EUROZONE_CODES.get(n.lower(), "FR")


def _variant_id(product: dict) -> str:
    for v in (product.get("cj_variants") or []):
        vid = v.get("vid") or v.get("variantId") or v.get("id")
        if vid:
            return str(vid)
    return ""


async def create_cj_order(order: dict) -> dict:
    """Create a fulfillment order on CJDropshipping for a paid Invovix order."""
    products = []
    for it in order.get("items", []):
        p = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
        if not p:
            raise RuntimeError(f"Produit introuvable: {it['product_id']}")
        vid = it.get("variant_id") or _variant_id(p)
        if not vid:
            raise RuntimeError(f"Produit sans variante CJ (non-dropshipping): {p.get('title','')}")
        products.append({"vid": vid, "quantity": int(it["quantity"])})

    addr = order.get("shipping_address") or {}
    pay_type = int(os.environ.get("CJ_PAY_TYPE", "3"))  # 3 = create without auto-payment
    payload = {
        "orderNumber": order["id"],
        "fromCountryCode": os.environ.get("CJ_FROM_COUNTRY", "CN"),
        "shippingCountryCode": country_to_code(addr.get("country")),
        "shippingCountry": addr.get("country") or "France",
        "shippingProvince": addr.get("city") or "",
        "shippingCity": addr.get("city") or "",
        "shippingAddress": addr.get("address") or "",
        "shippingCustomerName": addr.get("full_name") or "Client",
        "shippingZip": addr.get("postal_code") or "",
        "shippingPhone": addr.get("phone") or "0000000000",
        "logisticName": os.environ.get("CJ_DEFAULT_LOGISTIC", "CJPacket Ordinary"),
        "remark": "Invovix",
        "payType": pay_type,
        "products": products,
    }
    data = await cj_request("POST", "/shopping/order/createOrderV2", json=payload)
    return data.get("data") or {}


async def get_cj_order(cj_order_id: str) -> dict:
    data = await cj_request("GET", "/shopping/order/getOrderDetail", params={"orderId": cj_order_id})
    return data.get("data") or {}
