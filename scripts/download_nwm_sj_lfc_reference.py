#!/usr/bin/env python3
"""Download NWM SJ-LFC (FD2) gallery photos as normalized JPEG references.

The origin may serve WebP/PNG or an anti-bot HTML page even when the URL ends
in .jpg. We inspect the actual response and decode it instead of trusting the
filename or requiring JPEG magic bytes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

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


def fetch_image(url: str, timeout: int) -> Image.Image:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": SOURCE_PAGE,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "unknown")
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read(300).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} while downloading {url}. Server says: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error downloading {url}: {exc.reason}") from exc

    try:
        image = Image.open(BytesIO(payload))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        preview = payload[:180].decode("utf-8", errors="replace")
        raise RuntimeError(
            f"URL did not return a decodable image (HTTP {status}, "
            f"Content-Type={content_type}, {len(payload)} bytes). "
            f"Response starts with: {preview!r}"
        ) from exc
    return image.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/external/nwm_sj_lfc_reference")
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--force", action="store_true", help="Download again and replace existing images")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []

    for filename, url in IMAGES:
        path = out / filename
        try:
            if args.force or not path.exists():
                image = fetch_image(url, args.timeout)
                image.save(path, format="JPEG", quality=95, optimize=True)
                time.sleep(0.4)
            # Validate even cached/existing files and hash the normalized JPEG.
            with Image.open(path) as check:
                check.verify()
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
            print(f"[OK] {path} ({path.stat().st_size:,} bytes)")
        except Exception as exc:
            failures.append((filename, str(exc)))
            print(f"[FAILED] {filename}: {exc}")

    if rows:
        with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        (out / "README.txt").write_text(
            "NWM SJ-LFC (FD2) product-gallery reference images.\\n"
            "These images have no verified per-image dial/odometer ground truth.\\n"
            "They are visual references only, not a labeled training dataset.\\n\\n"
            f"Source page: {SOURCE_PAGE}\\n"
            "Check the source site's rights before training, redistribution, or commercial use.\\n",
            encoding="utf-8",
        )
        print(f"\\nDownloaded/validated {len(rows)} of {len(IMAGES)} reference images.")
        print(f"Manifest: {out / 'manifest.csv'}")

    if failures:
        print("\\nSome images could not be downloaded:")
        for filename, error in failures:
            print(f" - {filename}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
