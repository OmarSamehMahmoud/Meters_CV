from __future__ import annotations
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image, ImageOps
from .digit_model import TinyDigitCNN

def _load_bgr(path):
    pil=ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.asarray(pil),cv2.COLOR_RGB2BGR)

def _prepare_five(image, roi, overlap=0.08):
    h,w=image.shape[:2]; x1,y1,x2,y2=roi
    reg=image[int(y1*h):int(y2*h),int(x1*w):int(x2*w)]
    if reg.size==0: raise ValueError("Empty integer register ROI; recalibrate meter profile.")
    rh,rw=reg.shape[:2]; cell=rw/5.0; batch=[]
    for i in range(5):
        left=max(0,int(i*cell-overlap*cell)); right=min(rw,int((i+1)*cell+overlap*cell))
        crop=cv2.cvtColor(reg[:,left:right],cv2.COLOR_BGR2GRAY)
        crop=cv2.resize(crop,(32,48),interpolation=cv2.INTER_AREA)
        crop=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(4,4)).apply(crop)
        batch.append(crop.astype(np.float32)/255.0)
    return torch.from_numpy(np.stack(batch)[:,None,:,:])

def predict_five_digits(image_path: str, profile: dict, checkpoint_path: str, device: str="cpu"):
    checkpoint=torch.load(checkpoint_path,map_location=device,weights_only=True)
    model=TinyDigitCNN().to(device); model.load_state_dict(checkpoint["model_state"]); model.eval()
    image=_load_bgr(image_path); x=_prepare_five(image,profile["integer_register_roi"]).to(device)
    with torch.no_grad():
        probs=torch.softmax(model(x),dim=1)
        confidence,pred=probs.max(dim=1)
    digits="".join(str(int(v)) for v in pred.cpu().tolist())
    scores=[round(float(v),4) for v in confidence.cpu().tolist()]
    return {"integer_digits":digits,"digit_confidences":scores,
            "mean_digit_confidence":round(float(np.mean(scores)),4),
            "digit_model_version":"tiny-digit-cnn-0.1"}
