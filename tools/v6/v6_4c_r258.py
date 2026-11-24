#!/usr/bin/env python3
"""v6 step 4c (run once, kipy): R258 33R in INU_ADCLK at the U21 output.

Planning session 2026-11-24 (rules for the sigma-delta links): the clock gets a series resistor at its driving end.
ADCLK has R22 39R at U15; INU_ADCLK (U21 pin 14 -> U4 at J9, over 100 mm) had none. R258 (0603, bottom side like
U21) stands right at U21 pin 14: pad 1 = INU_ADCLK_U21 (U21-14), pad 2 = INU_ADCLK. Staged by v6 step 1 like every
new part; this script places it and gives U21-14 its new net.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P  # noqa: E402

b = Board(6009)
B = b.b
if b.fp("R258") is not None:
    raise SystemExit("v6 step 4c already applied")
b.add_part("R258", "B", (76.5, 42.375), (76.5, 44.025))
u21 = next(p for p in b.fp("U21").Pads() if p.GetNumber() == "14")
u21.SetNet(b.net(b.pin_net[("U21", "14")]))
b.log.append(f"U21-14 -> {u21.GetNetname()}")
for p in b.fp("R258").Pads():
    b.log.append(f"R258-{p.GetNumber()} [{p.GetNetname()}] at ({T(p.GetPosition().x):.2f}, {-T(p.GetPosition().y):.2f})")
# courtyard check on the bottom side
mine = b.fp("R258").GetBoundingBox(False)      # the courtyard cache is stale right after the move
hit = [o.GetReference() for o in B.GetFootprints() if o.GetReference() != "R258"
       and (o.IsFlipped() or any(q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for q in o.Pads()))
       and o.GetCourtyard(pcbnew.B_CrtYd if o.IsFlipped() else pcbnew.F_CrtYd).OutlineCount()
       and o.GetCourtyard(pcbnew.B_CrtYd if o.IsFlipped() else pcbnew.F_CrtYd).BBox().Intersects(mine)]
if hit:
    raise SystemExit(f"R258 courtyard overlaps {hit}")
pcbnew.SaveBoard(B.GetFileName(), B)
print("\n".join(["== v6 step 4c: R258 at U21-14"] + ["  " + x for x in b.log]))
