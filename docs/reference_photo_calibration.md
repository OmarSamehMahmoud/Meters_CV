# Reference photo ROI calibration

Two different framings of the same meter were supplied on 2026-11-12:

- `WhatsApp Image 2026-11-12 at 3.15.33 PM.jpeg`: close framing.
- `WhatsApp Image 2026-11-12 at 3.15.32 PM.jpeg`: wide framing.

The previous single normalized profile was visibly offset for these photos. The PC app now provides separate manually measured presets in `configs/reference_presets.json`.

## Using the presets

1. Run `streamlit run app.py`.
2. Upload one of the reference photos.
3. Select the matching framing in the sidebar.
4. Inspect the overlay before pressing Analyze:
   - green rectangle: five black odometer windows only;
   - orange circles: four printed fractional dial faces;
   - cross: dial center.
5. Fine-tune the register rectangle or dial circles with the sidebar controls if the camera framing differs.

## Important

The two photos have different scale and vertical placement, so their coordinates are not interchangeable. These presets are calibrated for the two supplied images, not for every future camera position. Once the AI Thinker ESP32-CAM is mounted in its final fixed position, capture a calibration image and create a dedicated preset for that exact installation.

The current OCR output is a hypothesis, not a billing-grade result. Dial circles are positioned for visualization only; pointer angle-to-value mapping still needs separate calibration.


## Source-of-truth correction

The two user-supplied photographs listed above are the source of truth for this project's calibration. The NWM PDF is only a technical specification reference. Do not use PDF-rendered illustrations as photographs, and do not substitute the manufacturer's product-gallery images for the user's supplied meter photos. The separate gallery downloader is optional product-inspection material only.

The user-provided provisional reading is five black digits `00000` and fractional value `0.0899 m³` (89.9 L). Preserve this as a human-provided reference note, not as an automatically verified label.
