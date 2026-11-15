# WaterMeterVision

PC-first computer-vision system for the same-family mechanical water meter shown in the project references, targeting AI Thinker ESP32-CAM (OV2640).

## Pipeline
- Fixed camera capture and quality checks
- Register ROI alignment and five-wheel digit recognition
- Four red pointer dial angle estimation
- Reading reconstruction and confidence-based rejection
- INT8 deployment feasibility evaluation for ESP32-CAM

## Status
Initial repository bootstrap. ROI calibration and model training require a straight-on image from the final camera mount and a labeled dataset. Never use unvalidated output for billing.

## Hardware
Original AI Thinker ESP32-CAM is memory-constrained. Prefer fixed geometry, classical CV, and a small int8 digit classifier; benchmark PSRAM, heap, flash and latency before deployment. Consider ESP32-S3 if resource limits are exceeded.
