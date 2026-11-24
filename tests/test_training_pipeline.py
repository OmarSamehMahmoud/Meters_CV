import pandas as pd
import pytest

from training.train_digits import split_frame


def _frame():
    return pd.DataFrame([
        {"image_path": f"meter_{meter}_{image}.jpg", "meter_id": meter,
         "digit_1": 1, "digit_2": 2, "digit_3": 3, "digit_4": 4, "digit_5": 5}
        for meter in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]
        for image in range(3)
    ])


def test_automatic_split_has_no_meter_leakage():
    train, val, test = split_frame(_frame())
    groups = [{*part.meter_id.astype(str)} for part in (train, val, test)]
    assert all(groups[i].isdisjoint(groups[j]) for i in range(3) for j in range(i + 1, 3))
    assert all(not part.empty for part in (train, val, test))


def test_explicit_split_rejects_meter_leakage():
    frame = _frame().iloc[:6].copy()
    frame["split"] = ["train", "train", "val", "val", "test", "test"]
    frame.loc[frame.index[2], "meter_id"] = frame.loc[frame.index[0], "meter_id"]
    with pytest.raises(ValueError, match="leakage"):
        split_frame(frame)


def test_partial_explicit_split_is_rejected():
    frame = _frame()
    frame["split"] = ""
    frame.loc[frame.index[0], "split"] = "train"
    with pytest.raises(ValueError, match="every row"):
        split_frame(frame)


def test_explicit_split_requires_all_partitions():
    frame = _frame()
    frame["split"] = "train"
    with pytest.raises(ValueError, match="non-empty"):
        split_frame(frame)


def test_automatic_split_requires_enough_distinct_meters():
    frame = _frame()
    frame = frame[frame.meter_id.isin(["M1", "M2", "M3"])]
    with pytest.raises(ValueError, match="at least 4"):
        split_frame(frame)
