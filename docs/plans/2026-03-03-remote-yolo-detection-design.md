# Remote YOLO12 Detection via Gradio — Design

**Date:** 2026-03-03

## Problem

The local `yolo12n.pt` model loaded on Render causes OOM crashes. The fix is to offload inference to a CSDN Yunchi GPU instance running a Gradio YOLO12 service.

## Approach: Remote-first with local fallback (Option A)

`detect_items()` tries the remote Gradio service first. On any failure it falls back to the local ultralytics model. If both fail, a descriptive `DetectionUnavailableError` is raised.

The `YOLO_SERVICE_URL` env var controls routing:
- **Absent** (local dev) → always uses local model
- **Set** (Render prod) → tries remote first, local on failure

> ⚠️ The Yunchi GPU instance URL is temporary — it changes on each session restart. Update `YOLO_SERVICE_URL` in Render's environment variables whenever the instance is recreated.

## Remote service details

- **Host:** CSDN Yunchi GPU instance, port 7860
- **App:** `/opt/yolo12/app.py` (Gradio Blocks)
- **Model:** `yolov12m.pt` (COCO-80, same class set as local `yolo12n.pt`)
- **Gradio event:** `fn_index=0` — the detect button click handler
- **Inputs:** `(image_path, conf_threshold=0.25, iou_threshold=0.45)`
- **Output shape:** `[annotated_img, detections_json, info_str]`
- **Detection format:**
  ```python
  {"类别": "chair", "置信度": "90.00%", "坐标": [x1, y1, x2, y2]}
  ```

## Data normalisation

`remote_detect.py` maps the remote response to the internal format:
```python
{"class_id": int, "label": str, "confidence": float, "bbox": [x1, y1, x2, y2]}
```

- Class name → `class_id`: reverse lookup on local `model.names` (both use COCO-80)
- Confidence: parse `"90.00%"` → `0.90`

## Error handling

| Scenario | Behaviour |
|---|---|
| Remote succeeds | Return remote detections |
| Remote fails (offline, timeout) | Log warning, fall back to local |
| Local also fails | Raise `DetectionUnavailableError` with message explaining both paths failed |

## Files changed

| File | Change |
|---|---|
| `backend/remote_detect.py` | **New** — Gradio client wrapper + response parser |
| `backend/main.py` | `detect_items()` try remote → local → raise error |
| `requirements.txt` | Add `gradio_client` |
| `render.yaml` | Add `YOLO_SERVICE_URL` env var reference |
