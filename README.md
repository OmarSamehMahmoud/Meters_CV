# RAGURA WM — Intelligent Meter Reading Platform

**RAGURA WM by PhotonX** is an offline-first, PC-based meter-reading platform. ESP32-CAM devices provide local HTTP/MJPEG video streams; the PC handles image processing, calibration, recognition and review through a React + FastAPI application.

## Current architecture

- **Camera layer:** ESP32-CAM over a private local Wi-Fi network; HTTP/MJPEG only.
- **Processing layer:** Python, FastAPI and OpenCV on the PC.
- **Operator interface:** React + Vite dashboard.
- **Recognition:** pretrained TensorFlow Lite digit and analog models from AI-on-the-edge-device v16.1.0, executed locally on the PC through LiteRT. The ESP32-CAM only streams frames.
- **Storage:** Per-channel ROI and dial calibration is persisted locally in `data/meter_calibrations.json`.
- **Connectivity:** No cloud, MQTT or internet dependency is required for the local workflow.

## Recognition Workbench

Open the **Recognition Workbench** from the left navigation to:
1. Select a meter channel.
2. Inspect its current camera frame with the configured digit-register and analog-dial regions overlaid.
3. Adjust normalized digit ROI coordinates.
4. Select each analog dial and adjust its center and radius.
5. Save calibration locally; it survives backend restarts.
6. Save the current camera frame as a per-meter geometric reference.
7. Trigger recognition; when a reference exists, ORB feature matching and RANSAC estimate a similarity transform and warp the live frame into reference coordinates before ROI extraction.
8. Inspect alignment match/inlier metrics and the candidate value, digit-model confidence and warning.

### Important implementation status

The live trigger now routes through the original pretrained AI-on-the-edge-device TFLite models. It does not silently fall back to EasyOCR or the earlier red-pixel dial heuristic. If the model files are not installed, the API reports `models_missing` and suppresses a candidate reading. The first integration uses the upstream 100-output continuous digit model and two-output analog model. Per-channel register/dial geometry still needs calibration and field validation. The current broad digit-register ROI is divided into equal-width cells; meters with uneven digit spacing will need individual digit ROI calibration in the next refinement. The SQLite review history and manual acceptance workflow remain in place. Do not use readings for billing until the exact meter type, alignment, ROI boundaries, dial direction and output accuracy are validated against labeled captures.

## AI-on-the-edge-device model setup

Install the LiteRT runtime and download the pinned upstream models once:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-pc.txt
python scripts/download_ai_edge_models.py
```

Models are stored under `models/ai-on-the-edge-device/v16.1.0`. After this one-time setup, the recognition inference is local/offline. Model readiness is available at `GET /api/recognition/models`. See [docs/ai_on_the_edge_pc_integration.md](docs/ai_on_the_edge_pc_integration.md) for the model and calibration details.

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

The PC inference adapter uses the upstream AI-on-the-edge-device pretrained TFLite model files downloaded by the user from the official v16.1.0 repository. The upstream license remains applicable to those model files; see [docs/ai_on_the_edge_pc_integration.md](docs/ai_on_the_edge_pc_integration.md) before redistribution or commercial deployment.

## Brand

**RAGURA WM** · **PhotonX**  
Copyright © 2026 — PhotonX
