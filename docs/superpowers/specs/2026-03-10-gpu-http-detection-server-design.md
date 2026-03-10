# GPU HTTP Detection Server — Design

## Architecture

```
Frontend
   ↓
Arcera Flask API (Render)
   ↓  POST /detect → multipart image file
GPU Server (rented, tmux-persistent)
   ├── custom model (best.onnx)
   ├── COCO model (yolo12n.pt)
   ├── whitelist filter + IoU dedup
   └── returns {"detections": [...]} JSON
```

`YOLO_SERVICE_URL` in `.env` / Render dashboard points to `http://<gpu-server-ip>:8000`.
When unset, Arcera falls back to running both models locally (existing behaviour, unchanged).

## Components

### `gpu_server/detect_server.py` (new — deployed to GPU machine)
- Standalone Flask app, zero Supabase/auth dependencies
- Loads both models once at startup via `get_custom_model()` / `get_coco_model()`
- Single endpoint: `POST /detect` — accepts multipart `image` field
- Runs `_extract_boxes` on both models, applies COCO whitelist + IoU dedup (custom wins)
- Returns `{"detections": [{"class_id", "label", "confidence", "bbox"}, ...]}`
- Self-contained: all config (class names, whitelist, offset) lives inside the file

### `gpu_server/requirements.txt` (new)
Dependencies for the GPU server: `ultralytics`, `onnxruntime-gpu`, `flask`, `flask-cors`

### `backend/remote_detect.py` (rewrite)
- Drops Gradio client entirely
- `requests.post(YOLO_SERVICE_URL + "/detect", files={"image": ...}, timeout=DETECT_SERVICE_TIMEOUT)`
- Parses `{"detections": [...]}` directly — no Chinese field names
- Raises on HTTP error or timeout so `main.py` fallback still triggers

### `backend/config.py` (addition)
- Add `DETECT_SERVICE_TIMEOUT: int` (default 30s)

### `requirements.txt` (addition)
- Add `requests`

### `.env.example` (update)
- Document `DETECT_SERVICE_TIMEOUT`

## Data Flow

1. Arcera backend receives image upload
2. `detect_items()` checks `YOLO_SERVICE_URL`
3. If not set → raises `DetectionServiceError("No detection service configured")`
4. If set → `remote_detect(path)` opens image as bytes, POSTs to GPU server
5. GPU server returns merged, deduplicated JSON detections
6. `detect_items()` returns list directly — no further merging needed
7. If GPU server unreachable or returns error → raises `DetectionServiceError`

## Error Handling

- HTTP errors, timeouts, and JSON parse failures in `remote_detect.py` all raise a new `DetectionServiceError` exception
- `detect_items()` in `main.py` removes all fallback logic — if `YOLO_SERVICE_URL` is set and the call fails, `DetectionServiceError` propagates to the caller
- If `YOLO_SERVICE_URL` is not set at all, `detect_items()` raises `DetectionServiceError("No detection service configured")` immediately
- Local two-model code (`_extract_boxes`, `_iou`, `get_custom_model`, `get_coco_model`) is removed from `main.py` entirely
- `DetectionUnavailableError` is replaced by `DetectionServiceError`
- `app.py` catches `DetectionServiceError` and returns HTTP 503 with a clear message

## Testing

- Unit test for `remote_detect.py`: mock `requests.post`, verify image is sent and response parsed correctly
- Smoke test for `detect_server.py`: verify Flask app starts and `/detect` route exists
- Existing `test_workflow.py` covers full end-to-end (runs against whichever detection path is active)
