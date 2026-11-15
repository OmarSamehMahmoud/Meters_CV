"""Controlled perturbations for fixed-camera reference images.
These variants are NOT independent labeled readings and must not be used to
claim digit generalization or to form a train/test split.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cv2
import numpy as np

def augment(image, rng):
    h,w=image.shape[:2]
    angle=float(rng.uniform(-1.2,1.2)); scale=float(rng.uniform(.985,1.015))
    M=cv2.getRotationMatrix2D((w/2,h/2),angle,scale)
    M[:,2]+=np.array([rng.uniform(-.006,.006)*w,rng.uniform(-.006,.006)*h])
    out=cv2.warpAffine(image,M,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    out=cv2.convertScaleAbs(out,alpha=float(rng.uniform(.88,1.12)),beta=float(rng.uniform(-12,12)))
    if rng.random()<.35: out=cv2.GaussianBlur(out,(3,3),float(rng.uniform(.2,.8)))
    if rng.random()<.35:
        noise=rng.normal(0,float(rng.uniform(1,4)),out.shape).astype(np.float32)
        out=np.clip(out.astype(np.float32)+noise,0,255).astype(np.uint8)
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="data/reference")
    p.add_argument("--output",default="data/augmented_reference")
    p.add_argument("--variants",type=int,default=20)
    p.add_argument("--seed",type=int,default=42)
    a=p.parse_args(); src=Path(a.input); dst=Path(a.output); dst.mkdir(parents=True,exist_ok=True)
    files=sorted(x for x in src.rglob("*") if x.suffix.lower() in {".jpg",".jpeg",".png"})
    if not files: raise SystemExit(f"No reference images found in {src}")
    rng=np.random.default_rng(a.seed)
    for f in files:
        image=cv2.imread(str(f))
        if image is None: continue
        for i in range(a.variants):
            cv2.imwrite(str(dst/f"{f.stem}_aug_{i:03d}.jpg"),augment(image,rng),[cv2.IMWRITE_JPEG_QUALITY,95])
    print(f"Generated {len(files)*a.variants} correlated robustness variants in {dst}.")
    print("They are not new independent meters or ground-truth digit labels.")
if __name__=="__main__": main()
