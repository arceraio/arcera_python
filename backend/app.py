from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from main import get_image_path, check_file_exists, detect_and_store_items, export_member_items, MEMBER_ID

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
    # member_id = request.headers.get('X-Member-ID', '')  # swap in when Wix auth is live
    detections = detect_and_store_items(path, MEMBER_ID)
    return jsonify({"detections": detections})

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


if __name__ == '__main__':
    app.run(debug=True)
