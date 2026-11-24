# AI-on-the-edge-device models on the RAGURA PC

RAGURA can run the pretrained TensorFlow Lite meter models from the official
[jomjol/AI-on-the-edge-device](https://github.com/jomjol/AI-on-the-edge-device)
repository on the PC. ESP32-CAM devices remain HTTP/MJPEG cameras only.

## What is integrated

- Digit model: `dig-cont_0900_s3_q.tflite` (100 output classes representing 0.0–9.9 wheel positions).
- Analog model: `ana-cont_1500_s2_q.tflite` (two outputs interpreted as a pointer phase).
- Release pin: `v16.1.0`.
- Runtime: Google AI Edge LiteRT Python interpreter.
- Model files are downloaded from the official repository into the local `models/` folder; they are not copied into Git history.

The PC-side adapter follows the upstream input convention: crop the configured ROI,
resize it to the model's input tensor dimensions, convert BGR to RGB, and feed
channel values in the 0–255 range. Integer tensor quantization is handled from the
model's own tensor metadata.

## Install once (requires internet for setup)

From the RAGURA repository root in PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
pip install -r requirements-pc.txt
python scripts/download_ai_edge_models.py
```

After model download and dependency installation, recognition runs locally and
does not need internet access.

## Important calibration requirement

The existing RAGURA profile provides a broad integer-register rectangle and four
dial centers/radii. The PC adapter divides the register rectangle into the
configured number of equal-width digit crops and uses square crops around each
dial. This is a starting geometry, not a claim that every meter uses equal digit
spacing. Camera focus, crop boundaries, digit count, dial order, zero position,
and direction must be checked against actual captures.

## API/runtime behavior

The inference adapter is in `src/watermeter/ai_edge_pc.py`. It reports
`models_missing` if the model files have not been downloaded; it does not silently
substitute EasyOCR when the AI Edge models are absent.

## Licensing

The upstream repository uses its own dual-use license. Review the official
`Licence.md` before redistribution or commercial deployment. This integration
does not relicense the upstream source or model files.
