from __future__ import annotations

import math
import threading
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "ai-on-the-edge-device" / "v16.1.0"
DIGIT_MODEL = MODEL_DIR / "dig-cont_0900_s3_q.tflite"
ANALOG_MODEL = MODEL_DIR / "ana-cont_1500_s2_q.tflite"

_lock = threading.RLock()
_interpreters: dict[str, object] = {}


def _make_interpreter(model_path: Path):
    if not model_path.is_file():
        raise FileNotFoundError(
            f"AI-on-the-edge model is missing: {model_path}. "
            "Run: python scripts/download_ai_edge_models.py"
        )
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError as exc:
        raise RuntimeError(
            "AI Edge LiteRT is not installed. Install requirements-pc.txt "
            "inside the active virtual environment."
        ) from exc
    interpreter = Interpreter(model_path=str(model_path), num_threads=2)
    interpreter.allocate_tensors()
    return interpreter


def _interpreter(model_path: Path):
    key = str(model_path.resolve())
    with _lock:
        if key not in _interpreters:
            _interpreters[key] = _make_interpreter(model_path)
        return _interpreters[key]


def models_status() -> dict:
    return {
        "engine": "AI-on-the-edge-device",
        "source_release": "v16.1.0",
        "runtime": "ai-edge-litert",
        "models": {
            "digit": {"file": DIGIT_MODEL.name, "available": DIGIT_MODEL.is_file()},
            "analog": {"file": ANALOG_MODEL.name, "available": ANALOG_MODEL.is_file()},
        },
        "ready": DIGIT_MODEL.is_file() and ANALOG_MODEL.is_file(),
        "model_directory": str(MODEL_DIR),
    }


def _dequantize(values: np.ndarray, detail: dict) -> np.ndarray:
    values = values.astype(np.float32)
    scale, zero_point = detail.get("quantization", (0.0, 0))
    if np.issubdtype(detail["dtype"], np.integer) and scale:
        values = (values - float(zero_point)) * float(scale)
    return values


def _infer(model_path: Path, crop_bgr: np.ndarray) -> np.ndarray:
    if crop_bgr is None or crop_bgr.size == 0:
        raise ValueError("Cannot run inference on an empty ROI.")
    interpreter = _interpreter(model_path)
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    shape = input_detail["shape"]
    if len(shape) != 4 or int(shape[0]) != 1 or int(shape[3]) != 3:
        raise RuntimeError(f"Unsupported model input tensor shape: {shape}")
    target_h, target_w = int(shape[1]), int(shape[2])

    # The upstream ESP32 implementation feeds RGB channel values in [0, 255].
    resized = cv2.resize(crop_bgr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    tensor = rgb.astype(np.float32)[None, ...]

    input_dtype = input_detail["dtype"]
    if np.issubdtype(input_dtype, np.integer):
        scale, zero_point = input_detail.get("quantization", (0.0, 0))
        if not scale:
            raise RuntimeError("Quantized model input has no valid quantization scale.")
        tensor = np.round(tensor / float(scale) + float(zero_point))
        limits = np.iinfo(input_dtype)
        tensor = np.clip(tensor, limits.min, limits.max).astype(input_dtype)
    else:
        tensor = tensor.astype(input_dtype)

    interpreter.set_tensor(input_detail["index"], tensor)
    interpreter.invoke()
    output = interpreter.get_tensor(output_detail["index"])
    return _dequantize(np.asarray(output).reshape(-1), output_detail)


def _softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    values = values - float(np.max(values))
    exp = np.exp(values)
    total = float(exp.sum())
    return exp / total if total > 0 else np.zeros_like(exp)


def _pixel_roi(roi: list[float], width: int, height: int):
    x1, y1, x2, y2 = [float(v) for v in roi]
    left = max(0, min(width - 1, int(round(x1 * width))))
    top = max(0, min(height - 1, int(round(y1 * height))))
    right = max(left + 1, min(width, int(round(x2 * width))))
    bottom = max(top + 1, min(height, int(round(y2 * height))))
    return left, top, right, bottom


def _read_continuous_digit(crop: np.ndarray) -> dict:
    scores = _softmax(_infer(DIGIT_MODEL, crop))
    if scores.size != 100:
        raise RuntimeError(
            f"Expected the upstream 100-output continuous digit model, got {scores.size} outputs."
        )
    index = int(np.argmax(scores))
    return {
        "continuous_value": index / 10.0,
        "class_index": index,
        "confidence": round(float(scores[index]), 4),
    }


def _evaluate_hybrid_digit(number: float, predecessor: float, evaluated_predecessor: int) -> int:
    """Port of PointerEvalHybridNew for the upstream continuous digit model."""
    after_decimal = int(math.floor(number * 10.0)) % 10
    before_decimal = (int(math.floor(number)) + 10) % 10

    if evaluated_predecessor < 0:
        return int(math.trunc(round(number * 100.0))) // 100

    if 0.7 <= predecessor <= 9.3:
        if after_decimal <= 3 or after_decimal >= 7:
            return (int(round(number)) + 10) % 10
        return (int(math.trunc(number)) + 10) % 10

    if evaluated_predecessor <= 1:
        return (before_decimal + 1) % 10 if after_decimal > 5 else before_decimal

    if 9.7 >= predecessor or after_decimal >= 4:
        return before_decimal
    return (before_decimal - 1 + 10) % 10


def _read_analog(crop: np.ndarray, counter_clockwise: bool) -> dict:
    values = _infer(ANALOG_MODEL, crop)
    if values.size != 2:
        raise RuntimeError(
            f"Expected the upstream 2-output analog model, got {values.size} outputs."
        )
    f1, f2 = float(values[0]), float(values[1])
    phase = (math.atan2(f1, f2) / (2.0 * math.pi) + 2.0) % 1.0
    value = 10.0 - phase * 10.0 if counter_clockwise else phase * 10.0
    return {"value": round(value % 10.0, 4), "model_outputs": [f1, f2]}


def analyze_ai_edge(
    frame: np.ndarray,
    digit_roi: list[float],
    dials: list[dict],
    channel_id: str,
    alignment: dict | None = None,
    expected_digits: int = 5,
):
    """Run the original project's pretrained TFLite digit and analog models on a PC frame.

    The camera only supplies frames. All crop preparation and inference run locally
    on the PC. Meter-specific ROI geometry still has to be calibrated.
    """
    status = models_status()
    if not status["ready"]:
        annotated = frame.copy()
        cv2.putText(
            annotated, "AI-on-the-edge models missing", (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
        )
        return ({
            "channel_id": channel_id,
            "status": "models_missing",
            "recognition_engine": "AI-on-the-edge-device",
            "model_status": status,
            "candidate_reading_m3": None,
            "warning": "Download the original pretrained TFLite models before triggering recognition.",
            "alignment": alignment or {"status": "not_configured"},
        }, annotated)

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = _pixel_roi(digit_roi, width, height)
    register = frame[y1:y2, x1:x2]
    if register.size == 0 or expected_digits < 1:
        raise ValueError("Invalid integer-register ROI or digit count.")

    cell_width = register.shape[1] / float(expected_digits)
    digit_cells = []
    for index in range(expected_digits):
        left = max(0, int(round(index * cell_width)))
        right = min(register.shape[1], int(round((index + 1) * cell_width)))
        crop = register[:, left:right]
        item = _read_continuous_digit(crop)
        item.update({"position": index + 1})
        digit_cells.append(item)

    # The source firmware evaluates wheel transitions from right to left,
    # using the adjacent lower-order wheel and its already evaluated digit.
    evaluated = [-1] * len(digit_cells)
    for index in range(len(digit_cells) - 1, -1, -1):
        current = digit_cells[index]["continuous_value"]
        if index == len(digit_cells) - 1:
            evaluated[index] = _evaluate_hybrid_digit(current, -1.0, -1)
        else:
            predecessor = digit_cells[index + 1]["continuous_value"]
            evaluated[index] = _evaluate_hybrid_digit(
                current, predecessor, evaluated[index + 1]
            )
    for index, item in enumerate(digit_cells):
        item["digit"] = evaluated[index]
        item["status"] = "read" if item["confidence"] >= 0.20 else "low_confidence"

    digits = "".join(str(item["digit"]) for item in digit_cells)
    digits_complete = len(digit_cells) == expected_digits and all(
        item["confidence"] >= 0.20 for item in digit_cells
    )

    analog_results = []
    fractional = 0.0
    all_analog_valid = len(dials) == 4
    weights = {"x0.1": 0.1, "x0.01": 0.01, "x0.001": 0.001, "x0.0001": 0.0001}
    annotated = frame.copy()
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (55, 220, 160), 2)
    cv2.putText(annotated, "AI EDGE DIGITS", (x1, max(20, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (55, 220, 160), 2)

    for dial in dials:
        cx = int(round(float(dial["center"][0]) * width))
        cy = int(round(float(dial["center"][1]) * height))
        radius = max(5, int(round(float(dial["radius"]) * min(width, height))))
        left, top = max(0, cx - radius), max(0, cy - radius)
        right, bottom = min(width, cx + radius), min(height, cy + radius)
        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            all_analog_valid = False
            continue
        direction = str(dial.get("direction", "clockwise")).lower()
        counter_clockwise = direction in {"counterclockwise", "counter-clockwise", "ccw"}
        reading = _read_analog(crop, counter_clockwise)
        name = str(dial.get("name", "")).lower()
        value = reading["value"]
        analog_results.append({
            "name": name,
            "value": value,
            "confidence": None,
            "angle_degrees": None,
            "center": [cx, cy],
            "tip": None,
            "status": "AI Edge model output; calibration required",
            "model_outputs": reading["model_outputs"],
        })
        if name in weights:
            fractional += value * weights[name]
        cv2.circle(annotated, (cx, cy), radius, (0, 165, 255), 2)

    all_analog_valid = all_analog_valid and len(analog_results) == 4 and all(
        item["name"] in weights for item in analog_results
    )
    complete = digits_complete and all_analog_valid
    candidate = round(int(digits) + fractional, 6) if complete else None
    mean_confidence = (
        round(float(np.mean([item["confidence"] for item in digit_cells])), 4)
        if digit_cells else 0.0
    )
    result = {
        "channel_id": channel_id,
        "status": "needs_review",
        "recognition_engine": "AI-on-the-edge-device",
        "source_release": "v16.1.0",
        "digit_model": DIGIT_MODEL.name,
        "analog_model": ANALOG_MODEL.name,
        "integer_digits": digits if digits_complete else None,
        "digit_cells": digit_cells,
        "digit_recognition_mode": "original_ai_on_the_edge_tflite_100_class_hybrid",
        "fractional_dials": analog_results,
        "fractional_estimate_m3": round(fractional, 6) if analog_results else None,
        "candidate_reading_m3": candidate,
        "ocr_confidence": mean_confidence,
        "frame_size": [width, height],
        "captured_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "alignment": alignment or {"status": "not_configured"},
        "warning": (
            "Pretrained AI-on-the-edge models are active. Validate each meter's ROI, "
            "dial orientation and readings against labeled captures before operational use."
        ),
    }
    return result, annotated
