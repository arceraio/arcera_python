from ultralytics import YOLO
import os

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

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

def get_image_path(path):
    return path.strip()

def check_file_exists(path):
    if not os.path.isfile(path):
        return False, "File not found."
    ext = os.path.splitext(path)[1].lower()
    if ext not in VALID_EXTENSIONS:
        return False, f"Invalid file type '{ext}'. Supported: {', '.join(VALID_EXTENSIONS)}"
    return True, "File is valid."

model = YOLO('yolo12n.pt')

def get_results(path):
    results = model(path)
    boxes = results[0].boxes
    if not boxes:
        return []
    items = []
    for box in boxes:
        class_id = int(box.cls[0])
        label = results[0].names[class_id]
        confidence = round(float(box.conf[0]), 2)
        purchase_year, cost, room_id = prompt_user_inputs(label)
        items.append({
            "class_id": class_id,
            "label": label,
            "confidence": confidence,
            "filepath": path,
            "purchase_year": purchase_year,
            "cost": cost,
            "room_id": room_id,
        })
    return items
