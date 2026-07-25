"""Tests for the new features batch: settings, related, featured reviews,
wishlist, promo codes, sitemap."""
import os
import time
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0]
           ).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"
CUSTOMER_EMAIL = "client@invovix.store"
CUSTOMER_PASSWORD = "Client2026!"


# --------------- fixtures ---------------
@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def customer_headers():
    # try login, if it fails, register
    r = requests.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD}, timeout=15)
    if r.status_code != 200:
        r = requests.post(
            f"{API}/auth/register",
            json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD, "name": "Test Client"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def sample_product():
    r = requests.get(f"{API}/products?size=5", timeout=15)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "no products seeded"
    return items[0]


# --------------- Settings ---------------
class TestSettings:
    def test_get_settings_public(self):
        r = requests.get(f"{API}/settings", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("banner_enabled", "banner_text", "banner_text_en",
                  "whatsapp_enabled", "whatsapp_number"):
            assert k in d, f"missing key {k}"

    def test_update_settings_admin(self, admin_headers):
        payload = {
            "banner_enabled": True,
            "banner_text": "TEST banner FR",
            "banner_text_en": "TEST banner EN",
            "whatsapp_enabled": False,
            "whatsapp_number": "",
        }
        r = requests.put(f"{API}/admin/settings", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["banner_text"] == "TEST banner FR"
        # verify persisted
        r2 = requests.get(f"{API}/settings", timeout=15)
        assert r2.json()["banner_text"] == "TEST banner FR"

    def test_update_settings_requires_admin(self):
        r = requests.put(f"{API}/admin/settings", json={"banner_enabled": True, "banner_text": "x"}, timeout=15)
        assert r.status_code in (401, 403)


# --------------- Related products ---------------
class TestRelated:
    def test_related_returns_items(self, sample_product):
        pid = sample_product["id"]
        r = requests.get(f"{API}/products/{pid}/related", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert isinstance(items, list)
        # should exclude the product itself
        assert all(x["id"] != pid for x in items)

    def test_related_bad_id_returns_empty(self):
        r = requests.get(f"{API}/products/nonexistent-xyz/related", timeout=15)
        assert r.status_code == 200
        assert r.json()["items"] == []


# --------------- Featured reviews ---------------
class TestFeaturedReviews:
    def test_featured_reviews_endpoint(self):
        r = requests.get(f"{API}/reviews/featured", timeout=15)
        assert r.status_code == 200
        assert "items" in r.json()
        assert isinstance(r.json()["items"], list)


# --------------- Wishlist ---------------
class TestWishlist:
    def test_wishlist_requires_auth(self):
        r = requests.get(f"{API}/wishlist", timeout=15)
        assert r.status_code in (401, 403)

    def test_wishlist_toggle_requires_auth(self, sample_product):
        r = requests.post(f"{API}/wishlist/{sample_product['id']}", timeout=15)
        assert r.status_code in (401, 403)

    def test_wishlist_toggle_add_then_remove(self, customer_headers, sample_product):
        pid = sample_product["id"]
        # add
        r = requests.post(f"{API}/wishlist/{pid}", headers=customer_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # first toggle may add or remove depending on previous state; ensure state known
        if not data["added"]:
            # was already there; toggle again to make sure of clean start (removed now)
            r = requests.post(f"{API}/wishlist/{pid}", headers=customer_headers, timeout=15)
            data = r.json()
            assert data["added"] is True
        assert pid in data["product_ids"]

        # GET verifies persisted
        r = requests.get(f"{API}/wishlist", headers=customer_headers, timeout=15)
        assert r.status_code == 200
        assert pid in r.json()["product_ids"]

        # toggle off
        r = requests.post(f"{API}/wishlist/{pid}", headers=customer_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["added"] is False
        assert pid not in r.json()["product_ids"]


# --------------- Promo codes ---------------
class TestPromo:
    def test_validate_welcome10(self):
        r = requests.post(f"{API}/promo/validate", json={"code": "WELCOME10", "subtotal": 100}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["valid"] is True
        assert d["code"] == "WELCOME10"
        assert d["type"] == "percent"
        assert d["discount"] == 10.0

    def test_validate_invalid_code(self):
        r = requests.post(f"{API}/promo/validate", json={"code": "NOTHING_XYZ", "subtotal": 100}, timeout=15)
        assert r.status_code == 400

    def test_validate_case_insensitive(self):
        r = requests.post(f"{API}/promo/validate", json={"code": "welcome10", "subtotal": 50}, timeout=15)
        assert r.status_code == 200
        assert r.json()["discount"] == 5.0

    def test_admin_promo_crud(self, admin_headers):
        code = f"TEST{int(time.time())}"[:15]
        # create
        r = requests.post(f"{API}/admin/promos",
                          json={"code": code, "type": "fixed", "value": 5, "min_subtotal": 20, "active": True},
                          headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["code"] == code.upper()
        # list
        r2 = requests.get(f"{API}/admin/promos", headers=admin_headers, timeout=15)
        assert code.upper() in [p["code"] for p in r2.json()["items"]]
        # validate uses it
        r3 = requests.post(f"{API}/promo/validate", json={"code": code, "subtotal": 100}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["discount"] == 5.0
        # delete
        r4 = requests.delete(f"{API}/admin/promos/{code}", headers=admin_headers, timeout=15)
        assert r4.status_code == 200
        # gone
        r5 = requests.get(f"{API}/admin/promos", headers=admin_headers, timeout=15)
        assert code.upper() not in [p["code"] for p in r5.json()["items"]]

    def test_admin_promo_requires_auth(self):
        r = requests.get(f"{API}/admin/promos", timeout=15)
        assert r.status_code in (401, 403)


# --------------- Order with promo applied ---------------
class TestOrderPromo:
    def test_order_applies_promo_discount(self, customer_headers, sample_product):
        p = sample_product
        payload = {
            "items": [{"product_id": p["id"], "quantity": 2}],
            "shipping_address": {
                "full_name": "TEST Client",
                "email": "test@example.com",
                "address": "1 rue test",
                "city": "Paris",
                "postal_code": "75001",
                "country": "FR",
                "phone": "0600000000",
            },
            "promo_code": "WELCOME10",
        }
        r = requests.post(f"{API}/orders", json=payload, headers=customer_headers, timeout=15)
        assert r.status_code == 200, r.text
        o = r.json()
        subtotal_expected = round(p["price"] * 2, 2)
        assert o["subtotal"] == subtotal_expected
        assert o["promo_code"] == "WELCOME10"
        assert o["discount"] == round(subtotal_expected * 0.10, 2)
        shipping = 0.0 if subtotal_expected >= 50 else 4.90
        assert o["total"] == round(subtotal_expected + shipping - o["discount"], 2)


# --------------- Sitemap ---------------
class TestSitemap:
    def test_sitemap_includes_new_paths(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=15)
        assert r.status_code == 200
        body = r.text
        assert "/blog" in body
        assert "/faq" in body
        assert "/contact" in body
        # includes at least one blog post slug beyond just /blog
        # (seeded blog posts should be present)
        assert body.count("/blog/") >= 1
