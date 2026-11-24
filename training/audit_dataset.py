from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from training.train_digits import split_frame


REQUIRED_COLUMNS = ["image_path", "meter_id", "digit_1", "digit_2", "digit_3", "digit_4", "digit_5"]


def audit_dataset(csv_path: Path, profile_path: Path, project_root: Path = Path(".")):
    frame = pd.read_csv(csv_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        return {"status": "failed", "errors": [f"Missing columns: {missing}"], "warnings": [], "images": 0}

    if frame.empty:
        return {"status": "failed", "errors": ["CSV contains no rows."], "warnings": [], "images": 0}
    if frame["image_path"].isna().any() or frame["meter_id"].isna().any():
        errors.append("Every row must have image_path and meter_id.")
    if frame["image_path"].astype(str).duplicated().any():
        errors.append("Duplicate image_path entries found.")
    if frame["meter_id"].fillna("").astype(str).str.strip().eq("").any():
        errors.append("Every row must have a non-empty physical meter_id.")

    for column in REQUIRED_COLUMNS[2:]:
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = values.isna() | (values % 1 != 0) | (values < 0) | (values > 9)
        if invalid.any():
            errors.append(f"{column} must contain integer labels from 0 to 9 (invalid rows: {int(invalid.sum())}).")

    roi = profile.get("integer_register_roi")
    if not isinstance(roi, list) or len(roi) != 4:
        errors.append("Profile integer_register_roi must contain [x1, y1, x2, y2].")
        roi = None
    elif not (0 <= roi[0] < roi[2] <= 1 and 0 <= roi[1] < roi[3] <= 1):
        errors.append("Profile integer_register_roi must be normalized and satisfy 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1.")
        roi = None

    preview_rows = []
    missing_images = 0
    if roi is not None:
        for row_index, row in frame.iterrows():
            image_path = Path(str(row["image_path"]))
            if not image_path.is_absolute():
                image_path = project_root / image_path
            image = cv2.imread(str(image_path))
            if image is None:
                missing_images += 1
                continue
            height, width = image.shape[:2]
            x1, y1, x2, y2 = roi
            crop = image[int(y1 * height):int(y2 * height), int(x1 * width):int(x2 * width)]
            if crop.size == 0 or crop.shape[1] < 5:
                errors.append(f"Row {row_index + 2}: ROI is empty or too narrow for five digit cells.")
                continue
            cell_width = crop.shape[1] / 5.0
            thumbs = []
            for index in range(5):
                left = max(0, int(index * cell_width - cell_width * 0.08))
                right = min(crop.shape[1], int((index + 1) * cell_width + cell_width * 0.08))
                cell = cv2.cvtColor(crop[:, left:right], cv2.COLOR_BGR2GRAY)
                cell = cv2.resize(cell, (64, 96), interpolation=cv2.INTER_AREA)
                thumbs.append(cv2.cvtColor(cell, cv2.COLOR_GRAY2BGR))
            labels = "".join(str(int(row[f"digit_{i}"])) if pd.notna(row[f"digit_{i}"]) else "?" for i in range(1, 6))
            preview_rows.append((str(row["meter_id"]), labels, thumbs))

    if missing_images:
        errors.append(f"{missing_images} image file(s) could not be opened.")
    if "split" in frame.columns:
        try:
            split_frame(frame)
        except (ValueError, KeyError) as exc:
            errors.append(f"Split validation failed: {exc}")
    else:
        meter_count = frame["meter_id"].nunique(dropna=True)
        if meter_count < 4:
            errors.append(f"Automatic group split needs at least 4 distinct physical meters; found {meter_count}.")
        else:
            try:
                split_frame(frame)
            except ValueError as exc:
                errors.append(f"Automatic split validation failed: {exc}")

    if len(frame) < 100:
        warnings.append("Dataset has fewer than 100 labeled images; treat metrics as an early experiment.")
    if frame["meter_id"].nunique(dropna=True) < 10:
        warnings.append("Fewer than 10 physical meters are represented; generalization evidence will be limited.")
    if len(preview_rows) != len(frame):
        warnings.append("The crop preview omits rows with unreadable image files or invalid ROIs.")

    return {
        "status": "passed" if not errors else "failed",
        "images": int(len(frame)),
        "physical_meters": int(frame["meter_id"].nunique(dropna=True)),
        "preview_images": len(preview_rows),
        "errors": errors,
        "warnings": warnings,
        "split_strategy": "meter_id grouped train/validation/test",
        "roi": roi,
        "_preview_rows": preview_rows,
    }


def save_contact_sheet(rows, output_path: Path):
    if not rows:
        return
    tiles = []
    for meter_id, labels, crops in rows:
        label = np.full((24, 5 * 68, 3), 245, dtype=np.uint8)
        cv2.putText(label, f"{meter_id} | GT {labels}", (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (25, 25, 25), 1)
        cells = []
        for crop in crops:
            tile = np.full((100, 68, 3), 255, dtype=np.uint8)
            tile[2:98, 2:66] = cv2.resize(crop, (64, 96))
            cells.append(tile)
        tiles.append(np.vstack([label, np.hstack(cells)]))
    sheet = np.vstack(tiles)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), sheet)


def main():
    parser = argparse.ArgumentParser(description="Validate labeled water-meter digit data and export a five-cell crop preview.")
    parser.add_argument("--csv", required=True, help="Labeled annotation CSV.")
    parser.add_argument("--profile", required=True, help="Meter profile JSON containing integer_register_roi.")
    parser.add_argument("--root", default=".", help="Project root used to resolve relative image_path values.")
    parser.add_argument("--out", default="reports/dataset_audit", help="Output directory for report and contact sheet.")
    args = parser.parse_args()

    output_dir = Path(args.out)
    report = audit_dataset(Path(args.csv), Path(args.profile), Path(args.root))
    preview_rows = report.pop("_preview_rows", [])
    output_dir.mkdir(parents=True, exist_ok=True)
    save_contact_sheet(preview_rows, output_dir / "digit_crop_contact_sheet.jpg")
    (output_dir / "dataset_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport: {output_dir / 'dataset_audit.json'}")
    if preview_rows:
        print(f"Crop preview: {output_dir / 'digit_crop_contact_sheet.jpg'}")
    raise SystemExit(0 if report["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
