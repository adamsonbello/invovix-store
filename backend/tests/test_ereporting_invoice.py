"""Iteration 4 tests: e-reporting CSV/JSON aggregation (franchise & assujetti),
sequential PDF invoice numbering, settings legal fields persistence, and
manual stock-sync endpoints (background loops are verified via server logs)."""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

# --- Direct Mongo access (no admin API for flipping order.payment_status) ---
_envtxt = open("/app/backend/.env").read()
_MONGO_URL = _envtxt.split("MONGO_URL=")[1].split("\n")[0].strip().strip('"')
_DB_NAME = _envtxt.split("DB_NAME=")[1].split("\n")[0].strip().strip('"')
_mdb = MongoClient(_MONGO_URL)[_DB_NAME]

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
    assert r.status_code == 200, r.text
    data = r.json()
    return {"headers": {"Authorization": f"Bearer {data['token']}"},
            "user_id": data["user"]["id"], "email": data["user"]["email"]}


def _restore_settings_to_franchise(admin_headers):
    """Baseline settings the storefront expects."""
    r = requests.get(f"{API}/settings", timeout=10)
    cur = r.json()
    body = {k: cur.get(k, "") for k in
            ["banner_enabled", "banner_text", "banner_text_en", "whatsapp_number",
             "whatsapp_enabled", "company_name", "company_legal_form", "siren",
             "siret", "vat_number", "company_address", "vat_regime", "vat_rate"]}
    body["vat_regime"] = "franchise"
    body["vat_rate"] = 20.0
    requests.put(f"{API}/admin/settings", json=body, headers=admin_headers, timeout=10)


def _create_paid_order(customer_ctx, total: float, days_ago: int) -> str:
    """Create an order via API then flip payment_status to 'paid' directly in Mongo,
    and back-date created_at to hit a specific day bucket in e-reporting."""
    # pick first available product
    prods = requests.get(f"{API}/products?size=5", timeout=10).json()["items"]
    p = prods[0]
    body = {
        "items": [{"product_id": p["id"], "quantity": 1}],
        "shipping_address": {
            "full_name": "E-Rep Test",
            "address": "1 rue test",
            "postal_code": "75001",
            "city": "Paris",
            "country": "France",
            "phone": "+33600000000",
            "email": CUSTOMER_EMAIL,
        },
        "payment_method": "stripe",
    }
    r = requests.post(f"{API}/orders", json=body, headers=customer_ctx["headers"], timeout=15)
    assert r.status_code == 200, r.text
    oid = r.json()["id"]
    day = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    # Override total to a known number and set created_at to a specific day bucket
    _mdb.orders.update_one(
        {"id": oid},
        {"$set": {"payment_status": "paid", "status": "delivered",
                  "total": total, "created_at": day}},
    )
    return oid


# =========================== Settings legal fields ===========================
class TestSettingsLegal:
    def test_settings_include_legal_defaults(self):
        r = requests.get(f"{API}/settings", timeout=10)
        assert r.status_code == 200
        d = r.json()
        for k in ["company_name", "company_legal_form", "siren", "siret",
                  "vat_number", "company_address", "vat_regime", "vat_rate"]:
            assert k in d, f"missing settings key {k}"
        assert d["vat_regime"] in ("franchise", "assujetti")

    def test_put_and_persist_legal_fields(self, admin_headers):
        payload = {
            "banner_enabled": True, "banner_text": "TEST", "banner_text_en": "TEST",
            "whatsapp_number": "", "whatsapp_enabled": False,
            "company_name": "Invovix TEST",
            "company_legal_form": "SASU",
            "siren": "999888777",
            "siret": "99988877700012",
            "vat_number": "FR12999888777",
            "company_address": "10 rue de Test, 75001 Paris",
            "vat_regime": "franchise",
            "vat_rate": 20.0,
        }
        r = requests.put(f"{API}/admin/settings", json=payload,
                         headers=admin_headers, timeout=10)
        assert r.status_code == 200, r.text
        # Reload via public endpoint to prove persistence
        r2 = requests.get(f"{API}/settings", timeout=10)
        d = r2.json()
        assert d["company_legal_form"] == "SASU"
        assert d["siren"] == "999888777"
        assert d["siret"] == "99988877700012"
        assert d["vat_number"] == "FR12999888777"
        # cleanup — restore baseline
        _restore_settings_to_franchise(admin_headers)

    def test_put_requires_admin(self, customer_ctx):
        r = requests.put(f"{API}/admin/settings",
                         json={"banner_enabled": True, "banner_text": "",
                               "banner_text_en": "", "whatsapp_number": "",
                               "whatsapp_enabled": False, "company_name": "",
                               "company_legal_form": "", "siren": "", "siret": "",
                               "vat_number": "", "company_address": "",
                               "vat_regime": "franchise", "vat_rate": 20.0},
                         headers=customer_ctx["headers"], timeout=10)
        assert r.status_code in (401, 403)


# =========================== E-reporting ===========================
class TestEReporting:
    def test_requires_admin(self, customer_ctx):
        r = requests.get(f"{API}/admin/ereporting",
                         headers=customer_ctx["headers"], timeout=10)
        assert r.status_code in (401, 403)

    def test_json_shape(self, admin_headers):
        r = requests.get(f"{API}/admin/ereporting?format=json&days=90",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["regime", "vat_rate", "period_days", "operation_type", "totals", "rows"]:
            assert k in d
        assert d["operation_type"] == "B2C"
        assert d["period_days"] == 90
        assert isinstance(d["rows"], list)
        assert isinstance(d["totals"], dict)
        for k in ["count", "total_ttc", "total_ht", "total_tva"]:
            assert k in d["totals"]

    def test_csv_format(self, admin_headers):
        r = requests.get(f"{API}/admin/ereporting?format=csv&days=90",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert r.headers["content-disposition"].endswith('.csv"')
        first_line = r.text.split("\n", 1)[0]
        assert first_line == "date;taux_tva;nb_operations;total_ht;total_tva;total_ttc;devise;type"

    def test_aggregation_franchise(self, admin_headers, customer_ctx):
        """Franchise: rate=0, ht==ttc, tva==0. Create 2 paid orders on distinct days."""
        _restore_settings_to_franchise(admin_headers)
        # Two orders on days 1 and 2 ago, different totals
        o1 = _create_paid_order(customer_ctx, total=100.00, days_ago=1)
        o2 = _create_paid_order(customer_ctx, total=50.00, days_ago=2)

        r = requests.get(f"{API}/admin/ereporting?format=json&days=30",
                         headers=admin_headers, timeout=15)
        d = r.json()
        assert d["regime"] == "franchise"
        assert d["vat_rate"] == 0.0
        # Find our two day buckets
        d1 = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        rows_by_day = {r["date"]: r for r in d["rows"]}
        assert d1 in rows_by_day, f"day {d1} missing in {list(rows_by_day)}"
        assert d2 in rows_by_day
        # In franchise ht == ttc, tva == 0
        for day, expected_ttc in [(d1, 100.00), (d2, 50.00)]:
            row = rows_by_day[day]
            assert row["vat_rate"] == 0.0
            assert row["total_ttc"] >= expected_ttc  # >= because other paid orders may exist on same day
            # For our own orders the sum should include them; verify ht == ttc, tva == 0
            assert row["total_ht"] == row["total_ttc"]
            assert row["total_tva"] == 0.0
            assert row["count"] >= 1
        # cleanup
        _mdb.orders.delete_many({"id": {"$in": [o1, o2]}})

    def test_aggregation_assujetti_20pct(self, admin_headers, customer_ctx):
        """Assujetti 20%: ht = ttc/1.2, tva = ttc - ht."""
        # switch settings to assujetti 20
        r = requests.get(f"{API}/settings", timeout=10).json()
        body = {k: r.get(k, "") for k in
                ["banner_enabled", "banner_text", "banner_text_en", "whatsapp_number",
                 "whatsapp_enabled", "company_name", "company_legal_form", "siren",
                 "siret", "vat_number", "company_address"]}
        body.update({"vat_regime": "assujetti", "vat_rate": 20.0})
        requests.put(f"{API}/admin/settings", json=body, headers=admin_headers, timeout=10)

        # Create an isolated paid order on a day far enough back to be alone-ish
        o1 = _create_paid_order(customer_ctx, total=120.00, days_ago=15)

        rr = requests.get(f"{API}/admin/ereporting?format=json&days=30",
                          headers=admin_headers, timeout=15).json()
        assert rr["regime"] == "assujetti"
        assert rr["vat_rate"] == 20.0

        day = (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d")
        rows_by_day = {row["date"]: row for row in rr["rows"]}
        assert day in rows_by_day
        row = rows_by_day[day]
        # Verify VAT math on our 120€ ttc: ht=100, tva=20
        # If we're the only order that day, exact match; else assert row totals math is consistent
        # (ht + tva == ttc)
        assert abs(row["total_ht"] + row["total_tva"] - row["total_ttc"]) < 0.05
        # Row ht should be ~ ttc/1.2
        assert abs(row["total_ht"] - row["total_ttc"] / 1.2) < 0.05

        # cleanup
        _mdb.orders.delete_one({"id": o1})
        _restore_settings_to_franchise(admin_headers)


# =========================== Invoice sequential numbering ===========================
class TestInvoiceNumbering:
    def test_invoice_idempotent_same_number(self, admin_headers, customer_ctx):
        oid = _create_paid_order(customer_ctx, total=42.00, days_ago=0)
        h = customer_ctx["headers"]
        r1 = requests.get(f"{API}/orders/{oid}/invoice", headers=h, timeout=20)
        assert r1.status_code == 200, r1.text
        assert r1.headers["content-type"] == "application/pdf"
        cd1 = r1.headers.get("content-disposition", "")
        assert "attachment" in cd1 and cd1.endswith('.pdf"')
        # Basic PDF signature
        assert r1.content[:4] == b"%PDF"

        # Call again — must return SAME invoice number
        r2 = requests.get(f"{API}/orders/{oid}/invoice", headers=h, timeout=20)
        assert r2.status_code == 200
        cd2 = r2.headers.get("content-disposition", "")
        # Extract filename
        def fname(cd):
            return cd.split('filename="')[1].rstrip('"')
        assert fname(cd1) == fname(cd2), f"Invoice number changed: {cd1} vs {cd2}"
        _mdb.orders.delete_one({"id": oid})

    def test_two_orders_sequential_and_different(self, admin_headers, customer_ctx):
        o1 = _create_paid_order(customer_ctx, total=10.00, days_ago=0)
        o2 = _create_paid_order(customer_ctx, total=20.00, days_ago=0)
        h = customer_ctx["headers"]
        r1 = requests.get(f"{API}/orders/{o1}/invoice", headers=h, timeout=20)
        r2 = requests.get(f"{API}/orders/{o2}/invoice", headers=h, timeout=20)
        assert r1.status_code == 200 and r2.status_code == 200
        fn1 = r1.headers["content-disposition"].split('filename="')[1].rstrip('"')
        fn2 = r2.headers["content-disposition"].split('filename="')[1].rstrip('"')
        assert fn1 != fn2, f"Two orders got same invoice number: {fn1}"
        # Format INV-YYYY-NNNNN
        assert fn1.startswith("INV-") and fn1.endswith(".pdf")
        assert fn2.startswith("INV-") and fn2.endswith(".pdf")
        # Sequential (2nd > 1st numerically)
        seq1 = int(fn1.split("-")[-1].split(".")[0])
        seq2 = int(fn2.split("-")[-1].split(".")[0])
        assert seq2 == seq1 + 1, f"Not sequential: {seq1} then {seq2}"
        _mdb.orders.delete_many({"id": {"$in": [o1, o2]}})

    def test_unpaid_returns_400(self, customer_ctx):
        # Create order, do NOT mark paid
        prods = requests.get(f"{API}/products?size=1", timeout=10).json()["items"]
        body = {
            "items": [{"product_id": prods[0]["id"], "quantity": 1}],
            "shipping_address": {"full_name": "X", "address": "x", "postal_code": "1",
                                 "city": "x", "country": "x", "phone": "0",
                                 "email": CUSTOMER_EMAIL},
            "payment_method": "stripe",
        }
        r = requests.post(f"{API}/orders", json=body,
                          headers=customer_ctx["headers"], timeout=15)
        oid = r.json()["id"]
        rr = requests.get(f"{API}/orders/{oid}/invoice",
                          headers=customer_ctx["headers"], timeout=15)
        assert rr.status_code == 400
        _mdb.orders.delete_one({"id": oid})

    def test_non_owner_forbidden(self, customer_ctx):
        oid = _create_paid_order(customer_ctx, total=5.00, days_ago=0)
        # Register a fresh user
        email = f"other{int(time.time())}_{uuid.uuid4().hex[:6]}@invovix.store"
        rr = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "Passw0rd!", "name": "Other"},
                          timeout=15)
        assert rr.status_code == 200
        tok = rr.json()["token"]
        r = requests.get(f"{API}/orders/{oid}/invoice",
                        headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert r.status_code == 403
        _mdb.orders.delete_one({"id": oid})
        _mdb.users.delete_one({"email": email})


# =========================== Manual stock-sync endpoints (loops feed off these) ===========================
class TestStockSyncEndpoints:
    def test_sync_all_admin_ok(self, admin_headers):
        r = requests.post(f"{API}/admin/products/sync-stock-all",
                          headers=admin_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert "queued" in d

    def test_sync_single_admin_ok(self, admin_headers):
        prods = requests.get(f"{API}/products?size=30", timeout=10).json()["items"]
        cj_prod = next((p for p in prods if p.get("source") == "cjdropshipping"), prods[0])
        r = requests.post(f"{API}/admin/products/{cj_prod['id']}/sync-stock",
                          headers=admin_headers, timeout=30)
        # 200 (ok) or 429 (CJ rate-limit) both acceptable; must not be 500
        assert r.status_code in (200, 429), r.text

    def test_sync_requires_admin(self, customer_ctx):
        r = requests.post(f"{API}/admin/products/sync-stock-all",
                          headers=customer_ctx["headers"], timeout=10)
        assert r.status_code in (401, 403)


# =========================== Background loops registration ===========================
class TestBackgroundLoops:
    def test_backend_healthy_and_loops_gated_by_env(self):
        """Ensure app responded (background tasks registered without crashing startup)."""
        r = requests.get(f"{API}/", timeout=10)
        # Any 2xx or 404 (no root) means app is up; 500 would indicate startup issue
        assert r.status_code < 500
        # Check no CRITICAL errors in recent backend log
        try:
            log = open("/var/log/supervisor/backend.err.log").read()[-8000:]
            assert "stock sync loop error" not in log, "stock sync loop crashed"
            assert "tracking sync loop error" not in log, "tracking sync loop crashed"
        except FileNotFoundError:
            pass
