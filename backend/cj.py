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
        r.raise_for_status()
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
