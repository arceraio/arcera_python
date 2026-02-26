from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, MEMBER_ID, ROOMS, model
from store import get_items as db_get_items, delete_item as db_delete_item, update_item as db_update_item

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

uploaded_file_path = {"path": None}

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Arcera YOLO API is running"})

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No file provided."}), 400
    file = request.files['image']
    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    uploaded_file_path["path"] = get_image_path(save_path)
    return jsonify({"message": f"Uploaded: {file.filename}", "path": save_path})

@app.route('/validate', methods=['POST'])
def validate():
    path = uploaded_file_path.get("path")
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    return jsonify({"valid": valid, "message": message})

@app.route('/detect', methods=['POST'])
def detect():
    path = uploaded_file_path.get("path")
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    if not valid:
        return jsonify({"error": message}), 400
    detections = detect_items(path)
    return jsonify({"detections": detections, "path": path})


@app.route('/store', methods=['POST'])
def store():
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "No items provided."}), 400
    path = data.get("path") or uploaded_file_path.get("path")
    if not path:
        return jsonify({"error": "No file path provided."}), 400
    try:
        store_items(MEMBER_ID, data["items"], path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"message": f"Stored {len(data['items'])} items."})

@app.route('/member', methods=['GET'])
def member():
    return jsonify({"member_id": MEMBER_ID})


@app.route('/export/<member_id>', methods=['GET'])
def export(member_id):
    try:
        csv_path = export_member_items(member_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return send_file(csv_path, as_attachment=True, download_name=f"{member_id}_items.csv")


@app.route('/items', methods=['GET'])
def list_items():
    rows = db_get_items(MEMBER_ID)
    items = []
    for row in rows:
        room_id = row.get("room_id")
        items.append({
            "id": row["id"],
            "label": model.names.get(row["class_id"], f"class_{row['class_id']}"),
            "purchase_year": row["purchase_year"],
            "cost": row["cost"],
            "room": ROOMS[room_id - 1] if room_id and 1 <= room_id <= len(ROOMS) else "Unknown",
            "room_id": room_id,
            "created_at": row["created_at"],
        })
    return jsonify({"items": items})


@app.route('/items/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    db_delete_item(item_id)
    return jsonify({"message": "Deleted."})


@app.route('/items/<int:item_id>', methods=['PUT'])
def edit_item(item_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400
    db_update_item(item_id, purchase_year=data.get("purchase_year"), cost=data.get("cost"))
    return jsonify({"message": "Updated."})


if __name__ == '__main__':
    app.run(debug=True)
