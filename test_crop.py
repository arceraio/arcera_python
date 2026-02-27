"""
One-time integration test for the crop thumbnail pipeline.
Run with: python test_crop.py

Expects the Flask backend to be running on localhost:5000.
"""

import requests
import sys

API = "http://localhost:5000"
TEST_IMAGE = "uploads/furniture_10.jpg"
FAKE_METADATA = {"purchase_year": 2020, "cost": 100.0, "room_id": 1}

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"{status}  {label}" + (f"  →  {detail}" if detail else ""))
    return condition

def run():
    ok = True

    # ── 1. Health check ──────────────────────────────────────────────────────
    print("\n── 1. Health check")
    try:
        r = requests.get(f"{API}/")
        ok &= check("GET /", r.status_code == 200, r.json().get("status"))
    except requests.ConnectionError:
        check("GET /", False, "backend not reachable — is Flask running?")
        sys.exit(1)

    # ── 2. Upload ────────────────────────────────────────────────────────────
    print("\n── 2. Upload image")
    with open(TEST_IMAGE, "rb") as f:
        r = requests.post(f"{API}/upload", files={"image": f})
    ok &= check("POST /upload", r.status_code == 200, r.json().get("message"))

    # ── 3. Detect ────────────────────────────────────────────────────────────
    print("\n── 3. Run detection")
    r = requests.post(f"{API}/detect")
    ok &= check("POST /detect", r.status_code == 200)
    detections = r.json().get("detections", [])
    ok &= check("detections returned", len(detections) > 0, f"{len(detections)} found")

    if not detections:
        print("  No detections — cannot continue crop test.")
        sys.exit(1)

    has_bbox = all("bbox" in d for d in detections)
    ok &= check("every detection has bbox", has_bbox,
                str(detections[0].get("bbox")) if detections else "")

    # ── 4. Store ─────────────────────────────────────────────────────────────
    print("\n── 4. Store items")
    items_to_store = [
        {**d, **FAKE_METADATA}
        for d in detections
    ]
    r = requests.post(f"{API}/store", json={"items": items_to_store})
    ok &= check("POST /store", r.status_code == 200, r.json().get("message"))

    # ── 5. Items list ─────────────────────────────────────────────────────────
    print("\n── 5. Check /items response")
    r = requests.get(f"{API}/items")
    ok &= check("GET /items", r.status_code == 200)
    items = r.json().get("items", [])
    ok &= check("items list non-empty", len(items) > 0, f"{len(items)} items")

    newest = items[0]  # ordered by created_at DESC
    crop_url = newest.get("crop_url")
    bbox = newest.get("bbox")
    ok &= check("newest item has crop_url", crop_url is not None, str(crop_url))
    ok &= check("newest item has bbox", bbox is not None, str(bbox))

    # ── 6. Fetch crop image ───────────────────────────────────────────────────
    print("\n── 6. Fetch crop image")
    if crop_url:
        r = requests.get(f"{API}{crop_url}")
        ok &= check("GET crop_url → 200", r.status_code == 200)
        ok &= check("content-type is image", "image" in r.headers.get("Content-Type", ""),
                    r.headers.get("Content-Type"))
        ok &= check("crop file non-empty", len(r.content) > 0,
                    f"{len(r.content)} bytes")
    else:
        check("GET crop_url", False, "skipped — no crop_url on newest item")
        ok = False

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + ("─" * 40))
    if ok:
        print("\033[92mAll checks passed.\033[0m")
    else:
        print("\033[91mSome checks failed.\033[0m")
    print()

if __name__ == "__main__":
    run()
