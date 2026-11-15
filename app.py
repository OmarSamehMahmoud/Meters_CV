from __future__ import annotations
import json
from pathlib import Path
import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageOps
from src.watermeter.pipeline import load_image
from src.watermeter.dials import detect_red_pointer_angle

PROFILE_PATH = Path("configs/meter_profile.example.json")
st.set_page_config(page_title="WaterMeterVision", page_icon="💧", layout="wide")
st.title("WaterMeterVision")
st.caption("PC-first mechanical water-meter reader · AI Thinker ESP32-CAM target")
@st.cache_resource
def get_reader():
    return easyocr.Reader(["en"], gpu=False, verbose=False)

profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
with st.sidebar:
    st.header("Meter calibration")
    st.info("Start with the example ROI, then adjust it to tightly contain the five black odometer windows. The example coordinates are approximate.")
    roi = profile["integer_register_roi"]
    x1 = st.slider("Register left", 0.0, 0.95, float(roi[0]), 0.005)
    y1 = st.slider("Register top", 0.0, 0.95, float(roi[1]), 0.005)
    x2 = st.slider("Register right", 0.05, 1.0, float(roi[2]), 0.005)
    y2 = st.slider("Register bottom", 0.05, 1.0, float(roi[3]), 0.005)
    run_dials = st.checkbox("Analyze red dials (experimental)", value=True)

uploaded = st.file_uploader("Upload a meter photo", type=["jpg","jpeg","png","bmp"])
if uploaded:
    pil = ImageOps.exif_transpose(Image.open(uploaded)).convert("RGB")
    image = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    h,w = image.shape[:2]
    left,top,right,bottom = int(x1*w),int(y1*h),int(x2*w),int(y2*h)
    if right <= left or bottom <= top:
        st.error("Invalid ROI. Right/bottom must be greater than left/top.")
        st.stop()
    crop = image[top:bottom,left:right]
    col1,col2 = st.columns(2)
    with col1:
        st.subheader("Uploaded image")
        st.image(pil, use_container_width=True)
    with col2:
        st.subheader("Integer-register ROI")
        st.image(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB), use_container_width=True)
    if st.button("Analyze meter", type="primary"):
        with st.spinner("Running CPU OCR and computer vision... First run downloads the EasyOCR weights."):
            gray = cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0,tileGridSize=(4,4)).apply(gray)
            reader = get_reader()
            results = reader.readtext(clahe, allowlist="0123456789", detail=1, paragraph=False,
                                      text_threshold=0.35, low_text=0.25, link_threshold=0.25)
            chars=[]
            for box,text,conf in results:
                digits="".join(c for c in text if c.isdigit())
                if digits:
                    xs=[p[0] for p in box]
                    chars.append((min(xs),digits,float(conf)))
            chars.sort(key=lambda item:item[0])
            integer="".join(item[1] for item in chars)
            confidence=float(np.mean([item[2] for item in chars])) if chars else 0.0
            overlay=image.copy()
            cv2.rectangle(overlay,(left,top),(right,bottom),(0,255,0),3)
            dial_results=[]
            if run_dials:
                for d in profile["dials"]:
                    cx,cy=int(d["center"][0]*w),int(d["center"][1]*h)
                    radius=int(d["radius"]*min(w,h))
                    angle,support=detect_red_pointer_angle(image,(cx,cy),radius)
                    cv2.circle(overlay,(cx,cy),radius,(255,180,0),2)
                    dial_results.append({"dial":d["name"],"pointer_angle_deg":None if angle is None else round(angle,1),
                                         "heuristic_support":round(support,3),"calibrated_value":None})
            st.session_state["analysis"]={"integer_digits":integer,"ocr_confidence":confidence,
                "ocr_raw":[{"text":v[1],"confidence":round(v[2],3)} for v in chars],
                "dial_results":dial_results,"roi":[x1,y1,x2,y2]}
            st.session_state["overlay"]=cv2.cvtColor(overlay,cv2.COLOR_BGR2RGB)
    if "analysis" in st.session_state:
        out=st.session_state["analysis"]
        st.divider()
        st.subheader("Recognition result")
        if len(out["integer_digits"]) == 5:
            st.metric("Black register (m³)",out["integer_digits"])
        else:
            st.warning(f"OCR returned '{out['integer_digits'] or 'no digits'}' — expected exactly 5 digits. Adjust ROI and retry.")
        st.write(f"Mean OCR confidence: {out['ocr_confidence']:.3f}")
        st.image(st.session_state["overlay"],caption="Detected register ROI and approximate dial regions",use_container_width=True)
        if out["dial_results"]:
            st.subheader("Red fractional dials")
            st.dataframe(out["dial_results"],use_container_width=True)
            st.caption("Dial angles are experimental diagnostics only. Values are deliberately not calculated until each dial's zero direction, rotation and scale are calibrated.")
        payload={"status":"needs_review","integer_digits":out["integer_digits"] if len(out["integer_digits"])==5 else None,
                 "reading_m3":None,"ocr_confidence":out["ocr_confidence"],"dial_results":out["dial_results"],
                 "roi":out["roi"],"note":"PC OCR prototype; verify every reading manually. Fractional dial calibration is pending."}
        st.download_button("Download result JSON",json.dumps(payload,indent=2),file_name="watermeter_result.json",mime="application/json")
else:
    st.info("Upload a photo to begin. The first analysis downloads EasyOCR's pretrained English recognition weights; subsequent runs can reuse the cached weights.")
st.caption("Prototype only — not approved for billing or safety-critical decisions.")
