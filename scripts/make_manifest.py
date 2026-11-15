import argparse,csv
from pathlib import Path

p=argparse.ArgumentParser(description="Create a human-labeling CSV for meter images")
p.add_argument("--images",default="data/raw")
p.add_argument("--out",default="data/labels/manifest.csv")
a=p.parse_args()
root=Path(a.images)
images=sorted(x for x in root.rglob("*") if x.suffix.lower() in {".jpg",".jpeg",".png",".bmp"})
fields=["image_path","meter_id","meter_family","reading_m3","digit_1","digit_2","digit_3","digit_4","digit_5","dial_x0_1","dial_x0_01","dial_x0_001","dial_x0_0001","lighting","blur","glare","occlusion","split","reviewer","notes"]
out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
with out.open("w",newline="",encoding="utf-8-sig") as f:
    writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
    for image in images:
        writer.writerow({"image_path":image.as_posix(),"meter_family":"same_meter_family_v1"})
print(f"Created {len(images)} rows: {out}")
