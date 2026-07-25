"""Seed the catalog with real CJDropshipping products via the admin API.
Reuses the existing admin endpoints (search + import-bulk) so image
localization, margin calc and anti-429 pacing are all applied.
Run: python seed_cj.py
"""
import os
import sys
import time
import requests

API = os.environ.get("SEED_API", "http://localhost:8001/api")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@invovix.store")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "Invovix2026!")
MARGIN = float(os.environ.get("SEED_MARGIN", "55"))
PER_CATEGORY = int(os.environ.get("SEED_PER_CATEGORY", "8"))

CATEGORIES = {
    "smart-home": ["smart bulb", "smart plug", "led strip light", "motion sensor", "smart thermostat", "wifi socket", "smart switch", "temperature sensor"],
    "workspace": ["desk lamp", "laptop stand", "wireless charger", "desk organizer", "usb hub", "monitor stand", "cable organizer", "phone holder"],
    "security": ["security camera", "door window sensor", "smart lock", "video doorbell", "wifi camera", "alarm sensor", "cctv camera", "door alarm"],
}
SEARCH_DELAY = float(os.environ.get("SEED_SEARCH_DELAY", "3.5"))


def search_once(headers, kw):
    try:
        r = requests.get(f"{API}/admin/cj/search", params={"q": kw, "page": 1}, headers=headers, timeout=60)
        return r.json().get("items", []) if r.ok else []
    except Exception as e:
        print(f"   search '{kw}' failed: {e}")
        return []


def login():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def collect_pids(headers, keywords):
    pids = []
    seen = set()
    for kw in keywords:
        if len(pids) >= PER_CATEGORY:
            break
        items = search_once(headers, kw)
        if not items:  # likely throttled -> wait and retry once
            time.sleep(SEARCH_DELAY)
            items = search_once(headers, kw)
        for it in items:
            pid = it.get("pid") or it.get("productId")
            if pid and pid not in seen:
                seen.add(pid)
                pids.append(pid)
                if len(pids) >= PER_CATEGORY:
                    break
        print(f"   '{kw}': +{len(items)} results (total pids: {len(pids)})")
        time.sleep(SEARCH_DELAY)
    return pids


def main():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    status = requests.get(f"{API}/admin/cj/status", headers=headers, timeout=30).json()
    if not status.get("configured"):
        print("CJ API not configured. Abort.")
        sys.exit(1)

    grand = {"imported": 0, "skipped": 0, "errors": 0}
    for category, keywords in CATEGORIES.items():
        print(f"\n=== Category: {category} ===")
        pids = collect_pids(headers, keywords)
        if not pids:
            print("   no pids found, skipping")
            continue
        print(f"   importing {len(pids)} products (margin {MARGIN}%)...")
        try:
            r = requests.post(
                f"{API}/admin/cj/import-bulk",
                json={"pids": pids, "margin": MARGIN, "category": category},
                headers=headers,
                timeout=300,
            )
            data = r.json()
            print(f"   -> imported {data.get('imported')} | skipped {data.get('skipped')} | errors {data.get('errors')}")
            for k in grand:
                grand[k] += data.get(k, 0)
        except Exception as e:
            print(f"   import-bulk failed: {e}")

    print(f"\n=== DONE === imported {grand['imported']} | skipped {grand['skipped']} | errors {grand['errors']}")


if __name__ == "__main__":
    main()
