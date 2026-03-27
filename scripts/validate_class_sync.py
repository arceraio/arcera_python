#!/usr/bin/env python3
"""Assert that detect_server.py class constants match config.py."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gpu_server'))

from config import CUSTOM_CLASS_NAMES as BE_NAMES, COCO_CLASS_WHITELIST as BE_WL, CUSTOM_CLASS_OFFSET as BE_OFFSET
from detect_server import CUSTOM_CLASS_NAMES as GPU_NAMES, COCO_CLASS_WHITELIST as GPU_WL, CUSTOM_CLASS_OFFSET as GPU_OFFSET

errors = []
if BE_NAMES != GPU_NAMES:
    errors.append(f"CUSTOM_CLASS_NAMES mismatch:\n  backend: {BE_NAMES}\n  gpu:     {GPU_NAMES}")
if BE_WL != GPU_WL:
    errors.append(f"COCO_CLASS_WHITELIST mismatch:\n  backend: {BE_WL}\n  gpu:     {GPU_WL}")
if BE_OFFSET != GPU_OFFSET:
    errors.append(f"CUSTOM_CLASS_OFFSET mismatch: backend={BE_OFFSET}, gpu={GPU_OFFSET}")

if errors:
    print("CLASS CONFIG DRIFT DETECTED:")
    for e in errors: print(e)
    sys.exit(1)
else:
    print("OK — class configs in sync.")
