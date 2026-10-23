#!/usr/bin/env python3
"""v4 fix 3 (run once, kipy): 1 nF 0402 filter caps C88 (ADA2) and C89 (ADA3) to GND, bottom side
under U11 (In1.Cu GND plane), each with a via onto the F.Cu input track and a GND via."""
from v4board import Board

b = Board(4103)
# C88: ADA2 via on the F.Cu ADA2 track (y -8.5), cap pads horizontal, GND via right of it
b.add_part("C88", "bottom", (59.6, -9.35), (60.56, -9.35))
b.via(59.6, -8.5, "ADA2")
b.track("B.Cu", [(59.6, -8.5), (59.6, -9.35)], 0.2, "ADA2")
b.via(61.4, -9.35, "GND")
b.track("B.Cu", [(60.56, -9.35), (61.4, -9.35)], 0.3, "GND")
# C89: ADA3 via on the F.Cu ADA3 diagonal, cap pads vertical, GND via below
b.add_part("C89", "bottom", (57.6, -7.55), (57.6, -8.51))
b.via(57.6, -6.741, "ADA3")
b.track("B.Cu", [(57.6, -6.741), (57.6, -7.55)], 0.2, "ADA3")
b.via(57.6, -9.35, "GND")
b.track("B.Cu", [(57.6, -8.51), (57.6, -9.35)], 0.3, "GND")
b.save("fix 3: C88/C89 on ADA2/ADA3")
