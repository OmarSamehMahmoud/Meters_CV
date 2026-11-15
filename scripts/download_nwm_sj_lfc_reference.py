#!/usr/bin/env python3
"""Backward-compatible entry point: download real NWM SJ-LFC product photos.

The old version of this script rendered technical PDF pages. Use
download_nwm_sj_lfc_real_photos.py for real product photographs instead.
The certificate PDF remains a geometry/specification reference only.
"""
from download_nwm_sj_lfc_real_photos import main

if __name__ == "__main__":
    main()
