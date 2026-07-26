"""Tests for Cerveau IA (Phase 1 AI Brain) endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://smart-home-shop-20.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"
CUSTOMER_EMAIL = "client@invovix.store"
CUSTOMER_PASSWORD = "Client2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    # try register
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "name": "Client Test"}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    pytest.skip("no customer token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ----- Auth guard tests -----
def test_ai_status_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/ai/status", timeout=30)
    assert r.status_code in (401, 403)


def test_ai_status_forbidden_for_customer(customer_token):
    r = requests.get(f"{BASE_URL}/api/admin/ai/status", headers={"Authorization": f"Bearer {customer_token}"}, timeout=30)
    assert r.status_code in (401, 403)


def test_ai_rewrite_requires_auth():
    r = requests.post(f"{BASE_URL}/api/admin/ai/rewrite-product", json={"title": "Test"}, timeout=30)
    assert r.status_code in (401, 403)


# ----- Status -----
def test_ai_status_ok(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/ai/status", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("configured") is True
    assert "text_model" in data
    assert "image_model" in data


# ----- Rewrite product -----
def test_ai_rewrite_product(admin_headers):
    payload = {"title": "Ampoule LED connectée E27", "description": "Ampoule wifi 10W", "category": "smart-home"}
    r = requests.post(f"{BASE_URL}/api/admin/ai/rewrite-product", json=payload, headers=admin_headers, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    for field in ["title", "title_en", "description", "description_en", "bullet_points", "seo_title", "seo_description", "keywords", "faq"]:
        assert field in data, f"missing {field} in {list(data.keys())}"
    assert isinstance(data["bullet_points"], list)
    assert isinstance(data["keywords"], list)
    assert isinstance(data["faq"], list)


# ----- Product score -----
def test_ai_product_score(admin_headers):
    payload = {"title": "Caméra WiFi 1080p intérieur", "category": "security", "sell_price": 39.9, "cost_price": 12.0}
    r = requests.post(f"{BASE_URL}/api/admin/ai/product-score", json=payload, headers=admin_headers, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    for field in ["opportunity_score", "demand", "margin", "competition", "verdict", "reasons", "recommended_price", "margin_pct"]:
        assert field in data, f"missing {field} in {list(data.keys())}"
    assert 0 <= float(data["opportunity_score"]) <= 100
    assert isinstance(data["reasons"], list)
    assert data["margin_pct"] > 0


# ----- Analyze -----
def test_ai_analyze(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/ai/analyze", json={"question": "Quels sont mes 3 top produits ce mois-ci ?"}, headers=admin_headers, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "answer" in data and "context_used" in data
    assert isinstance(data["answer"], str) and len(data["answer"].strip()) > 20


# ----- Image generation -----
def test_ai_generate_image(admin_headers):
    payload = {"prompt": "Ampoule LED connectée", "style": "white", "use_reference": False}
    r = requests.post(f"{BASE_URL}/api/admin/ai/generate-image", json=payload, headers=admin_headers, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    url = data.get("url", "")
    assert url.startswith("/products/"), f"unexpected url {url}"
    # File served
    img = requests.get(f"{BASE_URL}{url}", timeout=30)
    assert img.status_code == 200
    assert len(img.content) > 500
