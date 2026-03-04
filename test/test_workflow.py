#!/usr/bin/env python3
"""
End-to-end workflow diagnostic test.

Steps tested:
  1. Supabase connectivity
  2. Create test user (auth.users)
  3. Upload image  → /upload
  4. YOLO detect   → /detect
  5. Store items   → /store  (requires JWT)
  6. DB verify     → /items  (items present in Supabase)
  7. Local crops   → check crop files created on disk
  8. Supabase Storage → check user folder in storage bucket (not yet implemented)

Run from repo root:
  python test/test_workflow.py
"""

import sys
import os
import time
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import jwt as pyjwt

REPO_ROOT   = os.path.join(os.path.dirname(__file__), '..')
TEST_IMAGE  = os.path.join(REPO_ROOT, 'test_images', 'furniture_1.jpeg')
JWT_SECRET  = os.environ.get("SUPABASE_JWT_SECRET")

_pass = _fail = _skip = 0
_member_id = None
_item_ids: list[int] = []


# ── reporting ─────────────────────────────────────────────────────────────────

def ok(label: str, detail: str = ""):
    global _pass
    _pass += 1
    print(f"  [OK]   {label}" + (f"  ({detail})" if detail else ""))

def fail(label: str, detail: str = ""):
    global _fail
    _fail += 1
    print(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))

def skip(label: str, reason: str = ""):
    global _skip
    _skip += 1
    print(f"  [SKIP] {label}" + (f"  — {reason}" if reason else ""))

def section(title: str):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


# ── auth helpers ──────────────────────────────────────────────────────────────

def make_jwt(member_id: str) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {"sub": member_id, "aud": "authenticated", "role": "authenticated",
         "iat": now, "exp": now + 3600},
        JWT_SECRET, algorithm="HS256",
    )

def auth_headers(member_id: str) -> dict:
    return {"Authorization": f"Bearer {make_jwt(member_id)}"}


# ── step 1: Supabase connectivity ─────────────────────────────────────────────

def step_health(client):
    section("Step 1 — Supabase connectivity")
    try:
        r = client.get("/supabase/health")
        data = r.get_json()
        if r.status_code == 200 and data.get("status") == "ok":
            ok("Supabase client connected")
        else:
            fail("Supabase health check", f"status={r.status_code} body={data}")
    except Exception as e:
        fail("Supabase health check raised", str(e))


# ── step 2: create test user ──────────────────────────────────────────────────

def step_create_user() -> str | None:
    section("Step 2 — Create test user in auth.users")
    try:
        import uuid
        from supabase_client import get_supabase
        email = f"test-{uuid.uuid4().hex[:8]}@arcera-test.invalid"
        res = get_supabase().auth.admin.create_user(
            {"email": email, "email_confirm": True}
        )
        member_id = str(res.user.id)
        ok("Test user created", member_id)
        return member_id
    except Exception as e:
        fail("Create test user", str(e))
        return None


# ── step 3: upload image ──────────────────────────────────────────────────────

def step_upload(client) -> str | None:
    section("Step 3 — Upload image  →  POST /upload")
    try:
        if not os.path.isfile(TEST_IMAGE):
            skip("Upload", f"test image not found: {TEST_IMAGE}")
            return None
        with open(TEST_IMAGE, "rb") as f:
            data = {"image": (io.BytesIO(f.read()), os.path.basename(TEST_IMAGE))}
        r = client.post("/upload", data=data, content_type="multipart/form-data")
        body = r.get_json()
        if r.status_code == 200:
            path = body.get("path")
            ok("Image uploaded", path)
            return path
        else:
            fail("Upload failed", f"status={r.status_code} body={body}")
            return None
    except Exception as e:
        fail("Upload raised", str(e))
        return None


# ── step 4: YOLO detect ───────────────────────────────────────────────────────

def step_detect(client) -> list:
    section("Step 4 — YOLO detect  →  POST /detect")
    try:
        r = client.post("/detect")
        body = r.get_json()
        if r.status_code != 200:
            fail("Detect failed", f"status={r.status_code} body={body}")
            return []
        detections = body.get("detections", [])
        if detections:
            labels = [f"{d['label']} ({d['confidence']})" for d in detections]
            ok(f"Detected {len(detections)} item(s)", ", ".join(labels))
        else:
            ok("Detect ran (no objects found in image)")
        return detections
    except Exception as e:
        fail("Detect raised", str(e))
        return []


# ── step 5: store items ───────────────────────────────────────────────────────

def step_store(client, member_id: str, detections: list):
    section("Step 5 — Store items  →  POST /store")
    if not member_id:
        skip("Store", "no test user")
        return

    # Attach required metadata to each detection (simulate frontend input)
    items = [
        {**d, "purchase_year": 2022, "cost": 500.00, "room_id": 1}
        for d in detections
    ]
    if not items:
        # Use a synthetic item so we can still exercise the store path
        items = [{"class_id": 56, "label": "chair", "confidence": 0.9,
                  "bbox": [10, 20, 200, 300],
                  "purchase_year": 2022, "cost": 500.00, "room_id": 1}]
        print("  (no detections — using synthetic chair item)")

    try:
        payload = {"items": items}
        r = client.post("/store", json=payload, headers=auth_headers(member_id))
        body = r.get_json()
        if r.status_code == 200:
            ok("Items stored", body.get("message"))
        else:
            fail("Store failed", f"status={r.status_code} body={body}")
    except Exception as e:
        fail("Store raised", str(e))


# ── step 6: verify items in Supabase DB ──────────────────────────────────────

def step_verify_db(client, member_id: str):
    section("Step 6 — Verify items in Supabase  →  GET /items")
    if not member_id:
        skip("DB verify", "no test user")
        return

    try:
        r = client.get("/items", headers=auth_headers(member_id))
        body = r.get_json()
        if r.status_code != 200:
            fail("GET /items failed", f"status={r.status_code} body={body}")
            return
        items = body.get("items", [])
        if items:
            ok(f"{len(items)} item(s) found in Supabase DB")
            for it in items:
                print(f"     id={it['id']}  label={it['label']}  "
                      f"room={it['room']}  cost=${it['cost']}")
                _item_ids.append(it["id"])
        else:
            fail("No items found in DB after store")
    except Exception as e:
        fail("DB verify raised", str(e))


# ── step 7: Supabase Storage — originals ─────────────────────────────────────

def step_local_crops(member_id: str):
    section("Step 7 — Supabase Storage: originals/ in img bucket")
    if not member_id:
        skip("Storage originals check", "no test user")
        return

    try:
        from supabase_client import get_supabase
        sb = get_supabase()
        res = sb.storage.from_("img").list("originals")
        matching = [f for f in (res or []) if f.get("name", "").startswith(member_id)]
        if matching:
            ok(f"Found {len(matching)} original(s) in img/originals/", matching[0]["name"])
        else:
            fail("No originals found in img/originals/ for this user",
                 f"prefix={member_id}")
    except Exception as e:
        fail("Originals storage check raised", str(e))


# ── step 8: Supabase Storage — crops ─────────────────────────────────────────

def step_supabase_storage(member_id: str):
    section("Step 8 — Supabase Storage: crops/ in img bucket")
    if not member_id:
        skip("Storage crops check", "no test user")
        return

    try:
        from supabase_client import get_supabase
        sb = get_supabase()
        res = sb.storage.from_("img").list("crops")
        matching = [f for f in (res or []) if f.get("name", "").startswith(member_id)]
        if matching:
            ok(f"Found {len(matching)} crop(s) in img/crops/", matching[0]["name"])
        else:
            fail("No crops found in img/crops/ for this user",
                 f"prefix={member_id}")
    except Exception as e:
        fail("Crops storage check raised", str(e))


# ── cleanup ───────────────────────────────────────────────────────────────────

def cleanup(client, member_id: str):
    section("Cleanup")
    try:
        for item_id in _item_ids:
            client.delete(f"/items/{item_id}", headers=auth_headers(member_id))
        if member_id:
            from supabase_client import get_supabase
            get_supabase().auth.admin.delete_user(member_id)
            ok(f"Deleted test user + {len(_item_ids)} item(s)")
    except Exception as e:
        fail("Cleanup raised", str(e))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not JWT_SECRET:
        print("ERROR: SUPABASE_JWT_SECRET not set.")
        sys.exit(1)

    from app import app
    app.config["TESTING"] = True
    client = app.test_client()

    member_id = None
    try:
        step_health(client)
        member_id = step_create_user()
        step_upload(client)
        detections = step_detect(client)
        step_store(client, member_id, detections)
        step_verify_db(client, member_id)
        step_local_crops(member_id)
        step_supabase_storage(member_id)
    finally:
        if member_id:
            cleanup(client, member_id)

    print(f"\n{'='*50}")
    print(f"  {_pass} passed  |  {_fail} failed  |  {_skip} skipped")
    print(f"{'='*50}\n")
    sys.exit(0 if _fail == 0 else 1)


if __name__ == "__main__":
    main()
