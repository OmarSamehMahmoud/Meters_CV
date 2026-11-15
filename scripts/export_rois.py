import argparse,json
from pathlib import Path
import cv2
from src.watermeter.pipeline import load_image

p=argparse.ArgumentParser()
p.add_argument("--image",required=True); p.add_argument("--profile",default="configs/meter_profile.example.json"); p.add_argument("--out",default="runs/rois")
a=p.parse_args()
im=load_image(a.image); cfg=json.loads(Path(a.profile).read_text()); h,w=im.shape[:2]
out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
x1,y1,x2,y2=cfg["integer_register_roi"]
cv2.imwrite(str(out/"integer_register.png"),im[int(y1*h):int(y2*h),int(x1*w):int(x2*w)])
for i,d in enumerate(cfg["dials"]):
 cx,cy=int(d["center"][0]*w),int(d["center"][1]*h); r=int(d["radius"]*min(w,h))
 crop=im[max(0,cy-r):min(h,cy+r),max(0,cx-r):min(w,cx+r)]
 cv2.imwrite(str(out/f"dial_{i}.png"),crop)
print(f"Exported crops to {out}")
