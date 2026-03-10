from ultralytics import YOLO
from config import YOLO_MODEL_PATH, COCO_MODEL_PATH, CUSTOM_CLASS_NAMES, CUSTOM_CLASS_OFFSET

_custom_model: YOLO | None = None
_coco_model:   YOLO | None = None
_combined_names: dict[int, str] | None = None


def get_custom_model() -> YOLO:
    global _custom_model
    if _custom_model is None:
        _custom_model = YOLO(YOLO_MODEL_PATH)
    return _custom_model


def get_coco_model() -> YOLO:
    global _coco_model
    if _coco_model is None:
        _coco_model = YOLO(COCO_MODEL_PATH)
    return _coco_model


def get_combined_names() -> dict[int, str]:
    """COCO classes (0–79) merged with custom classes shifted by CUSTOM_CLASS_OFFSET."""
    global _combined_names
    if _combined_names is None:
        coco_names = dict(get_coco_model().names)
        custom_names = {k + CUSTOM_CLASS_OFFSET: v for k, v in CUSTOM_CLASS_NAMES.items()}
        _combined_names = {**coco_names, **custom_names}
    return _combined_names


# Backwards-compatible alias — callers that use get_model() get the custom model
def get_model() -> YOLO:
    return get_custom_model()
