# Initial data and prototype validity

The initial prototype uses the two supplied photographs of one physical meter. The five black odometer windows visually show 00000 in both references. The four red fractional dials are affected by perspective, reflections and central hub occlusion; their pointer values have not been independently verified.

## Valid work with these references
- Lock the same-meter-family layout and initial normalized ROI.
- Test orientation, crop extraction, resizing and illumination normalization.
- Compare the two views of the same register.
- Build fixed-camera capture and image-quality checks.
- Generate mild augmented copies for preprocessing robustness experiments.

## Limits
Two views of one physical meter do not provide ten digit classes, wheel transitions, meter-to-meter variation, or independent test data. Augmentation changes appearance but does not create new ground-truth digits. It is therefore invalid to train a general 0-9 recognizer or report production accuracy from these references alone.

## Engineering decision
Treat the integer label as provisional 00000 for both references. Never use augmented copies as independent train/validation/test samples. Keep all readings in needs_review until digit classes and dial calibration are verified. This is suitable for an approval prototype, not billing or unattended deployment.
