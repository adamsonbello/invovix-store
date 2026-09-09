"""LOT 1 tests: account profile/message, admin contact reply, product sync-specs."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://smart-home-shop-20.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASS = "Invovix2026!"
CJ_PRODUCT_ID = "aaacdc84-9c86-4f4e-bf07-75283ce330ca"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def customer():
    email = f"test_lot1_{uuid.uuid4().hex[:8]}@example.com"
    pw = "TestPass2026!"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "TEST Lot1 Customer"}, timeout=20)
    assert r.status_code == 200, f"register {r.status_code} {r.text}"
    token = r.json().get("token") or _login(email, pw)
    return {"email": email, "token": token}


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# --- Account profile ---
def test_get_profile_initial(customer):
    r = requests.get(f"{API}/account/profile", headers=_h(customer["token"]), timeout=15)
    assert r.status_code == 200
    data = r.json()
    for k in ("name", "email", "phone", "address", "city", "postal_code", "country"):
        assert k in data
    assert data["email"] == customer["email"]


def test_update_profile_then_get(customer):
    payload = {
        "name": "TEST Updated Name",
        "phone": "+33612345678",
        "address": "10 rue de Test",
        "city": "Paris",
        "postal_code": "75001",
        "country": "France",
    }
    r = requests.put(f"{API}/account/profile", headers=_h(customer["token"]), json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    prof = body["profile"]
    for k, v in payload.items():
        assert prof[k] == v, f"{k} not updated: {prof[k]}"
    # verify persistence
    r2 = requests.get(f"{API}/account/profile", headers=_h(customer["token"]), timeout=15)
    p2 = r2.json()
    for k, v in payload.items():
        assert p2[k] == v


# --- Account message + admin reply ---
def test_account_message_and_admin_reply(customer, admin_token):
    subject = f"TEST subject {uuid.uuid4().hex[:6]}"
    msg = "Bonjour, ceci est un message de test client."
    r = requests.post(f"{API}/account/message", headers=_h(customer["token"]),
                      json={"subject": subject, "message": msg}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    # admin lists contacts
    r2 = requests.get(f"{API}/admin/contacts", headers=_h(admin_token), timeout=15)
    assert r2.status_code == 200
    items = r2.json()["items"]
    match = [c for c in items if c.get("subject") == subject]
    assert match, "created contact not found in admin list"
    contact = match[0]
    assert contact.get("source") == "client"
    assert contact.get("email") == customer["email"]
    cid = contact["id"]

    # admin replies
    r3 = requests.post(f"{API}/admin/contacts/{cid}/reply", headers=_h(admin_token),
                       json={"message": "Réponse de test — merci pour votre message."}, timeout=30)
    assert r3.status_code == 200, r3.text
    body = r3.json()
    assert body.get("ok") is True
    assert "sent" in body and "brevo_configured" in body

    # verify reply stored
    r4 = requests.get(f"{API}/admin/contacts", headers=_h(admin_token), timeout=15)
    updated = [c for c in r4.json()["items"] if c["id"] == cid][0]
    replies = updated.get("replies") or []
    assert len(replies) >= 1
    assert "Réponse de test" in replies[-1]["message"]


# --- Sync specs on CJ product ---
def test_sync_specs_cj_product(admin_token):
    r = requests.post(f"{API}/admin/products/{CJ_PRODUCT_ID}/sync-specs",
                      headers=_h(admin_token), timeout=60)
    if r.status_code == 404:
        pytest.skip("CJ product id not present in DB")
    if r.status_code in (502, 503):
        pytest.skip(f"CJ API unavailable: {r.status_code} {r.text}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    specs = body.get("specs") or {}
    assert isinstance(specs, dict)
    # get product & check specs stored
    r2 = requests.get(f"{API}/products/{CJ_PRODUCT_ID}", timeout=15)
    assert r2.status_code == 200
    prod = r2.json()
    assert "specs" in prod
    assert isinstance(prod["specs"], dict)


def test_account_message_requires_auth():
    r = requests.post(f"{API}/account/message", json={"subject": "x", "message": "y"}, timeout=10)
    assert r.status_code in (401, 403)


def test_profile_requires_auth():
    r = requests.get(f"{API}/account/profile", timeout=10)
    assert r.status_code in (401, 403)
