# AI Thinker ESP32-CAM firmware plan

Board target: AI Thinker ESP32-CAM + OV2640.

## First firmware milestone
- Use ESP-IDF camera driver / esp32-camera component.
- Capture JPEG at VGA initially; verify framing and focus before increasing resolution.
- Keep camera fixed in a rigid mount with diffuse illumination.
- Send JPEG frames to the PC validation service over HTTP during dataset collection.
- Log free heap, PSRAM, frame size, capture time and Wi-Fi RSSI.

## On-device inference gate
Do not port a model until the PC model is trained and validated. Benchmark tensor arena, stack, heap, flash and latency on the exact board. The first candidate is fixed-ROI processing plus a compact int8 digit classifier; avoid YOLO on the original ESP32-CAM. Low-confidence readings must be rejected.
