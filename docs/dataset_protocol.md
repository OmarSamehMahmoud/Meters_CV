# Dataset collection and labeling protocol

Collect images from many distinct physical meters of this same face design. Keep the camera mount, focus and distance representative of deployment.

Each image needs: meter_id, timestamp, image_path, verified integer register digits (five ordered characters), four dial values, final reading in m3, lighting, blur/glare/occlusion flags, reviewer.

Include all digits 0-9 in every wheel position and especially wheel transitions. For each dial, cover the full 360° range, including near-zero wraparound. Capture day/night, shadows, reflections, dirt, condensation and modest camera displacement.

Split train/validation/test by physical meter_id, never randomly by image. Report exact full-reading accuracy, per-wheel accuracy, litre absolute error, false-accept rate, abstention rate and performance per meter.
