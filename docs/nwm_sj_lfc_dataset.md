# NWM SJ-LFC (FD2) target-specific dataset

## What is available now

Run:

```powershell
python scripts/download_nwm_sj_lfc_reference.py
```

This downloads five product-gallery photographs from the NWM SJ-LFC (FD2)
product page into `data/external/nwm_sj_lfc_reference/` and writes a SHA-256
manifest. The images are **unlabeled visual references only**. They do not
contain verified readings, do not represent independent meter installations,
and are not enough to train or validate a reading model.

Source: https://www.nbwatermeters.com/residential-water-meter/single-jet-water-meter/single-jet-liquid-sealed-type-cold-water.html

The source website displays a copyright notice. Keep downloaded images local.
Check with the rights holder before training a commercial model, redistribution,
or including images in a public dataset.

## Target annotation schema

For every new real capture, record:

- physical_meter_id and capture_id
- original image path and SHA-256
- five black roller digits, left-to-right
- for each of the four dials: center (x,y), radius, pointer-tip (x,y),
  angle in degrees, and the interpreted fractional digit
- verified full reading in m3, capture timestamp, camera distance/orientation
- glare, blur, shadow, occlusion and reviewer notes

Do not derive ground truth from an OCR prediction. Read the meter manually,
preferably with a second independent reviewer. When a roller or pointer lies
between marks, record the transition state explicitly instead of forcing an
integer label.

## Dataset stages

1. **Reference stage:** the five downloaded gallery photos plus the two user
   reference photos. Use these only to understand geometry and test ROI tools.
2. **Calibration stage:** capture the actual installed meter from the final
   fixed camera mount. Define the register ROI and four dial ROIs once.
3. **Labeled capture stage:** collect real readings across the operating range.
   Include every roller digit, wheel carry/rollover, every dial sector, and
   near-zero wraparound. Vary lighting and mild focus/glare conditions.
4. **Evaluation stage:** split by physical meter ID, not by adjacent frames.
   Keep a held-out test set untouched until model selection is complete.

## Important limitation

The product gallery has five views of product examples, not a sequence of
known readings from one physical meter. Rotating, recoloring, or duplicating
these images does not create new ground truth. Synthetic data may be used for
software tests, but must be reported separately and must not replace real
held-out meter captures.
