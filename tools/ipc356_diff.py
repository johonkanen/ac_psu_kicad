#!/usr/bin/env python3
"""IPC-D-356 of the board vs the Proteus file: the shared tool p2k.ipc356_diff with the v4
deviations (IPC records through tools/deviations.py, added parts with their listed nets, added
vias from lib/v4_copper.csv).

Usage: python3 tools/ipc356_diff.py [--kicad FILE] [-v]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common  # noqa: E402,F401  (configures p2k.pcb)
import deviations  # noqa: E402
from p2k import ipc356_diff  # noqa: E402

if __name__ == "__main__":
    if not deviations.proteus_mode():
        print(f"ipc356_diff: v4 deviations applied ({deviations.summary()})")
    sys.exit(ipc356_diff.main(added=deviations.added_parts(), extra_vias=[v[:3] for v in deviations.vias()]))
