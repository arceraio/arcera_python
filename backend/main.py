from ultralytics import YOLO
import os

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

def get_image_path(path):
    return path.strip()

def check_file_exists(path):
    if not os.path.isfile(path):
        return False, "File not found."
    ext = os.path.splitext(path)[1].lower()
    if ext not in VALID_EXTENSIONS:
        return False, f"Invalid file type '{ext}'. Supported: {', '.join(VALID_EXTENSIONS)}"
    return True, "File is valid."

def get_results(path):
    model = YOLO('yolo12n.pt')
    results = model(path)
    boxes = results[0].boxes
    if not boxes:
        return []
    detections = []
    for box in boxes:
        class_id = int(box.cls[0])
        detections.append({
            "label": results[0].names[class_id],
            "confidence": round(float(box.conf[0]), 2)
        })
    return detections
