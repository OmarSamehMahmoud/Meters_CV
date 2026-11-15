from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from io import BytesIO

import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageOps

PRESETS_PATH = Path("configs/reference_presets.json")
REFERENCE_DIR = Path("data/reference")
st.set_page_config(page_title="WaterMeterVision", page_icon="💧", layout="wide")
st.title("WaterMeterVision")
st.caption("NWM SJ-LFC / SJ-WDC · five-digit register OCR + experimental rotary-pointer detection")


@st.cache_resource
def get_reader():
    return easyocr.Reader(["en"], gpu=False, verbose=False)


def image_to_bgr(pil_image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(pil_image.convert("RGB")), cv2.COLOR_RGB2BGR)


def pixel_roi(roi, width, height):
    x1, y1, x2, y2 = roi
    return (
        max(0, min(width - 1, int(round(x1 * width)))),
        max(0, min(height - 1, int(round(y1 * height)))),
        max(1, min(width, int(round(x2 * width)))),
        max(1, min(height, int(round(y2 * height)))),
    )


def dial_geometry(dial, width, height):
    return (
        int(round(dial["center"][0] * width)),
        int(round(dial["center"][1] * height)),
        max(5, int(round(dial["radius"] * min(width, height)))),
    )


def detect_red_pointer(image, dial):
    """Experimental red-pointer angle detector. Dial zero is at 12 o'clock; values increase clockwise."""
    h, w = image.shape[:2]
    cx, cy, radius = dial_geometry(dial, w, h)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red_mask = (
        (((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 170))
         & (hsv[:, :, 1] >= 75) & (hsv[:, :, 2] >= 55))
    )
    yy, xx = np.ogrid[:h, :w]
    distance = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    annulus = (distance >= radius * 0.25) & (distance <= radius * 0.90)
    candidate = red_mask & annulus
    ys, xs = np.where(candidate)
    annulus_area = max(1, int(np.count_nonzero(annulus)))
    red_ratio = len(xs) / annulus_area

    if len(xs) < 12:
        return {"name": dial["name"], "value": None, "angle_degrees": None,
                "confidence": 0.0, "status": "Pointer not detected",
                "center": [cx, cy], "tip": None, "red_ratio": round(red_ratio, 4)}

    # The furthest red pixel outside the hub approximates the pointed end of the red needle.
    distances = (xs - cx) ** 2 + (ys - cy) ** 2
    index = int(np.argmax(distances))
    tip_x, tip_y = int(xs[index]), int(ys[index])
    angle = (math.degrees(math.atan2(tip_y - cy, tip_x - cx)) + 90.0) % 360.0
    value = angle / 36.0

    # A large red area usually means an obstruction or red object, not a clean needle.
    confidence = 0.82
    if red_ratio > 0.24:
        confidence = 0.25
        status = "Occluded / needs manual review"
    elif red_ratio > 0.15:
        confidence = 0.48
        status = "Possible obstruction"
    else:
        status = "Estimated from red pointer"

    return {
        "name": dial["name"], "value": round(value, 3),
        "angle_degrees": round(angle, 2), "confidence": confidence,
        "status": status, "center": [cx, cy], "tip": [tip_x, tip_y],
        "red_ratio": round(red_ratio, 4),
    }


def draw_calibration(image, roi, dials, pointer_results=None):
    canvas = image.copy()
    h, w = canvas.shape[:2]
    x1, y1, x2, y2 = pixel_roi(roi, w, h)
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (40, 220, 40), 3)
    cv2.putText(canvas, "5-digit register", (x1, max(24, y1 - 9)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 220, 40), 2, cv2.LINE_AA)
    result_by_name = {item["name"]: item for item in (pointer_results or [])}
    colors = {"x0.1": (0, 0, 255), "x0.01": (0, 200, 0),
              "x0.001": (255, 100, 0), "x0.0001": (200, 0, 200)}
    for dial in dials:
        cx, cy, radius = dial_geometry(dial, w, h)
        color = colors.get(dial["name"].lower(), (0, 165, 255))
        cv2.circle(canvas, (cx, cy), radius, color, 2)
        cv2.drawMarker(canvas, (cx, cy), color, cv2.MARKER_CROSS, 16, 2)
        cv2.putText(canvas, dial["name"], (cx - radius, cy - radius - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2, cv2.LINE_AA)
        result = result_by_name.get(dial["name"])
        if result and result.get("tip"):
            tip = tuple(result["tip"])
            line_color = (0, 220, 0) if result["confidence"] >= 0.7 else (0, 165, 255)
            cv2.arrowedLine(canvas, (cx, cy), tip, line_color, 3, tipLength=0.22)
            label = "?" if result["value"] is None else f'{result["value"]:.2f}'
            cv2.putText(canvas, label, (cx + 8, cy + radius + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, line_color, 2, cv2.LINE_AA)
    return canvas


def read_digits(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    results = get_reader().readtext(
        clahe, allowlist="0123456789", detail=1, paragraph=False,
        text_threshold=0.35, low_text=0.25, link_threshold=0.25
    )
    found = []
    for box, text, confidence in results:
        digits = "".join(char for char in text if char.isdigit())
        if digits:
            found.append((min(point[0] for point in box), digits, float(confidence)))
    found.sort(key=lambda item: item[0])
    return "".join(item[1] for item in found), found


presets_data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))["reference_presets"]
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
reference_images = sorted(
    p for p in REFERENCE_DIR.iterdir()
    if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
)

st.sidebar.header("Image source")
source_mode = st.sidebar.radio(
    "Choose image source",
    ["Use saved reference photo", "Upload a new photo"],
    index=0 if reference_images else 1,
)
uploaded = st.file_uploader("Upload a meter photo", type=["jpg", "jpeg", "png", "bmp"]) if source_mode == "Upload a new photo" else None

selected_reference = None
if source_mode == "Use saved reference photo":
    if reference_images:
        selected_reference = st.selectbox(
            "Select one of your original meter photos", options=reference_images,
            format_func=lambda p: p.name,
        )
    else:
        st.warning("No reference photos found. Copy your original images into data/reference/ or upload one.")

image_source = selected_reference if selected_reference is not None else uploaded

if image_source is not None:
    if isinstance(image_source, Path):
        raw = image_source.read_bytes()
        pil = ImageOps.exif_transpose(Image.open(image_source)).convert("RGB")
    else:
        raw = image_source.getvalue()
        pil = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
    image_key = hashlib.sha1(raw).hexdigest()
    image = image_to_bgr(pil)
    height, width = image.shape[:2]

    st.sidebar.header("Image calibration")
    preset_keys = list(presets_data)
    preset_labels = {key: presets_data[key]["label"] for key in preset_keys}
    preset_choice = st.sidebar.selectbox(
        "Choose matching photo framing", options=preset_keys,
        format_func=lambda key: preset_labels[key],
    )
    selected = presets_data[preset_choice]
    roi_default = selected["integer_register_roi"]
    roi_values = []
    for index, label in enumerate(["Register left", "Register top", "Register right", "Register bottom"]):
        lo, hi = (0.0, 0.95) if index < 2 else (0.05, 1.0)
        roi_values.append(st.sidebar.slider(
            label, min_value=lo, max_value=hi, value=float(roi_default[index]),
            step=0.001, format="%.3f", key=f"{image_key}_{preset_choice}_roi_{index}"
        ))
    roi = tuple(roi_values)

    dial_values = []
    with st.sidebar.expander("Fine-tune four dial positions", expanded=False):
        for dial_index, base_dial in enumerate(selected["dials"]):
            st.markdown(f'**{base_dial["name"]}**')
            cx = st.slider("Center X", 0.0, 1.0, float(base_dial["center"][0]), 0.001,
                           key=f"{image_key}_{preset_choice}_dx_{dial_index}")
            cy = st.slider("Center Y", 0.0, 1.0, float(base_dial["center"][1]), 0.001,
                           key=f"{image_key}_{preset_choice}_dy_{dial_index}")
            radius = st.slider("Radius", 0.02, 0.20, float(base_dial["radius"]), 0.001,
                               key=f"{image_key}_{preset_choice}_dr_{dial_index}")
            dial_values.append({"name": base_dial["name"], "center": [cx, cy], "radius": radius})

    st.subheader("Calibration overlay")
    initial_overlay = draw_calibration(image, roi, dial_values)
    st.image(cv2.cvtColor(initial_overlay, cv2.COLOR_BGR2RGB), width="stretch")
    st.caption("Green = five black digits. Colored circles = rotary dials. Analyze to overlay detected red-pointer directions.")

    x1, y1, x2, y2 = pixel_roi(roi, width, height)
    register_crop = image[y1:y2, x1:x2]
    with st.expander("Register crop preview"):
        st.image(cv2.cvtColor(register_crop, cv2.COLOR_BGR2RGB), width="stretch")

    if st.button("Analyze meter", type="primary"):
        if x2 <= x1 or y2 <= y1:
            st.error("Invalid register ROI.")
            st.stop()
        with st.spinner("Running register OCR and red-pointer detection..."):
            integer, raw_results = read_digits(register_crop)
            ocr_confidence = float(np.mean([item[2] for item in raw_results])) if raw_results else 0.0
            pointer_results = [detect_red_pointer(image, dial) for dial in dial_values]
            annotated = draw_calibration(image, roi, dial_values, pointer_results)

            weights = {"x0.1": 0.1, "x0.01": 0.01, "x0.001": 0.001, "x0.0001": 0.0001}
            usable = [p for p in pointer_results if p["value"] is not None and p["confidence"] >= 0.7]
            fractional = sum(p["value"] * weights[p["name"].lower()] for p in usable)
            all_clear = len(usable) == 4
            payload = {
                "status": "estimated" if all_clear and len(integer) == 5 else "needs_review",
                "integer_digits": integer if len(integer) == 5 else None,
                "fractional_dials": pointer_results,
                "fractional_estimate_m3": round(fractional, 6) if usable else None,
                "reading_m3": None,
                "ocr_confidence": round(ocr_confidence, 4),
                "ocr_raw": [{"text": item[1], "confidence": round(item[2], 4)} for item in raw_results],
                "selected_reference_preset": preset_choice,
                "register_roi_pixels": [x1, y1, x2, y2],
                "dial_convention": "0 at 12 o'clock; values increase clockwise; one revolution = 0..10",
                "warning": "Experimental CV estimate. Occluded or low-confidence dials are excluded; verify manually.",
            }
            st.session_state[f"result_{image_key}"] = payload
            st.session_state[f"overlay_{image_key}"] = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

    result = st.session_state.get(f"result_{image_key}")
    if result:
        st.divider()
        st.subheader("Detected rotary readings")
        for dial_result in result["fractional_dials"]:
            value_text = "Not detected" if dial_result["value"] is None else f'{dial_result["value"]:.2f} / 10'
            st.metric(dial_result["name"].upper(), value_text,
                      delta=f'Confidence {dial_result["confidence"]:.2f}')
            st.caption(dial_result["status"])
        st.image(st.session_state[f"overlay_{image_key}"], caption="Detected pointer directions", width="stretch")
        if result["integer_digits"]:
            st.metric("Black register (m³)", result["integer_digits"])
        else:
            st.warning(f"OCR returned {result['ocr_raw']}; expected five digits.")
        st.metric("Fractional estimate (m³)", result["fractional_estimate_m3"] if result["fractional_estimate_m3"] is not None else "Unavailable")
        st.warning("This is an experimental image-based estimate, not a validated meter reading. A dial with low confidence must be checked manually.")
        st.download_button("Download result JSON", json.dumps(result, indent=2),
                           file_name="watermeter_result.json", mime="application/json")
else:
    st.info("Place your reference photos in data/reference/ or choose Upload a new photo.")
    st.caption("Prototype: pointer detection is experimental and requires validation on multiple real meter photos.")
