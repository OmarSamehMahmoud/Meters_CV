from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageOps

PRESETS_PATH = Path("configs/reference_presets.json")
REFERENCE_DIR = Path("data/reference")
st.set_page_config(page_title="WaterMeterVision", page_icon="💧", layout="wide")
st.title("WaterMeterVision")
st.caption("PC-first mechanical water-meter reader · calibrated against the two supplied reference photos")


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


def draw_calibration(image, roi, dials):
    canvas = image.copy()
    h, w = canvas.shape[:2]
    x1, y1, x2, y2 = pixel_roi(roi, w, h)
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (40, 220, 40), 3)
    cv2.putText(canvas, "5-digit register", (x1, max(24, y1 - 9)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 220, 40), 2, cv2.LINE_AA)
    for dial in dials:
        cx = int(round(dial["center"][0] * w))
        cy = int(round(dial["center"][1] * h))
        radius = int(round(dial["radius"] * min(w, h)))
        cv2.circle(canvas, (cx, cy), radius, (0, 165, 255), 2)
        cv2.drawMarker(canvas, (cx, cy), (0, 80, 255), cv2.MARKER_CROSS, 18, 2)
        cv2.putText(canvas, dial["name"], (cx - radius, cy - radius - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 165, 255), 2, cv2.LINE_AA)
    return canvas


def read_digits(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Upscale the small mechanical register before OCR.
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    reader = get_reader()
    results = reader.readtext(
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
            "Select one of your original meter photos",
            options=reference_images,
            format_func=lambda p: p.name,
        )
    else:
        st.warning(
            "No reference photos found. Copy your two original WhatsApp images into "
            "data/reference/ and refresh this page, or switch to Upload a new photo."
        )

image_source = selected_reference if selected_reference is not None else uploaded

if image_source is not None:
    if isinstance(image_source, Path):
        raw = image_source.read_bytes()
        pil = ImageOps.exif_transpose(Image.open(image_source)).convert("RGB")
    else:
        raw = image_source.getvalue()
        from io import BytesIO
        pil = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
    image_key = hashlib.sha1(raw).hexdigest()
    image = image_to_bgr(pil)
    height, width = image.shape[:2]

    st.sidebar.header("Image calibration")
    preset_keys = list(presets_data)
    preset_labels = {key: presets_data[key]["label"] for key in preset_keys}
    preset_choice = st.sidebar.selectbox(
        "Choose the matching reference framing",
        options=preset_keys,
        format_func=lambda key: preset_labels[key],
        help="The close and wide reference photos have different framing. Select the one that matches the uploaded photo."
    )
    selected = presets_data[preset_choice]
    roi_default = selected["integer_register_roi"]

    st.sidebar.caption("Fine-tune the green register rectangle if needed.")
    roi_values = []
    labels = ["Register left", "Register top", "Register right", "Register bottom"]
    for index, label in enumerate(labels):
        lo, hi = (0.0, 0.95) if index < 2 else (0.05, 1.0)
        roi_values.append(st.sidebar.slider(
            label, min_value=lo, max_value=hi, value=float(roi_default[index]),
            step=0.001, format="%.3f", key=f"{image_key}_{preset_choice}_roi_{index}"
        ))
    roi = tuple(roi_values)

    dial_values = []
    with st.sidebar.expander("Fine-tune the four dial circles", expanded=False):
        for dial_index, base_dial in enumerate(selected["dials"]):
            st.markdown(f"**{base_dial['name']}**")
            cx = st.slider("Center X", 0.0, 1.0, float(base_dial["center"][0]), 0.001,
                           key=f"{image_key}_{preset_choice}_dx_{dial_index}")
            cy = st.slider("Center Y", 0.0, 1.0, float(base_dial["center"][1]), 0.001,
                           key=f"{image_key}_{preset_choice}_dy_{dial_index}")
            radius = st.slider("Radius", 0.02, 0.20, float(base_dial["radius"]), 0.001,
                               key=f"{image_key}_{preset_choice}_dr_{dial_index}")
            dial_values.append({"name": base_dial["name"], "center": [cx, cy], "radius": radius})

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Calibration overlay")
        overlay = draw_calibration(image, roi, dial_values)
        st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), width="stretch")
        st.caption("Green = five black digit windows. Orange = the four fractional dial faces. Cross = dial center.")
    with right:
        st.subheader("Register crop preview")
        x1, y1, x2, y2 = pixel_roi(roi, width, height)
        register_crop = image[y1:y2, x1:x2]
        st.image(cv2.cvtColor(register_crop, cv2.COLOR_BGR2RGB), use_container_width=True)
        st.write(f"Image: {width} × {height} px · ROI: ({x1}, {y1})–({x2}, {y2})")
        st.info("Check that the green rectangle includes all five black digit wheels and excludes the printed Q3 text below.")

    if st.button("Analyze meter", type="primary"):
        if x2 <= x1 or y2 <= y1:
            st.error("Invalid register ROI.")
            st.stop()
        with st.spinner("Running CPU OCR... First run may download EasyOCR weights."):
            integer, raw_results = read_digits(register_crop)
            confidence = float(np.mean([item[2] for item in raw_results])) if raw_results else 0.0
            annotated = draw_calibration(image, roi, dial_values)
            payload = {
                "status": "needs_review",
                "integer_digits": integer if len(integer) == 5 else None,
                "reading_m3": None,
                "ocr_confidence": round(confidence, 4),
                "ocr_raw": [{"text": item[1], "confidence": round(item[2], 4)} for item in raw_results],
                "selected_reference_preset": preset_choice,
                "register_roi_pixels": [x1, y1, x2, y2],
                "dial_centers_pixels": [
                    {"name": d["name"], "center": [int(round(d["center"][0] * width)),
                                                     int(round(d["center"][1] * height))],
                     "radius": int(round(d["radius"] * min(width, height)))}
                    for d in dial_values
                ],
                "note": "Dial positions are calibrated for overlay only. Dial pointer values and the complete meter reading are not yet validated."
            }
            st.session_state[f"result_{image_key}"] = payload
            st.session_state[f"overlay_{image_key}"] = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

    result = st.session_state.get(f"result_{image_key}")
    if result:
        st.divider()
        st.subheader("OCR result")
        if result["integer_digits"]:
            st.metric("Black register (m³)", result["integer_digits"])
        else:
            st.warning(f"OCR returned {result['ocr_raw']}; expected exactly five digits. Verify the crop before trusting the result.")
        st.write(f"Mean OCR confidence: {result['ocr_confidence']:.3f}")
        st.image(st.session_state[f"overlay_{image_key}"], caption="Calibration used for this analysis", use_container_width=True)
        st.download_button(
            "Download result JSON", json.dumps(result, indent=2),
            file_name="watermeter_result.json", mime="application/json"
        )
else:
    st.info(
        "Place your two original photos in data/reference/ to select them here, "
        "or choose 'Upload a new photo' from the sidebar."
    )
    st.caption("Prototype only — verify readings manually. Fractional dial interpretation is not yet validated.")
