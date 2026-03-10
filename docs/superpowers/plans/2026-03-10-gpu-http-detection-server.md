# GPU HTTP Detection Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Gradio remote detection client and local model fallback with a standalone HTTP Flask server (`detect_server.py`) that runs on a rented GPU machine and returns merged, deduplicated detections.

**Architecture:** Arcera backend POSTs an image to `YOLO_SERVICE_URL/detect`; the GPU server runs both models and returns JSON. If the service is unreachable or unconfigured, `DetectionServiceError` is raised immediately — no local fallback. `DetectionServiceError` lives in `backend/errors.py` to avoid circular imports.

**Tech Stack:** Python, Flask, Ultralytics YOLO, onnxruntime-gpu (server), requests (client)

---

## Chunk 1: GPU server + client rewrite

### Task 1: Create `backend/errors.py` — shared exception

**Files:**
- Create: `backend/errors.py`

Defines `DetectionServiceError` in a standalone module so both `main.py` and `remote_detect.py` can import it without a circular dependency.

- [ ] **Step 1: Create `backend/errors.py`**

```python
class DetectionServiceError(RuntimeError):
    """Raised when the GPU detection service is unreachable, unconfigured, or returns an error."""
    pass
```

- [ ] **Step 2: Verify**

```bash
grep "DetectionServiceError" backend/errors.py
```
Expected: one line

---

### Task 2: Create `gpu_server/detect_server.py`

**Files:**
- Create: `gpu_server/detect_server.py`
- Create: `gpu_server/requirements.txt`

- [ ] **Step 1: Create `gpu_server/requirements.txt`**

```
ultralytics
onnxruntime-gpu
flask
flask-cors
```

- [ ] **Step 2: Write `gpu_server/detect_server.py`**

```python
"""
detect_server.py — standalone YOLO detection service for GPU machine.

Deploy to rented GPU server and keep alive with:
    tmux new -s arcera-detect
    python detect_server.py
    # Ctrl+B, D to detach

Env vars:
    CUSTOM_MODEL_PATH   path to best.onnx   (default: ./best.onnx)
    COCO_MODEL_PATH     path to yolo12n.pt  (default: ./yolo12n.pt)
    PORT                port to listen on   (default: 8000)
"""

import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CUSTOM_MODEL_PATH = os.environ.get("CUSTOM_MODEL_PATH", "best.onnx")
COCO_MODEL_PATH   = os.environ.get("COCO_MODEL_PATH",   "yolo12n.pt")
PORT              = int(os.environ.get("PORT", 8000))

CUSTOM_CLASS_OFFSET = 100

CUSTOM_CLASS_NAMES: dict[int, str] = {
    0:  "bed",
    1:  "sofa",
    2:  "chair",
    3:  "table",
    4:  "lamp",
    5:  "tv",
    6:  "laptop",
    7:  "wardrobe",
    8:  "window",
    9:  "door",
    10: "potted plant",
    11: "photo frame",
}

COCO_CLASS_WHITELIST: frozenset[int] = frozenset({
    24,  # backpack
    25,  # umbrella
    26,  # handbag
    27,  # tie
    28,  # suitcase
    30,  # skis
    31,  # snowboard
    34,  # baseball bat
    36,  # skateboard
    37,  # surfboard
    38,  # tennis racket
    40,  # wine glass
    41,  # cup
    45,  # bowl
    61,  # toilet
    64,  # mouse
    65,  # remote
    66,  # keyboard
    67,  # cell phone
    68,  # microwave
    69,  # oven
    70,  # toaster
    71,  # sink
    72,  # refrigerator
    73,  # book
    74,  # clock
    75,  # vase
    77,  # teddy bear
    78,  # hair drier
})

# ---------------------------------------------------------------------------
# Model loading (lazy, loaded once on first request)
# ---------------------------------------------------------------------------

_custom_model: YOLO | None = None
_coco_model:   YOLO | None = None
_combined_names: dict[int, str] | None = None


def get_custom_model() -> YOLO:
    global _custom_model
    if _custom_model is None:
        _custom_model = YOLO(CUSTOM_MODEL_PATH)
    return _custom_model


def get_coco_model() -> YOLO:
    global _coco_model
    if _coco_model is None:
        _coco_model = YOLO(COCO_MODEL_PATH)
    return _coco_model


def get_combined_names() -> dict[int, str]:
    global _combined_names
    if _combined_names is None:
        coco_names   = dict(get_coco_model().names)
        custom_names = {k + CUSTOM_CLASS_OFFSET: v for k, v in CUSTOM_CLASS_NAMES.items()}
        _combined_names = {**coco_names, **custom_names}
    return _combined_names


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _iou(a: list, b: list) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def _extract_boxes(results, class_offset: int = 0) -> list[dict]:
    combined_names = get_combined_names()
    boxes = results[0].boxes
    if not boxes:
        return []
    items = []
    for box in boxes:
        raw_id     = int(box.cls[0])
        class_id   = raw_id + class_offset
        label      = combined_names.get(class_id, f"class_{class_id}")
        confidence = round(float(box.conf[0]), 2)
        x1, y1, x2, y2 = [round(float(v)) for v in box.xyxy[0]]
        items.append({
            "class_id":   class_id,
            "label":      label,
            "confidence": confidence,
            "bbox":       [x1, y1, x2, y2],
        })
    return items


def run_detection(image_path: str) -> list[dict]:
    custom_detections = _extract_boxes(get_custom_model()(image_path), class_offset=CUSTOM_CLASS_OFFSET)
    coco_raw          = _extract_boxes(get_coco_model()(image_path),   class_offset=0)

    custom_bboxes = [d["bbox"] for d in custom_detections]
    coco_detections = [
        d for d in coco_raw
        if d["class_id"] in COCO_CLASS_WHITELIST
        and not any(_iou(d["bbox"], cb) >= 0.5 for cb in custom_bboxes)
    ]
    return custom_detections + coco_detections


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/detect", methods=["POST"])
def detect():
    if "image" not in request.files:
        return jsonify({"error": "No image provided."}), 400

    file = request.files["image"]
    suffix = os.path.splitext(file.filename)[1] or ".jpg"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        detections = run_detection(tmp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(tmp_path)

    return jsonify({"detections": detections})


if __name__ == "__main__":
    # Warm up models at startup so first request isn't slow
    get_combined_names()
    print(f"Detection server ready on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
```

- [ ] **Step 3: Verify files exist**

```bash
ls gpu_server/
```
Expected: `detect_server.py  requirements.txt`

---

### Task 3: Rewrite `backend/remote_detect.py` as HTTP client

**Files:**
- Modify: `backend/remote_detect.py`

- [ ] **Step 1: Write the new `remote_detect.py`**

```python
# backend/remote_detect.py
import os
import requests
from config import YOLO_SERVICE_URL, DETECT_SERVICE_TIMEOUT
from errors import DetectionServiceError


def remote_detect(image_path: str) -> list[dict]:
    """
    POST image to the GPU detection server and return detections.

    Returns:
        list of {"class_id": int, "label": str, "confidence": float, "bbox": [x1,y1,x2,y2]}

    Raises:
        DetectionServiceError on connection failure, timeout, or invalid response.
    """
    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                f"{YOLO_SERVICE_URL}/detect",
                files={"image": (os.path.basename(image_path), f)},
                timeout=DETECT_SERVICE_TIMEOUT,
            )
        response.raise_for_status()
        return response.json()["detections"]
    except requests.exceptions.Timeout:
        raise DetectionServiceError(f"Detection service timed out after {DETECT_SERVICE_TIMEOUT}s.")
    except requests.exceptions.ConnectionError:
        raise DetectionServiceError(f"Detection service unreachable at {YOLO_SERVICE_URL}.")
    except (requests.exceptions.HTTPError, KeyError, ValueError) as e:
        raise DetectionServiceError(f"Detection service returned an invalid response: {e}")
```

- [ ] **Step 2: Verify old Gradio imports are gone**

```bash
grep -n "gradio" backend/remote_detect.py
```
Expected: no output

---

### Task 4: Update `backend/config.py` — add `DETECT_SERVICE_TIMEOUT`

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Add timeout config below the `YOLO_SERVICE_URL` line**

```python
# Seconds to wait for the GPU detection server before raising DetectionServiceError
DETECT_SERVICE_TIMEOUT: int = int(os.environ.get("DETECT_SERVICE_TIMEOUT", 30))
```

- [ ] **Step 2: Verify**

```bash
grep "DETECT_SERVICE_TIMEOUT" backend/config.py
```
Expected: one matching line

---

### Task 5: Simplify `backend/main.py` — remove fallback, use `DetectionServiceError`

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace `DetectionUnavailableError` with import from `errors.py`**

Remove:
```python
class DetectionUnavailableError(RuntimeError):
    """Raised when both the remote YOLO service and the local model fail."""
    pass
```
Add at the top of the imports:
```python
from errors import DetectionServiceError
```

- [ ] **Step 2: Update the yolo_model import — remove local model functions**

Change:
```python
from yolo_model import get_model, get_custom_model, get_coco_model, get_combined_names
```
To:
```python
from yolo_model import get_combined_names
```

- [ ] **Step 3: Remove `CUSTOM_CLASS_OFFSET` and `COCO_CLASS_WHITELIST` from config import**

Change:
```python
from config import VALID_EXTENSIONS, ROOMS, YOLO_SERVICE_URL, COCO_CLASS_WHITELIST
```
To:
```python
from config import VALID_EXTENSIONS, ROOMS, YOLO_SERVICE_URL
```

- [ ] **Step 4: Remove local detection helpers and rewrite `detect_items`**

Delete `_iou`, `_extract_boxes`, and the old `detect_items` entirely. Replace `detect_items` with:

```python
def detect_items(path: str) -> list[dict]:
    if not YOLO_SERVICE_URL:
        raise DetectionServiceError("No detection service configured. Set YOLO_SERVICE_URL.")
    from remote_detect import remote_detect
    return remote_detect(path)
```

- [ ] **Step 5: Verify no local model or old error references remain**

```bash
grep -n "get_custom_model\|get_coco_model\|_extract_boxes\|_iou\|DetectionUnavailableError\|COCO_CLASS_WHITELIST\|CUSTOM_CLASS_OFFSET" backend/main.py
```
Expected: no output

---

### Task 6: Update `backend/app.py` — use `DetectionServiceError`

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Update import**

Change:
```python
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS, DetectionUnavailableError
```
To:
```python
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS
from errors import DetectionServiceError
```

- [ ] **Step 2: Update `/detect` error handling**

```python
    try:
        detections = detect_items(path)
    except DetectionServiceError as e:
        return jsonify({"error": str(e)}), 503
```

- [ ] **Step 3: Update `/multiscan` error handling**

```python
        try:
            detections = detect_items(local_path)
        except DetectionServiceError as e:
            return jsonify({"error": str(e)}), 503
```

- [ ] **Step 4: Verify no old error references remain**

```bash
grep -n "DetectionUnavailableError" backend/app.py
```
Expected: no output

---

### Task 7: Update `requirements.txt` and `.env.example`

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: In `requirements.txt`, add `requests` and remove `gradio_client`**

Final `requirements.txt` should contain:
```
ultralytics
onnxruntime
flask
flask-cors
gunicorn
supabase
python-dotenv
PyJWT
requests
```

- [ ] **Step 2: Update `.env.example` — fix stale Gradio comments and add new vars**

Replace the `YOLO_SERVICE_URL` block:
```
# GPU detection server URL — set this to your rented GPU server's address
# YOLO_SERVICE_URL=http://<gpu-server-ip>:8000

# Seconds to wait for GPU detection server response (default: 30)
# DETECT_SERVICE_TIMEOUT=30
```

- [ ] **Step 3: Verify `gradio_client` is gone**

```bash
grep "gradio" requirements.txt
```
Expected: no output

---

### Task 8: Write tests

**Files:**
- Create: `test/test_remote_detect.py`
- Create: `test/test_detect_server.py`

- [ ] **Step 1: Write unit tests for `remote_detect.py`**

```python
"""
Unit tests for remote_detect.py — mocks HTTP calls, no real server needed.
Run from repo root: ./venv/bin/python3 -m pytest test/test_remote_detect.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_service_url(monkeypatch):
    monkeypatch.setenv("YOLO_SERVICE_URL", "http://fake-gpu:8000")
    monkeypatch.setenv("DETECT_SERVICE_TIMEOUT", "5")


def test_remote_detect_returns_detections(tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "detections": [
            {"class_id": 102, "label": "chair", "confidence": 0.91, "bbox": [10, 20, 100, 200]}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        import importlib, config, remote_detect
        importlib.reload(config)
        importlib.reload(remote_detect)
        result = remote_detect.remote_detect(str(img))

    assert len(result) == 1
    assert result[0]["label"] == "chair"
    assert result[0]["class_id"] == 102


def test_remote_detect_raises_on_timeout(tmp_path):
    import requests as req, importlib, config, remote_detect
    importlib.reload(config)
    importlib.reload(remote_detect)
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    from errors import DetectionServiceError
    with patch("requests.post", side_effect=req.exceptions.Timeout):
        with pytest.raises(DetectionServiceError, match="timed out"):
            remote_detect.remote_detect(str(img))


def test_remote_detect_raises_on_connection_error(tmp_path):
    import requests as req, importlib, config, remote_detect
    importlib.reload(config)
    importlib.reload(remote_detect)
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    from errors import DetectionServiceError
    with patch("requests.post", side_effect=req.exceptions.ConnectionError):
        with pytest.raises(DetectionServiceError, match="unreachable"):
            remote_detect.remote_detect(str(img))


def test_detect_items_raises_when_no_service_url(monkeypatch):
    monkeypatch.delenv("YOLO_SERVICE_URL", raising=False)
    import importlib, config, main
    importlib.reload(config)
    importlib.reload(main)
    from errors import DetectionServiceError
    with pytest.raises(DetectionServiceError, match="No detection service configured"):
        main.detect_items("some/path.jpg")
```

- [ ] **Step 2: Write smoke test for `detect_server.py`**

```python
"""
Smoke test for detect_server.py — verifies routes exist, no real models loaded.
Run from repo root: ./venv/bin/python3 -m pytest test/test_detect_server.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gpu_server'))

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    # Prevent model loading during import
    with patch("detect_server.get_combined_names", return_value={}):
        import detect_server
        detect_server.app.config["TESTING"] = True
        yield detect_server.app.test_client()


def test_health_route(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_detect_returns_400_with_no_image(client):
    r = client.post("/detect")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_detect_returns_detections(client, tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    with patch("detect_server.run_detection", return_value=[
        {"class_id": 102, "label": "chair", "confidence": 0.91, "bbox": [10, 20, 100, 200]}
    ]):
        import io
        data = {"image": (io.BytesIO(b"fakejpeg"), "test.jpg")}
        r = client.post("/detect", data=data, content_type="multipart/form-data")

    assert r.status_code == 200
    body = r.get_json()
    assert "detections" in body
    assert body["detections"][0]["label"] == "chair"
```

- [ ] **Step 3: Run both test files**

```bash
cd /home/kevin/Apps/Arcera/arcera_python
./venv/bin/python3 -m pytest test/test_remote_detect.py test/test_detect_server.py -v
```
Expected: all tests pass

---

### Task 9: Run full workflow test and commit

- [ ] **Step 1: Run the existing workflow test**

With `YOLO_SERVICE_URL` unset in `.env`, the test should now fail at detect with a clean `DetectionServiceError` and 503 response at step 4. Verify the error message is clear:

```bash
cd /home/kevin/Apps/Arcera/arcera_python
./venv/bin/python3 test/test_workflow.py 2>/dev/null
```
Expected: Step 4 (detect) fails with a clear message like `"No detection service configured. Set YOLO_SERVICE_URL."` — this is correct behaviour.

- [ ] **Step 2: Commit**

```bash
git add gpu_server/ backend/errors.py backend/remote_detect.py backend/main.py backend/app.py backend/config.py requirements.txt .env.example test/test_remote_detect.py test/test_detect_server.py docs/superpowers/
git commit -m "feat: replace Gradio detection client with GPU HTTP server"
```
