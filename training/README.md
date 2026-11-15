# Digit model training

The model is trained on PC and exported to ONNX for graph inspection / downstream conversion. Do not train from the two reference photos alone: the dataset needs verified labels and multiple physical meters.

## Annotation CSV

Create `data/labels/digit_labels.csv` with columns:

```csv
image_path,meter_id,digit_1,digit_2,digit_3,digit_4,digit_5,split
data/raw/meter001_0001.jpg,M001,0,0,1,2,3,
data/raw/meter002_0001.jpg,M002,0,0,1,2,4,
```

Digits must be human-verified integers 0..9, ordered left-to-right. Leave split blank to use deterministic group splitting by meter_id. If a wheel is between digits or unreadable, do not guess: exclude that image from this first classifier dataset and annotate it separately for transition research.

## Train

```powershell
pip install -r requirements-train.txt
python training/train_digits.py --csv data/labels/digit_labels.csv --profile configs/meter_profile.example.json --epochs 40 --out models/digit_cnn
```

The script crops the register ROI, divides it into five equal cells with configurable overlap, resizes each cell to 32x48 grayscale and trains a compact CNN. Inspect crops before training; if the printed windows are not evenly spaced, replace equal splitting with per-wheel normalized boxes in the meter profile.

## Export ONNX

```powershell
python training/export_onnx.py --checkpoint models/digit_cnn/best.pt --out models/digit_cnn/digit_cnn.onnx
```

The ONNX model is not yet an ESP32 binary. TFLite Micro conversion and board benchmarking are a separate gated step.
