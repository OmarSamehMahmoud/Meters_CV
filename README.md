# RAGURA — Intelligent Meter Reading Platform

**RAGURA by PhotonX** is an offline-first, PC-based meter-reading platform. ESP32-CAM devices provide local HTTP/MJPEG video streams; the PC handles image processing, calibration, recognition and review through a React + FastAPI application.

## Current architecture

- **Camera layer:** ESP32-CAM over a private local Wi-Fi network; HTTP/MJPEG only.
- **Processing layer:** Python, FastAPI and OpenCV on the PC.
- **Operator interface:** React + Vite dashboard.
- **Recognition currently implemented:** five independent EasyOCR crops across the configured five-digit register plus experimental red-pixel pointer estimation for the four analog dials.
- **Storage:** Per-channel ROI and dial calibration is persisted locally in `data/meter_calibrations.json`.
- **Connectivity:** No cloud, MQTT or internet dependency is required for the local workflow.

## Recognition Workbench

Open the **Recognition Workbench** from the left navigation to:
1. Select a meter channel.
2. Inspect its current camera frame with the configured digit-register and analog-dial regions overlaid.
3. Adjust normalized digit ROI coordinates.
4. Select each analog dial and adjust its center and radius.
5. Save calibration locally; it survives backend restarts.
6. Save the current camera frame as a per-meter geometric reference.\n7. Trigger recognition; when a reference exists, ORB feature matching and RANSAC estimate a similarity transform and warp the live frame into reference coordinates before ROI extraction.\n8. Inspect alignment match/inlier metrics and the candidate value, OCR confidence and warning.

### Important implementation status

The current recognition output is experimental. Digit recognition uses EasyOCR; analog pointer estimation uses red-pixel segmentation and configured dial geometry. **Reference-frame alignment is now implemented** using ORB descriptors, ratio-filtered feature matches, RANSAC similarity-transform estimation and perspective-safe affine warping. It requires a saved reference frame for each meter; if alignment fails, the candidate reading is suppressed. Digit recognition now runs five independent EasyOCR passes over equal-width, slightly overlapping digit cells and exposes per-cell confidence/status; this remains OCR-based and is not a trained digit classifier. The equal-width assumption requires meter-specific calibration and validation. Pointer angle now uses per-dial configurable zero angle and direction, but its current detector still depends on red-pixel segmentation. Persistent SQLite reading history and manual acceptance are implemented. Validation checks the first accepted baseline and rejects decreasing readings; meter rollover/reset and configurable maximum-flow checks are not implemented. The workbench labels this status explicitly. Do not use current candidate values for billing or operational decisions without a verified dataset and end-to-end validation.

## Offline camera network

The recommended deployment uses the laptop's Windows Mobile Hotspot as one private local Wi-Fi network. Each ESP32-CAM joins the network and exposes an independent MJPEG stream. The PC performs all recognition; cameras only capture and stream video.

- Firmware: [esp32_cam/WaterMeterVision_HTTP_Stream](esp32_cam/WaterMeterVision_HTTP_Stream/WaterMeterVision_HTTP_Stream.ino)
- Camera IP/URL configuration: [configs/camera_channels.json](configs/camera_channels.json)
- Network setup: [docs/eight_camera_local_http_architecture.md](docs/eight_camera_local_http_architecture.md)
- React dashboard setup: [docs/react_control_center.md](docs/react_control_center.md)

Example IPs are `192.168.137.201`–`192.168.137.208`; confirm the laptop hotspot gateway/subnet with `ipconfig` and check that addresses are unused before assigning them.

**Current bench setup:** the dashboard supports eight logical meter channels. When configured in shared-stream demo mode, those channels display the same physical ESP32-CAM feed while retaining separate meter IDs and calibration. This is not equivalent to eight independent cameras.

## Run locally (Windows PowerShell)

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

Open `http://127.0.0.1:5173`.

## Reference and implementation boundary

The product workflow takes inspiration from established analog-meter digitization patterns such as image capture, geometric calibration, region extraction, recognition and reading validation. RAGURA's implementation is developed independently; no third-party source code or model weights are bundled from those projects.

## Brand

**RAGURA** · **PhotonX**  
Copyright © 2026 — PhotonX
