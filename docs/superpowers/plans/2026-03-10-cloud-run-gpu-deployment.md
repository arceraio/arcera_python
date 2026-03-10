# Cloud Run GPU Deployment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerize `detect_server.py` and deploy it to Google Cloud Run with GPU, replacing the rented SSH server.

**Architecture:** A single `gpu_server/Dockerfile` bakes both model files (`best.onnx`, `yolo12n.pt`) into the image at build time. Cloud Run serves the container with GPU; `detect_server.py` requires zero changes. The backend's `YOLO_SERVICE_URL` is updated to the Cloud Run URL.

**Tech Stack:** Docker, Google Cloud Run (GPU preview), Google Artifact Registry, `ultralytics/ultralytics:latest-cuda` base image, Flask.

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `gpu_server/Dockerfile` | Container definition — copies server + models, sets env vars |
| Create | `.dockerignore` | Keeps build context clean (at repo root, where docker build runs) |
| Modify | `.env` | Update `YOLO_SERVICE_URL` to Cloud Run URL |
| Modify | `.env.example` | Update comment to reflect Cloud Run URL pattern |

`detect_server.py` is **not modified**.

---

## Chunk 1: Dockerfile

### Task 1: Write the Dockerfile

**Files:**
- Create: `gpu_server/Dockerfile`
- Create: `.dockerignore` (repo root)

> **Context:** Build is run from the **repo root** (`docker build -f gpu_server/Dockerfile .`) so the build context is the entire repo. `.dockerignore` must live at repo root for Docker to honour it. `detect_server.py` already reads `PORT`, `CUSTOM_MODEL_PATH`, and `COCO_MODEL_PATH` from env vars. Cloud Run injects `PORT` automatically.

- [ ] **Step 1: Create `.dockerignore` at repo root**

```
venv/
__pycache__/
*.pyc
.env
uploads/
exports/
*.db
docs/
test/
```

- [ ] **Step 2: Create `gpu_server/Dockerfile`**

```dockerfile
FROM ultralytics/ultralytics:latest-cuda

WORKDIR /app

# Install Flask + onnxruntime-gpu (ultralytics base has CUDA/cuDNN/PyTorch/ultralytics)
COPY gpu_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Detection server
COPY gpu_server/detect_server.py /app/detect_server.py

# Model files (baked in — update models by rebuilding the image)
COPY backend/best.onnx /app/best.onnx
COPY backend/yolo12n.pt /app/yolo12n.pt

# Tell detect_server.py where the models live
ENV CUSTOM_MODEL_PATH=/app/best.onnx
ENV COCO_MODEL_PATH=/app/yolo12n.pt

# Default PORT to 8080 (matches EXPOSE and Cloud Run convention)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "detect_server.py"]
```

- [ ] **Step 3: Build the image locally to verify it compiles**

Run from **repo root**:
```bash
docker build -f gpu_server/Dockerfile -t arcera-detect:local .
```

Expected: image builds successfully. The ultralytics base is ~8GB so first pull takes a few minutes.

If `COPY backend/yolo12n.pt` fails (file not found), verify the file exists:
```bash
ls -lh backend/yolo12n.pt backend/best.onnx
```

- [ ] **Step 4: Smoke-test the container (CPU-only locally)**

```bash
docker run --rm -p 8080:8080 -e PORT=8080 arcera-detect:local
```

In a second terminal:
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status": "ok"}
```

Stop the container with `Ctrl+C`.

- [ ] **Step 5: Commit**

```bash
git add gpu_server/Dockerfile .dockerignore
git commit -m "feat: add Dockerfile for Cloud Run GPU deployment"
```

---

## Chunk 2: Google Cloud Setup

### Task 2: Enable GCP APIs and create Artifact Registry repo

> **Context:** You need a GCP project with billing enabled. Cloud Run GPU is in preview — you may need to request access at https://cloud.google.com/run/docs/configuring/services/gpu. Install the gcloud CLI if not already installed: https://cloud.google.com/sdk/docs/install

- [ ] **Step 1: Set your project ID**

```bash
export PROJECT_ID=<your-gcp-project-id>
gcloud config set project $PROJECT_ID
```

- [ ] **Step 2: Enable required APIs**

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

Expected: APIs enabled (or already enabled).

- [ ] **Step 3: Create Artifact Registry repository**

```bash
gcloud artifacts repositories create arcera \
  --repository-format=docker \
  --location=us-central1 \
  --description="Arcera detection server images"
```

Expected: `Created repository [arcera]`

- [ ] **Step 4: Configure Docker to authenticate with Artifact Registry**

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

Expected: `Docker configuration file updated.`

---

### Task 3: Push image to Artifact Registry

- [ ] **Step 1: Tag the image for Artifact Registry**

```bash
docker tag arcera-detect:local \
  us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest
```

- [ ] **Step 2: Push the image**

```bash
docker push us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest
```

Expected: layers pushed, `latest` digest printed.

---

## Chunk 3: Cloud Run Deployment

### Task 4: Deploy to Cloud Run with GPU

> **Context:** Cloud Run GPU is in **preview**. Supported GPU types as of early 2026: `nvidia-l4`, `nvidia-h100-80gb`. RTX PRO 6000 Blackwell may appear as a different identifier — check https://cloud.google.com/run/docs/configuring/services/gpu for the current list.

- [ ] **Step 1: Check available GPU types in your region**

```bash
gcloud run regions describe us-central1
```

Look for GPU-related output. Use the best available type (RTX PRO 6000 Blackwell identifier if listed, otherwise `nvidia-h100-80gb` or `nvidia-l4`). Set it as a variable:

```bash
export GPU_TYPE=nvidia-l4   # replace with actual type from output above
```

- [ ] **Step 2: Deploy the Cloud Run service**

```bash
gcloud run deploy arcera-detect \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest \
  --region us-central1 \
  --gpu 1 \
  --gpu-type $GPU_TYPE \
  --memory 16Gi \
  --cpu 4 \
  --no-cpu-throttling \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 120 \
  --allow-unauthenticated \
  --port 8080
```

Expected: deploy succeeds, URL printed:
```
Service URL: https://arcera-detect-<hash>-uc.a.run.app
```

- [ ] **Step 3: Test the health endpoint**

```bash
curl https://arcera-detect-<hash>-uc.a.run.app/health
```

Expected:
```json
{"status": "ok"}
```

First request may take a few seconds (cold start + model warm-up).

- [ ] **Step 4: Test detection with a real image**

Pick any `.jpg` or `.png` from your machine and set it:

```bash
export TEST_IMAGE=/path/to/any-room-photo.jpg
```

Then POST it to the detect endpoint:

```bash
curl -X POST \
  https://arcera-detect-<hash>-uc.a.run.app/detect \
  -F "image=@$TEST_IMAGE" \
  --max-time 60
```

Expected:
```json
{"detections": [{"class_id": ..., "label": "...", "confidence": ..., "bbox": [...]}]}
```

---

## Chunk 4: Wire Backend to Cloud Run

### Task 5: Update YOLO_SERVICE_URL

- [ ] **Step 1: Update `.env`**

Replace the rented server IP with the Cloud Run URL:
```
YOLO_SERVICE_URL=https://arcera-detect-<hash>-uc.a.run.app
```

- [ ] **Step 2: Update `.env.example`**

```
# GPU detection server — Cloud Run service URL
# YOLO_SERVICE_URL=https://arcera-detect-<hash>-uc.a.run.app
```

- [ ] **Step 3: Run the existing backend test suite**

```bash
./venv/bin/python3 -m pytest test/test_remote_detect.py -v
```

Expected: all 4 tests pass (these mock HTTP so they don't call Cloud Run).

- [ ] **Step 4: Run end-to-end smoke test against live Cloud Run**

```bash
./venv/bin/python3 -m pytest test/ -v -k "workflow"
```

Or manually hit the backend:
```bash
curl -X POST http://localhost:5000/detect \
  -F "file=@<path-to-test-image.jpg>"
```

Expected: detections returned, status 200.

- [ ] **Step 5: Commit**

```bash
git add .env.example
git commit -m "config: point YOLO_SERVICE_URL to Cloud Run"
```

> Do not commit `.env` (it's gitignored and contains the real URL).

---

## Updating Models Later

To update `best.onnx` or `yolo12n.pt`:

```bash
# 1. Replace the file in backend/
cp /path/to/new-best.onnx backend/best.onnx

# 2. Rebuild
docker build -f gpu_server/Dockerfile -t arcera-detect:local .
docker tag arcera-detect:local us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest
docker push us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest

# 3. Redeploy
gcloud run deploy arcera-detect \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/arcera/detect:latest \
  --region us-central1
```
