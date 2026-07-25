"""Tests for blog + contact endpoints added in latest change."""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://drop-partner.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@invovix.store"
ADMIN_PASSWORD = "Invovix2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Public blog ----------

def test_public_blog_list_has_seeded_posts():
    r = requests.get(f"{API}/blog", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 3, f"Expected at least 3 seeded posts, got {len(data['items'])}"
    p = data["items"][0]
    for key in ("slug", "title", "excerpt", "cover_image"):
        assert key in p


def test_public_blog_get_by_slug():
    lst = requests.get(f"{API}/blog", timeout=15).json()["items"]
    assert lst
    slug = lst[0]["slug"]
    r = requests.get(f"{API}/blog/{slug}", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == slug
    assert "content" in data
    assert isinstance(data["content"], str)


def test_public_blog_get_404():
    r = requests.get(f"{API}/blog/this-does-not-exist-xyz", timeout=15)
    assert r.status_code == 404


# ---------- Contact ----------

CONTACT_MSG_SUBJECT = f"TEST_subject_{int(time.time())}"


def test_post_contact_public():
    payload = {
        "name": "TEST_User",
        "email": "test_contact@example.com",
        "subject": CONTACT_MSG_SUBJECT,
        "message": "TEST_message_body_content",
    }
    r = requests.post(f"{API}/contact", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_admin_contacts_list_contains_submitted(admin_headers):
    # small wait to make sure background insert finished (it's actually sync insert)
    r = requests.get(f"{API}/admin/contacts", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(m.get("subject") == CONTACT_MSG_SUBJECT for m in items), \
        f"submitted contact not found among {len(items)} messages"


def test_admin_contacts_requires_auth():
    r = requests.get(f"{API}/admin/contacts", timeout=15)
    assert r.status_code in (401, 403)


# ---------- Admin blog CRUD + upload ----------

created_post_id = {"id": None, "slug": None}


def test_admin_upload_image(admin_headers):
    # 1x1 png
    png = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
    )
    files = {"file": ("test.png", io.BytesIO(png), "image/png")}
    r = requests.post(f"{API}/admin/upload", headers=admin_headers, files=files, timeout=20)
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/blog/")
    # verify accessible same-origin
    full = f"{BASE_URL}{url}"
    r2 = requests.get(full, timeout=15)
    assert r2.status_code == 200, f"Uploaded image not accessible at {full}: {r2.status_code}"


def test_admin_upload_requires_auth():
    files = {"file": ("test.png", io.BytesIO(b"xx"), "image/png")}
    r = requests.post(f"{API}/admin/upload", files=files, timeout=15)
    assert r.status_code in (401, 403)


def test_admin_create_blog(admin_headers):
    payload = {
        "title": f"TEST_Post_{int(time.time())}",
        "excerpt": "TEST excerpt",
        "content": "<p>TEST content <strong>rich</strong></p>",
        "cover_image": "/blog/does-not-matter.png",
        "tags": ["test", "e2e"],
        "published": True,
    }
    r = requests.post(f"{API}/admin/blog", json=payload, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == payload["title"]
    assert data["slug"]
    assert data["tags"] == payload["tags"]
    assert data["published"] is True
    assert "_id" not in data
    created_post_id["id"] = data["id"]
    created_post_id["slug"] = data["slug"]


def test_public_can_see_created_post():
    slug = created_post_id["slug"]
    assert slug
    r = requests.get(f"{API}/blog/{slug}", timeout=15)
    assert r.status_code == 200
    assert r.json()["slug"] == slug


def test_admin_update_blog(admin_headers):
    pid = created_post_id["id"]
    assert pid
    payload = {
        "title": f"TEST_Post_updated_{int(time.time())}",
        "excerpt": "updated excerpt",
        "content": "<p>updated</p>",
        "cover_image": "/blog/x.png",
        "tags": ["updated"],
        "published": True,
    }
    r = requests.put(f"{API}/admin/blog/{pid}", json=payload, headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["excerpt"] == "updated excerpt"
    assert data["tags"] == ["updated"]


def test_admin_delete_blog(admin_headers):
    pid = created_post_id["id"]
    assert pid
    r = requests.delete(f"{API}/admin/blog/{pid}", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    # confirm gone from public (slug may change on update but slug in dict is stale; use admin list)
    r2 = requests.get(f"{API}/admin/blog", headers={"Authorization": admin_headers["Authorization"]}, timeout=15)
    assert r2.status_code == 200
    ids = [x["id"] for x in r2.json()["items"]]
    assert pid not in ids


def test_admin_blog_requires_auth():
    r = requests.get(f"{API}/admin/blog", timeout=15)
    assert r.status_code in (401, 403)


# ---------- Regression: shop/products still works ----------

def test_products_list_still_works():
    r = requests.get(f"{API}/products", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
