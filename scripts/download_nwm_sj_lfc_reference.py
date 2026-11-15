#!/usr/bin/env python3
"""Download the exact NWM SJ-LFC/SJ-WDC certificate and extract its figures."""
from __future__ import annotations
import argparse, csv, hashlib, urllib.error, urllib.request
from pathlib import Path
import fitz

PDF_URL = "https://www.nwmeurope.cz/wp-content/uploads/2022/01/sj-lfc-sj-wdc.pdf"
FIGURES = [
    (5, "sj_lfc_figure3_plastic_meter.png", "SJ-LFC plastic-body meter illustration"),
    (6, "sj_lfc_figure5_assembly_drawing.png", "SJ-LFC assembly drawing with front register and four dials"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/external/nwm_sj_lfc_certificate")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 100 <= args.dpi <= 600:
        parser.error("--dpi must be between 100 and 600")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdf_path = out / "sj-lfc-sj-wdc.pdf"
    if args.force or not pdf_path.exists():
        req = urllib.request.Request(PDF_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept": "application/pdf,*/*",
        })
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "unknown")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not download certificate: {exc}") from exc
        if not payload.startswith(b"%PDF-"):
            preview = payload[:160].decode("utf-8", errors="replace")
            raise RuntimeError(f"Expected PDF, got Content-Type={content_type}, {len(payload)} bytes: {preview!r}")
        pdf_path.write_bytes(payload)
        print(f"[downloaded] {pdf_path} ({len(payload):,} bytes)")
    else:
        print(f"[cached] {pdf_path}")

    doc = fitz.open(pdf_path)
    rows = []
    for page_no, filename, description in FIGURES:
        if page_no > len(doc):
            raise RuntimeError(f"PDF has {len(doc)} pages; requested page {page_no}")
        pix = doc[page_no - 1].get_pixmap(dpi=args.dpi, alpha=False)
        image_path = out / filename
        pix.save(image_path)
        rows.append({
            "file": filename, "source_pdf": PDF_URL, "pdf_page_1_based": page_no,
            "figure_description": description,
            "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "asset_type": "technical_illustration_not_real_meter_photo",
            "ground_truth_reading": "", "annotation_status": "geometry_reference_only",
        })
        print(f"[OK] PDF page {page_no} -> {image_path} ({pix.width}x{pix.height})")
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out / "README.txt").write_text(
        "Exact NWM SJ-LFC/SJ-WDC figures extracted from the certificate.\n"
        "PDF page 5 / Figure 3: SJ-LFC plastic-body meter illustration.\n"
        "PDF page 6 / Figure 5: SJ-LFC assembly drawing and front register layout.\n"
        "These are technical illustrations, not photographs or a labeled dataset.\n"
        f"Source PDF: {PDF_URL}\n"
        "Check document rights before redistribution or commercial use.\n",
        encoding="utf-8",
    )
    print(f"Done: {out}")

if __name__ == "__main__":
    main()
