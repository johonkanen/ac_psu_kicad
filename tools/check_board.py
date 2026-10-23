#!/usr/bin/env python3
"""Board vs the IPC-D-356A file: the shared tool p2k.check_board with the v4 deviations (added
parts with their listed nets, added vias from lib/v4_copper.csv; IPC records through
tools/deviations.py).

Usage: tools/p2k/bin/kipy tools/check_board.py [--pads-only]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common  # noqa: E402,F401  (configures p2k.pcb)
import deviations  # noqa: E402
from p2k import check_board  # noqa: E402

if __name__ == "__main__":
    check_board.main(added=deviations.added_parts(), extra_vias=[v[:3] for v in deviations.vias()])
