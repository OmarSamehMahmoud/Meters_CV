# WaterMeterVision — ESP32-CAM

This directory contains the embedded firmware track for the WaterMeterVision project.

## Runtime requirement

The final meter-reading solution is intended to run locally on an **AI Thinker ESP32-CAM with OV2640**.

- No PC inference at runtime
- No Python or Streamlit on the device
- No HTTP server, web dashboard, or browser UI
- No cloud service
- Local image processing and reading on the ESP32-CAM
- Serial Monitor is used for development diagnostics and reading output

The existing PC application and its dependencies remain unchanged in the repository. The ESP32-CAM firmware is kept isolated under this directory.

## Current status

### Phase 1 — Camera bring-up

The Arduino sketch currently:
1. Initializes the AI Thinker OV2640 camera.
2. Reports free heap and PSRAM information.
3. Captures a QVGA JPEG frame every five seconds.
4. Reports frame dimensions and byte count to Serial Monitor.

**This is a camera validation firmware, not yet a meter-reading model.** It deliberately does not print a fabricated meter value.

## Arduino IDE setup

1. Install the ESP32 board package from Espressif's Boards Manager.
2. Open the WaterMeterVision_ESP32CAM.ino sketch.
3. Select **AI Thinker ESP32-CAM**.
4. Enable PSRAM if the selected Arduino core exposes that setting.
5. Select the correct COM port.
6. Upload using an FTDI/USB-to-UART adapter.
7. Open Serial Monitor at **115200 baud**.

For upload mode, connect GPIO0 to GND, reset the board, upload, then disconnect GPIO0 from GND and reset again.

Typical USB-to-UART wiring:
- Adapter TX -> ESP32-CAM U0R (GPIO3)
- Adapter RX -> ESP32-CAM U0T (GPIO1)
- Adapter GND -> ESP32-CAM GND
- Adapter 5V -> ESP32-CAM 5V (use a stable supply capable of camera current peaks)

Do not connect the adapter's 3.3V output to the board's 5V input. Ensure a common ground.

## Repository layout

    esp32_cam/
    ├── README.md
    └── WaterMeterVision_ESP32CAM/
        └── WaterMeterVision_ESP32CAM.ino

## Planned embedded pipeline

1. Camera capture and image-quality checks.
2. Meter/register ROI calibration for the exact NWM SJ-LFC / SJ-WDC meter.
3. Five black-digit segmentation and recognition.
4. Four red rotary-pointer detections and angle-to-digit conversion.
5. Reading validation, confidence and a Needs Review state.
6. Serial output of the final reading and structured diagnostics.

The algorithms must be ported or reimplemented for ESP32 memory and CPU constraints. The PC's EasyOCR/OpenCV/Streamlit runtime is not copied onto the ESP32.

## Camera driver

The Arduino ESP32 core includes esp_camera.h from Espressif; a separate camera library installation is normally not required.

Reference: https://github.com/espressif/esp32-camera
