import json

import cv2
import numpy as np
import pandas as pd

from training.audit_dataset import audit_dataset


def _dataset(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    rows = []
    for index, (meter, split) in enumerate([
        ("M1", "train"), ("M2", "train"),
        ("M3", "val"), ("M4", "test"),
    ]):
        path = image_dir / f"meter_{meter}.jpg"
        cv2.imwrite(str(path), np.full((100, 300, 3), 180, dtype=np.uint8))
        rows.append({
            "image_path": str(path), "meter_id": meter,
            "digit_1": 1, "digit_2": 2, "digit_3": 3,
            "digit_4": 4, "digit_5": 5, "split": split,
        })
    csv_path = tmp_path / "labels.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"integer_register_roi": [0.1, 0.1, 0.9, 0.9]}), encoding="utf-8")
    return csv_path, profile_path


def test_audit_accepts_valid_meter_disjoint_dataset(tmp_path):
    csv_path, profile_path = _dataset(tmp_path)
    report = audit_dataset(csv_path, profile_path, tmp_path)
    assert report["status"] == "passed"
    assert report["images"] == 4
    assert report["physical_meters"] == 4
    assert len(report["_preview_rows"]) == 4


def test_audit_rejects_invalid_digit_labels(tmp_path):
    csv_path, profile_path = _dataset(tmp_path)
    frame = pd.read_csv(csv_path)
    frame.loc[0, "digit_3"] = 12
    frame.to_csv(csv_path, index=False)
    report = audit_dataset(csv_path, profile_path, tmp_path)
    assert report["status"] == "failed"
    assert any("digit_3" in error for error in report["errors"])


def test_audit_rejects_missing_source_image(tmp_path):
    csv_path, profile_path = _dataset(tmp_path)
    frame = pd.read_csv(csv_path)
    frame.loc[0, "image_path"] = str(tmp_path / "missing.jpg")
    frame.to_csv(csv_path, index=False)
    report = audit_dataset(csv_path, profile_path, tmp_path)
    assert report["status"] == "failed"
    assert any("could not be opened" in error for error in report["errors"])
