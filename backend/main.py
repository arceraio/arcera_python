from ultralytics import YOLO
import os
import uuid
from PIL import Image
from store import init_db, verify_member, create_item, find_duplicate
from export import export_to_csv

init_db()

MEMBER_ID = 'bc3abe70-a86a-4fdb-ab75-20f13cba66bb'  # replace with Wix session member ID later

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

model = YOLO('yolo12n.pt')

CROPS_BASE = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'crops')

def export_member_items(member_id):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")
    return export_to_csv(member_id)


def detect_items(path):
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


def store_items(member_id, items, filepath):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")

    member_crops_dir = os.path.join(CROPS_BASE, member_id)
    os.makedirs(member_crops_dir, exist_ok=True)

    img = Image.open(filepath)

    for item in items:
        bbox = item.get("bbox")
        x1, y1, x2, y2 = bbox if bbox else (None, None, None, None)

        duplicate_of = None
        if bbox:
            duplicate_of = find_duplicate(member_id, item["class_id"], x1, y1, x2, y2)

        crop_filename = None
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
            crop_filename = f"{uuid.uuid4().hex}_crop.jpg"
            crop.save(os.path.join(member_crops_dir, crop_filename), "JPEG")

        yolo_label = model.names.get(item["class_id"], f"class_{item['class_id']}")
        create_item(
            member_id,
            item["class_id"],
            item["purchase_year"],
            item["cost"],
            filepath,
            item["room_id"],
            name=yolo_label,
            crop_path=crop_filename,
            x1=x1, y1=y1, x2=x2, y2=y2,
            duplicate_of=duplicate_of,
        )
