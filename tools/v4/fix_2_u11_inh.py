#!/usr/bin/env python3
"""v4 fix 2 (run once, kipy): U11 (SN74LV4051) pin 6 INH from the floating single-pin net DGND to
GND: pad net, and a 0.25 mm F.Cu track from pad 6 to the adjacent GND pad 7 (both 0.4 x 1.1 mm,
0.65 mm pitch; the track stays inside the pad rows)."""
from v4board import Board

b = Board(4102)
if b.fp("U11").FindPadByNumber("6").GetNetname() == "GND":
    raise SystemExit("fix 2 already applied")
b.sync_pads("U11")
b.track("F.Cu", [(59.949, -0.98), (59.299, -0.98)], 0.25, "GND")
b.save("fix 2: U11 INH -> GND")
