# ESP32-CAM live-stream demo (PC-side processing)

This demo keeps the standard Arduino IDE **CameraWebServer** firmware on the ESP32-CAM. The ESP32 only streams JPEG video; all meter OCR and rotary analysis run on the PC.

## Camera URL

The camera web page may be reachable at `http://192.168.137.222`. For the standard Espressif Arduino CameraWebServer example, the MJPEG endpoint is normally `http://192.168.137.222:81/stream`. Open the stream URL in a browser on the same LAN first. If your firmware fork uses another endpoint, enter its actual stream URL in the sidebar.

## Install (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-pc.txt
```

EasyOCR may download pretrained weights on first use. Run once with internet if the PC must later work offline.

## Run

```powershell
streamlit run live_app.py
```

Open the Streamlit URL, normally `http://localhost:8501`.

## Calibrate the mounted camera

1. Point the camera straight at the meter and keep the meter/camera fixed.
2. Adjust the four Register sliders so the green rectangle covers only the five black odometer windows.
3. Adjust the four dial centers and radii to fit the printed rotary dials.
4. Confirm the overlay stays aligned in the live video.
5. Press **TRIGGER — READ METER**. The app copies the newest frame and runs EasyOCR plus OpenCV on the PC.

The live capture thread retains only the newest frame, preventing a growing queue of stale frames. The video panel refreshes continuously; CV runs only on button press.

## Limitations

- The digit recognizer is pretrained general-purpose EasyOCR, not a custom-trained meter model.
- The pointer detector is a heuristic red-pixel detector.
- Current dial values assume zero at 12 o'clock and clockwise increase. Actual zero-angle mapping must be calibrated separately for each dial.
- A candidate total is displayed only if exactly five digits and all four pointers pass the current heuristic threshold.
- This is an experimental demo, not a validated billing system.

## Troubleshooting

- If the root page works but `/stream` fails, verify the firmware stream endpoint and port 81.
- Confirm the PC and ESP32-CAM are on the same local network.
- If OpenCV cannot decode the stream, test the URL in a browser or VLC and check Windows Firewall.
- If the video is unstable, lower the camera frame size or JPEG quality in CameraWebServer.
- Old still-photo presets are only starting points. Calibrate the ROIs using the actual live camera framing.
