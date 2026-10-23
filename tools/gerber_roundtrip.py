#!/usr/bin/env python3
"""Gerber round trip vs the Proteus CADCAM gerbers: the shared tool p2k.gerber_roundtrip with
the v4 deviations (copper differences inside the areas of lib/v4_copper.csv are 'deviation',
the added vias there may have drills without a Proteus drill).

Usage: python3 tools/gerber_roundtrip.py [--check] [--kicad-dir DIR] [--keep]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common  # noqa: E402,F401  (configures p2k.pcb)
import deviations  # noqa: E402
from p2k import gerber_roundtrip  # noqa: E402

if __name__ == "__main__":
    gerber_roundtrip.main(in_area=deviations.in_area, extra_vias=deviations.vias())
