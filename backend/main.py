import os
import io
import uuid
import logging
from PIL import Image
from store import init_db, verify_member, create_item, find_duplicate, find_item_in_room, update_item
from export import export_to_csv
from yolo_model import get_model
from storage import upload_bytes


class DetectionUnavailableError(RuntimeError):
    """Raised when both the remote YOLO service and the local model fail."""
    pass

init_db()


VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

# rooms are the rooms in the house that the user can select from
ROOMS = [
    "Living Room",
    "Bedroom",
    "Kitchen",
    "Bathroom",
    "Dining Room",
    "Office",
    "Garage",
    "Other",
]

# prompt the user for the purchase year, cost, and room during the detection, and aims to create an item to store in the database
def prompt_user_inputs(label):
    print(f"\nDetected: {label}")

    while True:
        try:
            purchase_year = int(input("  Purchase year: "))
            break
        except ValueError:
            print("  Enter a valid year.")

    while True:
        try:
            cost = float(input("  Cost ($): "))
            break
        except ValueError:
            print("  Enter a valid cost.")

    print("  Select a room:")
    for i, room in enumerate(ROOMS, 1):
        print(f"    {i}. {room}")
    while True:
        try:
            selection = int(input("  Room number: "))
            if 1 <= selection <= len(ROOMS):
                break
            print(f"  Enter a number between 1 and {len(ROOMS)}.")
        except ValueError:
            print("  Enter a valid number.")

    return purchase_year, cost, selection

# get the image path from the uploaded file
def get_image_path(path):
    return path.strip()

# check if the file exists and is a valid image
def check_file_exists(path):
    if not os.path.isfile(path):
        return False, "File not found."
    ext = os.path.splitext(path)[1].lower()
    if ext not in VALID_EXTENSIONS:
        return False, f"Invalid file type '{ext}'. Supported: {', '.join(VALID_EXTENSIONS)}"
    return True, "File is valid."

def export_member_items(member_id):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")
    return export_to_csv(member_id)


def detect_items(path):
    model = get_model()

    # ── remote path ───────────────────────────────────────────────────────────
    remote_url = os.environ.get("YOLO_SERVICE_URL")
    if remote_url:
        try:
            from remote_detect import remote_detect
            name_to_id = {v: k for k, v in model.names.items()}
            return remote_detect(path, name_to_id)
        except Exception as exc:
            logging.warning("Remote YOLO service failed (%s), falling back to local model.", exc)

    # ── local path ────────────────────────────────────────────────────────────
    try:
        results = model(path)
        boxes = results[0].boxes
        if not boxes:
            return []

        items = []
        for box in boxes:
            class_id = int(box.cls[0])
            label = results[0].names[class_id]
            confidence = round(float(box.conf[0]), 2)
            x1, y1, x2, y2 = [round(float(v)) for v in box.xyxy[0]]
            items.append({
                "class_id": class_id,
                "label": label,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
            })
        return items
    except Exception as exc:
        raise DetectionUnavailableError(
            "Detection failed: the remote YOLO service is unreachable and the local "
            f"model also failed to run. Remote URL configured: {bool(remote_url)}. "
            f"Local error: {exc}"
        ) from exc


def store_items(member_id, items, filepath, original_storage_path=None):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")

    if original_storage_path is None:
        upload_uuid = uuid.uuid4().hex
        ext = os.path.splitext(filepath)[1].lower() or ".jpg"
        original_storage_path = f"originals/{member_id}_{upload_uuid}{ext}"
        with open(filepath, "rb") as f:
            upload_bytes(original_storage_path, f.read(), f"image/{ext.lstrip('.')}")

    img = Image.open(filepath)

    # Group detections by class_id — same class in one image → one item with count
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in items:
        grouped[item["class_id"]].append(item)

    for class_id, group in grouped.items():
        # Use highest-confidence detection as the representative
        item = max(group, key=lambda x: x.get("confidence", 0))
        count = len(group)

        # If an item of this class already exists in the same room, just add to its count
        existing = find_item_in_room(member_id, class_id, item["room_id"])
        if existing:
            update_item(existing["id"], count=(existing.get("count") or 1) + count)
            continue

        bbox = item.get("bbox")
        x1, y1, x2, y2 = bbox if bbox else (None, None, None, None)

        duplicate_of = None
        if bbox:
            duplicate_of = find_duplicate(member_id, item["class_id"], x1, y1, x2, y2)

        yolo_label = get_model().names.get(item["class_id"], f"class_{item['class_id']}")
        item_id = create_item(
            member_id,
            item["class_id"],
            item["purchase_year"],
            item["cost"],
            original_storage_path,
            item["room_id"],
            name=yolo_label,
            crop_path=None,
            x1=x1, y1=y1, x2=x2, y2=y2,
            duplicate_of=duplicate_of,
            count=count,
        )

        if bbox:
            bbox_area = (x2 - x1) * (y2 - y1)
            img_area  = img.width * img.height
            pad_ratio = 1.6 if (bbox_area / img_area) < 0.05 else 1
            pad_x = int((x2 - x1) * pad_ratio)
            pad_y = int((y2 - y1) * pad_ratio)
            cx1 = max(0, x1 - pad_x)
            cy1 = max(0, y1 - pad_y)
            cx2 = min(img.width,  x2 + pad_x)
            cy2 = min(img.height, y2 + pad_y)
            crop = img.crop((cx1, cy1, cx2, cy2))
            buf = io.BytesIO()
            crop.save(buf, "JPEG")
            crop_storage_path = f"crops/{member_id}_{item_id}_crop.jpg"
            upload_bytes(crop_storage_path, buf.getvalue(), "image/jpeg")
            update_item(item_id, crop_path=crop_storage_path)
