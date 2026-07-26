"""Tests for iteration 3: analytics, stock sync, variants, invoice PDF,
returns/refunds, CJ webhook. Uses public REACT_APP_BACKEND_URL."""
import os
import time
import pytest
import requests
from pymongo import MongoClient

# Load backend env for direct DB access to mark orders paid (no public API for it)
try:
    _envtxt = open("/app/backend/.env").read()
    _MONGO_URL = _envtxt.split("MONGO_URL=")[1].split("\n")[0].strip().strip('"')
    _DB_NAME = _envtxt.split("DB_NAME=")[1].split("\n")[0].strip().strip('"')
    _mdb = MongoClient(_MONGO_URL)[_DB_NAME]
except Exception:
    _mdb = None


def _mark_paid(order_id):
    if _mdb is None:
        return False
    res = _mdb.orders.update_one(
        {"id": order_id},
        {"$set": {"payment_status": "paid", "status": "delivered"}},
    )
    return res.matched_count == 1

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0]
           ).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"
CUSTOMER_EMAIL = "client@invovix.store"
CUSTOMER_PASSWORD = "Client2026!"


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def customer_ctx():
    r = requests.post(f"{API}/auth/login",
                      json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}, timeout=15)
    if r.status_code != 200:
        r = requests.post(f"{API}/auth/register",
                          json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD,
                                "name": "Test Client"}, timeout=15)
        assert r.status_code == 200, r.text
    data = r.json()
    return {"headers": {"Authorization": f"Bearer {data['token']}"},
            "user_id": data["user"]["id"], "email": data["user"]["email"]}


@pytest.fixture(scope="module")
def cj_product():
    r = requests.get(f"{API}/products?size=30", timeout=15)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    # prefer CJ product
    for it in items:
        full = requests.get(f"{API}/products/{it['id']}", timeout=15).json()
        if full.get("source") == "cjdropshipping":
            return full
    return requests.get(f"{API}/products/{items[0]['id']}", timeout=15).json()


# ------------- Analytics -------------
class TestAnalytics:
    def test_pageview_increments(self):
        r = requests.post(f"{API}/track/pageview", timeout=10)
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        # second one still ok
        r2 = requests.post(f"{API}/track/pageview", timeout=10)
        assert r2.status_code == 200

    def test_pageview_no_auth_needed(self):
        # no header should still work
        r = requests.post(f"{API}/track/pageview", timeout=10)
        assert r.status_code == 200

    def test_admin_analytics_requires_auth(self):
        r = requests.get(f"{API}/admin/analytics", timeout=10)
        assert r.status_code in (401, 403)

    def test_admin_analytics_shape(self, admin_headers):
        r = requests.get(f"{API}/admin/analytics", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("revenue", "paid_orders", "aov", "total_orders",
                  "status_breakdown", "revenue_series", "top_products",
                  "new_customers_30d", "total_customers", "visits_30d",
                  "conversion_rate"):
            assert k in d, f"missing {k}"
        assert isinstance(d["revenue_series"], list) and len(d["revenue_series"]) == 30
        for pt in d["revenue_series"]:
            assert "date" in pt and "revenue" in pt
        assert isinstance(d["status_breakdown"], dict)
        for s in ["pending", "processing", "shipped", "delivered", "cancelled"]:
            assert s in d["status_breakdown"]
        assert isinstance(d["top_products"], list)
        assert d["visits_30d"] >= 1  # from pageview above


# ------------- Product variants & stock (enrich) -------------
class TestProductEnrich:
    def test_product_detail_shape(self, cj_product):
        p = cj_product
        assert "variants" in p
        assert "has_variants" in p
        assert "stock_total" in p
        assert "in_stock" in p
        assert "cj_variants" not in p, "raw cj_variants should be stripped"
        assert isinstance(p["variants"], list)
        assert p["stock_total"] is None or isinstance(p["stock_total"], int)
        assert isinstance(p["in_stock"], bool)
        # variant should have vid, name, price, stock
        if p["variants"]:
            v = p["variants"][0]
            for k in ("vid", "name", "price", "stock"):
                assert k in v, f"variant missing {k}"


# ------------- Stock sync (admin) -------------
class TestStockSync:
    def test_sync_stock_requires_admin(self, cj_product):
        r = requests.post(f"{API}/admin/products/{cj_product['id']}/sync-stock", timeout=15)
        assert r.status_code in (401, 403)

    def test_sync_stock_all_requires_admin(self):
        r = requests.post(f"{API}/admin/products/sync-stock-all", timeout=15)
        assert r.status_code in (401, 403)

    def test_sync_stock_single(self, admin_headers, cj_product):
        # only meaningful for cj products; if not cj, endpoint may still work but return
        r = requests.post(f"{API}/admin/products/{cj_product['id']}/sync-stock",
                          headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # cj.sync_product_stock returns something like {ok:true, stock_total:int}
        assert "stock_total" in d or "ok" in d, d
        if "stock_total" in d:
            assert isinstance(d["stock_total"], int)

    def test_sync_stock_all(self, admin_headers):
        r = requests.post(f"{API}/admin/products/sync-stock-all",
                          headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert "queued" in d and isinstance(d["queued"], int)


# ------------- CJ webhook -------------
class TestCJWebhook:
    def test_webhook_accepts_body(self):
        payload = {"data": {"orderNumber": "nonexistent-xyz",
                            "orderId": "cj-xxx",
                            "trackNumber": "TRACK123"}}
        r = requests.post(f"{API}/webhook/cj", json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_webhook_empty_body(self):
        r = requests.post(f"{API}/webhook/cj", data="", timeout=15)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_sitemap_still_ok(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=10)
        assert r.status_code == 200


# ------------- Invoice PDF -------------
class TestInvoice:
    @pytest.fixture(scope="class")
    def unpaid_order(self, customer_ctx, cj_product):
        payload = {
            "items": [{"product_id": cj_product["id"], "quantity": 1}],
            "shipping_address": {
                "full_name": "TEST Invoice",
                "email": "test@example.com",
                "address": "1 rue test",
                "city": "Paris", "postal_code": "75001",
                "country": "FR", "phone": "0600000000",
            },
        }
        r = requests.post(f"{API}/orders", json=payload,
                          headers=customer_ctx["headers"], timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_invoice_requires_auth(self, unpaid_order):
        r = requests.get(f"{API}/orders/{unpaid_order['id']}/invoice", timeout=15)
        assert r.status_code in (401, 403)

    def test_invoice_unpaid_returns_400(self, customer_ctx, unpaid_order):
        r = requests.get(f"{API}/orders/{unpaid_order['id']}/invoice",
                         headers=customer_ctx["headers"], timeout=15)
        assert r.status_code == 400, r.text

    def test_invoice_non_owner_forbidden(self, unpaid_order):
        # register a different user
        email = f"other{int(time.time())}@invovix.store"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "Other2026!",
                                "name": "Other"}, timeout=15)
        assert r.status_code == 200
        other_hdr = {"Authorization": f"Bearer {r.json()['token']}"}
        r2 = requests.get(f"{API}/orders/{unpaid_order['id']}/invoice",
                          headers=other_hdr, timeout=15)
        # non-owner => 403 (or 404 depending on implementation, our code returns 404 first because find_one is not filtered by user)
        assert r2.status_code in (403, 404), r2.text

    def test_invoice_paid_order(self, admin_headers, customer_ctx, unpaid_order):
        """Mark the order paid via direct DB write then GET invoice."""
        if not _mark_paid(unpaid_order["id"]):
            pytest.skip("cannot mark paid via DB")
        r = requests.get(f"{API}/orders/{unpaid_order['id']}/invoice",
                         headers=customer_ctx["headers"], timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# ------------- Returns flow -------------
class TestReturns:
    @pytest.fixture(scope="class")
    def paid_order(self, customer_ctx, cj_product, admin_headers):
        payload = {
            "items": [{"product_id": cj_product["id"], "quantity": 1}],
            "shipping_address": {
                "full_name": "TEST Return",
                "email": "test@example.com",
                "address": "1 rue test",
                "city": "Paris", "postal_code": "75001",
                "country": "FR", "phone": "0600000000",
            },
        }
        r = requests.post(f"{API}/orders", json=payload,
                          headers=customer_ctx["headers"], timeout=15)
        assert r.status_code == 200
        oid = r.json()["id"]
        if not _mark_paid(oid):
            pytest.skip("cannot mark paid")
        return oid

    def test_returns_requires_auth(self):
        r = requests.post(f"{API}/returns",
                         json={"order_id": "x", "reason": "test"}, timeout=10)
        assert r.status_code in (401, 403)

    def test_return_on_unpaid_returns_400(self, customer_ctx, cj_product):
        payload = {
            "items": [{"product_id": cj_product["id"], "quantity": 1}],
            "shipping_address": {"full_name": "TEST", "email": "t@t.t",
                                 "address": "x", "city": "Paris", "postal_code": "75001",
                                 "country": "FR", "phone": "0600000000"},
        }
        r = requests.post(f"{API}/orders", json=payload,
                          headers=customer_ctx["headers"], timeout=15)
        oid = r.json()["id"]
        r2 = requests.post(f"{API}/returns",
                           json={"order_id": oid, "reason": "unpaid test"},
                           headers=customer_ctx["headers"], timeout=15)
        assert r2.status_code == 400

    def test_return_full_flow(self, customer_ctx, admin_headers, paid_order):
        # create return
        r = requests.post(f"{API}/returns",
                          json={"order_id": paid_order, "reason": "Défectueux (test)"},
                          headers=customer_ctx["headers"], timeout=15)
        assert r.status_code == 200, r.text
        ret = r.json()
        assert ret["order_id"] == paid_order
        assert ret["status"] == "requested"
        rid = ret["id"]

        # duplicate should be rejected
        r_dup = requests.post(f"{API}/returns",
                              json={"order_id": paid_order, "reason": "dup"},
                              headers=customer_ctx["headers"], timeout=15)
        assert r_dup.status_code == 400

        # admin lists
        r_l = requests.get(f"{API}/admin/returns", headers=admin_headers, timeout=15)
        assert r_l.status_code == 200
        assert any(x["id"] == rid for x in r_l.json()["items"])

        # customer lists
        r_c = requests.get(f"{API}/returns", headers=customer_ctx["headers"], timeout=15)
        assert r_c.status_code == 200
        assert any(x["id"] == rid for x in r_c.json()["items"])

        # admin approve
        r_a = requests.put(f"{API}/admin/returns/{rid}",
                           json={"action": "approve", "admin_note": "ok"},
                           headers=admin_headers, timeout=30)
        assert r_a.status_code == 200, r_a.text
        assert r_a.json()["status"] in ("approved", "refunded")

    def test_admin_returns_requires_auth(self):
        r = requests.get(f"{API}/admin/returns", timeout=10)
        assert r.status_code in (401, 403)

    def test_return_reject_flow(self, customer_ctx, admin_headers, cj_product):
        # create+pay a fresh order
        payload = {
            "items": [{"product_id": cj_product["id"], "quantity": 1}],
            "shipping_address": {"full_name": "TEST", "email": "t@t.t",
                                 "address": "x", "city": "Paris", "postal_code": "75001",
                                 "country": "FR", "phone": "0600000000"},
        }
        oid = requests.post(f"{API}/orders", json=payload,
                            headers=customer_ctx["headers"], timeout=15).json()["id"]
        if not _mark_paid(oid):
            pytest.skip("cannot mark paid")
        rid = requests.post(f"{API}/returns",
                            json={"order_id": oid, "reason": "reject test"},
                            headers=customer_ctx["headers"], timeout=15).json()["id"]
        r = requests.put(f"{API}/admin/returns/{rid}",
                         json={"action": "reject", "admin_note": "no"},
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_return_invalid_action(self, admin_headers, customer_ctx, cj_product):
        # need a valid return id — reuse: create paid + return
        payload = {"items": [{"product_id": cj_product["id"], "quantity": 1}],
                   "shipping_address": {"full_name": "TEST", "email": "t@t.t",
                                        "address": "x", "city": "Paris",
                                        "postal_code": "75001",
                                        "country": "FR", "phone": "0600000000"}}
        oid = requests.post(f"{API}/orders", json=payload,
                            headers=customer_ctx["headers"], timeout=15).json()["id"]
        if not _mark_paid(oid):
            pytest.skip("cannot mark paid")
        rid = requests.post(f"{API}/returns",
                            json={"order_id": oid, "reason": "x"},
                            headers=customer_ctx["headers"], timeout=15).json()["id"]
        r = requests.put(f"{API}/admin/returns/{rid}",
                         json={"action": "bogus"},
                         headers=admin_headers, timeout=15)
        assert r.status_code == 400
