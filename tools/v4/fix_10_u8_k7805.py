#!/usr/bin/env python3
"""v4 fix 10 (run once, kipy): U8 (5V_ISOL) VXO7805-1000 -> Mornsun K7805-2000R3 (5 V / 2 A, same
SIP-3 pinout 1 Vin / 2 GND / 3 Vout, 2.54 mm, Ø1.2 mm holes) for the isolated control card, with the
datasheet's (Fig. 2) input / output capacitors on the bottom side just south of U8's pins
(pins at y -20.1, x 104.36 / 106.90 / 109.44; the module body stands on the top side):
C93 10u 50V 1210 horizontal between pin 1 (20V_ISO_SEC, also in the B.Cu pour) and pin 2
(ISOGND, on the In1 ISOGND zone), C94 22u 10V 0805 vertical under pin 3 (5V_ISOL), its ISOGND
pad joined to C93's. The footprint stays (U9 shares it); its courtyard is 0.075 mm short of the
K7805's 6.85 mm body depth on the side away from J12."""
import pcbnew
from v4board import Board, P

b = Board(4110)
if b.fp("U8").GetValue() == "K7805-2000R3":
    raise SystemExit("fix 10 already applied")
b.set_value("U8", "K7805-2000R3")
b.add_part("C93", "bottom", (103.925, -22.9), (106.875, -22.9))
b.track("B.Cu", [(104.36, -20.1), (104.36, -22.9), (103.925, -22.9)], 0.6, "20V_ISO_SEC")
b.track("B.Cu", [(106.9, -20.1), (106.875, -22.9)], 0.6, "ISOGND")
b.add_part("C94", "bottom", (109.44, -22.35), (109.44, -24.25))
b.track("B.Cu", [(109.44, -20.1), (109.44, -22.35)], 0.6, "5V_ISOL")
b.track("B.Cu", [(109.44, -24.0), (106.875, -24.0), (106.875, -22.9)], 0.6, "ISOGND")
ref = b.fp("C94").GetField(pcbnew.FIELD_T_REFERENCE)       # clear of C93's pads (fix 8 rules)
ref.SetTextAngleDegrees(90)
ref.SetPosition(P(111.25, -23.3))
b.log.append("C94 reference at (111.250,-23.300) angle 90")
b.save("fix 10: U8 K7805-2000R3, C93/C94")
