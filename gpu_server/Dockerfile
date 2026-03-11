FROM ultralytics/ultralytics:latest

WORKDIR /app

# Install Flask + onnxruntime-gpu (base already has CUDA, cuDNN, PyTorch, ultralytics)
COPY gpu_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Detection server
COPY gpu_server/detect_server.py /app/detect_server.py

# Model files (baked in — update models by rebuilding the image)
COPY backend/best.onnx /app/best.onnx
COPY backend/yolo12n.pt /app/yolo12n.pt

# Tell detect_server.py where the models live
ENV CUSTOM_MODEL_PATH=/app/best.onnx
ENV COCO_MODEL_PATH=/app/yolo12n.pt

# Default PORT to 8080 (matches Cloud Run convention)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "detect_server.py"]
