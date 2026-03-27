from flask import Flask, request, jsonify, send_file, abort, redirect
from flask_cors import CORS
import os
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS
from errors import DetectionServiceError
from yolo_model import get_combined_names
import uuid
from store import get_items as db_get_items, delete_item as db_delete_item, update_item as db_update_item, get_item_filepath, upsert_temp_photo, get_temp_photo, remove_from_temp_photo
from supabase_client import get_supabase
from auth import get_member_id
from storage import get_signed_url, upload_bytes

app = Flask(__name__)
CORS(app)

from config import UPLOAD_FOLDER, MIN_STORE_CONFIDENCE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

_member_upload_paths: dict = {}   # member_id → local path

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
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    if 'image' not in request.files:
        return jsonify({"error": "No file provided."}), 400
    file = request.files['image']
    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    _member_upload_paths[member_id] = get_image_path(save_path)
    return jsonify({"message": f"Uploaded: {file.filename}", "path": save_path})

@app.route('/validate', methods=['POST'])
def validate():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    path = _member_upload_paths.get(member_id)
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    return jsonify({"valid": valid, "message": message})

@app.route('/detect', methods=['POST'])
def detect():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    path = _member_upload_paths.get(member_id)
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    if not valid:
        return jsonify({"error": message}), 400
    try:
        detections = detect_items(path)
    except DetectionServiceError as e:
        return jsonify({"error": str(e)}), 503
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
    items = [it for it in data["items"] if (it.get("confidence") or 0) >= MIN_STORE_CONFIDENCE]
    if not items:
        return jsonify({"error": "No items met the minimum confidence threshold."}), 422
    path = data.get("path") or _member_upload_paths.get(member_id)
    if not path:
        return jsonify({"error": "No file path provided."}), 400
    original_storage_path = data.get("original_storage_path")
    try:
        store_items(member_id, items, path, original_storage_path=original_storage_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    if original_storage_path:
        remove_from_temp_photo(member_id, original_storage_path)
    return jsonify({"message": f"Stored {len(items)} items."})

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
        crop_path = row.get("crop_path")
        crop_url = get_signed_url(crop_path) if crop_path else None
        original_path = row.get("filepath")
        original_url = get_signed_url(original_path) if original_path else None
        yolo_label = get_combined_names().get(row["class_id"], f"class_{row['class_id']}")
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
            "original_url": original_url,
            "bbox": [row["x1"], row["y1"], row["x2"], row["y2"]] if row["x1"] is not None else None,
            "duplicate_of": row["duplicate_of"],
            "created_at": row["created_at"],
        })
    return jsonify({"items": items})


@app.route('/crops/<member_id>/<filename>', methods=['GET'])
def serve_crop(member_id, filename):
    try:
        requesting_member = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    if requesting_member != member_id:
        abort(403)
    signed = get_signed_url(f"crops/{member_id}/{filename}")
    if not signed:
        abort(404)
    return redirect(signed)


@app.route('/photo/<int:item_id>', methods=['GET'])
def serve_photo(item_id):
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    storage_path = get_item_filepath(item_id, member_id=member_id)
    if not storage_path:
        abort(404)
    signed = get_signed_url(storage_path)
    if not signed:
        abort(404)
    return redirect(signed)


@app.route('/items/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    try:
        get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    db_delete_item(item_id)
    return jsonify({"message": "Deleted."})


@app.route('/items/<int:item_id>', methods=['PUT'])
def edit_item(item_id):
    try:
        get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
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


@app.route('/multi-upload', methods=['POST'])
def multi_upload():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    files = request.files.getlist('images')
    if not files:
        return jsonify({"error": "No images provided."}), 400

    storage_paths, local_paths = [], []
    for file in files:
        uid = uuid.uuid4().hex
        ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
        local_path = os.path.join(UPLOAD_FOLDER, f"{uid}{ext}")
        file.save(local_path)
        storage_path = f"originals/{member_id}_{uid}{ext}"
        with open(local_path, "rb") as f:
            upload_bytes(storage_path, f.read(), f"image/{ext.lstrip('.')}")
        storage_paths.append(storage_path)
        local_paths.append(local_path)

    upsert_temp_photo(member_id, storage_paths, local_paths)
    return jsonify({"count": len(files), "storage_paths": storage_paths})


@app.route('/multiscan', methods=['POST'])
def multiscan():
    try:
        member_id = get_member_id()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    row = get_temp_photo(member_id)
    if not row or not row.get("img_url"):
        return jsonify({"error": "No staged images found."}), 404

    local_paths   = row.get("local_paths") or []
    storage_paths = row.get("img_url")     or []
    results = []
    for local_path, storage_path in zip(local_paths, storage_paths):
        try:
            detections = detect_items(local_path)
        except DetectionServiceError as e:
            return jsonify({"error": str(e)}), 503
        results.append({
            "local_path":   local_path,
            "storage_path": storage_path,
            "detections":   detections,
        })
    return jsonify({"results": results})


if __name__ == '__main__':
    app.run(debug=True)
