from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import os
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS, CROPS_BASE
from yolo_model import get_model
from store import get_items as db_get_items, delete_item as db_delete_item, update_item as db_update_item, get_item_filepath
from supabase_client import get_supabase
from auth import get_member_id

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

uploaded_file_path = {"path": None}

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Arcera YOLO API is running"})


@app.route('/supabase/health', methods=['GET'])
def supabase_health():
    try:
        get_supabase()
        return jsonify({"status": "ok", "message": "Supabase connected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "No items provided."}), 400
    path = data.get("path") or uploaded_file_path.get("path")
    if not path:
        return jsonify({"error": "No file path provided."}), 400
    try:
        store_items(member_id, data["items"], path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"message": f"Stored {len(data['items'])} items."})

@app.route('/member', methods=['GET'])
def member():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    return jsonify({"member_id": member_id})


@app.route('/export', methods=['GET'])
def export():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    try:
        csv_path = export_member_items(member_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return send_file(csv_path, as_attachment=True, download_name=f"{member_id}_items.csv")


@app.route('/items', methods=['GET'])
def list_items():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    rows = db_get_items(member_id)
    items = []
    for row in rows:
        room_id = row.get("room_id")
        crop_filename = row.get("crop_path")
        crop_url = f"/crops/{member_id}/{crop_filename}" if crop_filename else None
        yolo_label = get_model().names.get(row["class_id"], f"class_{row['class_id']}")
        items.append({
            "id": row["id"],
            "class_id": row["class_id"],
            "label": row.get("name") or yolo_label,
            "description": row.get("description") or None,
            "purchase_year": row["purchase_year"],
            "cost": row["cost"],
            "count": row.get("count") or 1,
            "room": ROOMS[room_id - 1] if room_id and 1 <= room_id <= len(ROOMS) else "Unknown",
            "room_id": room_id,
            "crop_url": crop_url,
            "bbox": [row["x1"], row["y1"], row["x2"], row["y2"]] if row["x1"] is not None else None,
            "duplicate_of": row["duplicate_of"],
            "created_at": row["created_at"],
        })
    return jsonify({"items": items})


@app.route('/crops/<member_id>/<filename>', methods=['GET'])
def serve_crop(member_id, filename):
    crop_path = os.path.join(CROPS_BASE, member_id, filename)
    if not os.path.isfile(crop_path):
        abort(404)
    return send_file(crop_path, mimetype='image/jpeg')


@app.route('/photo/<int:item_id>', methods=['GET'])
def serve_photo(item_id):
    filepath = get_item_filepath(item_id)
    if not filepath or not os.path.isfile(filepath):
        abort(404)
    return send_file(filepath)


@app.route('/items/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    db_delete_item(item_id)
    return jsonify({"message": "Deleted."})


@app.route('/items/<int:item_id>', methods=['PUT'])
def edit_item(item_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400
    name = data.get("name")
    if name is not None:
        name = name.strip() or None  # empty string → clear custom name
    description = data.get("description")
    if description is not None:
        description = description.strip() or None
    db_update_item(item_id,
                   purchase_year=data.get("purchase_year"),
                   cost=data.get("cost"),
                   name=name,
                   description=description,
                   count=data.get("count"),
                   room_id=data.get("room_id"))
    return jsonify({"message": "Updated."})


if __name__ == '__main__':
    app.run(debug=True)
