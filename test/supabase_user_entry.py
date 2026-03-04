#!/usr/bin/env python3
"""
Local integration test for the Supabase-backed Flask API.

Requires a valid .env at the repo root with:
  SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET

Run from repo root:
  python test/supabase_user_entry.py
"""

import sys
import os
import uuid
import time

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import jwt as pyjwt

# ── helpers ────────────────────────────────────────────────────────────────────

JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")
_created_item_ids: list[int] = []
_pass = 0
_fail = 0


def create_test_user() -> str:
    """Create a throw-away user in auth.users via the admin API. Returns their UUID."""
    from supabase_client import get_supabase
    sb = get_supabase()
    email = f"test-{uuid.uuid4().hex[:8]}@arcera-test.invalid"
    res = sb.auth.admin.create_user({"email": email, "email_confirm": True})
    return str(res.user.id)


def delete_test_user(member_id: str):
    """Remove the throw-away user (cascades to item rows via FK)."""
    from supabase_client import get_supabase
    get_supabase().auth.admin.delete_user(member_id)


def make_jwt(member_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": member_id,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def auth_headers(member_id: str) -> dict:
    return {"Authorization": f"Bearer {make_jwt(member_id)}"}


def check(label: str, condition: bool, detail: str = ""):
    global _pass, _fail
    status = "PASS" if condition else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    if condition:
        _pass += 1
    else:
        _fail += 1


# ── scenarios ──────────────────────────────────────────────────────────────────

def scenario_health(client):
    print("\n[1] Supabase connectivity")
    r = client.get("/supabase/health")
    data = r.get_json()
    check("HTTP 200", r.status_code == 200, str(r.status_code))
    check("status ok", data.get("status") == "ok", str(data))


def scenario_auth(client, member_id: str):
    print("\n[2] JWT auth — /member")
    r = client.get("/member", headers=auth_headers(member_id))
    data = r.get_json()
    check("HTTP 200", r.status_code == 200, str(r.status_code))
    check("member_id matches", data.get("member_id") == member_id)

    # bad token should be rejected
    r_bad = client.get("/member", headers={"Authorization": "Bearer bad.token.here"})
    check("bad token → 401", r_bad.status_code == 401)


def scenario_store_items(client, member_id: str):
    print("\n[3] Store items — /store")
    payload = {
        "path": os.path.join(os.path.dirname(__file__), '..', 'test_images', 'furniture_1.jpeg'),
        "items": [
            {"class_id": 56, "purchase_year": 2021, "cost": 349.99, "room_id": 1,
             "bbox": [10, 20, 200, 300]},   # chair, living room
            {"class_id": 59, "purchase_year": 2019, "cost": 1200.00, "room_id": 2,
             "bbox": [50, 60, 400, 500]},   # bed, bedroom
        ],
    }
    r = client.post("/store", json=payload, headers=auth_headers(member_id))
    data = r.get_json()
    check("HTTP 200", r.status_code == 200, str(r.status_code))
    check("stored message present", "Stored" in data.get("message", ""), str(data))


def scenario_list_items(client, member_id: str):
    print("\n[4] List items — /items")
    r = client.get("/items", headers=auth_headers(member_id))
    data = r.get_json()
    check("HTTP 200", r.status_code == 200)
    items = data.get("items", [])
    check("at least 2 items", len(items) >= 2, f"got {len(items)}")

    # collect IDs for later cleanup
    for item in items:
        item_id = item.get("id")
        if item_id and item_id not in _created_item_ids:
            _created_item_ids.append(item_id)

    # spot-check first item shape
    if items:
        first = items[0]
        check("has label", "label" in first)
        check("has room", "room" in first)
        check("has cost", "cost" in first)


def scenario_update_item(client, member_id: str):
    print("\n[5] Update item — PUT /items/<id>")
    if not _created_item_ids:
        print("  SKIP — no items to update")
        return
    item_id = _created_item_ids[0]
    r = client.put(
        f"/items/{item_id}",
        json={"name": "Test Chair", "cost": 299.99, "count": 2},
        headers=auth_headers(member_id),
    )
    check("HTTP 200", r.status_code == 200, str(r.status_code))

    # verify update
    r2 = client.get("/items", headers=auth_headers(member_id))
    updated = next((i for i in r2.get_json().get("items", []) if i["id"] == item_id), None)
    check("name updated", updated and updated.get("label") == "Test Chair",
          str(updated.get("label") if updated else None))
    check("cost updated", updated and updated.get("cost") == 299.99)
    check("count updated", updated and updated.get("count") == 2)


def scenario_delete_items(client, member_id: str):
    print("\n[6] Delete items — DELETE /items/<id>")
    for item_id in list(_created_item_ids):
        r = client.delete(f"/items/{item_id}", headers=auth_headers(member_id))
        check(f"deleted item {item_id}", r.status_code == 200, str(r.status_code))

    # confirm items are gone
    r = client.get("/items", headers=auth_headers(member_id))
    remaining = [i for i in r.get_json().get("items", []) if i["id"] in _created_item_ids]
    check("all test items removed", len(remaining) == 0, f"{len(remaining)} remaining")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    if not JWT_SECRET:
        print("ERROR: SUPABASE_JWT_SECRET not set. Check your .env file.")
        sys.exit(1)

    # import app after env is loaded
    from app import app
    app.config["TESTING"] = True
    client = app.test_client()

    print("\nCreating test user in auth.users...")
    member_id = create_test_user()
    print(f"Test member: {member_id}")

    try:
        scenario_health(client)
        scenario_auth(client, member_id)
        scenario_store_items(client, member_id)
        scenario_list_items(client, member_id)
        scenario_update_item(client, member_id)
        scenario_delete_items(client, member_id)
    finally:
        print("\nCleaning up test user...")
        delete_test_user(member_id)
        print("Done.")

    print(f"\n{'='*40}")
    print(f"Results: {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)


if __name__ == "__main__":
    main()
