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
