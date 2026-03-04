from ultralytics import YOLO

_model = None


def get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO('yolo12n.pt')
    return _model
