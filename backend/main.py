from ultralytics import YOLO
import os
from store import init_db, verify_member, create_item
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

def export_member_items(member_id):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")
    return export_to_csv(member_id)


# detect the items in the image and store them in the database
def detect_and_store_items(path, member_id):
    if not verify_member(member_id):
        raise ValueError(f"Member '{member_id}' not found in database.")

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

        create_item(member_id, class_id, purchase_year, cost, path, room_id)

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
