#!/usr/bin/env python3
"""Phase 3 step: the shared tool p2k.assign_nets (proteus2kicad) with this board's paths and v4
deviations (tools/board_common.py). Run under tools/p2k/bin/kipy; see tools/make_pcb.sh.

Usage: tools/p2k/bin/kipy tools/assign_nets.py [--check]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common  # noqa: E402,F401  (configures p2k.pcb)
from p2k import assign_nets  # noqa: E402


if __name__ == "__main__":
    assign_nets.main()
