# Cloud Run GPU Deployment Design

**Date:** 2026-03-10
**Status:** Approved

## Summary

Containerize `gpu_server/detect_server.py` and deploy it on Google Cloud Run with GPU support (NVIDIA RTX PRO 6000 Blackwell). Model files are baked directly into the Docker image. No external storage, no startup download scripts, zero moving parts.

## Motivation

The current GPU detection server runs on a rented machine via SSH. This is fragile — it goes down without tmux, requires manual restarts, and has no auto-scaling. Cloud Run with GPU solves all of this:

- Auto-scales to zero when idle (no cost when not scanning)
- Cold starts under 5 seconds
- No server management
- Redeploy = model update

## Architecture

```
Client (backend/app.py)
    └── POST /detect ──► Cloud Run (detect_server.py)
                              ├── best.onnx       (baked in image)
                              └── yolo12n.pt      (baked in image)
```

## Components

### 1. `gpu_server/Dockerfile`

- Base image: `ultralytics/ultralytics:latest-cuda`
  - Includes CUDA, cuDNN, PyTorch, Ultralytics — no extra setup needed
- Copies into `/app/`:
  - `gpu_server/detect_server.py`
  - `gpu_server/requirements.txt`
  - `backend/best.onnx`
  - `backend/yolo12n.pt`
- Sets env vars `CUSTOM_MODEL_PATH=/app/best.onnx` and `COCO_MODEL_PATH=/app/yolo12n.pt`
- Installs `flask` and `flask-cors` on top of base
- `CMD ["python", "detect_server.py"]`
- Built from repo root so the build context includes both `gpu_server/` and `backend/`

### 2. Cloud Run Service

| Setting | Value |
|---|---|
| GPU | NVIDIA RTX PRO 6000 Blackwell (96GB vGPU) |
| Min instances | 0 (scale to zero) |
| Max instances | configurable (start with 1) |
| Port | `PORT` env var (already supported by detect_server.py) |
| Auth | Allow unauthenticated (or restrict by bearer token) |

### 3. `.env` Update

```
YOLO_SERVICE_URL=https://<cloud-run-service-url>
```

Backend requires zero code changes — it already reads `YOLO_SERVICE_URL` from config.

### 4. `detect_server.py`

**Zero changes.** Already reads `PORT`, `CUSTOM_MODEL_PATH`, `COCO_MODEL_PATH` from env vars.

## Model Updates

To update a model:
1. Replace `backend/best.onnx` or `backend/yolo12n.pt`
2. `docker build` → `docker push` → `gcloud run deploy`

## Out of Scope

- GCS model storage (decided against — adds complexity)
- Containerizing the main backend (`backend/app.py`) — stays on current host
- Auth on the Cloud Run endpoint (can add later)
