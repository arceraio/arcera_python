"""
Unit tests for remote_detect.py — mocks HTTP calls, no real server needed.
Run from repo root: ./venv/bin/python3 -m pytest test/test_remote_detect.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_service_url(monkeypatch):
    monkeypatch.setenv("YOLO_SERVICE_URL", "http://fake-gpu:8000")
    monkeypatch.setenv("DETECT_SERVICE_TIMEOUT", "5")


def test_remote_detect_returns_detections(tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "detections": [
            {"class_id": 102, "label": "chair", "confidence": 0.91, "bbox": [10, 20, 100, 200]}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        import importlib, config, remote_detect
        importlib.reload(config)
        importlib.reload(remote_detect)
        result = remote_detect.remote_detect(str(img))

    assert len(result) == 1
    assert result[0]["label"] == "chair"
    assert result[0]["class_id"] == 102


def test_remote_detect_raises_on_timeout(tmp_path):
    import requests as req, importlib, config, remote_detect
    importlib.reload(config)
    importlib.reload(remote_detect)
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    from errors import DetectionServiceError
    with patch("requests.post", side_effect=req.exceptions.Timeout):
        with pytest.raises(DetectionServiceError, match="timed out"):
            remote_detect.remote_detect(str(img))


def test_remote_detect_raises_on_connection_error(tmp_path):
    import requests as req, importlib, config, remote_detect
    importlib.reload(config)
    importlib.reload(remote_detect)
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fakejpeg")

    from errors import DetectionServiceError
    with patch("requests.post", side_effect=req.exceptions.ConnectionError):
        with pytest.raises(DetectionServiceError, match="unreachable"):
            remote_detect.remote_detect(str(img))


def test_detect_items_raises_when_no_service_url(monkeypatch):
    monkeypatch.delenv("YOLO_SERVICE_URL", raising=False)
    import importlib, config, main
    importlib.reload(config)
    importlib.reload(main)
    from errors import DetectionServiceError
    with pytest.raises(DetectionServiceError, match="No detection service configured"):
        main.detect_items("some/path.jpg")
