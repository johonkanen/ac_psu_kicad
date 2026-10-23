#!/usr/bin/env python3
"""Footprints vs the IPC-D-356A pads: the shared tool p2k.check_footprints, with the v4 added
parts (lib/v4_deviations.csv, no IPC pads) passed through so that their footprint and pad
numbers are checked instead of fitted.

Usage: python3 tools/check_footprints.py [-v]
       tools/p2k/bin/kipy tools/check_footprints.py --pcbnew [-v]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import check_footprints  # noqa: E402
import deviations  # noqa: E402

if __name__ == "__main__":
    check_footprints.main(added=deviations.added_parts())
