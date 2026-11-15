# NWM SJ-LFC (FD2) real product photographs

This source is the manufacturer's product gallery for **NWM SJ-LFC (FD2)**:

- Product page: https://www.nbwatermeters.com/residential-water-meter/single-jet-water-meter/single-jet-liquid-sealed-type-cold-water.html
- The page identifies the brand as NWM and the model as SJ-LFC (FD2).
- It exposes five image assets named SJ-LFC-DN15(1-1) through SJ-LFC-DN15(1-5).

## Download on Windows

From the repository root:

```cmd
python -m pip install Pillow
python scripts/download_nwm_sj_lfc_real_photos.py
```

Optional re-download:

```cmd
python scripts/download_nwm_sj_lfc_real_photos.py --force
```

Output:

```text
data/external/nwm_sj_lfc_real_photos/
  sj_lfc_fd2_photo_01.jpg
  sj_lfc_fd2_photo_02.jpg
  sj_lfc_fd2_photo_03.jpg
  sj_lfc_fd2_photo_04.jpg
  sj_lfc_fd2_photo_05.jpg
  manifest.csv
  README.txt
```

## Important dataset limits

These are photographs of the physical meter from the manufacturer's product gallery. They are **studio/product photographs**, not field-installation photographs. They show a particular product presentation and do not provide independently verified ground-truth readings. They are suitable for visual inspection, geometry/ROI prototyping, and confirming the meter family, but not for claiming OCR accuracy or training a robust reading model.

Do not mix these photographs with PDF page renders or technical drawings. Keep the PDF certificate in a separate reference folder.

For a real-world training/evaluation dataset, collect photos of installed SJ-LFC/SJ-WDC meters under different lighting, distances, angles, dirt/reflections, and actual readings. Record the meter reading at capture time and split train/validation/test by physical meter, not by near-duplicate image. Ask NWM for written permission before redistribution or commercial use of their photographs.
