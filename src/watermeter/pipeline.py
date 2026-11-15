from __future__ import annotations
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
from .dials import detect_red_pointer_angle, angle_to_dial_value

def load_image(path: str | Path):
    pil=ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.asarray(pil),cv2.COLOR_RGB2BGR)

def _crop_norm(img, roi):
    h,w=img.shape[:2]; x1,y1,x2,y2=roi
    return img[max(0,int(y1*h)):min(h,int(y2*h)),max(0,int(x1*w)):min(w,int(x2*w))]

def run_pipeline(image_path: str, profile_path: str):
    image=load_image(image_path)
    profile=json.loads(Path(profile_path).read_text(encoding="utf-8"))
    register=_crop_norm(image,profile["integer_register_roi"])
    dials=[]
    h,w=image.shape[:2]
    for item in profile["dials"]:
        center=(int(item["center"][0]*w),int(item["center"][1]*h))
        radius=int(item["radius"]*min(w,h))
        angle,support=detect_red_pointer_angle(image,center,radius)
        estimate=None if angle is None else angle_to_dial_value(angle,item.get("zero_angle_deg",270),item.get("clockwise",True))
        dials.append({"name":item["name"],"angle_deg":angle,"dial_estimate":estimate,
                      "heuristic_support":round(support,3),"trusted":False})
    return {
      "reading_m3":None,
      "integer_digits":None,
      "integer_register_crop_shape":list(register.shape),
      "fractional_dials":dials,
      "confidence":0.0,
      "status":"needs_review",
      "quality_flags":["digit_model_not_trained","dial_calibration_unverified","meter_roi_not_field_calibrated"],
      "image_shape":[h,w],
      "model_version":"pc-baseline-0.1"
    }
