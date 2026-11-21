# React Control Center

The live meter dashboard now has a React/Vite frontend and a FastAPI backend. The existing Streamlit entry point remains available as a legacy prototype; it is not required for the React interface.

## Architecture
- React + Vite: responsive industrial control-center UI, 8 station cards, live frame refresh, trigger actions and calibration drawer.
- FastAPI: local API on 127.0.0.1:8000.
- Python/OpenCV/EasyOCR: all image capture and recognition stays on the PC.
- ESP32-CAM: unchanged CameraWebServer firmware, local HTTP MJPEG stream.
- No cloud, MQTT or internet connection is required for the camera-to-PC data path. Google Fonts in the stylesheet are optional; the interface falls back to local system fonts if offline.

## Windows setup
Terminal 1 — backend, from the repository root:
```powershell
.venv\Scripts\activate
pip install -r requirements-pc.txt
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:
```powershell
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173

## Notes
- Configure the eight independent camera stream URLs in `configs/camera_channels.json`.
- The dashboard displays each camera's configured IP as a clickable link to its raw MJPEG stream.
- The API creates one MJPEG reader for each unique stream URL. The recommended offline deployment has eight ESP32-CAM devices joining the laptop's single Mobile Hotspot, each with a unique static IP.
- The backend reads camera configuration at startup; restart Uvicorn after changing camera IPs or stream URLs.
- Follow `docs/eight_camera_local_http_architecture.md` and flash `esp32_cam/WaterMeterVision_HTTP_Stream/WaterMeterVision_HTTP_Stream.ino` with a unique `CAMERA_INDEX` on each camera.
- Trigger All processes the latest available frame for each logical channel using the configured worker count. EasyOCR access is serialized for stability.
- Calibration is held in API memory for the current process and resets when the backend restarts.
- Current OCR and rotary-dial estimates are experimental and are not approved for billing.
