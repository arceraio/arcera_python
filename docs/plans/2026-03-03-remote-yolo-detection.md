# Remote YOLO12 Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route YOLO inference to a remote Gradio service on a CSDN Yunchi GPU instance, falling back to the local ultralytics model if the remote is unavailable, and raising a descriptive error if both fail.

**Architecture:** `detect_items()` in `main.py` tries `remote_detect()` first (if `YOLO_SERVICE_URL` is set); on any exception it falls back to the local ultralytics model; if that also fails, it raises `DetectionUnavailableError`. A new `remote_detect.py` wraps the Gradio client and normalises the response to the internal detection format.

**Tech Stack:** `gradio_client` (Gradio HTTP client), `ultralytics` (local fallback), Flask (unchanged)

---

### Task 1: Add `gradio_client` to dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `render.yaml`

**Step 1: Add `gradio_client` to requirements.txt**

```
gradio_client
```

Append after the last existing line.

**Step 2: Add `YOLO_SERVICE_URL` env var to render.yaml**

In the `envVars` list:
```yaml
      - key: YOLO_SERVICE_URL
        sync: false
```

**Step 3: Commit**

```bash
git add requirements.txt render.yaml
git commit -m "chore: add gradio_client dep and YOLO_SERVICE_URL env var"
```

---

### Task 2: Create `backend/remote_detect.py`

**Files:**
- Create: `backend/remote_detect.py`

The remote Gradio app (`/opt/yolo12/app.py` on the GPU instance) exposes a single Blocks event at `fn_index=0`:
- **Inputs:** `(image: PIL, conf_threshold: float, iou_threshold: float)`
- **Output:** `[annotated_img, detections_list, info_str]`
- **Detection shape:** `{"类别": "chair", "置信度": "90.00%", "坐标": [x1, y1, x2, y2]}`

We normalise to: `{"class_id": int, "label": str, "confidence": float, "bbox": [x1,y1,x2,y2]}`

Class name → `class_id` uses a reverse lookup on the local model's `names` dict (both use COCO-80).

> ⚠️ `YOLO_SERVICE_URL` is a **temporary URL** that changes each time the Yunchi GPU instance is restarted. Update the env var in Render whenever the instance is recreated.

**Step 1: Write the file**

```python
# backend/remote_detect.py
#
# ⚠️  YOLO_SERVICE_URL is temporary — it changes on every Yunchi instance restart.
#     Update the env var in Render whenever the GPU instance is recreated.

import os
from gradio_client import Client, handle_file

_client = None
YOLO_SERVICE_URL = os.environ.get("YOLO_SERVICE_URL")


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(YOLO_SERVICE_URL)
    return _client


def remote_detect(image_path: str, name_to_id: dict) -> list[dict]:
    """
    Call the remote Gradio YOLO12 service and return detections in internal format.

    Returns a list of:
        {"class_id": int, "label": str, "confidence": float, "bbox": [x1,y1,x2,y2]}

    Raises on any connection/timeout/parse failure — caller handles fallback.
    """
    result = _get_client().predict(
        handle_file(image_path),   # image input
        0.25,                      # conf_threshold
        0.45,                      # iou_threshold
        fn_index=0,
    )

    # result = [annotated_img, detections_list, info_str]
    raw_detections = result[1] or []

    detections = []
    for d in raw_detections:
        label = d["类别"]
        confidence = float(d["置信度"].rstrip("%")) / 100
        x1, y1, x2, y2 = [round(v) for v in d["坐标"]]
        class_id = name_to_id.get(label, -1)
        detections.append({
            "class_id": class_id,
            "label": label,
            "confidence": confidence,
            "bbox": [x1, y1, x2, y2],
        })
    return detections
```

**Step 2: Commit**

```bash
git add backend/remote_detect.py
git commit -m "feat: add remote_detect.py wrapping Gradio YOLO12 client"
```

---

### Task 3: Update `detect_items()` in `backend/main.py`

**Files:**
- Modify: `backend/main.py`

**Step 1: Add `DetectionUnavailableError` and update imports at the top of `main.py`**

Replace the existing imports block:
```python
import os
import io
import uuid
from PIL import Image
from store import init_db, verify_member, create_item, find_duplicate, update_item
from export import export_to_csv
from yolo_model import get_model
from storage import upload_bytes
```

With:
```python
import os
import io
import uuid
import logging
from PIL import Image
from store import init_db, verify_member, create_item, find_duplicate, update_item
from export import export_to_csv
from yolo_model import get_model
from storage import upload_bytes


class DetectionUnavailableError(RuntimeError):
    """Raised when both the remote YOLO service and the local model fail."""
    pass
```

**Step 2: Replace `detect_items()` with remote-first + local fallback**

Replace the existing `detect_items` function:

```python
def detect_items(path):
    model = get_model()

    # ── remote path ───────────────────────────────────────────────────────────
    remote_url = os.environ.get("YOLO_SERVICE_URL")
    if remote_url:
        try:
            from remote_detect import remote_detect
            name_to_id = {v: k for k, v in model.names.items()}
            return remote_detect(path, name_to_id)
        except Exception as exc:
            logging.warning("Remote YOLO service failed (%s), falling back to local model.", exc)

    # ── local path ────────────────────────────────────────────────────────────
    try:
        results = model(path)
        boxes = results[0].boxes
        if not boxes:
            return []

        items = []
        for box in boxes:
            class_id = int(box.cls[0])
            label = results[0].names[class_id]
            confidence = round(float(box.conf[0]), 2)
            x1, y1, x2, y2 = [round(float(v)) for v in box.xyxy[0]]
            items.append({
                "class_id": class_id,
                "label": label,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
            })
        return items
    except Exception as exc:
        raise DetectionUnavailableError(
            "Detection failed: the remote YOLO service is unreachable and the local "
            f"model also failed to run. Remote URL configured: {bool(remote_url)}. "
            f"Local error: {exc}"
        ) from exc
```

**Step 3: Surface `DetectionUnavailableError` in `app.py`'s `/detect` route**

In `backend/app.py`, update the `/detect` route to catch the new error:

```python
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS, DetectionUnavailableError

# ...

@app.route('/detect', methods=['POST'])
def detect():
    path = uploaded_file_path.get("path")
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    if not valid:
        return jsonify({"error": message}), 400
    try:
        detections = detect_items(path)
    except DetectionUnavailableError as e:
        return jsonify({"error": str(e)}), 503
    return jsonify({"detections": detections, "path": path})
```

**Step 4: Commit**

```bash
git add backend/main.py backend/app.py
git commit -m "feat: remote-first YOLO detection with local fallback and DetectionUnavailableError"
```

---

### Task 4: Run the test suite

**Step 1: Run the existing workflow test**

```bash
python test/test_workflow.py
```

Expected: all steps pass including Step 4 (YOLO detect). The test uses the local model since `YOLO_SERVICE_URL` is not set in the local `.env`.

**Step 2: Smoke-test remote path manually (optional)**

Set the env var temporarily and run detect:
```bash
YOLO_SERVICE_URL=<current-yunchi-url> python -c "
import sys; sys.path.insert(0, 'backend')
from main import detect_items
print(detect_items('test_images/furniture_1.jpeg'))
"
```

Expected: list of detections with `class_id`, `label`, `confidence`, `bbox`.

**Step 3: Commit if any fixes were needed, then done**

```bash
git add -p
git commit -m "fix: <description of any fixes>"
```
