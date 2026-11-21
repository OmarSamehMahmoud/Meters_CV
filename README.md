# WaterMeterVision

PC-first computer-vision system for reading a fixed family of mechanical water meters, targeting **AI Thinker ESP32-CAM + OV2640**.

## 8-camera offline streaming setup

The recommended deployment uses the laptop's Windows Mobile Hotspot as one private local Wi-Fi network (internet is not required). All eight ESP32-CAM devices join this network with unique static IPs and expose independent MJPEG streams. The PC runs React, FastAPI, OpenCV and OCR; the ESP32-CAM devices only capture and stream video.

- Firmware: [esp32_cam/WaterMeterVision_HTTP_Stream](esp32_cam/WaterMeterVision_HTTP_Stream/WaterMeterVision_HTTP_Stream.ino)
- Eight-camera IP/URL configuration: [configs/camera_channels.json](configs/camera_channels.json)
- Network setup and flashing guide: [docs/eight_camera_local_http_architecture.md](docs/eight_camera_local_http_architecture.md)
- React dashboard setup: [docs/react_control_center.md](docs/react_control_center.md)

Example IPs are `192.168.137.201`–`192.168.137.208`; confirm the laptop hotspot gateway/subnet with `ipconfig` and check that these addresses are unused before flashing.

## React control center

Backend:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-pc.txt
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The eight camera cards show independent streams and expose their direct stream links. The backend loads camera URLs from `configs/camera_channels.json` at startup; restart it after changing the configuration.

## Important accuracy note

The current OCR and rotary-dial estimates are experimental. Dial zero-angle calibration, rollover logic and end-to-end accuracy are not validated. Do not use these readings for billing without a verified dataset and full system validation.
