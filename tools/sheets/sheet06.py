#!/usr/bin/env python3
"""Sheet 6 - Dual Active Bridge, v6: both half bridges (Q9 / Q10, Q11 / Q12) and the split capacitors are on the
two DAB power cards (sheet 2); the off-board transformer TR1 (excluded from board) is wired to the SW and MID
terminals of those cards. Nothing of the DAB power stage is left on the baseboard except the secondary shunt R64
(sheet 8) between the card's DC- terminal (DAB_GROUND) and ISOPGND."""
from _common import *  # noqa: F401,F403

sh = sheet("06_dual_active_bridge.kicad_sch")
tr1 = sh.place("ETD34_TRAN_1P1S", "TR1", g(82), g(57), value="ETD34 TRAN 1P1S")
for n in (1, 2, 3, 4):
    sh.no_connect(*tr1.pin(n))
sh.text("v6: TR1 is not on the PCB (excluded from board). Its leads go to the DAB cards:", g(20), g(84))
sh.text("  1 = SW of the DAB primary card, 2 = MID of the DAB primary card,", g(20), g(87))
sh.text("  3 = SW of the DAB secondary card, 4 = MID of the DAB secondary card.", g(20), g(90))
sh.text("The transformer leakage is the series inductance; the split capacitors (3 + 3 x 2.2 uF) are on the cards.", g(20), g(93))
sh.save()
print("sheet06: written")
