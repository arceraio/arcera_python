"""
Smoke tests for detect_server.py — verifies routes exist, no real models loaded.
Run from repo root: ./venv/bin/python3 -m pytest test/test_detect_server.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gpu_server'))

import pytest
from unittest.mock import patch


@pytest.fixture
def client():
    with patch("detect_server.get_combined_names", return_value={}):
        import detect_server
        detect_server.app.config["TESTING"] = True
        yield detect_server.app.test_client()


def test_health_route(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_detect_returns_400_with_no_image(client):
    r = client.post("/detect")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_detect_returns_detections(client, tmp_path):
    import io
    with patch("detect_server.run_detection", return_value=[
        {"class_id": 102, "label": "chair", "confidence": 0.91, "bbox": [10, 20, 100, 200]}
    ]):
        data = {"image": (io.BytesIO(b"fakejpeg"), "test.jpg")}
        r = client.post("/detect", data=data, content_type="multipart/form-data")

    assert r.status_code == 200
    body = r.get_json()
    assert "detections" in body
    assert body["detections"][0]["label"] == "chair"
