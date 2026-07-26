"""Tests for new modules: imports, documents, predict, stores."""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    if data.get("twofa_required"):
        pytest.skip("2FA is enabled on admin account")
    token = data.get("token")
    assert token
    return token


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------- RBAC ----------------
class TestRBAC:
    def test_stores_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/stores", timeout=10)
        assert r.status_code in (401, 403)

    def test_documents_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/documents", timeout=10)
        assert r.status_code in (401, 403)

    def test_predict_forecast_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/predict/forecast", timeout=10)
        assert r.status_code in (401, 403)

    def test_import_url_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/import/url", json={"url": "https://example.com"}, timeout=10)
        assert r.status_code in (401, 403)


# ---------------- Imports (CSV/URL) ----------------
class TestImports:
    def test_csv_import(self, admin_headers):
        csv = (
            "title,description,price,buy_price,category,brand,sku,stock\n"
            "TEST_Prod_A,Awesome A,29.99,10,smart-home,TestBrand,SKUA1,50\n"
            "TEST_Prod_B,Awesome B,,15,smart-home,TestBrand,SKUB1,20\n"
            "TEST_Prod_C,No price no buy,,,smart-home,TestBrand,SKUC1,5\n"
        ).encode("utf-8")
        files = {"file": ("test.csv", csv, "text/csv")}
        data = {"margin": "60", "category": "smart-home"}
        r = requests.post(
            f"{BASE_URL}/api/admin/import/file",
            headers=admin_headers, files=files, data=data, timeout=60,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["imported"] >= 2, j
        # Prod_B: empty price -> should be computed 15 * 1.6 = 24.0
        results = j.get("results", [])
        b = next((x for x in results if x.get("title") == "TEST_Prod_B"), None)
        assert b is not None
        assert abs(b.get("price", 0) - 24.0) < 0.01, f"Expected 24.00, got {b.get('price')}"

    def test_url_import_bad_url(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/admin/import/url",
            headers=admin_headers,
            json={"url": "not_a_url", "margin": 60, "category": "smart-home"},
            timeout=15,
        )
        assert r.status_code in (400, 422)

    def test_url_import_public_page(self, admin_headers):
        # example.com has no product data → expect 422 (clean error) — should not crash
        r = requests.post(
            f"{BASE_URL}/api/admin/import/url",
            headers=admin_headers,
            json={"url": "https://example.com", "margin": 60, "category": "smart-home"},
            timeout=45,
        )
        assert r.status_code in (200, 422, 502), f"Unexpected: {r.status_code} {r.text}"


# ---------------- Documents ----------------
class TestDocuments:
    _doc_id = None

    def test_upload(self, admin_headers):
        files = {"file": ("test_contract.txt", b"Hello, this is a test document.", "text/plain")}
        data = {"name": "TEST_Contract_A", "category": "contract", "tags": "test,rbac", "notes": "Test upload"}
        r = requests.post(f"{BASE_URL}/api/admin/documents", headers=admin_headers, files=files, data=data, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["name"] == "TEST_Contract_A"
        assert j["category"] == "contract"
        assert j.get("id")
        TestDocuments._doc_id = j["id"]

    def test_list_with_by_category(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/documents", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert "items" in j and "by_category" in j
        assert isinstance(j["by_category"], dict)
        assert j["by_category"].get("contract", 0) >= 1

    def test_download(self, admin_headers):
        assert TestDocuments._doc_id
        r = requests.get(
            f"{BASE_URL}/api/admin/documents/{TestDocuments._doc_id}/download",
            headers=admin_headers, timeout=10,
        )
        assert r.status_code == 200
        assert b"Hello, this is a test document." in r.content

    def test_delete(self, admin_headers):
        assert TestDocuments._doc_id
        r = requests.delete(
            f"{BASE_URL}/api/admin/documents/{TestDocuments._doc_id}",
            headers=admin_headers, timeout=10,
        )
        assert r.status_code == 200
        # Verify gone
        r2 = requests.get(
            f"{BASE_URL}/api/admin/documents/{TestDocuments._doc_id}/download",
            headers=admin_headers, timeout=10,
        )
        assert r2.status_code == 404


# ---------------- Predict ----------------
class TestPredict:
    def test_forecast(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/predict/forecast", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        for key in ("history", "forecast", "predicted_total", "trend", "growth_30d", "demand"):
            assert key in j, f"missing {key}"
        assert isinstance(j["history"], list)
        assert isinstance(j["forecast"], list)
        assert isinstance(j["demand"], list)

    def test_pricing_suggestions(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/predict/pricing", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "items" in j
        # If items exist, verify keys
        if j["items"]:
            it = j["items"][0]
            for k in ("id", "suggested_price", "delta", "price"):
                assert k in it

    def test_apply_price(self, admin_headers):
        # Find any product to update
        r = requests.get(f"{BASE_URL}/api/admin/predict/pricing", headers=admin_headers, timeout=30)
        items = r.json().get("items", [])
        if not items:
            # Fall back — find any product
            rp = requests.get(f"{BASE_URL}/api/products?limit=1", timeout=10)
            if rp.status_code == 200:
                data = rp.json()
                lst = data if isinstance(data, list) else data.get("items", [])
                if not lst:
                    pytest.skip("No products available")
                pid = lst[0]["id"]
                new_price = 42.42
            else:
                pytest.skip("No pricing suggestions and no products")
        else:
            pid = items[0]["id"]
            new_price = float(items[0]["suggested_price"])
        r2 = requests.post(
            f"{BASE_URL}/api/admin/predict/pricing/apply",
            headers=admin_headers,
            json={"product_id": pid, "price": new_price},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        j = r2.json()
        assert j["ok"] is True
        assert abs(j["price"] - round(new_price, 2)) < 0.01

    def test_ai_price(self, admin_headers):
        # Get any product
        rp = requests.get(f"{BASE_URL}/api/products?limit=1", timeout=10)
        if rp.status_code != 200:
            pytest.skip("Cannot fetch products")
        data = rp.json()
        lst = data if isinstance(data, list) else data.get("items", [])
        if not lst:
            pytest.skip("No products available")
        pid = lst[0]["id"]
        r = requests.post(
            f"{BASE_URL}/api/admin/predict/ai-price/{pid}",
            headers=admin_headers, timeout=60,  # AI is slow
        )
        # 200 expected but tolerate 502 if LLM fails
        assert r.status_code in (200, 502), f"{r.status_code} {r.text[:300]}"
        if r.status_code == 200:
            j = r.json()
            assert "recommended_price" in j
            assert "opportunity_score" in j


# ---------------- Stores ----------------
class TestStores:
    _store_id = None
    _store_slug = None

    def test_create(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/admin/stores",
            headers=admin_headers,
            json={"name": "TEST_Boutique_Alpha", "categories": ["smart-home"], "tagline": "Test tagline", "active": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["name"] == "TEST_Boutique_Alpha"
        assert j.get("slug")
        assert "product_count" in j
        TestStores._store_id = j["id"]
        TestStores._store_slug = j["slug"]

    def test_list(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/stores", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert "items" in j
        assert "available_categories" in j
        assert any(s.get("id") == TestStores._store_id for s in j["items"])

    def test_update(self, admin_headers):
        assert TestStores._store_id
        r = requests.put(
            f"{BASE_URL}/api/admin/stores/{TestStores._store_id}",
            headers=admin_headers,
            json={"name": "TEST_Boutique_Alpha", "categories": ["smart-home"], "tagline": "Updated tagline", "active": True},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["tagline"] == "Updated tagline"

    def test_catalog(self, admin_headers):
        assert TestStores._store_id
        r = requests.get(
            f"{BASE_URL}/api/admin/stores/{TestStores._store_id}/catalog",
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert "items" in j and "store" in j

    def test_public_store(self):
        assert TestStores._store_slug
        r = requests.get(f"{BASE_URL}/api/public/stores/{TestStores._store_slug}", timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["store"]["slug"] == TestStores._store_slug
        assert "products" in j

    def test_delete(self, admin_headers):
        assert TestStores._store_id
        r = requests.delete(
            f"{BASE_URL}/api/admin/stores/{TestStores._store_id}",
            headers=admin_headers, timeout=10,
        )
        assert r.status_code == 200
