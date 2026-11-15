# Analysis Output

This folder stores the visual analysis outputs for the two supplied water-meter reference photos.

## Annotated previews
- [Close reference annotated preview](close_reference_annotated.svg)
- [Wide reference annotated preview](wide_reference_annotated.svg)

## Overlay legend
- Green rectangle: five black odometer digit windows.
- Orange circles: four fractional dial faces.
- Red cross: estimated dial center.

## Calibration data
The corresponding normalized ROI coordinates are stored in [reference_presets.json](../configs/reference_presets.json).

These are manually measured, photo-specific starting ROIs. The two source photos have different scale and framing, so their presets must not be mixed. Dial pointer angle interpretation and OCR accuracy remain unvalidated.
