# backend/remote_detect.py
import os
import requests
from config import YOLO_SERVICE_URL, DETECT_SERVICE_TIMEOUT, DETECT_API_KEY
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
        headers = {"X-API-Key": DETECT_API_KEY} if DETECT_API_KEY else {}
        with open(image_path, "rb") as f:
            response = requests.post(
                f"{YOLO_SERVICE_URL}/detect",
                files={"image": (os.path.basename(image_path), f)},
                headers=headers,
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
