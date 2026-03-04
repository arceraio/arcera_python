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
