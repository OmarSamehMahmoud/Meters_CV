# PC inference prototype

## What this first PC version does
- Lets you upload a meter photo in a browser UI.
- Uses EasyOCR's pretrained English digit/text recognizer on the configured five-wheel register ROI.
- Uses OpenCV to mark the approximate four red dial regions and estimate pointer angles for diagnostics.
- Exports a JSON result and displays an annotated image.

This is a pretrained general OCR engine plus meter-specific computer-vision logic. It is **not yet a custom-trained meter model**. EasyOCR downloads its recognition/detection weights on first run; keep the downloaded cache if you need repeat offline use. The four fractional dial values are intentionally not emitted until the dial geometry and direction are calibrated.

## Windows
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-pc.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

## First test
1. Upload one of the existing reference photos.
2. Adjust Register left/top/right/bottom until the preview contains only the five black digit wheels.
3. Click Analyze meter.
4. Check the returned five digits against the physical meter. If OCR does not return exactly five digits, do not treat the result as a reading.
5. Repeat with the second viewpoint and compare stability.

## Current reference label
The user-confirmed black register is `00000`. The user-described fractional dials are x0.1 between 0 and 1, x0.01 at 8, x0.001 between 9 and 0, and x0.0001 at 9. This gives a provisional fractional contribution of 0.0899 m³ and provisional total `00000.0899 m³`, assuming the two between-number pointers have not crossed the next mark. This label is a reference for manual comparison, not a training dataset.

## Important
The two supplied images show one physical meter from different viewpoints. They are useful for ROI/lighting sanity checks, but not enough to train or validate a general digit model. Do not train the CNN on repeated/augmented copies and report it as generalized recognition. Once the PC pipeline is stable, collect labeled images from multiple physical meters and train/evaluate the compact CNN. Only after measured PC results should the model be ported to the ESP32-CAM.
