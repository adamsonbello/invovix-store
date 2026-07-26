"""Phase 3 tests: CRM (customers, loyalty, abandoned),
Marketing (campaigns, bundles, flash sales), Notifications, Analytics ad-spend.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

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
        assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- Auth guards ----------
def test_customers_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/customers", timeout=15)
    assert r.status_code in (401, 403)


def test_customers_forbidden_for_customer(customer_headers):
    r = requests.get(f"{BASE_URL}/api/admin/customers", headers=customer_headers, timeout=15)
    assert r.status_code in (401, 403)


def test_bundles_admin_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/bundles", timeout=15)
    assert r.status_code in (401, 403)


def test_flash_admin_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/flash-sales", timeout=15)
    assert r.status_code in (401, 403)


def test_campaigns_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/campaigns", timeout=15)
    assert r.status_code in (401, 403)


def test_abandoned_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/abandoned", timeout=15)
    assert r.status_code in (401, 403)


# ---------- CRM ----------
def test_list_customers(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/customers", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and "count" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        c = data["items"][0]
        for key in ("id", "email", "orders_count", "total_spent", "aov",
                    "loyalty_points", "tier", "status"):
            assert key in c, f"missing key {key}"
        assert c["tier"] in ("Bronze", "Argent", "Or", "Platine")
        assert c["status"] in ("nouveau", "actif", "VIP")


def test_customers_segments_and_search(admin_headers):
    for seg in ("vip", "active", "new"):
        r = requests.get(f"{BASE_URL}/api/admin/customers?segment={seg}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert "items" in r.json()
    r = requests.get(f"{BASE_URL}/api/admin/customers?q=client", headers=admin_headers, timeout=30)
    assert r.status_code == 200


def test_customer_detail(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/customers", headers=admin_headers, timeout=30)
    items = r.json()["items"]
    if not items:
        pytest.skip("no customers in db")
    cid = items[0]["id"]
    r = requests.get(f"{BASE_URL}/api/admin/customers/{cid}", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "customer" in d and "orders" in d and "returns" in d
    assert isinstance(d["orders"], list)
    assert isinstance(d["returns"], list)


def test_customer_detail_404(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/customers/does-not-exist", headers=admin_headers, timeout=15)
    assert r.status_code == 404


def test_loyalty_customer(customer_headers):
    r = requests.get(f"{BASE_URL}/api/loyalty", headers=customer_headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ("points", "total_spent", "tier", "perk", "next_tier", "to_next"):
        assert key in d, f"missing {key}"
    assert d["tier"] in ("Bronze", "Argent", "Or", "Platine")


def test_loyalty_requires_auth():
    r = requests.get(f"{BASE_URL}/api/loyalty", timeout=10)
    assert r.status_code in (401, 403)


# ---------- Abandoned ----------
def test_abandoned_list(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/abandoned", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("items", "count", "potential_revenue", "reminded", "recovered", "recovered_revenue"):
        assert k in d, f"missing key {k}"


def test_abandoned_remind_404(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/abandoned/nonexistent-id/remind",
                      headers=admin_headers, timeout=15)
    assert r.status_code == 404


def test_abandoned_run(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/abandoned/run", headers=admin_headers, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "candidates" in d and "sent" in d


# ---------- Campaigns ----------
def test_segment_counts(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/segments/count", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for s in ("newsletter", "customers", "vip", "all"):
        assert s in d
        assert isinstance(d[s], int)


def test_campaign_invalid_segment(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/campaigns", headers=admin_headers,
                      json={"subject": "T", "body_html": "<p>t</p>", "segment": "bad"}, timeout=15)
    assert r.status_code == 400


def test_campaign_create_and_list(admin_headers):
    payload = {"subject": "TEST_Phase3 campaign", "body_html": "<p>hello</p>", "segment": "newsletter"}
    r = requests.post(f"{BASE_URL}/api/admin/campaigns", headers=admin_headers, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "id" in d and "recipients" in d and "status" in d
    r2 = requests.get(f"{BASE_URL}/api/admin/campaigns", headers=admin_headers, timeout=15)
    assert r2.status_code == 200
    ids = [c.get("id") for c in r2.json()["items"]]
    assert d["id"] in ids


# ---------- Bundles ----------
@pytest.fixture(scope="module")
def sample_product_ids():
    r = requests.get(f"{BASE_URL}/api/products", timeout=30)
    assert r.status_code == 200
    prods = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    ids = [p["id"] for p in prods[:2]]
    assert len(ids) >= 2, "need 2 products for bundle test"
    return ids


def test_bundle_crud(admin_headers, sample_product_ids):
    payload = {"title": "TEST_Bundle", "product_ids": sample_product_ids, "bundle_price": 49.99}
    r = requests.post(f"{BASE_URL}/api/admin/bundles", headers=admin_headers, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    for k in ("id", "normal_price", "savings", "savings_pct", "products"):
        assert k in b
    assert len(b["products"]) == 2
    bundle_id = b["id"]

    # list admin
    r = requests.get(f"{BASE_URL}/api/admin/bundles", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    assert any(x["id"] == bundle_id for x in r.json()["items"])

    # public
    r = requests.get(f"{BASE_URL}/api/bundles", timeout=15)
    assert r.status_code == 200
    assert any(x["id"] == bundle_id for x in r.json()["items"])

    # PUT
    payload2 = dict(payload, title="TEST_Bundle Updated", bundle_price=39.99)
    r = requests.put(f"{BASE_URL}/api/admin/bundles/{bundle_id}", headers=admin_headers, json=payload2, timeout=15)
    assert r.status_code == 200
    assert r.json()["title"] == "TEST_Bundle Updated"

    # DELETE
    r = requests.delete(f"{BASE_URL}/api/admin/bundles/{bundle_id}", headers=admin_headers, timeout=15)
    assert r.status_code == 200


# ---------- Flash sales ----------
def test_flash_invalid_scope(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/flash-sales", headers=admin_headers,
                      json={"title": "T", "scope": "invalid", "target": "", "discount_percent": 10,
                            "ends_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
                      timeout=15)
    assert r.status_code == 400


def test_flash_crud_and_apply(admin_headers):
    ends = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    payload = {"title": "TEST_Flash smart-home", "scope": "category", "target": "smart-home",
               "discount_percent": 20, "ends_at": ends, "active": True}
    r = requests.post(f"{BASE_URL}/api/admin/flash-sales", headers=admin_headers, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    sale = r.json()
    sid = sale["id"]

    # admin list has is_active
    r = requests.get(f"{BASE_URL}/api/admin/flash-sales", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    items = r.json()["items"]
    found = [x for x in items if x["id"] == sid]
    assert found and found[0]["is_active"] is True

    # public active
    r = requests.get(f"{BASE_URL}/api/flash-sales/active", timeout=15)
    assert r.status_code == 200
    assert any(x["id"] == sid for x in r.json()["items"])

    # products in smart-home should be discounted
    r = requests.get(f"{BASE_URL}/api/products?category=smart-home", timeout=30)
    assert r.status_code == 200
    prods = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    if prods:
        discounted = [p for p in prods if p.get("flash_discount")]
        assert discounted, "expected at least one product with flash_discount"
        p = discounted[0]
        assert p.get("original_price") and p["price"] < p["original_price"]

    # cleanup
    r = requests.delete(f"{BASE_URL}/api/admin/flash-sales/{sid}", headers=admin_headers, timeout=15)
    assert r.status_code == 200


# ---------- Notifications ----------
def test_notifications_test_dummy(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/notifications/test", headers=admin_headers,
                      json={"discord_webhook_url": "https://discord.com/api/webhooks/invalid/xxx"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_notifications_test_empty(admin_headers):
    r = requests.post(f"{BASE_URL}/api/admin/notifications/test", headers=admin_headers,
                      json={}, timeout=15)
    assert r.status_code == 400


# ---------- Settings + Analytics ad-spend ----------
def test_settings_and_analytics_roas(admin_headers):
    payload = {"ad_spend_30d": 100, "discord_webhook_url": "https://example.com/d",
               "slack_webhook_url": "https://example.com/s", "notify_new_order": True}
    r = requests.put(f"{BASE_URL}/api/admin/settings", headers=admin_headers, json=payload, timeout=15)
    assert r.status_code == 200, r.text

    r = requests.get(f"{BASE_URL}/api/admin/analytics", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("ad_spend_30d") == 100
    rev = d.get("revenue_30d", 0)
    roas = d.get("roas")
    if roas is not None:
        assert abs(roas - (rev / 100)) < 0.01
