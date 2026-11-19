#!/usr/bin/env python3
"""v5 step 10 (run once, kipy): the spare isolator footprint U17 leaves the board (user 2026-11-19).

U17 (SOIC-16W across the P|I barrier at (88.0, 0.53), all pins unconnected since Proteus) was an unpopulated
spare. The user removed it from the schematic; tools/sheets/sheet11.py and tools/v5/v5_parts.py (REMOVED)
follow, and this step deletes the footprint. The slot under it stays as part of the P|I barrier.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T  # noqa: E402

b = Board(5010)
fp = b.fp("U17")
if fp is None:
    raise SystemExit("v5 step 10 already applied (U17 is not on the board)")
nets = sorted({p.GetNetname() for p in fp.Pads() if p.GetNetname() and not p.GetNetname().startswith("unconnected-")})
if nets:
    raise SystemExit(f"U17 has connected pads: {nets}")
b.log.append(f"U17 ({fp.GetFPID().GetLibItemName()}) at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f}) deleted: "
             f"16 unconnected pads")
b.b.Delete(fp)
b.save("v5 step 10: spare isolator footprint U17 removed")
