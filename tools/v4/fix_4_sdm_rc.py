#!/usr/bin/env python3
"""v4 fix 4 (run once, kipy): shunt-inductance compensation of the ADuM7701 inputs.
Series resistors R92/R93 (U4), R57/R58 (U5), R73/R74 (U6) 10R -> 12.4R (values only, same 0402
footprints), and a 100 nF C0G 1206 across VIN+/VIN- of each modulator: C90 (U4), C91 (U5),
C92 (U6), all on the bottom side.

VIN+ and VIN- are fenced in by each other and by GND1 copper at every ADuM7701, so one net jumps
through vias. U4 and U5 float on switching nodes and the F.Cu above them is a high-voltage pour
(ISODC+ above U4, PGND above U5): their jumper vias get a F.Cu pour keep-out circle of r = 1.8 mm
(via copper to pour >= 1.57 mm, like the designer's 1.5 mm between HV pours) and the jump runs on
In1.Cu (empty there). U6 (DAB shunt, ISOGND level) is on top: C92 sits under its input pins on
the bottom side with one via per net (In1/In2 are the ISOGND / 3V3_ISO planes there)."""
from v4board import Board

b = Board(4104)
for ref in ("R92", "R93", "R57", "R58", "R73", "R74"):
    b.set_value(ref, "12.4R")

# U4 (bottom): C90 below U4; VIN+ straight down from R92-1, VIN- from the R93-1 -> C51-1 track
# through In1.Cu
b.add_part("C90", "bottom", (11.708, 37.3), (8.758, 37.3))
b.track("B.Cu", [(11.708, 41.178), (11.708, 37.3)], 0.2, "Net-(U4-VIN+)")
b.via(11.678, 43.35, "Net-(U4-VIN-)")
b.track("In1.Cu", [(11.678, 43.35), (8.758, 39.0)], 0.2, "Net-(U4-VIN-)")
b.via(8.758, 39.0, "Net-(U4-VIN-)")
b.track("B.Cu", [(8.758, 39.0), (8.758, 37.3)], 0.2, "Net-(U4-VIN-)")
for x, y in ((11.678, 43.35), (8.758, 39.0)):
    b.pour_keepout("F.Cu", x, y, 1.8, f"v4 fix 4 HV keep-out U4 via ({x},{y})")

# U5 (bottom): C91 right of R57 between U5 and R48-2; VIN+ from R57-1, VIN- from the
# R58-1 -> C52-1 track through In1.Cu
b.add_part("C91", "bottom", (8.1, -62.55), (8.1, -65.5))
b.track("B.Cu", [(6.463, -62.741), (7.4, -62.741), (7.591, -62.55), (8.1, -62.55)], 0.2, "Net-(U5-VIN+)")
b.via(4.2, -62.75, "Net-(U5-VIN-)")
b.track("In1.Cu", [(4.2, -62.75), (9.3, -65.5)], 0.2, "Net-(U5-VIN-)")
b.via(9.3, -65.5, "Net-(U5-VIN-)")
b.track("B.Cu", [(9.3, -65.5), (8.1, -65.5)], 0.2, "Net-(U5-VIN-)")
for x, y in ((4.2, -62.75), (9.3, -65.5)):
    b.pour_keepout("F.Cu", x, y, 1.8, f"v4 fix 4 HV keep-out U5 via ({x},{y})")

# U6 (top): C92 on the bottom under the U6 input pins, one via per net
b.add_part("C92", "bottom", (110.075, 33.0), (107.125, 33.0))
b.track("F.Cu", [(110.56, 34.276), (111.3, 34.3)], 0.2, "Net-(U6-VIN+)")
b.via(111.3, 34.3, "Net-(U6-VIN+)")
b.track("B.Cu", [(111.3, 34.3), (110.075, 33.0)], 0.2, "Net-(U6-VIN+)")
b.via(108.6, 34.306, "Net-(U6-VIN-)")
b.track("B.Cu", [(108.6, 34.306), (107.125, 33.0)], 0.2, "Net-(U6-VIN-)")
b.save("fix 4: ADuM7701 RC compensation")
