from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import os
import time
import requests as http
from main import get_image_path, check_file_exists, detect_items, store_items, export_member_items, ROOMS, model, CROPS_BASE
from store import get_items as db_get_items, delete_item as db_delete_item, update_item as db_update_item, get_item_filepath, upsert_user

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Wix site ID — not a secret, matches wix.config.json
WIX_SITE_ID = os.environ.get('WIX_SITE_ID', '3728b0ed-c153-4a3a-af42-e556d24be992')
WIX_MEMBERS_URL = 'https://www.wixapis.com/members/v1/members/my'

# Short-lived cache: token → (member_id, expiry)
# Avoids calling Wix on every single request.
_token_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300  # seconds


def resolve_member_id(token: str) -> str | None:
    """
    Verify a Wix Bearer token by calling the Wix Members API.
    Returns the member_id if valid, None otherwise.
    No shared secret — Wix is the authoritative verifier.
    """
    now = time.time()

    # Return cached result if still fresh
    if token in _token_cache:
        member_id, expiry = _token_cache[token]
        if now < expiry:
            return member_id
        del _token_cache[token]

    try:
        resp = http.get(
            WIX_MEMBERS_URL,
            headers={
                'Authorization': f'Bearer {token}',
                'wix-site-id':   WIX_SITE_ID,
            },
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        member_id = resp.json().get('member', {}).get('id')
    except Exception:
        return None

    if member_id:
        _token_cache[token] = (member_id, now + CACHE_TTL)
        upsert_user(member_id)   # register member in DB on first seen

    return member_id


def get_member_id() -> str | None:
    """Extract and verify the Wix Bearer token from the Authorization header."""
    # Local dev bypass: set DEV_MEMBER_ID to skip Wix verification
    dev = os.environ.get('DEV_MEMBER_ID')
    if dev:
        upsert_user(dev)
        return dev
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    return resolve_member_id(auth[len('Bearer '):])


# Per-user upload tracking (keyed by member_id)
_uploaded: dict[str, str] = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Arcera YOLO API is running"})


@app.route('/upload', methods=['POST'])
def upload():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    if 'image' not in request.files:
        return jsonify({"error": "No file provided."}), 400
    file = request.files['image']
    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    _uploaded[member_id] = get_image_path(save_path)
    return jsonify({"message": f"Uploaded: {file.filename}", "path": save_path})


@app.route('/validate', methods=['POST'])
def validate():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    path = _uploaded.get(member_id)
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    return jsonify({"valid": valid, "message": message})


@app.route('/detect', methods=['POST'])
def detect():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    path = _uploaded.get(member_id)
    if not path:
        return jsonify({"error": "No file uploaded yet."}), 400
    valid, message = check_file_exists(path)
    if not valid:
        return jsonify({"error": message}), 400
    detections = detect_items(path)
    return jsonify({"detections": detections, "path": path})


@app.route('/store', methods=['POST'])
def store():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "No items provided."}), 400
    path = data.get("path") or _uploaded.get(member_id)
    if not path:
        return jsonify({"error": "No file path provided."}), 400
    try:
        store_items(member_id, data["items"], path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"message": f"Stored {len(data['items'])} items."})


@app.route('/member', methods=['GET'])
def member():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"member_id": member_id})


@app.route('/export/<member_id>', methods=['GET'])
def export(member_id):
    requester = get_member_id()
    if not requester:
        return jsonify({"error": "Unauthorized"}), 401
    if requester != member_id:
        return jsonify({"error": "Forbidden"}), 403
    try:
        csv_path = export_member_items(member_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return send_file(csv_path, as_attachment=True, download_name=f"{member_id}_items.csv")


@app.route('/items', methods=['GET'])
def list_items():
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    rows = db_get_items(member_id)
    items = []
    for row in rows:
        room_id = row.get("room_id")
        crop_filename = row.get("crop_path")
        crop_data = row.get("crop_data")
        # Prefer base64 (persists across restarts); fall back to file URL for
        # when cloud storage is wired up via crop_path.
        crop_url = crop_data or (f"/crops/{member_id}/{crop_filename}" if crop_filename else None)
        yolo_label = model.names.get(row["class_id"], f"class_{row['class_id']}")
        items.append({
            "id":           row["id"],
            "class_id":     row["class_id"],
            "label":        row.get("name") or yolo_label,
            "description":  row.get("description") or None,
            "purchase_year": row["purchase_year"],
            "cost":         row["cost"],
            "count":        row.get("count") or 1,
            "room":         ROOMS[room_id - 1] if room_id and 1 <= room_id <= len(ROOMS) else "Unknown",
            "room_id":      room_id,
            "crop_url":     crop_url,
            "bbox":         [row["x1"], row["y1"], row["x2"], row["y2"]] if row["x1"] is not None else None,
            "duplicate_of": row["duplicate_of"],
            "created_at":   row["created_at"],
        })
    return jsonify({"items": items})


@app.route('/crops/<member_id>/<filename>', methods=['GET'])
def serve_crop(member_id, filename):
    requester = get_member_id()
    if not requester:
        return jsonify({"error": "Unauthorized"}), 401
    if requester != member_id:
        abort(403)
    crop_path = os.path.join(CROPS_BASE, member_id, filename)
    if not os.path.isfile(crop_path):
        abort(404)
    return send_file(crop_path, mimetype='image/jpeg')


@app.route('/photo/<int:item_id>', methods=['GET'])
def serve_photo(item_id):
    member_id = get_member_id()
    if not member_id:
        return jsonify({"error": "Unauthorized"}), 401
    filepath = get_item_filepath(item_id)
    if not filepath or not os.path.isfile(filepath):
        abort(404)
    return send_file(filepath)


@app.route('/items/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    if not get_member_id():
        return jsonify({"error": "Unauthorized"}), 401
    db_delete_item(item_id)
    return jsonify({"message": "Deleted."})


@app.route('/items/<int:item_id>', methods=['PUT'])
def edit_item(item_id):
    if not get_member_id():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400
    name = data.get("name")
    if name is not None:
        name = name.strip() or None
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
