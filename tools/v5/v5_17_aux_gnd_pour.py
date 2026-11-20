#!/usr/bin/env python3
"""v5 step 17 (run once, kipy): GND pour on In2.Cu under the aux flyback controller
(routing pass 5 follow-up, reports/v5_layout/routing_pass5.md on branch routing-pass5; user 2026-11-20:
"Go with your recommendation").

The GND planes of the primary logic (In1 / In4) end at y -20.7. South of that the aux flyback (U18 and its small
parts, x 67 .. 82.9, y -21.6 .. -54.6) had only tracks for GND, and pass 5 left seven GND pads open, shut in by
signal tracks that were routed first. This step adds a GND pour on In2.Cu over the primary aux area PX
(tools/v5/card_layout.py AUX_AREAS), from y -21.6 (0.7 mm south of the VCC pour on In2) to the area's south edge.

In2 and not In1 / In4: those are 0.10 mm from the outer layers, where DC+ (F.Cu pour) and the drain pads of U18
(B.Cu) are; In2 is 0.65 mm from F.Cu and 0.76 mm from B.Cu. Zone clearance 1.0 mm (vias of the 450 V nets pass
through it); the through-hole pads T1-11 / T1-12 keep their own 2.0 / 2.5 mm. The pour is tied to GND at the
through-hole pad T1-2; the vias of the GND pads come with the routing.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T  # noqa: E402
import card_layout as L  # noqa: E402

NAME = "v5 aux P In2.Cu GND"
b = Board(5017)
if any(z.GetZoneName() == NAME for z in b.b.Zones()):
    raise SystemExit("v5 step 17 already applied (zone exists)")
px = L.AUX_AREAS["PX"][1]
x0, x1 = min(p[0] for p in px), max(p[0] for p in px)
y0 = min(p[1] for p in px)
Y1 = -21.6
prio = max(z.GetAssignedPriority() for z in b.b.Zones() if not z.GetIsRuleArea()) + 1
b.zone("In2.Cu", [(x0, y0), (x1, y0), (x1, Y1), (x0, Y1)], "GND", NAME, prio, clearance=1.0)
b.save("v5 step 17: GND pour on In2 under the aux flyback controller")

B2 = pcbnew.LoadBoard(b.b.GetFileName())
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
z = next(z for z in B2.Zones() if z.GetZoneName() == NAME)
fill = z.GetFilledPolysList(pcbnew.In2_Cu)
print(f"  fill: {fill.OutlineCount()} island(s), {fill.Area() / 1e12:.1f} mm2 of {(x1 - x0) * (Y1 - y0):.1f} mm2")
if fill.OutlineCount() != 1:
    raise SystemExit("the pour is not one island")
pcbnew.SaveBoard(B2.GetFileName(), B2)
