#!/usr/bin/env python3
"""DRC of kicad/ac_psu.kicad_pcb with schematic parity: the shared tool p2k.drc (accepted
violation types in p2k_config.py DRC_ACCEPTED, justified in STATUS.md). Stdlib only.

Usage: python3 tools/drc.py [-v]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import drc  # noqa: E402

if __name__ == "__main__":
    drc.main()
