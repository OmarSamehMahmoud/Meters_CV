from __future__ import annotations

import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import easyocr
import numpy as np
import streamlit as st

from src.watermeter.camera_stream import LatestFrameCamera

ROOT = Path(__file__).resolve().parent
CHANNELS = json.loads((ROOT / "configs" / "camera_channels.json").read_text(encoding="utf-8"))["cameras"]
PRESETS = json.loads((ROOT / "configs" / "reference_presets.json").read_text(encoding="utf-8"))["reference_presets"]
WEIGHTS = {"x0.1": 0.1, "x0.01": 0.01, "x0.001": 0.001, "x0.0001": 0.0001}
OCR_LOCK = threading.Lock()

st.set_page_config(
    page_title="RAGURA WM | 8-Camera Control",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: radial-gradient(ellipse at 15% 0%, #14263a 0%, #0b1220 42%, #080d17 100%); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #0d1726; border-right: 1px solid #26364b; }
    .block-container { padding-top: 1.2rem; max-width: 1900px; }
    .wm-hero { padding: 18px 22px; border: 1px solid #263b52; border-radius: 18px;
        background: linear-gradient(115deg, rgba(18,39,60,.96), rgba(12,24,40,.92));
        box-shadow: 0 12px 40px rgba(0,0,0,.22); margin-bottom: 14px; }
    .wm-eyebrow { color:#55d6be; font-size:11px; letter-spacing:2.4px; font-weight:800; }
    .wm-title { color:#f2f7fc; font-size:29px; font-weight:800; letter-spacing:-.7px; margin:4px 0; }
    .wm-sub { color:#9db0c5; font-size:13px; }
    .wm-card { border:1px solid #2b3e55; border-radius:15px; padding:12px;
        background: linear-gradient(160deg, rgba(19,34,52,.98), rgba(12,22,36,.98));
        box-shadow: 0 8px 24px rgba(0,0,0,.18); }
    .wm-card-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
    .wm-cam { color:#edf5ff; font-weight:800; font-size:15px; letter-spacing:.7px; }
    .wm-id { color:#7f98b4; font-size:10px; letter-spacing:1.2px; }
    .wm-reading { color:#f3f8ff; font-size:24px; font-weight:800; letter-spacing:1px; }
    .wm-label { color:#8da4bd; font-size:10px; text-transform:uppercase; letter-spacing:1.3px; }
    .wm-muted { color:#9bb0c5; font-size:11px; }
    div[data-testid="stMetric"] { background:rgba(22,40,60,.72); border:1px solid #2a4058; padding:10px 13px; border-radius:12px; }
    div[data-testid="stMetricLabel"] { color:#9bb0c5; }
    div[data-testid="stMetricValue"] { color:#f4f8fc; }
    .stButton > button[kind="primary"] { border:0; background:linear-gradient(100deg,#12a88c,#087f9b); color:white; font-weight:800; }
    .stButton > button { border-radius:10px; }
    div[data-testid="stExpander"] { border:1px solid #2b4058; border-radius:10px; background:rgba(13,27,43,.7); }
    hr { border-color:#26384e; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_reader():
    return easyocr.Reader(["en"], gpu=False, verbose=False)


@st.cache_resource
def get_camera(url: str):
    # Streamlit cache shares one reader for identical URLs.
    # In demo mode, all 8 logical channels use one physical ESP32-CAM stream.
    return LatestFrameCamera(url)


def pixel_roi(roi, w, h):
    x1, y1, x2, y2 = roi
    return (
        max(0, min(w - 1, int(round(x1 * w)))),
        max(0, min(h - 1, int(round(y1 * h)))),
        max(1, min(w, int(round(x2 * w)))),
        max(1, min(h, int(round(y2 * h)))),
    )


def dial_geometry(dial, w, h):
    return (
        int(round(dial["center"][0] * w)),
        int(round(dial["center"][1] * h)),
        max(5, int(round(dial["radius"] * min(w, h)))),
    )


def read_digits(crop):
    if crop.size == 0:
        return "", []
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    # EasyOCR Reader is shared by all channels; serialize OCR access for safety.
    with OCR_LOCK:
        results = get_reader().readtext(
            gray, allowlist="0123456789", detail=1, paragraph=False,
            text_threshold=0.35, low_text=0.25, link_threshold=0.25,
        )
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
    cv2.rectangle(out, (x1, y1), (x2, y2), (55, 220, 160), 2)
    cv2.putText(out, "DIGITS ROI", (x1, max(20, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (55, 220, 160), 2)
    by_name = {p["name"]: p for p in (pointer_results or [])}
    for dial in dials:
        cx, cy, radius = dial_geometry(dial, w, h)
        cv2.circle(out, (cx, cy), radius, (0, 165, 255), 2)
        cv2.drawMarker(out, (cx, cy), (0, 165, 255), cv2.MARKER_CROSS, 12, 2)
        item = by_name.get(dial["name"])
        if item and item["tip"]:
            cv2.arrowedLine(out, (cx, cy), tuple(item["tip"]), (0, 220, 0), 2)
    return out


def analyze(frame, roi, dials, channel_id):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = pixel_roi(roi, w, h)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid digit ROI. Adjust the channel calibration.")
    digits, ocr = read_digits(frame[y1:y2, x1:x2])
    pointers = [detect_pointer(frame, dial) for dial in dials]
    valid = [p for p in pointers if p["value"] is not None and p["confidence"] >= 0.7]
    fractional = sum(p["value"] * WEIGHTS[p["name"].lower()] for p in valid)
    all_valid = len(digits) == 5 and len(valid) == 4
    result = {
        "channel_id": channel_id,
        "status": "experimental_candidate" if all_valid else "needs_review",
        "integer_digits": digits if len(digits) == 5 else None,
        "fractional_dials": pointers,
        "fractional_estimate_m3": round(fractional, 6) if valid else None,
        "candidate_reading_m3": round(int(digits) + fractional, 6) if all_valid else None,
        "ocr_confidence": round(float(np.mean([x[2] for x in ocr])) if ocr else 0.0, 4),
        "ocr_raw": [{"text": x[1], "confidence": round(x[2], 4)} for x in ocr],
        "frame_size": [w, h],
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "warning": "Experimental only. Dial zero-angle calibration and end-to-end accuracy are not validated; do not use for billing.",
    }
    return result, draw_overlay(frame, roi, dials, pointers)


def channel_geometry(channel):
    preset = channel.get("preset", next(iter(PRESETS)))
    cfg = PRESETS[preset]
    return list(cfg["integer_register_roi"]), [dict(d) for d in cfg["dials"]]


def current_channel_geometry(channel):
    default_roi, default_dials = channel_geometry(channel)
    channel_id = channel["id"]
    roi = [
        float(st.session_state.get(f"{channel_id}_roi_slider_{i}", value))
        for i, value in enumerate(default_roi)
    ]
    dials = []
    for i, dial in enumerate(default_dials):
        dials.append({
            "name": dial["name"],
            "center": [
                float(st.session_state.get(f"{channel_id}_cx_{i}", dial["center"][0])),
                float(st.session_state.get(f"{channel_id}_cy_{i}", dial["center"][1])),
            ],
            "radius": float(st.session_state.get(f"{channel_id}_r_{i}", dial["radius"])),
        })
    return roi, dials


# One stream worker per unique HTTP URL; duplicate demo URLs share a single
# underlying ESP32 connection instead of opening eight connections to one board.
camera_by_url = {}
for channel in CHANNELS:
    url = channel["stream_url"].strip()
    if url:
        camera_by_url[url] = get_camera(url)

with st.sidebar:
    st.markdown("## 💧 RAGURA WM")
    st.caption("8-channel local meter monitoring")
    st.markdown("---")
    st.markdown("### Network architecture")
    st.success("LOCAL HTTP · NO CLOUD")
    st.caption("The ESP32-CAM exposes an HTTP MJPEG endpoint. The PC connects over a local link; internet access is not required.")
    st.markdown("### Demo configuration")
    st.info("All 8 logical channels currently point to one physical camera/IP. One stream is shared; each channel has its own ROI and trigger.")
    st.markdown("### Processing")
    workers = st.select_slider("Parallel channel workers", options=[1, 2, 4, 8], value=4)
    st.caption("OCR is serialized safely; image/dial processing runs in worker threads.")
    st.markdown("---")
    st.markdown("### Channel addresses")
    for ch in CHANNELS:
        st.caption(f'{ch["name"]}  ·  {ch["ip_label"]}')


st.markdown("""
<div class="wm-hero">
  <div class="wm-eyebrow">INDUSTRIAL METER INTELLIGENCE · LOCAL EDGE SYSTEM</div>
  <div class="wm-title">WATERMETERVISION <span style="color:#55d6be">/ CONTROL CENTER</span></div>
  <div class="wm-sub">Eight independent meter stations · live MJPEG monitoring · on-demand computer vision · local HTTP transport</div>
</div>
""", unsafe_allow_html=True)

# Resolve each unique stream once and collect current frames.
frames_by_url = {url: camera.latest() for url, camera in camera_by_url.items()}
connected_urls = {url for url, camera in camera_by_url.items() if camera.connected and camera.latest() is not None}
online_channels = sum(1 for ch in CHANNELS if ch["stream_url"] in connected_urls)
col1, col2, col3, col4 = st.columns(4)
col1.metric("CAMERA CHANNELS", f"{online_channels:02d} / 08", "Logical stations online")
col2.metric("METER STATIONS", "08", "Configured")
col3.metric("TRANSPORT", "HTTP / MJPEG", "Local network")
col4.metric("PROCESSING", "PC / CPU", "Trigger-based")

st.markdown("### LIVE CAMERA WALL")
st.caption("4 × 2 channel layout. Each station has its own calibration, trigger and result panel.")

# Per-channel geometry persists in session state and is independently adjustable.
geometries = {ch["id"]: current_channel_geometry(ch) for ch in CHANNELS}

# A single "trigger all" captures all latest frames first, then processes channels
# concurrently. The same test camera can therefore emulate 8 separate stations.
toolbar_left, toolbar_right = st.columns([3, 1])
with toolbar_left:
    st.markdown("**Station operations**")
    st.caption("Trigger one station independently, or capture all eight stations together.")
with toolbar_right:
    trigger_all = st.button("⚡ TRIGGER ALL 8", type="primary", use_container_width=True)

if trigger_all:
    jobs = []
    for ch in CHANNELS:
        frame = frames_by_url.get(ch["stream_url"])
        if frame is not None:
            roi, dials = current_channel_geometry(ch)
            jobs.append((ch, frame.copy(), roi, dials))
    if not jobs:
        st.error("No camera frames are available. Check the HTTP stream URLs and local network.")
    else:
        results = st.session_state.setdefault("channel_results", {})
        with st.spinner(f"Capturing {len(jobs)} stations and processing on the PC..."):
            with ThreadPoolExecutor(max_workers=int(workers)) as pool:
                future_map = {
                    pool.submit(analyze, frame, roi, dials, ch["id"]): ch
                    for ch, frame, roi, dials in jobs
                }
                for future in as_completed(future_map):
                    ch = future_map[future]
                    try:
                        result, annotated = future.result()
                        results[ch["id"]] = {
                            "result": result,
                            "annotated": cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                        }
                    except Exception as exc:
                        results[ch["id"]] = {"error": str(exc)}
        st.session_state["channel_results"] = results
        st.success(f"Trigger batch completed for {len(jobs)} channels.")

@st.fragment(run_every=0.8)
def camera_wall():
    results = st.session_state.get("channel_results", {})
    for row_start in (0, 4):
        cols = st.columns(4, gap="medium")
        for offset, col in enumerate(cols):
            ch = CHANNELS[row_start + offset]
            url = ch["stream_url"]
            camera = camera_by_url.get(url)
            frame = camera.latest() if camera else None
            result_data = results.get(ch["id"], {})
            with col:
                with st.container(border=True):
                    st.markdown(
                    f'<div class="wm-card-head"><div><div class="wm-cam">{ch["name"]}</div>'
                    f'<div class="wm-id">{ch["meter_id"]} · {ch["ip_label"]}</div></div></div>',
                    unsafe_allow_html=True,
                )
                    if frame is not None:
                        roi, dials = current_channel_geometry(ch)
                        preview = draw_overlay(frame, roi, dials)
                        preview = cv2.resize(preview, (480, int(480 * preview.shape[0] / preview.shape[1])))
                        st.image(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB), use_container_width=True)
                        st.markdown('<span style="color:#55d6be;font-size:11px">● STREAM RECEIVING</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            '<div style="height:145px;border:1px dashed #52677e;border-radius:10px;display:flex;'
                            'align-items:center;justify-content:center;color:#93a8bd;background:#101d2c">WAITING FOR HTTP FRAME</div>',
                            unsafe_allow_html=True,
                        )
                        error = camera.last_error if camera else "No URL configured"
                        st.caption(error[:100])
                    st.markdown('<div class="wm-label">Latest meter reading · m³</div>', unsafe_allow_html=True)
                    if "result" in result_data:
                        reading = result_data["result"].get("candidate_reading_m3")
                        digits = result_data["result"].get("integer_digits") or "REVIEW"
                        st.markdown(
                            f'<div class="wm-reading">{format(reading, ".4f") if reading is not None else "NEEDS REVIEW"}</div>'
                            f'<div class="wm-muted">Register: {digits} · OCR confidence: {result_data["result"]["ocr_confidence"]:.2f}</div>',
                            unsafe_allow_html=True,
                        )
                    elif "error" in result_data:
                        st.error(result_data["error"])
                    else:
                        st.markdown('<div class="wm-reading">— — — — —</div><div class="wm-muted">No trigger result yet</div>', unsafe_allow_html=True)

                    if st.button("TRIGGER READ", key=f'trigger_{ch["id"]}', use_container_width=True):
                        if frame is None:
                            st.error("No frame received from this camera.")
                        else:
                            roi, dials = current_channel_geometry(ch)
                            with st.spinner(f'Processing {ch["name"]}...'):
                                try:
                                    result, annotated = analyze(frame.copy(), roi, dials, ch["id"])
                                    results[ch["id"]] = {
                                        "result": result,
                                        "annotated": cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                                    }
                                    st.session_state["channel_results"] = results
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Analysis failed: {exc}")

                    with st.expander("⚙ CALIBRATION / CHANNEL SETTINGS"):
                        roi, dials = current_channel_geometry(ch)
                        st.caption("Adjust normalized coordinates for this station only.")
                        labels = ["Register left", "Register top", "Register right", "Register bottom"]
                        for i, label in enumerate(labels):
                            lo, hi = (0.0, 0.95) if i < 2 else (0.05, 1.0)
                            st.slider(
                                label, lo, hi, float(roi[i]), 0.001,
                                key=f'{ch["id"]}_roi_slider_{i}',
                            )
                        for i, dial in enumerate(dials):
                            st.markdown(f'**{dial["name"]}**')
                            cx = st.slider("Center X", 0.0, 1.0, float(dial["center"][0]), 0.001, key=f'{ch["id"]}_cx_{i}')
                            cy = st.slider("Center Y", 0.0, 1.0, float(dial["center"][1]), 0.001, key=f'{ch["id"]}_cy_{i}')
                            radius = st.slider("Radius", 0.02, 0.20, float(dial["radius"]), 0.001, key=f'{ch["id"]}_r_{i}')

                    if "result" in result_data:
                        with st.expander("VIEW ANALYSIS DETAILS"):
                            r = result_data["result"]
                            st.write("**Black digits:**", r["integer_digits"] or "Needs review")
                            st.write("**Fractional estimate:**", r["fractional_estimate_m3"])
                            for dial in r["fractional_dials"]:
                                st.write(f'{dial["name"]}: {dial["value"]} · confidence {dial["confidence"]}')
                            st.image(result_data["annotated"], caption="Triggered frame with detection overlay", use_container_width=True)
                            st.download_button(
                                "Download station JSON",
                                json.dumps(r, indent=2),
                                file_name=f'{ch["id"]}_reading.json',
                                mime="application/json",
                                key=f'download_{ch["id"]}',
                            )

camera_wall()

st.markdown("---")
st.markdown(
    '<div style="color:#7f95ad;font-size:11px;text-align:center">'
    'WATERMETERVISION · LOCAL-FIRST ARCHITECTURE · EXPERIMENTAL CV OUTPUT · NOT FOR BILLING'
    '</div>',
    unsafe_allow_html=True,
)
