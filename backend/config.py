"""
config.py — single source of truth for all runtime settings.

Every configurable value lives here. To change behaviour, either:
  • set the corresponding environment variable, or
  • edit the default directly in this file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET: str = os.environ.get("SUPABASE_JWT_SECRET", "")

# Storage bucket where originals and crops are kept
STORAGE_BUCKET: str = os.environ.get("STORAGE_BUCKET", "img")

# How long (seconds) a signed image URL stays valid
SIGNED_URL_TTL: int = int(os.environ.get("SIGNED_URL_TTL", 3600))

# ---------------------------------------------------------------------------
# YOLO / detection
# ---------------------------------------------------------------------------

# GPU detection server URL (e.g. http://<gpu-server-ip>:8000)
YOLO_SERVICE_URL: str | None = os.environ.get("YOLO_SERVICE_URL")

# Seconds to wait for the GPU detection server before raising DetectionServiceError
DETECT_SERVICE_TIMEOUT: int = int(os.environ.get("DETECT_SERVICE_TIMEOUT", 30))

# Shared secret sent as X-API-Key header to the detection server
DETECT_API_KEY: str = os.environ.get("DETECT_API_KEY", "")

# Custom (fine-tuned) model — absolute path derived from this file's location
YOLO_MODEL_PATH: str = os.environ.get(
    "YOLO_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "best.onnx"),
)

# General COCO model used alongside the custom model for broader coverage
COCO_MODEL_PATH: str = os.environ.get(
    "COCO_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "yolo12n.pt"),
)

# Custom class IDs are shifted by this amount to avoid clashing with COCO (0–79)
CUSTOM_CLASS_OFFSET: int = int(os.environ.get("CUSTOM_CLASS_OFFSET", 100))

# Authoritative class name map for the custom model (raw IDs, before offset)
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

# COCO classes to keep — everything else from the COCO model is discarded.
# The custom model already covers overlapping categories, so only unique
# COCO items are listed here.
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

# Detection thresholds passed to the remote service
DETECTION_CONF_THRESHOLD: float = float(os.environ.get("DETECTION_CONF_THRESHOLD", 0.25))
DETECTION_IOU_THRESHOLD: float = float(os.environ.get("DETECTION_IOU_THRESHOLD", 0.45))

# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------

UPLOAD_FOLDER: str = os.environ.get(
    "UPLOAD_FOLDER",
    os.path.join(os.path.dirname(__file__), "..", "uploads"),
)

VALID_EXTENSIONS: set[str] = {
    ext.strip()
    for ext in os.environ.get(
        "VALID_EXTENSIONS", ".jpg,.jpeg,.png,.webp,.bmp,.tiff"
    ).split(",")
}

# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

ROOMS: list[str] = [
    "Living Room",
    "Bedroom",
    "Kitchen",
    "Bathroom",
    "Dining Room",
    "Office",
    "Garage",
    "Other",
]
