#!/usr/bin/env python3
"""Sheet 7 - Auxiliary supply (PDF page 7): IW1830 flyback PWM1 from DC+ through TR2 (EF20),
20 V primary output (D2 from the aux winding, C28/C41), 5 V rail caps (C67/C58/C57), startup
resistors R43/R34/R33 + D7 into Vcc, RCD snubber R24/C62/R23/D6, feedback divider R44||R25 /
R26||R29 with C63 into Vsense via R31, sense resistors R45||R47, isolated 20V_ISO_SEC output
(D1, C36, C15, R49) referenced to ISOGND (v4; RET_ISO in v3)."""
from _common import *  # noqa: F401,F403

sh = sheet("07_auxiliary_supply.kicad_sch")

# ---- 20 V / 5 V rail capacitors (top left) -------------------------------------------------
R20V, RGND, R5V = g(20), g(34), g(48)
for x, ref, val, sym in ((g(20), "C28", "220u", "C_Polarized"), (g(28), "C41", "4.7u", "C")):
    _, t, b = vert2(sh, sym, ref, x, g(27), val, top=1)          # pin 1 = 20V
    sh.wire(t, (x, R20V)); sh.wire(b, (x, RGND))
for x, ref, val, sym in ((g(20), "C67", "100u", "C"), (g(28), "C58", "22u", "C"), (g(36), "C57", "22u", "C")):
    _, t, b = vert2(sh, sym, ref, x, g(41), val, top=1)          # pin 1 = GND, pin 2 = 5V
    sh.wire(t, (x, RGND)); sh.wire(b, (x, R5V))
sh.wire((g(20), R20V), (g(40), R20V)); sh.junction(g(28), R20V)
flagged_power(sh, "20V", g(40), R20V)
sh.wire((g(20), RGND), (g(44), RGND)); sh.junction(g(28), RGND); sh.junction(g(36), RGND)
flagged_power(sh, "GND", g(44), RGND)
sh.wire((g(20), R5V), (g(40), R5V)); sh.junction(g(28), R5V); sh.junction(g(36), R5V)
power_at(sh, "5V", (g(40), R5V), "right")
sh.text("C67: 100 uF ceramic (X5R 1206, non-polar land pattern like C57/C58; v4 clean-up, was drawn polarized).", g(20), g(116))

# ---- DC+ rail, startup chain, snubber, C68 ---------------------------------------------------
RDC = g(12)
sh.wire((g(64), RDC), (g(98), RDC))
power_at(sh, "DC+", (g(76), RDC), "up"); sh.junction(g(76), RDC)
_, t, b = vert2(sh, "C", "C68", g(70), g(19), "100n", top=2)      # 2 = DC+, 1 = GND
sh.wire(t, (g(70), RDC)); sh.junction(g(70), RDC)
sh.wire(b, down(b, 2)); power_at(sh, "GND", down(b, 2), "down")
prev = (g(64), RDC)
for ref, y in (("R43", g(20)), ("R34", g(28)), ("R33", g(36))):
    _, t, b = vert2(sh, "R", ref, g(64), y, "1M", top=1, text="left")
    sh.wire(prev, t); prev = b
RVCC = g(55)
sh.wire(prev, (g(64), RVCC))

# ---- PWM1 IW1830 ------------------------------------------------------------------------------
pwm = sh.place("IW1830", "PWM1", g(80), g(60), value="IW1830")
vcc, vsense, gnd, isense, src, d7p, d8p = (pwm.pin(n) for n in (1, 2, 3, 4, 5, 7, 8))
# Vcc node: D7 from 20V, C65/C66, startup chain, power flag
_, d7a, d7c = horiz2(sh, "D_Schottky", "D7", g(46), RVCC, "ZLLS400TA", left="A")
sh.wire(d7a, left(d7a, 2)); power_at(sh, "20V", left(d7a, 2), "left")
sh.wire(d7c, vcc)
for x, ref in ((g(52), "C66"), (g(58), "C65")):
    _, t, b = vert2(sh, "C", ref, x, g(61), "4.7u", top=1)       # 1 = Vcc node
    sh.wire(t, (x, RVCC)); sh.junction(x, RVCC)
    sh.wire(b, (x, g(70)))
sh.wire((g(52), g(70)), (g(58), g(70)))
sh.junction(g(55), g(70)); power_at(sh, "GND", (g(55), g(70)), "down")
sh.junction(g(64), RVCC)
sh.pwr_flag(g(61), RVCC, 0); sh.junction(g(61), RVCC)
sh.wire(gnd, left(gnd, 2)); power_at(sh, "GND", left(gnd, 2), "down")
# switch node: D pins 7/8 joined, up to TR2 pin 2
SW = d8p[1]
sh.wire(d7p, right(d7p, 2), (right(d7p, 2)[0], SW)); sh.junction(right(d7p, 2)[0], SW)
sh.wire(d8p, (g(100), SW))
sh.label("AUX_SWITCH_NODE", g(94), SW, 0)
# RCD snubber: DC+ -> R24 || C62 -> R23 -> D6 -> switch node
NODE = g(26)
_, t, b = vert2(sh, "R", "R24", g(90), g(19), "1M", top=1, text="left")   # 1 = DC+
sh.wire(t, (g(90), RDC)); sh.junction(g(90), RDC); sh.wire(b, (g(90), NODE))
_, t, b = vert2(sh, "C", "C62", g(98), g(19), "470p", top=1)              # 1 = DC+
sh.wire(t, (g(98), RDC)); sh.wire(b, (g(98), NODE))
sh.wire((g(90), NODE), (g(98), NODE)); sh.junction(g(94), NODE)
_, t, b = vert2(sh, "R", "R23", g(94), g(33), "100R", top=1)              # 1 = R24/C62 node
sh.wire(t, (g(94), NODE))
_, dt, db = vert2(sh, "D", "D6", g(94), g(43), "S1M", top="C")
sh.wire(b, dt)
sh.wire(db, (g(94), SW)); sh.junction(g(94), SW)
# current sense: S and I_sense joined, R45 || R47 to GND
RIS = isense[1]
sh.wire(src, right(src, 2), (right(src, 2)[0], RIS)); sh.junction(right(src, 2)[0], RIS)
sh.wire(isense, (g(110), RIS))
sh.label("AUX_ISENSE", g(103), RIS, 0)
for x, ref in ((g(104), "R45"), (g(110), "R47")):
    _, t, b = vert2(sh, "R", ref, x, g(68), "2.49R", top=1)      # 1 = AUX_ISENSE
    sh.wire(t, (x, RIS))
    sh.wire(b, (x, g(74)))
sh.junction(g(104), RIS)
sh.wire((g(104), g(74)), (g(110), g(74)))
sh.junction(g(107), g(74)); power_at(sh, "GND", (g(107), g(74)), "down")

# ---- feedback: AUX_FB -> R44 || R25 -> AUX_FEEDBACK (C63, R26, R29 to GND) -> R31 -> Vsense ---
FB, FB2 = g(84), g(90)
node = (g(20), FB)
sh.glabel("AUX_FB", g(18), FB, 180); sh.wire((g(18), FB), node)
_, dt, db = vert2(sh, "D", "D2", g(20), g(76), "ES1A", top="C")   # A = AUX_FB, C = 20V
sh.wire(db, node); sh.junction(*node)
sh.wire(dt, up(dt, 2)); power_at(sh, "20V", up(dt, 2), "up")
_, l, r = horiz2(sh, "R", "R44", g(28), FB, "39k", left=1)
sh.wire(node, l)
_, l2, r2 = horiz2(sh, "R", "R25", g(28), FB2, "15k", left=1)
sh.wire(node, (g(20), FB2), l2)
fbn = (g(36), FB)
sh.wire(r, fbn); sh.wire(r2, (g(36), FB2), fbn); sh.junction(*fbn)
sh.label("AUX_FEEDBACK", g(37), FB, 0)
RG2 = g(104)
for x, ref, val, sym, top in ((g(40), "C63", "22pF", "C", 2), (g(46), "R26", "NA", "R", 1), (g(52), "R29", "1.2k", "R", 1)):
    _, t, b = vert2(sh, sym, ref, x, g(97), val, top=top)       # upper pin = AUX_FEEDBACK
    sh.wire(t, (x, FB)); sh.junction(x, FB)
    sh.wire(b, (x, RG2))
sh.wire((g(40), RG2), (g(52), RG2)); sh.junction(g(46), RG2)
power_at(sh, "GND", (g(46), RG2), "down")
_, l, r = horiz2(sh, "R", "R31", g(60), FB, "1k", left=2)         # 2 = AUX_FEEDBACK, 1 = Vsense
sh.wire(fbn, l)
sh.wire(r, (g(66), FB), (g(66), vsense[1]), vsense)
sh.text("R26: NA (not fitted) in the PDF.", g(40), g(110))

# ---- TR2 EF20 and the isolated 20 V output -------------------------------------------------
tr2 = sh.place("EF20_AUX_TRANS", "TR2", g(132), g(30), value="EF20_AUX_TRANS")
p = tr2.pin
sh.wire(p(1), left(p(1), 2), up(left(p(1), 2), 2)); power_at(sh, "DC+", up(left(p(1), 2), 2), "up")
sh.wire(p(2), (g(100), p(2)[1]), (g(100), SW))
sh.wire(p(3), left(p(3), 2)); sh.glabel("AUX_FB", *left(p(3), 2), 180)
sh.wire(p(4), left(p(4), 2)); power_at(sh, "GND", left(p(4), 2), "left")
for n in (5, 8, 9, 10):
    sh.no_connect(*p(n))
RISO, RRET = p(7)[1], g(44)
_, d1a, d1c = horiz2(sh, "D", "D1", g(144), RISO, "ES1A", left="A")
sh.wire(p(7), d1a)
sh.wire(d1c, (g(180), RISO))
sh.wire(p(6), right(p(6), 2), (right(p(6), 2)[0], RRET), (g(180), RRET))
for x, ref, val, sym, top in ((g(152), "C36", "4.7u", "C", 1), (g(160), "C15", "220u", "C_Polarized", 1),
                              (g(168), "R49", "12.1K", "R", 2)):
    _, t, b = vert2(sh, sym, ref, x, g(38), val, top=top)       # upper pin = 20V_ISO_SEC
    sh.wire(t, (x, RISO)); sh.junction(x, RISO)
    sh.wire(b, (x, RRET)); sh.junction(x, RRET)
flagged_power(sh, "20V_ISO_SEC", g(180), RISO)
power_at(sh, "ISOGND", (g(180), RRET), "down")   # v4: was RET_ISO
sh.text("v4: the isolated 20 V return is ISOGND (v3: the PDF's ISO_GND terminal was wired to RET_iso, net RET_ISO,", g(126), g(56))
sh.text("not connected to ISOGND although U8 and the gate drivers J4/J6/J8 return 20V_ISO_SEC on ISOGND).", g(126), g(59))

# PDF notes
for i, t in enumerate(("PDF notes: vsense nominal = 1.536 V, vsense OVP threshold = 1.838 V, Isense pk = 1 V, Vpeak = 520 V",
                       "Vsense @ 1.536 V = 5.8368 Vaux; Isense ocp = 1.15 V; V5.1; 'R64 = 39k / v2 trans' (refers to R44 here)",
                       "TR1 : core 227 nH, 52/8/3 || 7/3/3/42 (note printed on this page, TR1 is on sheet 6)")):
    sh.text(t, g(20), g(122 + 3 * i))
sh.save()
print("sheet07: written")
