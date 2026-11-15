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


## Run the PC image-upload application (first milestone)

The interactive PC prototype is now available in `app.py`. It accepts a photo, lets you adjust the five-wheel register ROI, runs pretrained EasyOCR on that crop, marks the approximate dial regions with OpenCV, and exports a JSON result.

Install and launch:

```powershell
py -3.11 -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-pc.txt
streamlit run app.py
```

See [docs/pc_quickstart.md](docs/pc_quickstart.md) for the test procedure. EasyOCR downloads pretrained weights on first run. This is a PC OCR/CV prototype, not yet a custom-trained water-meter model. It deliberately does not calculate the fractional dial contribution until the four dial scales and pointer directions are calibrated. Every result must be manually checked.


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

## Exact-model reference dataset (NWM SJ-LFC / FD2)\n\nDownload the five official product-gallery reference photos locally (not committed to Git):\n\n```powershell\npython scripts/download_nwm_sj_lfc_reference.py\n```\n\nThe script writes a SHA-256 manifest under `data/external/nwm_sj_lfc_reference/`. These are unlabeled product references, not training data. The source site displays a copyright notice; check rights before model training, redistribution, or commercial use. Read [the target-specific dataset protocol](docs/nwm_sj_lfc_dataset.md).\n\n## Dataset rules

Split by physical meter ID, never by random frames from the same meter. Include all digits and transitions, all dial positions around 360°, and realistic glare, shadow, dirt, blur and lighting changes. Do not use unvalidated readings for billing.

## Digit recognition training (new)

The repository now includes a compact PC-trained CNN for the five odometer windows:
- `src/watermeter/digit_model.py`: compact 32x48 grayscale CNN.
- `training/train_digits.py`: supervised training with meter-ID grouped splitting and per-digit + full-register exact-match evaluation.
- `src/watermeter/digit_inference.py`: five-digit inference from a trained checkpoint.
- `training/export_onnx.py`: ONNX export.
- `docs/annotation_template.csv`: starter annotation schema.

Install training dependencies:

```powershell
pip install -r requirements-train.txt
```

Create `data/labels/digit_labels.csv` using the schema in `training/README.md`, then train:

```powershell
python training/train_digits.py --csv data/labels/digit_labels.csv --profile configs/meter_profile.example.json --epochs 40 --out models/digit_cnn
```

Run inference once a checkpoint exists:

```powershell
python -m src.watermeter.cli --image data/raw/meter.jpg --profile configs/meter_profile.example.json --checkpoint models/digit_cnn/best.pt --out runs/result.json
```

The CLI still forces `needs_review` and null `reading_m3`: fractional dial calibration, rollover logic and end-to-end validation are not complete. Training code is ready, but no model weights or accuracy claims exist until a labeled dataset is supplied and training is run.


## Fixed-camera approval prototype (current decision)

No additional user photographs are required for the initial approval prototype. Use the two existing reference photographs as the only initial samples and assume a rigid, fixed camera-to-meter distance and fixed meter orientation.

The five black odometer windows are provisionally labeled 00000 in both references. This is a provisional visual label, not a verified billing record. The four fractional dial values remain unverified.

To create mild preprocessing robustness variants after placing the two existing photos in data/reference:

```powershell
python training/augment_reference.py --input data/reference --output data/augmented_reference --variants 20
```

Augmented copies are correlated views of the same two source photos. They are for testing crop/illumination stability only, not for training a general 0-9 classifier or claiming accuracy.

Read docs/current_data_limitations.md before interpreting any results. The current goal is a fixed-layout PC proof of concept and a camera-capture demonstration for project approval. Production-grade digit recognition across tens of thousands of meters cannot be validated from two photographs of one physical meter.

## Corrected reference-photo calibration (2026-11-15)

The PC app now has separate measured ROI presets for the two supplied reference images:

- Close framing: `WhatsApp Image 2026-11-12 at 3.15.33 PM.jpeg`
- Wide framing: `WhatsApp Image 2026-11-12 at 3.15.32 PM.jpeg`

Run the app, upload the matching photo, and select the corresponding framing in the sidebar. The green register rectangle and four orange dial circles are displayed before OCR. Fine-tuning controls are available for the digit rectangle and each dial center/radius. See [reference photo calibration](docs/reference_photo_calibration.md).

These are photo-specific ROIs. Recalibrate after installing the ESP32-CAM in its final fixed position. Fractional dial values are not yet validated.
