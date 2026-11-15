from __future__ import annotations
import cv2
import numpy as np

def detect_red_pointer_angle(image: np.ndarray, center: tuple[int,int], radius: int):
    """Return pointer angle in image coordinates (0°=right, 90°=up), or None.

    Heuristic prototype only. Validate on labeled dial images before use.
    """
    h,w=image.shape[:2]; cx,cy=center
    x1,y1=max(0,cx-radius),max(0,cy-radius)
    x2,y2=min(w,cx+radius),min(h,cy+radius)
    crop=image[y1:y2,x1:x2]
    if crop.size==0: return None,0.0
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    m1=cv2.inRange(hsv,np.array([0,65,45]),np.array([12,255,255]))
    m2=cv2.inRange(hsv,np.array([165,65,45]),np.array([180,255,255]))
    mask=cv2.bitwise_or(m1,m2)
    yy,xx=np.where(mask>0)
    if len(xx)<8: return None,0.0
    dx=xx-(cx-x1); dy=yy-(cy-y1)
    dist=np.hypot(dx,dy)
    keep=dist>0.22*radius
    if keep.sum()<5: return None,0.0
    # Farthest red pixels approximate the narrow pointer tip, not the hub.
    threshold=np.quantile(dist[keep],0.88)
    tip=keep & (dist>=threshold)
    vx,vy=float(np.mean(dx[tip])),float(np.mean(dy[tip]))
    angle=(np.degrees(np.arctan2(-vy,vx))+360)%360
    support=min(1.0,float(keep.sum())/max(20,0.15*radius*radius))
    return float(angle),support

def angle_to_dial_value(angle: float, zero_angle: float, clockwise: bool=True) -> float:
    delta=(angle-zero_angle)%360 if clockwise else (zero_angle-angle)%360
    return (delta/36.0)%10.0
