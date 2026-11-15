# WaterMeterVision — ESP32-CAM standalone firmware

This is a separate embedded target inside the repository. The existing PC application, scripts, Python requirements and PC calibration workflow are not changed by the ESP32-CAM work.

## Runtime architecture

Target: **AI Thinker ESP32-CAM + OV2640**.

- All capture and image processing run on the ESP32-CAM.
- No Python, Streamlit, PC inference, cloud, HTTP server, web page or dashboard is used at runtime.
- Serial Monitor is only the development/debug output channel. The final standalone unit can run without a PC attached.
- The firmware uses the Arduino ESP32 camera driver (`esp_camera.h`) and JPEG-to-RGB conversion.

## Current implementation status

### Implemented in firmware
1. AI Thinker OV2640 pin configuration.
2. Arduino ESP32 core 2.x / 3.x SCCB field-name compatibility.
3. QVGA JPEG camera capture.
4. PSRAM/RAM RGB888 buffer allocation.
5. JPEG-to-RGB888 conversion.
6. Experimental red-pixel angular histogram for each configured dial ROI.
7. Optional angle-to-digit conversion using a per-dial zero-angle and direction.
8. Conservative output: no final reading is printed while required calibration/model components are missing.

### Not implemented / not validated yet
- The five black digits do not have an ESP32-compatible trained model artifact yet.
- No TFLite Micro model or quantized model weights are included.
- The four dial centers/radii and zero-angle/direction are not calibrated for the final ESP32-CAM mounting.
- The red-pixel detector is a first heuristic; it can confuse red printed scale marks/reflections with the pointer.
- No physical-board compile/upload/test has been performed by the repository editor.
- Therefore this firmware does **not** yet produce a validated meter reading.

## Arduino IDE setup

1. Install Espressif's **esp32** board package in Boards Manager.
2. Open `WaterMeterVision_ESP32CAM/WaterMeterVision_ESP32CAM.ino`.
3. Select **AI Thinker ESP32-CAM**.
4. Enable **PSRAM** when the board menu exposes the option.
5. Select the correct COM port.
6. Upload using a stable 5V USB-to-UART adapter.
7. Open Serial Monitor at **115200 baud**.

Upload mode:
- Connect GPIO0 to GND.
- Reset the board and upload.
- After upload, disconnect GPIO0 from GND and reset again.

UART wiring:
- USB-UART TX -> U0R / GPIO3
- USB-UART RX -> U0T / GPIO1
- GND -> GND
- Stable 5V -> 5V

Use a supply that can handle the camera's current peaks. Do not power the board from a weak 3.3V UART adapter output.

## Current source layout

```text
esp32_cam/
├── README.md
└── WaterMeterVision_ESP32CAM/
    ├── WaterMeterVision_ESP32CAM.ino
    ├── config/
    │   └── meter_config.h
    ├── vision/
    │   ├── red_pointer_detector.h
    │   └── red_pointer_detector.cpp
    └── meter/
        ├── reading_engine.h
        └── reading_engine.cpp
```

## Calibration gate

Edit `WaterMeterVision_ESP32CAM/config/meter_config.h` only after the camera is rigidly mounted and its actual QVGA frame geometry is known.

- Set `METER_GEOMETRY_CALIBRATED = true` only after entering the register/dial geometry measured in the ESP32-CAM frame.
- Set each dial's normalized center and radius in `ROTARY_DIALS`.
- Set `ROTARY_ANGLE_CALIBRATED = true` only after measuring the exact angle that corresponds to digit zero and confirming the direction of increasing values for each dial.
- Do not copy normalized coordinates from `configs/reference_presets.json`: those coordinates belong to the two PC photographs and are not guaranteed to match the ESP32-CAM framing.
- Keep `DIGIT_MODEL_AVAILABLE = false` until a real compatible model is added and tested.

A rotary digit is calculated as one of ten equal divisions around a revolution after its zero-angle and direction are calibrated. This is only a geometric estimate; the physical dial scale, pointer shape, perspective and reading convention must be confirmed before use.

## Next engineering milestones

1. Fix the camera mount, focus, distance, lighting and orientation.
2. Establish a safe way to inspect the exact ESP32-CAM frame and measure normalized ROIs.
3. Validate red-pointer detection on each dial under real lighting; add pointer-specific shape/radial filtering and reject ambiguous detections.
4. Port the existing TinyDigitCNN only after a verified labeled dataset and trained checkpoint exist; convert/quantize it for TensorFlow Lite Micro and benchmark flash, PSRAM, tensor arena and latency.
5. Implement wheel-transition handling, dial rollover rules and full reading validation.
6. Run repeated tests on the physical meter and report exact-match rate, litre error and false-accept rate.

## Why the pipeline is conservative

The two original reference photos show the same physical meter and are useful for photo-specific calibration, but they do not provide a general 0–9 digit training dataset or full angular calibration. The provisional reference reading `00000.0899 m³` is not model-verified ground truth. The firmware therefore reports `NEEDS REVIEW` instead of inventing missing digits or dial values.

## Camera driver reference

The Arduino ESP32 core already includes `esp_camera.h`; no separate camera library installation is normally required.

- https://github.com/espressif/esp32-camera
