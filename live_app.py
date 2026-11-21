from __future__ import annotations

import json
import math
import time
from pathlib import Path

import cv2
import easyocr
import numpy as np
import streamlit as st

from src.watermeter.camera_stream import LatestFrameCamera

WEIGHTS = {"x0.1": 0.1, "x0.01": 0.01, "x0.001": 0.001, "x0.0001": 0.0001}
PRESETS = json.loads(Path("configs/reference_presets.json").read_text(encoding="utf-8"))["reference_presets"]

st.set_page_config(page_title="WaterMeterVision Live", page_icon="💧", layout="wide")
st.title("WaterMeterVision | ESP32-CAM Live Demo")
st.caption("Continuous live video · PC-side OpenCV/EasyOCR · manual trigger")


@st.cache_resource
def get_reader():
    return easyocr.Reader(["en"], gpu=False, verbose=False)


@st.cache_resource
def get_camera(url):
    return LatestFrameCamera(url)


def pixel_roi(roi, w, h):
    x1, y1, x2, y2 = roi
    return (max(0, min(w - 1, int(round(x1 * w)))),
            max(0, min(h - 1, int(round(y1 * h)))),
            max(1, min(w, int(round(x2 * w)))),
            max(1, min(h, int(round(y2 * h)))))


def dial_geometry(dial, w, h):
    return (int(round(dial["center"][0] * w)),
            int(round(dial["center"][1] * h)),
            max(5, int(round(dial["radius"] * min(w, h)))))


def read_digits(crop):
    if crop.size == 0:
        return "", []
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    results = get_reader().readtext(gray, allowlist="0123456789", detail=1,
                                    paragraph=False, text_threshold=0.35,
                                    low_text=0.25, link_threshold=0.25)
    found = []
    for box, text, confidence in results:
        digits = "".join(c for c in text if c.isdigit())
        if digits:
            found.append((min(p[0] for p in box), digits, float(confidence)))
    found.sort(key=lambda x: x[0])
    return "".join(x[1] for x in found), found


def detect_pointer(image, dial):
    h, w = image.shape[:2]
    cx, cy, radius = dial_geometry(dial, w, h)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red = (((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 170)) &
           (hsv[:, :, 1] >= 75) & (hsv[:, :, 2] >= 55))
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    annulus = (dist >= radius * 0.25) & (dist <= radius * 0.90)
    ys, xs = np.where(red & annulus)
    ratio = len(xs) / max(1, int(np.count_nonzero(annulus)))
    if len(xs) < 12:
        return {"name": dial["name"], "value": None, "confidence": 0.0,
                "angle_degrees": None, "tip": None, "center": [cx, cy],
                "status": "Pointer not detected"}
    idx = int(np.argmax((xs - cx) ** 2 + (ys - cy) ** 2))
    tx, ty = int(xs[idx]), int(ys[idx])
    angle = (math.degrees(math.atan2(ty - cy, tx - cx)) + 90.0) % 360.0
    confidence = 0.82 if ratio <= 0.15 else (0.48 if ratio <= 0.24 else 0.25)
    return {"name": dial["name"], "value": round(angle / 36.0, 3),
            "confidence": confidence, "angle_degrees": round(angle, 2),
            "tip": [tx, ty], "center": [cx, cy],
            "status": "Experimental estimate" if confidence >= 0.7 else "Needs manual review"}


def draw_overlay(image, roi, dials, pointer_results=None):
    out = image.copy()
    h, w = out.shape[:2]
    x1, y1, x2, y2 = pixel_roi(roi, w, h)
    cv2.rectangle(out, (x1, y1), (x2, y2), (40, 220, 40), 2)
    cv2.putText(out, "BLACK DIGITS ROI", (x1, max(20, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 220, 40), 2)
    by_name = {p["name"]: p for p in (pointer_results or [])}
    for dial in dials:
        cx, cy, r = dial_geometry(dial, w, h)
        cv2.circle(out, (cx, cy), r, (0, 165, 255), 2)
        cv2.drawMarker(out, (cx, cy), (0, 165, 255), cv2.MARKER_CROSS, 12, 2)
        item = by_name.get(dial["name"])
        if item and item["tip"]:
            cv2.arrowedLine(out, (cx, cy), tuple(item["tip"]), (0, 220, 0), 2)
    return out


def analyze(frame, roi, dials, preset):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = pixel_roi(roi, w, h)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid digit ROI. Adjust the green rectangle.")
    digits, ocr = read_digits(frame[y1:y2, x1:x2])
    pointers = [detect_pointer(frame, d) for d in dials]
    valid = [p for p in pointers if p["value"] is not None and p["confidence"] >= 0.7]
    fractional = sum(p["value"] * WEIGHTS[p["name"].lower()] for p in valid)
    all_valid = len(digits) == 5 and len(valid) == 4
    return {
        "status": "experimental_candidate" if all_valid else "needs_review",
        "integer_digits": digits if len(digits) == 5 else None,
        "fractional_dials": pointers,
        "fractional_estimate_m3": round(fractional, 6) if valid else None,
        "candidate_reading_m3": round(int(digits) + fractional, 6) if all_valid else None,
        "ocr_confidence": round(float(np.mean([x[2] for x in ocr])) if ocr else 0.0, 4),
        "ocr_raw": [{"text": x[1], "confidence": round(x[2], 4)} for x in ocr],
        "preset": preset, "frame_size": [w, h],
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "warning": "Experimental only: pointer zero-angle mapping and end-to-end accuracy are not validated. Do not use for billing."
    }, draw_overlay(frame, roi, dials, pointers)


with st.sidebar:
    st.header("ESP32-CAM")
    stream_url = st.text_input("MJPEG stream URL", "http://192.168.137.222:81/stream")
    st.caption("CameraWebServer home page: http://192.168.137.222. The stream is normally on port 81 at /stream.")
    st.header("Meter calibration")
    preset = st.selectbox("Starting preset", list(PRESETS),
                          format_func=lambda k: PRESETS[k]["label"])
    cfg = PRESETS[preset]
    defaults = cfg["integer_register_roi"]
    labels = ["Register left", "Register top", "Register right", "Register bottom"]
    roi = tuple(st.slider(labels[i], 0.0 if i < 2 else 0.05,
                          0.95 if i < 2 else 1.0, float(defaults[i]), 0.001,
                          key="roi_" + preset + "_" + str(i))
                for i in range(4))
    dials = []
    with st.expander("Fine-tune four rotary dials", expanded=True):
        for i, dial in enumerate(cfg["dials"]):
            st.markdown("**" + dial["name"] + "**")
            cx = st.slider("Center X", 0.0, 1.0, float(dial["center"][0]), 0.001, key="cx_" + preset + str(i))
            cy = st.slider("Center Y", 0.0, 1.0, float(dial["center"][1]), 0.001, key="cy_" + preset + str(i))
            radius = st.slider("Radius", 0.02, 0.20, float(dial["radius"]), 0.001, key="r_" + preset + str(i))
            dials.append({"name": dial["name"], "center": [cx, cy], "radius": radius})

if not stream_url.strip():
    st.error("Enter the camera stream URL.")
    st.stop()

camera = get_camera(stream_url.strip())
frame0 = None
for _ in range(20):
    frame0 = camera.latest()
    if frame0 is not None:
        break
    time.sleep(0.15)

if frame0 is None:
    st.warning("Waiting for camera: " + camera.last_error)
    st.info("Test http://192.168.137.222:81/stream in a browser on the same local network.")
    st.stop()

h, w = frame0.shape[:2]
st.success("Camera connected · " + str(w) + " × " + str(h) + " · newest frame is continuously refreshed")

@st.fragment(run_every=0.4)
def live_panel():
    frame = camera.latest()
    if frame is None:
        st.warning(camera.last_error or "No frame received.")
        return
    left, right = st.columns([1.6, 1])
    with left:
        preview = draw_overlay(frame, roi, dials)
        st.image(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB),
                 caption="Live stream · green = digit ROI · circles = dial ROIs",
                 use_container_width=True)
    with right:
        st.subheader("Manual trigger")
        st.write("Live video continues. CV starts only when you press Trigger.")
        if st.button("TRIGGER — READ METER", type="primary", use_container_width=True):
            shot = camera.latest()
            if shot is None:
                st.error("No fresh frame available.")
            else:
                with st.spinner("Running OCR and rotary-pointer detection on the PC..."):
                    try:
                        result, annotated = analyze(shot, roi, dials, preset)
                        st.session_state["live_result"] = result
                        st.session_state["live_annotated"] = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                    except Exception as exc:
                        st.error("Analysis failed: " + str(exc))
        result = st.session_state.get("live_result")
        if result:
            st.divider()
            st.metric("Black digits", result["integer_digits"] or "Needs review")
            st.metric("Fractional estimate (m³)", result["fractional_estimate_m3"] if result["fractional_estimate_m3"] is not None else "Unavailable")
            candidate = result["candidate_reading_m3"]
            st.metric("Candidate total (m³)", format(candidate, ".4f") if candidate is not None else "Needs review")
            st.caption("Status: " + result["status"] + " · OCR confidence: " + str(result["ocr_confidence"]))
            for p in result["fractional_dials"]:
                value = "Not detected" if p["value"] is None else format(p["value"], ".2f") + " / 10"
                st.write("**" + p["name"] + ":** " + value + " · confidence " + str(p["confidence"]))
            st.image(st.session_state["live_annotated"], caption="Triggered frame analysis", use_container_width=True)
            st.download_button("Download result JSON", json.dumps(result, indent=2),
                               file_name="watermeter_live_result.json", mime="application/json")
            st.warning(result["warning"])

live_panel()
