#!/usr/bin/env python3
"""v4 fix 15 (run once, kipy): cable-tie anchors next to the soldered lead pins that did not get an
M4 terminal in fix 13 (user decision 2026-11-01, "option 2"): each wire gets a second, independent
mechanical fixing besides the solder joint (IEC 61010-1 internal wiring) - a cable tie (2.5-3.6 mm)
through two 3.0 mm NPTH holes 5.5 mm apart, footprint ac_psu:CableTie_NPTH_2x3.0mm_P5.5mm, board-only
reference TIE_<lead>.

Positions (IPC frame) from /tmp/claude-1000/v4term/ties.py: hole edges 3-8 mm from the pin copper
(the tie clamps the insulation), nearer to their own pin than to any other terminal, >= 0.5 mm from
every pad/track/via of any net, outside every courtyard, >= 1 mm from the board edge, not within
5 mm of both primary and ISO copper, the strap underneath clear of bottom-side parts; among those
the nearest, preferring the direction of the nearest board edge and little pour cut. Pours refill
around the holes. ACIN2, PE4, PE6, PE7, PE8, DAB_PRI_1/2 and DAB_SEC_1/2 have no such spot
(courtyards of the neighbouring parts / board edge); STATUS.md."""
import math

import pcbnew
from v4board import Board, P, T, load_fp

TIES = {   # lead ref: (hole 1, hole 2)
    "ACIN1": ((-116.811, -49.562), (-112.922, -53.451)),
    "ACOUT1": ((-97.3, -9.25), (-97.3, -3.75)),
    "ACOUT2": ((-117.533, 36.097), (-118.956, 30.785)),
    "PE1": ((-60.75, -60.25), (-60.75, -65.75)),
    "PE2": ((-124.456, -55.422), (-119.144, -53.999)),
    "PE3": ((-91.746, -70.632), (-88.996, -65.868)),
    "PE5": ((-61.4, 31.35), (-61.4, 25.85)),
    "AFE_OUT": ((54.071, -72.982), (51.321, -68.218)),
}
FPID = "ac_psu:CableTie_NPTH_2x3.0mm_P5.5mm"

b = Board(4115)
if b.fp("TIE_PE1") is not None:
    raise SystemExit("fix 15 already applied")
for lead, ((x1, y1), (x2, y2)) in TIES.items():
    fp = load_fp(FPID)
    fp.SetReference("TIE_" + lead)
    fp.SetValue("cable tie")
    b.b.Add(fp)
    fp.thisown = False
    fp.SetPosition(P((x1 + x2) / 2, (y1 + y2) / 2))
    fp.SetOrientationDegrees(math.degrees(math.atan2(y2 - y1, x2 - x1)))
    got = sorted((round(T(p.GetPosition().x), 2), round(-T(p.GetPosition().y), 2)) for p in fp.Pads())
    want = sorted([(round(x1, 2), round(y1, 2)), (round(x2, 2), round(y2, 2))])
    if max(math.hypot(a[0] - c[0], a[1] - c[1]) for a, c in zip(got, want)) > 0.02:
        raise SystemExit(f"TIE_{lead}: holes at {got}, wanted {want}")
    b.log.append(f"TIE_{lead}: cable-tie anchor, NPTH 2 x 3.0 mm at ({x1:.3f},{y1:.3f}) and ({x2:.3f},{y2:.3f})")
b.save("fix 15: cable-tie anchors next to 8 soldered lead pins")
