"""Phase 4A Security tests: RBAC enforcement, Staff CRUD, Login Journal, 2FA (TOTP).

Uses REACT_APP_BACKEND_URL from /app/frontend/.env for external calls.
Creates a throwaway staff account for 2FA testing and cleans up after.
"""
import os
import pathlib
import time
import uuid
import pytest
import pyotp
import requests


def _load_backend_url() -> str:
    env_path = pathlib.Path("/app/frontend/.env")
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL missing")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PWD = "Invovix2026!"
MARKETING_EMAIL = "marketing@invovix.store"
MARKETING_PWD = "Marketing2026!"
CUSTOMER_EMAIL = "client@invovix.store"
CUSTOMER_PWD = "Client2026!"


def _login(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=15)
    return r


def _token(email, pwd):
    r = _login(email, pwd)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    body = r.json()
    assert "token" in body, f"expected direct token for {email}, got {body}"
    return body["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# -------------------------- Fixtures --------------------------
@pytest.fixture(scope="module")
def admin_token():
    return _token(ADMIN_EMAIL, ADMIN_PWD)


@pytest.fixture(scope="module")
def marketing_token():
    return _token(MARKETING_EMAIL, MARKETING_PWD)


@pytest.fixture(scope="module")
def customer_token():
    return _token(CUSTOMER_EMAIL, CUSTOMER_PWD)


# -------------------------- Permissions endpoint --------------------------
class TestPermissions:
    def test_marketing_permissions(self, marketing_token):
        r = requests.get(f"{API}/auth/permissions", headers=_auth(marketing_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "marketing"
        assert d["is_staff"] is True
        assert d["is_admin"] is False
        perms = set(d["permissions"])
        for expected in ["analytics", "marketing", "content", "ai", "catalog"]:
            assert expected in perms, f"missing {expected} in {perms}"

    def test_admin_permissions_all(self, admin_token):
        r = requests.get(f"{API}/auth/permissions", headers=_auth(admin_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "admin"
        assert d["is_admin"] is True
        assert d["permissions"] == "all"

    def test_customer_permissions_empty(self, customer_token):
        r = requests.get(f"{API}/auth/permissions", headers=_auth(customer_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "customer"
        assert d["is_staff"] is False
        assert list(d["permissions"]) == []


# -------------------------- RBAC access --------------------------
class TestRBACMarketing:
    def test_marketing_can_access_analytics(self, marketing_token):
        r = requests.get(f"{API}/admin/analytics", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_marketing_can_access_campaigns(self, marketing_token):
        r = requests.get(f"{API}/admin/campaigns", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_marketing_can_access_customers(self, marketing_token):
        r = requests.get(f"{API}/admin/customers", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 200, r.text

    def test_marketing_cannot_access_orders(self, marketing_token):
        r = requests.get(f"{API}/admin/orders", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 403, r.text

    def test_marketing_cannot_access_staff(self, marketing_token):
        r = requests.get(f"{API}/admin/staff", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 403, r.text

    def test_marketing_cannot_put_settings(self, marketing_token):
        r = requests.put(f"{API}/admin/settings",
                         headers=_auth(marketing_token),
                         json={}, timeout=15)
        assert r.status_code == 403, r.text

    def test_marketing_cannot_access_login_journal(self, marketing_token):
        r = requests.get(f"{API}/admin/login-journal", headers=_auth(marketing_token), timeout=15)
        assert r.status_code == 403


class TestRBACAdmin:
    def test_admin_can_access_orders(self, admin_token):
        r = requests.get(f"{API}/admin/orders", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200

    def test_admin_can_access_staff(self, admin_token):
        r = requests.get(f"{API}/admin/staff", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "role_permissions" in data

    def test_admin_can_access_login_journal(self, admin_token):
        r = requests.get(f"{API}/admin/login-journal", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "failed_24h" in data


class TestRBACCustomer:
    def test_customer_blocked_from_admin_endpoints(self, customer_token):
        for ep in ["/admin/analytics", "/admin/orders", "/admin/staff",
                   "/admin/campaigns", "/admin/customers", "/admin/login-journal"]:
            r = requests.get(f"{API}{ep}", headers=_auth(customer_token), timeout=15)
            assert r.status_code == 403, f"{ep} expected 403, got {r.status_code}"

    def test_customer_login_returns_normal_token(self):
        r = _login(CUSTOMER_EMAIL, CUSTOMER_PWD)
        assert r.status_code == 200
        b = r.json()
        assert "token" in b and "user" in b
        assert b["user"]["role"] == "customer"
        assert "twofa_required" not in b


# -------------------------- Staff CRUD --------------------------
class TestStaffCRUD:
    _created_ids = []

    def test_create_staff_invalid_role(self, admin_token):
        r = requests.post(f"{API}/admin/staff",
                          headers=_auth(admin_token),
                          json={"email": f"TEST_bad_{uuid.uuid4().hex[:6]}@invovix.test",
                                "name": "Bad", "password": "Test2026!", "role": "godmode"},
                          timeout=15)
        assert r.status_code == 400

    def test_create_staff_ok_then_duplicate(self, admin_token):
        email = f"test_staff_{uuid.uuid4().hex[:8]}@invovix.test"
        r = requests.post(f"{API}/admin/staff",
                          headers=_auth(admin_token),
                          json={"email": email, "name": "Test Support",
                                "password": "Test2026!", "role": "support"},
                          timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == email
        assert data["role"] == "support"
        assert "id" in data
        TestStaffCRUD._created_ids.append(data["id"])

        # duplicate
        r2 = requests.post(f"{API}/admin/staff", headers=_auth(admin_token),
                          json={"email": email, "name": "Dup",
                                "password": "Test2026!", "role": "support"}, timeout=15)
        assert r2.status_code == 400

    def test_list_shows_created(self, admin_token):
        r = requests.get(f"{API}/admin/staff", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()["items"]]
        for cid in TestStaffCRUD._created_ids:
            assert cid in ids

    def test_change_role(self, admin_token):
        if not TestStaffCRUD._created_ids:
            pytest.skip("no created")
        sid = TestStaffCRUD._created_ids[0]
        r = requests.put(f"{API}/admin/staff/{sid}/role",
                         headers=_auth(admin_token), json={"role": "accounting"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "accounting"

    def test_cannot_change_own_role(self, admin_token):
        # find admin id
        me = requests.get(f"{API}/auth/me", headers=_auth(admin_token), timeout=10).json()
        admin_id = me["user"]["id"]
        r = requests.put(f"{API}/admin/staff/{admin_id}/role",
                         headers=_auth(admin_token), json={"role": "manager"}, timeout=10)
        assert r.status_code == 400

    def test_delete_nonexistent(self, admin_token):
        r = requests.delete(f"{API}/admin/staff/nope-{uuid.uuid4().hex}",
                            headers=_auth(admin_token), timeout=10)
        assert r.status_code == 404

    def test_delete_created(self, admin_token):
        for sid in list(TestStaffCRUD._created_ids):
            r = requests.delete(f"{API}/admin/staff/{sid}",
                                headers=_auth(admin_token), timeout=10)
            assert r.status_code == 200
        TestStaffCRUD._created_ids.clear()


# -------------------------- Login Journal --------------------------
class TestLoginJournal:
    def test_journal_records_failed_and_success(self, admin_token):
        # Failed login (wrong password)
        bad_email = "marketing@invovix.store"
        requests.post(f"{API}/auth/login",
                      json={"email": bad_email, "password": "WRONG_PWD_1234"}, timeout=10)
        # Successful login
        requests.post(f"{API}/auth/login",
                      json={"email": bad_email, "password": MARKETING_PWD}, timeout=10)
        # small pause to allow write
        time.sleep(0.5)
        r = requests.get(f"{API}/admin/login-journal?limit=50",
                         headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        # find at least one failed and one success for that email recently
        recent_for_email = [i for i in items if i.get("email") == bad_email][:20]
        assert any(i.get("success") is False for i in recent_for_email), "no failed event recorded"
        assert any(i.get("success") is True for i in recent_for_email), "no success event recorded"
        # each item has required fields
        sample = recent_for_email[0]
        for k in ["email", "success", "ip", "role", "created_at"]:
            assert k in sample, f"missing {k} in journal item {sample}"


# -------------------------- 2FA full flow --------------------------
class TestTwoFAFlow:
    """Create throwaway support staff, enable 2FA, login, disable, cleanup."""

    def test_full_2fa_flow(self, admin_token):
        email = f"test_2fa_{uuid.uuid4().hex[:8]}@example.com"
        password = "Test2FA2026!"
        # Create staff
        r = requests.post(f"{API}/admin/staff", headers=_auth(admin_token),
                          json={"email": email, "name": "2FA Test", "password": password,
                                "role": "support"}, timeout=15)
        assert r.status_code == 200, r.text
        staff_id = r.json()["id"]

        try:
            # Login and get token
            tok = _token(email, password)

            # 2FA setup
            r = requests.post(f"{API}/auth/2fa/setup", headers=_auth(tok), timeout=15)
            assert r.status_code == 200, r.text
            setup = r.json()
            assert "secret" in setup and "otpauth_uri" in setup
            assert setup["qr"].startswith("data:image/png;base64,")
            secret = setup["secret"]

            # wrong code -> 400
            r = requests.post(f"{API}/auth/2fa/enable", headers=_auth(tok),
                              json={"code": "000000"}, timeout=10)
            assert r.status_code == 400

            # correct code
            code = pyotp.TOTP(secret).now()
            r = requests.post(f"{API}/auth/2fa/enable", headers=_auth(tok),
                              json={"code": code}, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["twofa_enabled"] is True

            # Login now returns twofa_required + temp_token
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": password}, timeout=15)
            assert r.status_code == 200
            b = r.json()
            assert b.get("twofa_required") is True
            assert "temp_token" in b
            assert "token" not in b

            # 2FA login with wrong code -> 400
            r = requests.post(f"{API}/auth/2fa/login",
                              json={"temp_token": b["temp_token"], "code": "000000"}, timeout=10)
            assert r.status_code == 400

            # 2FA login with correct code
            # small wait to avoid reusing same window; but valid_window=1 tolerates
            code2 = pyotp.TOTP(secret).now()
            r = requests.post(f"{API}/auth/2fa/login",
                              json={"temp_token": b["temp_token"], "code": code2}, timeout=10)
            assert r.status_code == 200, r.text
            full = r.json()
            assert "token" in full and "user" in full
            new_tok = full["token"]

            # Disable 2FA
            code3 = pyotp.TOTP(secret).now()
            r = requests.post(f"{API}/auth/2fa/disable", headers=_auth(new_tok),
                              json={"code": code3}, timeout=10)
            assert r.status_code == 200
            assert r.json()["twofa_enabled"] is False

            # Login now returns full token (no 2FA gate)
            r = _login(email, password)
            assert r.status_code == 200
            assert "token" in r.json()
            assert "twofa_required" not in r.json()

        finally:
            # Cleanup
            requests.delete(f"{API}/admin/staff/{staff_id}",
                            headers=_auth(admin_token), timeout=10)
