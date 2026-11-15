#!/usr/bin/env python3
"""Download real product photographs from the NWM SJ-LFC (FD2) manufacturer page.

These are photographs of the physical meter, not PDF drawings. They are product
photographs (studio shots), not field-installation images and not a labeled
training dataset. Check the manufacturer's terms before commercial reuse.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

PRODUCT_PAGE = (
    "https://www.nbwatermeters.com/residential-water-meter/"
    "single-jet-water-meter/single-jet-liquid-sealed-type-cold-water.html"
)

PHOTOS = [
    ("sj_lfc_fd2_photo_01.jpg",
     "https://www.nbwatermeters.com/uploads/43019/page/"
     "single-jet-liquid-sealed-type-cold-water71f2a.jpg"),
    ("sj_lfc_fd2_photo_02.jpg",
     "https://www.nbwatermeters.com/uploads/202543019/"
     "single-jet-liquid-sealed-type-cold-water33a6f665-d739-45ed-b7b9-e221e2b9fd8d.jpg"),
    ("sj_lfc_fd2_photo_03.jpg",
     "https://www.nbwatermeters.com/uploads/202543019/"
     "single-jet-liquid-sealed-type-cold-water78f7e185-603e-4775-9d44-75d3d4886972.jpg"),
    ("sj_lfc_fd2_photo_04.jpg",
     "https://www.nbwatermeters.com/uploads/202543019/"
     "single-jet-liquid-sealed-type-cold-water9cbef39c-ef73-4ccc-a650-7aecc628f0c3.jpg"),
    ("sj_lfc_fd2_photo_05.jpg",
     "https://www.nbwatermeters.com/uploads/202543019/"
     "single-jet-liquid-sealed-type-cold-waterc9b8f3e5-f4af-4cc8-9f05-5232a3e4f866.jpg"),
]


def fetch(url: str, timeout: int, attempts: int) -> bytes:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": PRODUCT_PAGE,
    }
    last_error = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
            if not payload:
                raise RuntimeError("server returned an empty response")
            if not content_type.lower().startswith("image/"):
                raise RuntimeError(
                    f"expected image content, got Content-Type={content_type!r}; "
                    f"body starts with {payload[:100]!r}"
                )
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"download failed after {attempts} attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/external/nwm_sj_lfc_real_photos")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    for filename, url in PHOTOS:
        target = out / filename
        if target.exists() and not args.force:
            print(f"[cached] {target}")
            payload = target.read_bytes()
        else:
            print(f"[download] {url}")
            payload = fetch(url, args.timeout, args.attempts)
            try:
                from io import BytesIO
                with Image.open(BytesIO(payload)) as im:
                    im.verify()
                with Image.open(BytesIO(payload)) as im:
                    im = im.convert("RGB")
                    im.save(target, format="JPEG", quality=95)
            except Exception as exc:
                raise RuntimeError(
                    f"{url} returned data that Pillow cannot decode as an image: {exc}"
                ) from exc
            payload = target.read_bytes()
            print(f"[OK] {target} ({len(payload):,} bytes)")

        with Image.open(target) as im:
            width, height = im.size
            fmt = im.format
        rows.append({
            "file": filename,
            "source_url": url,
            "product_page": PRODUCT_PAGE,
            "model": "NWM SJ-LFC (FD2)",
            "image_type": "manufacturer_product_photograph",
            "photo_context": "studio_product_photo_not_field_installation",
            "width": width,
            "height": height,
            "format": fmt,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "ground_truth_reading": "",
            "annotation_status": "unlabeled_reference_only",
        })

    manifest = out / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    (out / "README.txt").write_text(
        "NWM SJ-LFC (FD2) manufacturer product photographs\n"
        "These are real photographs of the physical product from the manufacturer's "
        "product gallery, not images extracted from the PDF. They are studio/product "
        "shots, not field-installation photos. They have no verified meter readings "
        "and must not be treated as labeled training samples.\n\n"
        f"Product page: {PRODUCT_PAGE}\n"
        "Review image rights/permission with NWM before redistribution or commercial use.\n",
        encoding="utf-8",
    )
    print(f"\nDownloaded/verified {len(rows)} photographs.")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
