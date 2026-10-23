#!/usr/bin/env python3
"""Phase 3 step: the shared tool p2k.build_pcb (proteus2kicad) with this board's paths and v4
deviations (tools/board_common.py). Run under tools/p2k/bin/kipy; see tools/make_pcb.sh.

Usage: tools/p2k/bin/kipy tools/build_pcb.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common  # noqa: E402,F401  (configures p2k.pcb)
from p2k import build_pcb  # noqa: E402
from p2k.build_pcb import load_fp  # noqa: E402,F401  (used by tools/v4/v4board.py)

if __name__ == "__main__":
    build_pcb.main()
