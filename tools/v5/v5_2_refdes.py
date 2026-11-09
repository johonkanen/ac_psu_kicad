#!/usr/bin/env python3
"""v5 step 2 (run once, kipy): KiCad refdes for the Proteus terminals without a trailing number.

KiCad counts a reference that does not end in a digit as unannotated, and "Update PCB from
Schematic" refuses an unannotated schematic. tools/v5/v5_parts.py REFDES (lib/v5_deviations.csv
kind refdes) renames AFE_OUT, FILTER_IN and FILTER_OUT to AFE_OUT1, FILTER_IN1 and FILTER_OUT1 in
the schematic. This script gives the board footprints the same references and links them to the
renamed symbols (the generated symbol UUIDs follow the refdes). The cable-tie anchor of the
AFE_OUT lead follows: TIE_AFE_OUT -> TIE_AFE_OUT1 (board-only footprint, v4 fix 15).
No copper, pad or position changes.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v4"))
sys.path.insert(0, HERE)
from v4board import Board  # noqa: E402
import v5_parts as V  # noqa: E402

b = Board(5002)
if b.fp("AFE_OUT1") is not None:
    raise SystemExit("v5 step 2 already applied (AFE_OUT1 is on the board)")

for old, new in V.REFDES.items():
    fp = b.fp(old)
    if fp is None:
        raise SystemExit(f"v5 step 2: {old} not on the board")
    c = b.comps[new]
    fp.SetReference(new)
    fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
    b.log.append(f"{old} -> {new} (linked to its schematic symbol)")
    tie = b.fp("TIE_" + old)
    if tie is not None:
        tie.SetReference("TIE_" + new)
        b.log.append(f"TIE_{old} -> TIE_{new}")
b.save("v5 step 2: KiCad refdes AFE_OUT1, FILTER_IN1, FILTER_OUT1 (annotation)")
