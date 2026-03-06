#!/usr/bin/env python3
"""
Multi-image workflow test.

Steps:
  1. Supabase connectivity
  2. Create test user
  3. POST /multi-upload  (2 images)   → temp_photo row created with both paths
  4. POST /multiscan                   → detections for both images
  5. POST /store  (image 1 with original_storage_path)  → item stored, path removed
  6. Verify temp_photo: image 1 path gone, image 2 path still present
  7. POST /store  (image 2 with original_storage_path)  → item stored
  8. Verify temp_photo: both paths gone (arrays empty)
  9. GET /items  → items present in Supabase
  10. Cleanup

Run from repo root:
  python test/test_multi_workflow.py
"""

import sys
import os
import io
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import jwt as pyjwt

REPO_ROOT    = os.path.join(os.path.dirname(__file__), '..')
IMAGE_1      = os.path.join(REPO_ROOT, 'test_images', 'furniture_1.jpeg')
IMAGE_2      = os.path.join(REPO_ROOT, 'test_images', 'furniture_2.jpg')
JWT_SECRET   = os.environ.get("SUPABASE_JWT_SECRET")

_pass = _fail = _skip = 0
_item_ids: list[int] = []


# ── reporting ──────────────────────────────────────────────────────────────────

def ok(label, detail=""):
    global _pass; _pass += 1
    print(f"  [OK]   {label}" + (f"  ({detail})" if detail else ""))

def fail(label, detail=""):
    global _fail; _fail += 1
    print(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))

def skip(label, reason=""):
    global _skip; _skip += 1
    print(f"  [SKIP] {label}" + (f"  — {reason}" if reason else ""))

def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


# ── auth ───────────────────────────────────────────────────────────────────────

def make_jwt(member_id):
    now = int(time.time())
    return pyjwt.encode(
        {"sub": member_id, "aud": "authenticated", "role": "authenticated",
         "iat": now, "exp": now + 3600},
        JWT_SECRET, algorithm="HS256",
    )

def auth_headers(member_id):
    return {"Authorization": f"Bearer {make_jwt(member_id)}"}


# ── steps ──────────────────────────────────────────────────────────────────────

def step_health(client):
    section("Step 1 — Supabase connectivity")
    r = client.get("/supabase/health")
    if r.status_code == 200 and r.get_json().get("status") == "ok":
        ok("Supabase client connected")
    else:
        fail("Supabase health check", str(r.get_json()))


def step_create_user():
    section("Step 2 — Create test user")
    import uuid
    from supabase_client import get_supabase
    email = f"test-multi-{uuid.uuid4().hex[:8]}@arcera-test.invalid"
    res = get_supabase().auth.admin.create_user(
        {"email": email, "email_confirm": True}
    )
    member_id = str(res.user.id)
    ok("Test user created", member_id)
    return member_id


def step_multi_upload(client, member_id):
    section("Step 3 — POST /multi-upload  (2 images)")
    with open(IMAGE_1, "rb") as f1, open(IMAGE_2, "rb") as f2:
        data = {
            "images": [
                (io.BytesIO(f1.read()), os.path.basename(IMAGE_1)),
                (io.BytesIO(f2.read()), os.path.basename(IMAGE_2)),
            ]
        }
    r = client.post("/multi-upload", data=data,
                    content_type="multipart/form-data",
                    headers=auth_headers(member_id))
    body = r.get_json()
    if r.status_code != 200:
        fail("multi-upload failed", f"status={r.status_code} body={body}")
        return []
    storage_paths = body.get("storage_paths", [])
    ok(f"Uploaded {body['count']} image(s)", ", ".join(storage_paths))

    # verify temp_photo row in DB
    from store import get_temp_photo
    row = get_temp_photo(member_id)
    if row and len(row.get("img_url") or []) == 2 and len(row.get("local_paths") or []) == 2:
        ok("temp_photo row has 2 storage paths and 2 local paths")
    else:
        fail("temp_photo row unexpected", str(row))
    return storage_paths


def step_multiscan(client, member_id):
    section("Step 4 — POST /multiscan")
    r = client.post("/multiscan", headers=auth_headers(member_id))
    body = r.get_json()
    if r.status_code != 200:
        fail("multiscan failed", f"status={r.status_code} body={body}")
        return []
    results = body.get("results", [])
    ok(f"Received results for {len(results)} image(s)")
    all_detections = []
    for i, res in enumerate(results):
        dets = res.get("detections", [])
        labels = [f"{d['label']} ({d['confidence']})" for d in dets]
        print(f"     image {i+1}: {len(dets)} detection(s)"
              + (f"  — {', '.join(labels[:3])}" if labels else ""))
        all_detections.append((res["storage_path"], res["local_path"], dets))
    return all_detections


def step_store_one(client, member_id, storage_path, local_path, detections, label):
    section(f"Step 5/7 — POST /store  ({label})")
    items = [
        {**d, "purchase_year": 2023, "cost": 300.0, "room_id": 2}
        for d in (detections or [{"class_id": 56, "label": "chair",
                                   "confidence": 0.9, "bbox": [10, 20, 200, 300]}])
    ][:2]  # store at most 2 items per image to keep test fast
    payload = {
        "items": items,
        "path": local_path,
        "original_storage_path": storage_path,
    }
    r = client.post("/store", json=payload, headers=auth_headers(member_id))
    body = r.get_json()
    if r.status_code == 200:
        ok(f"Store OK", body.get("message"))
    else:
        fail(f"Store failed", f"status={r.status_code} body={body}")


def step_verify_temp_photo(member_id, expected_count, step_label):
    section(f"{step_label} — Verify temp_photo row")
    from store import get_temp_photo
    row = get_temp_photo(member_id)
    urls = (row.get("img_url") or []) if row else []
    if len(urls) == expected_count:
        ok(f"temp_photo.img_url has {expected_count} path(s) (expected)")
    else:
        fail(f"temp_photo.img_url length wrong",
             f"expected={expected_count} got={len(urls)}")


def step_verify_items(client, member_id):
    section("Step 9 — GET /items")
    r = client.get("/items", headers=auth_headers(member_id))
    body = r.get_json()
    if r.status_code != 200:
        fail("GET /items failed", str(body))
        return
    items = body.get("items", [])
    ok(f"{len(items)} item(s) in DB")
    for it in items:
        print(f"     id={it['id']}  label={it['label']}  cost=${it['cost']}")
        _item_ids.append(it["id"])


def cleanup(client, member_id):
    section("Cleanup")
    from supabase_client import get_supabase
    for item_id in _item_ids:
        client.delete(f"/items/{item_id}", headers=auth_headers(member_id))
    # also wipe any remaining temp_photo row
    get_supabase().table("temp_photo").delete().eq("user_id", member_id).execute()
    get_supabase().auth.admin.delete_user(member_id)
    ok(f"Deleted test user + {len(_item_ids)} item(s)")


# ── main ───────────────────────────────────────────────────────────────────────

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
        storage_paths = step_multi_upload(client, member_id)
        if not storage_paths:
            return
        scan_results = step_multiscan(client, member_id)
        if not scan_results:
            return

        sp1, lp1, dets1 = scan_results[0]
        sp2, lp2, dets2 = scan_results[1]

        step_store_one(client, member_id, sp1, lp1, dets1, "image 1")
        step_verify_temp_photo(member_id, 1, "Step 6")

        step_store_one(client, member_id, sp2, lp2, dets2, "image 2")
        step_verify_temp_photo(member_id, 0, "Step 8")

        step_verify_items(client, member_id)
    finally:
        if member_id:
            cleanup(client, member_id)

    print(f"\n{'='*50}")
    print(f"  {_pass} passed  |  {_fail} failed  |  {_skip} skipped")
    print(f"{'='*50}\n")
    sys.exit(0 if _fail == 0 else 1)


if __name__ == "__main__":
    main()
