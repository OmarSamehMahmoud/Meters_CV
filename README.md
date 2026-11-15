# WaterMeterVision

PC-first computer-vision system for reading a fixed family of mechanical water meters, targeting **AI Thinker ESP32-CAM + OV2640**.

Repository: https://github.com/OmarSamehMahmoud/Meters_CV

## Target meter

The reference meter has five black odometer wheels for the integer m³ register and four red pointer dials for fractional precision. The dial labels/order and pointer rotation convention must be confirmed against a straight-on capture and the meter specification before precision readings are reconstructed.

## Current repository contents

- `src/watermeter/pipeline.py`: image loading, fixed-family register crop, dial heuristic pipeline.
- `src/watermeter/dials.py`: red pointer angle estimation baseline.
- `src/watermeter/reading.py`: reading validation helpers.
- `configs/meter_profile.example.json`: approximate starting geometry only.
- `scripts/export_rois.py`: exports register and dial crops for visual inspection.
- `docs/dataset_protocol.md`: collection, annotation and split rules.
- `firmware/esp32_cam/README.md`: AI Thinker camera integration plan.
- `tests/`: initial validation tests.

## PC setup (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Put calibration images in `data/raw/` (not committed by default), then export crops:

```powershell
python scripts/export_rois.py --image data/raw/meter.jpg --profile configs/meter_profile.example.json --out runs/rois
```

Run the baseline:

```powershell
python -m src.watermeter.cli --image data/raw/meter.jpg --profile configs/meter_profile.example.json --out runs/result.json
```

## Important status

This is an initial software baseline, **not a trained OCR model**. The digit recognizer is not implemented/trained yet. The dial estimator is heuristic and uncalibrated. The current profile coordinates are approximate and must be re-measured after the final rigid camera mount is installed. The pipeline intentionally returns `needs_review` and a null reading rather than fabricating a result.

## Development roadmap

1. Obtain straight-on images from the final fixed camera mount.
2. Calibrate the meter face, register ROI and dial centers/radii.
3. Collect many verified images from distinct physical meters of this same family.
4. Train a compact digit classifier with explicit wheel-transition handling.
5. Calibrate dial angle-to-value mapping and reading carry/rollover logic.
6. Evaluate exact full-reading accuracy, litre error, false-accept rate and abstention rate.
7. Quantize and benchmark on the exact AI Thinker ESP32-CAM (flash, free heap, PSRAM, tensor arena and latency).
8. If the original ESP32 cannot meet the measured resource budget, evaluate ESP32-S3 with PSRAM.

## Edge hardware constraints

Do not target a YOLO detector on the original AI Thinker ESP32-CAM. The practical first edge candidate is fixed geometry + classical image processing + a very small INT8 digit classifier. During data collection, the ESP32-CAM can upload JPEG images to a PC for annotation and training.

## Dataset rules

Split by physical meter ID, never by random frames from the same meter. Include all digits and transitions, all dial positions around 360°, and realistic glare, shadow, dirt, blur and lighting changes. Do not use unvalidated readings for billing.
