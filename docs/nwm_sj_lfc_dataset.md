# Exact NWM SJ-LFC / SJ-WDC reference

Authoritative visual reference:
https://www.nwmeurope.cz/wp-content/uploads/2022/01/sj-lfc-sj-wdc.pdf

The earlier gallery photographs from another website were not confirmed to
depict this exact face design and are no longer used by this workflow.

## Extract the exact figures

```powershell
python -m pip install -r requirements-pc.txt
python scripts/download_nwm_sj_lfc_reference.py
```

The script downloads the certificate and extracts:
- PDF page 5, Figure 3: SJ-LFC plastic-body meter illustration.
- PDF page 6, Figure 5: SJ-LFC assembly drawing with front register and four dials.

Output: `data/external/nwm_sj_lfc_certificate/`

These are technical illustrations, not photographs at varied readings and not
a labeled training dataset. Figure 5 is a geometry reference. Collect real
captures of this exact meter family for training and independent evaluation.
Check document rights before redistribution or commercial use.
