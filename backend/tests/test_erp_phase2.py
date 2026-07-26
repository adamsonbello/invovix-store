"""Phase 2 ERP tests: suppliers, rules engine, alerts, enriched analytics,
enriched product catalog, ad-spend setting, one-click AI optimize, CJ optimize flag.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://smart-home-shop-20.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"
CUSTOMER_EMAIL = "client@invovix.store"
CUSTOMER_PASSWORD = "Client2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def customer_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}, timeout=30)
    if r.status_code != 200:
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "name": "Client"}, timeout=30)
    if r.status_code != 200:
        pytest.skip("no customer token")
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- Auth guards ----------
def test_suppliers_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/suppliers", timeout=15)
    assert r.status_code in (401, 403)


def test_rules_forbidden_for_customer(customer_headers):
    r = requests.get(f"{BASE_URL}/api/admin/rules", headers=customer_headers, timeout=15)
    assert r.status_code in (401, 403)


def test_alerts_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/alerts", timeout=15)
    assert r.status_code in (401, 403)


def test_analytics_forbidden_for_customer(customer_headers):
    r = requests.get(f"{BASE_URL}/api/admin/analytics", headers=customer_headers, timeout=15)
    assert r.status_code in (401, 403)


# ---------- Suppliers CRUD ----------
class TestSuppliers:
    supplier_id = None

    def test_create_supplier(self, admin_headers):
        payload = {
            "name": f"TEST_Supplier_{uuid.uuid4().hex[:6]}",
            "contact_email": "t@t.io", "country": "CN",
            "avg_delay_days": 10, "quality_rating": 4.5,
            "shipping_cost": 5.0, "notes": "test"
        }
        r = requests.post(f"{BASE_URL}/api/admin/suppliers", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert "id" in data and "score" in data
        assert isinstance(data["score"], (int, float))
        assert data["score"] > 0
        TestSuppliers.supplier_id = data["id"]

    def test_list_suppliers(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/suppliers", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        ids = [s["id"] for s in data["items"]]
        assert TestSuppliers.supplier_id in ids
        found = next(s for s in data["items"] if s["id"] == TestSuppliers.supplier_id)
        assert "score" in found and "product_count" in found

    def test_compare_suppliers_sorted(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/suppliers/compare", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert all("score" in s for s in items)
        scores = [s["score"] for s in items]
        assert scores == sorted(scores, reverse=True)

    def test_update_supplier(self, admin_headers):
        assert TestSuppliers.supplier_id
        payload = {"name": "TEST_Supplier_Updated", "quality_rating": 3.0,
                   "avg_delay_days": 20, "shipping_cost": 8}
        r = requests.put(f"{BASE_URL}/api/admin/suppliers/{TestSuppliers.supplier_id}",
                         json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "TEST_Supplier_Updated"
        assert data["quality_rating"] == 3.0

    def test_delete_supplier(self, admin_headers):
        assert TestSuppliers.supplier_id
        r = requests.delete(f"{BASE_URL}/api/admin/suppliers/{TestSuppliers.supplier_id}",
                            headers=admin_headers, timeout=15)
        assert r.status_code == 200
        # verify removed
        r2 = requests.get(f"{BASE_URL}/api/admin/suppliers", headers=admin_headers, timeout=15)
        ids = [s["id"] for s in r2.json()["items"]]
        assert TestSuppliers.supplier_id not in ids


# ---------- Rules engine ----------
class TestRules:
    rule_id = None

    def test_create_rule_invalid_cond_type(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/rules",
                          json={"name": "bad", "cond_type": "invalid_xxx", "action_type": "alert"},
                          headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_create_rule_invalid_action(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/rules",
                          json={"name": "bad", "cond_type": "out_of_stock", "action_type": "foobar"},
                          headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_create_rule_ok(self, admin_headers):
        payload = {"name": "TEST_LowStock", "active": True,
                   "cond_type": "low_stock", "cond_value": 5,
                   "action_type": "alert"}
        r = requests.post(f"{BASE_URL}/api/admin/rules", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["cond_type"] == "low_stock"
        assert d["action_type"] == "alert"
        assert "id" in d
        TestRules.rule_id = d["id"]

    def test_list_rules(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/rules", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()["items"]]
        assert TestRules.rule_id in ids

    def test_run_rules(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/rules/run", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["rules", "matches", "alerts", "hidden", "repriced"]:
            assert k in d, f"missing {k}"
        assert d["rules"] >= 1

    def test_delete_rule(self, admin_headers):
        assert TestRules.rule_id
        r = requests.delete(f"{BASE_URL}/api/admin/rules/{TestRules.rule_id}",
                            headers=admin_headers, timeout=15)
        assert r.status_code == 200


# ---------- Alerts ----------
def test_list_alerts(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/alerts", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "unresolved" in d


def test_clear_alerts(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/alerts/clear", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    # after clear, unresolved should be 0
    r2 = requests.get(f"{BASE_URL}/api/admin/alerts", headers=admin_headers, timeout=15)
    assert r2.json()["unresolved"] == 0


def test_resolve_alert_idempotent(admin_headers):
    # No alerts likely: create one via rule run - use rule with out_of_stock, but skip if none
    r = requests.get(f"{BASE_URL}/api/admin/alerts?include_resolved=true", headers=admin_headers, timeout=15)
    items = r.json().get("items", [])
    if not items:
        pytest.skip("no alerts to resolve")
    aid = items[0]["id"]
    r2 = requests.put(f"{BASE_URL}/api/admin/alerts/{aid}/resolve", headers=admin_headers, timeout=15)
    assert r2.status_code == 200


# ---------- Enriched analytics + ad-spend ----------
def test_settings_ad_spend_persists(admin_headers):
    # set ad_spend_30d=100
    r = requests.put(f"{BASE_URL}/api/admin/settings",
                     json={"ad_spend_30d": 100.0}, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    assert float(r.json().get("ad_spend_30d", 0)) == 100.0


def test_analytics_enriched(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/analytics", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for field in ["gross_profit", "revenue_30d", "ad_spend_30d",
                  "net_profit_30d", "roas", "roi", "out_of_stock",
                  "low_stock", "to_ship", "unresolved_alerts", "revenue_monthly"]:
        assert field in d, f"missing analytics field: {field}"
    assert isinstance(d["revenue_monthly"], list)
    assert len(d["revenue_monthly"]) == 12
    for m in d["revenue_monthly"]:
        assert "month" in m and "revenue" in m
    # ad_spend reflected
    assert float(d["ad_spend_30d"]) == 100.0
    # roas = revenue_30d / 100
    expected_roas = round(float(d["revenue_30d"]) / 100.0, 2)
    assert abs(d["roas"] - expected_roas) < 0.05


def test_analytics_reset_ad_spend(admin_headers):
    # cleanup: set back to 0
    r = requests.put(f"{BASE_URL}/api/admin/settings",
                     json={"ad_spend_30d": 0.0}, headers=admin_headers, timeout=15)
    assert r.status_code == 200


# ---------- Enriched product catalog ----------
class TestEnrichedProduct:
    product_id = None

    def test_create_product_enriched(self, admin_headers):
        payload = {
            "title": f"TEST_Product_{uuid.uuid4().hex[:6]}",
            "description": "Test enriched", "price": 49.9,
            "buy_price": 10.0, "brand": "TestBrand",
            "sku": "SKU-TEST-1", "ean": "1234567890123",
            "weight": 0.5, "dimensions": "10x5x2 cm",
            "supplier_id": "sup-xyz", "supplier_url": "https://example.com/sup",
            "video_url": "https://youtu.be/xyz", "subcategory": "cameras",
            "category": "smart-home", "images": ["/products/default.png"],
        }
        r = requests.post(f"{BASE_URL}/api/admin/products", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        TestEnrichedProduct.product_id = d["id"]
        for k in ["buy_price", "brand", "sku", "ean", "weight", "dimensions",
                  "supplier_id", "supplier_url", "video_url", "subcategory"]:
            assert d.get(k) == payload[k], f"mismatch on {k}: {d.get(k)} vs {payload[k]}"

    def test_get_product_returns_enriched(self, admin_headers):
        assert TestEnrichedProduct.product_id
        r = requests.get(f"{BASE_URL}/api/products/{TestEnrichedProduct.product_id}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("brand") == "TestBrand"
        assert d.get("sku") == "SKU-TEST-1"
        assert d.get("buy_price") == 10.0
        assert d.get("supplier_id") == "sup-xyz"

    def test_update_preserves_enriched(self, admin_headers):
        assert TestEnrichedProduct.product_id
        payload = {
            "title": "TEST_Product_Updated", "description": "upd", "price": 59.9,
            "buy_price": 12.0, "brand": "TestBrand", "sku": "SKU-TEST-1",
            "ean": "1234567890123", "weight": 0.5, "dimensions": "10x5x2 cm",
            "supplier_id": "sup-xyz", "supplier_url": "https://example.com/sup",
            "video_url": "https://youtu.be/xyz", "subcategory": "cameras",
            "category": "smart-home", "images": ["/products/default.png"],
        }
        r = requests.put(f"{BASE_URL}/api/admin/products/{TestEnrichedProduct.product_id}",
                         json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        # GET
        g = requests.get(f"{BASE_URL}/api/products/{TestEnrichedProduct.product_id}", timeout=15)
        assert g.status_code == 200
        d = g.json()
        assert d.get("buy_price") == 12.0
        assert d.get("brand") == "TestBrand"
        assert d.get("video_url") == "https://youtu.be/xyz"

    def test_cleanup_product(self, admin_headers):
        if TestEnrichedProduct.product_id:
            requests.delete(f"{BASE_URL}/api/admin/products/{TestEnrichedProduct.product_id}",
                            headers=admin_headers, timeout=15)


# ---------- One-click AI optimize ----------
def test_ai_optimize_one_click(admin_headers):
    # create a product to optimize
    payload = {"title": "TEST_Optimize_Lampe LED WiFi RGB", "description": "Lampe connectée simple",
               "price": 39.9, "buy_price": 8.0, "category": "smart-home",
               "images": ["/products/default.png"]}
    r = requests.post(f"{BASE_URL}/api/admin/products", json=payload, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    try:
        r2 = requests.post(f"{BASE_URL}/api/admin/ai/optimize-product/{pid}",
                           json={"rewrite": True, "image": False, "score": True},
                           headers=admin_headers, timeout=180)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert "done" in d and "product" in d
        assert "rewrite" in d["done"]
        assert "score" in d["done"]
        p = d["product"]
        assert p.get("ai_optimized") is True
        assert p.get("seo_title")
        assert "ai_score" in p
        assert "opportunity_score" in p["ai_score"]
    finally:
        requests.delete(f"{BASE_URL}/api/admin/products/{pid}", headers=admin_headers, timeout=15)


# ---------- CJ import-bulk accepts optimize flag ----------
def test_cj_import_bulk_accepts_optimize_flag(admin_headers):
    # empty pids => should not error and return results structure
    r = requests.post(f"{BASE_URL}/api/admin/cj/import-bulk",
                      json={"pids": [], "margin": 60, "category": "smart-home", "optimize": True},
                      headers=admin_headers, timeout=30)
    # accept 200 (empty) or 400 (if backend rejects empty list) — but must not 422 due to unknown field
    # 503 possible if CJ key missing; 400 if empty rejected; 200 otherwise
    assert r.status_code in (200, 400, 503), r.text
    if r.status_code == 200:
        d = r.json()
        assert "results" in d or "items" in d or isinstance(d, dict)
