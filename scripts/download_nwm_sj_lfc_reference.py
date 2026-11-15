#!/usr/bin/env python3
"""Download the publicly displayed NWM SJ-LFC (FD2) product-gallery images.

These are reference photographs, NOT a labeled training dataset. Check the
source site's rights/terms before using them for training or redistribution.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import urllib.request
from pathlib import Path

SOURCE_PAGE = (
    "https://www.nbwatermeters.com/residential-water-meter/"
    "single-jet-water-meter/single-jet-liquid-sealed-type-cold-water.html"
)
IMAGES = [
    ("sj_lfc_gallery_01.jpg", "https://www.nbwatermeters.com/uploads/43019/page/single-jet-liquid-sealed-type-cold-water71f2a.jpg"),
    ("sj_lfc_gallery_02.jpg", "https://www.nbwatermeters.com/uploads/202543019/single-jet-liquid-sealed-type-cold-water33a6f665-d739-45ed-b7b9-e221e2b9fd8d.jpg"),
    ("sj_lfc_gallery_03.jpg", "https://www.nbwatermeters.com/uploads/202543019/single-jet-liquid-sealed-type-cold-water78f7e185-603e-4775-9d44-75d3d4886972.jpg"),
    ("sj_lfc_gallery_04.jpg", "https://www.nbwatermeters.com/uploads/202543019/single-jet-liquid-sealed-type-cold-water9cbef39c-ef73-4ccc-a650-7aecc628f0c3.jpg"),
    ("sj_lfc_gallery_05.jpg", "https://www.nbwatermeters.com/uploads/202543019/single-jet-liquid-sealed-type-cold-waterc9b8f3e5-f4af-4cc8-9f05-5232a3e4f866.jpg"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/external/nwm_sj_lfc_reference")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for filename, url in IMAGES:
        path = out / filename
        if not path.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "WaterMeterVision-research/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
            if not payload.startswith(b"\xff\xd8"):
                raise RuntimeError(f"Expected JPEG image from {url}")
            path.write_bytes(payload)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({
            "image_path": filename,
            "source_url": url,
            "source_page": SOURCE_PAGE,
            "meter_model": "NWM SJ-LFC (FD2)",
            "sha256": digest,
            "ground_truth_reading": "",
            "annotation_status": "unlabeled_reference_only",
            "rights_status": "all_rights_reserved_or_unverified_check_source",
        })
        print(f"{path} ({path.stat().st_size:,} bytes)")
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / "README.txt").write_text(
        "NWM SJ-LFC (FD2) product-gallery reference images.\n"
        "These five images show the target meter family but have no verified\n"
        "per-image dial/odometer ground truth. Do not treat them as training\n"
        "examples or infer a reading from the product-gallery photos.\n\n"
        f"Source page: {SOURCE_PAGE}\n"
        "The source website displays a copyright notice. Use for local visual\n"
        "inspection only unless you obtain permission/a suitable license.\n"
        "Do not redistribute these image files or use commercially without\n"
        "checking and obtaining the required rights.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
