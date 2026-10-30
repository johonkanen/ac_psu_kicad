#!/usr/bin/env python3
"""Sheet 9 - primary side ADC (PDF page 9): SN74LV4051 input multiplexer U11, TLV316 buffer
U12 with R86/C9 RC, ADS7056 ADC AD1 with L1/C17/C18 filtered supply, R87 series array in
the SPI lines. AGND / DC- in the PDF = net GND; 3V3 = VCC."""
from _common import *  # noqa: F401,F403

sh = sheet("09_primary_side_adc.kicad_sch")

# C39 decoupling + the AGND/DC- note (top left in the PDF)
_, ct, cb = vert2(sh, "C", "C39", g(20), g(30), "1u", top=2)
sh.wire(ct, up(ct, 2)); power_at(sh, "VCC", up(ct, 2), "up")
sh.wire(cb, down(cb, 2)); power_at(sh, "GND", down(cb, 2), "down")
sh.text("AGND and DC- in the Proteus schematic are both net GND; 3V3 = VCC.", g(30), g(32))

# U11 analogue multiplexer
MX, MY = g(50), g(70)
u11 = sh.place("SN74LV4051", "U11", MX, MY, value="SN74LV4051", value_at=(MX + g(4), MY + g(24), 0, "left"))
for pin, lab in ((13, "ADA2"), (14, "ADA1"), (15, "ADA0"), (12, "ADA3"), (1, "ADA4"), (2, "ADA5"), (4, "ADA6"),
                 (11, "ADASEL0"), (10, "ADASEL1"), (9, "ADASEL2")):
    glabel_left(sh, lab, u11.pin(pin))
sh.wire(u11.pin(5), left(u11.pin(5), 4)); power_at(sh, "GND", left(u11.pin(5), 4), "left")   # X5
inh = u11.pin(6)
sh.wire(inh, left(inh, 6)); power_at(sh, "GND", left(inh, 6), "left")   # v4: was the floating net DGND
sh.text("v4: INH (pin 6) tied to GND (v3: single-pin net DGND, floating).", MX - g(8), MY + g(33))
vdd = u11.pin(16)
sh.wire(vdd, up(vdd, 2)); power_at(sh, "VCC", up(vdd, 2), "up")
vee, vss = u11.pin(7), u11.pin(8)
gy = vee[1] + g(2)
sh.wire(vee, (vee[0], gy), (vss[0], gy), vss)
sh.junction(MX, gy); power_at(sh, "GND", (MX, gy), "down")
sh.text("VDD = 3V3 (VCC), VEE = VSS = AGND (GND).", MX - g(8), MY + g(30))
sh.text("check logic", MX - g(18), MY - g(26))

# v4: 1 nF filter caps on the mux inputs ADA2 / ADA3 (ADA1 has C42 on sheet 4), next to U11
for i, (ref, lab) in enumerate((("C88", "ADA2"), ("C89", "ADA3"))):
    x = g(16 + 10 * i)
    _, ct, cb = vert2(sh, "C", ref, x, g(104), "4.7n C0G", top=1)
    sh.wire(ct, up(ct, 2)); sh.glabel(lab, *up(ct, 2), 90)
    sh.wire(cb, down(cb, 2)); power_at(sh, "GND", down(cb, 2), "down")
sh.text("v4: C88/C89 4.7n C0G (0402) with R18/R9 8.2k filter ADA2/ADA3 at 4.1 kHz; placed next to U11.", g(10), g(114))

# U12 unity-gain buffer
OX, OY = g(100), g(58)
u12 = sh.place("TLV316IDBVR", "U12", OX, OY, value="TLV316IDBVR")
inp, inn, out, vp, vn = u12.pin(3), u12.pin(4), u12.pin(1), u12.pin(5), u12.pin(2)
mx_out = u11.pin(3)
sh.wire(mx_out, (OX - g(8), mx_out[1]), (OX - g(8), inp[1]), inp)
fb_x, fb_y = OX - g(12), OY + g(14)
sh.wire(inn, (fb_x, inn[1]), (fb_x, fb_y), (OX + g(8), fb_y), (OX + g(8), out[1]))
sh.junction(OX + g(8), out[1])
RAIL = g(50)                                   # filtered 3V3 for U12 / AD1 (Proteus auto-net)
sh.wire(vp, (vp[0], RAIL))
sh.wire(vn, down(vn, 2)); power_at(sh, "GND", down(vn, 2), "down")
r86, r86l, r86r = horiz2(sh, "R", "R86", OX + g(18), out[1], "10R", left=2)
sh.wire(out, r86l)
# RC into the ADC input
cx = OX + g(26)
sh.junction(cx, out[1])
_, c9t, c9b = vert2(sh, "C", "C9", cx, out[1] + g(4), "1n", top=2)
sh.wire((cx, out[1]), c9t)
sh.wire(c9b, down(c9b, 2)); power_at(sh, "GND", down(c9b, 2), "down")

# AD1 ADC
AX, AY = g(170), g(60)
ad1 = sh.place("ADS7056", "AD1", AX, AY, value="ADS7056")
ainm, ainp, avdd, agnd = ad1.pin(8), ad1.pin(7), ad1.pin(6), ad1.pin(5)
cs, sdo, sclk, dvdd = ad1.pin(1), ad1.pin(2), ad1.pin(3), ad1.pin(4)
sh.wire(r86r, ainp)
sh.wire(ainm, left(ainm, 2)); power_at(sh, "GND", left(ainm, 2), "left")
sh.wire(agnd, down(agnd, 2)); power_at(sh, "GND", down(agnd, 2), "down")
# AVDD / DVDD fed from the rail, routed under the ADC and up on the right
UNDER = g(76)
FEED_X = g(216)
sh.wire(avdd, left(avdd, 2), (left(avdd, 2)[0], UNDER), (FEED_X, UNDER), (FEED_X, RAIL))
sh.wire(dvdd, right(dvdd, 1), (right(dvdd, 1)[0], UNDER))
sh.junction(right(dvdd, 1)[0], UNDER)
# L1 + C17/C18 on the rail
LX = g(150)
_, l1t, l1b = vert2(sh, "L", "L1", LX, g(44), "22uH", top=2)
sh.wire(l1t, up(l1t, 2)); power_at(sh, "VCC", up(l1t, 2), "up")
sh.wire(l1b, (LX, RAIL))
sh.wire((vp[0], RAIL), (FEED_X, RAIL))
sh.junction(LX, RAIL)
sh.pwr_flag(g(140), RAIL, 0); sh.junction(g(140), RAIL)
for xcol, ref in ((g(204), "C17"), (g(210), "C18")):
    _, t, b = vert2(sh, "C", ref, xcol, g(54), "100n", top=2)
    sh.wire(t, (xcol, RAIL)); sh.junction(xcol, RAIL)
    sh.wire(b, (xcol, g(58)))
sh.wire((g(204), g(58)), (g(210), g(58)))
sh.junction(g(207), g(58)); power_at(sh, "GND", (g(207), g(58)), "down")
# SPI lines through R87 (A/B/C), unit D unused (pads 4/5 have no net in the IPC)
_, ral, rar = horiz2(sh, "RESISTOR_ARRAY_4", "R87", AX + g(16), cs[1], "RESISTOR_ARRAY", left=8, unit=1, text="above")
sh.wire(cs, ral); glabel_right(sh, "CS1", rar, 2)
sh.wire(sdo, right(sdo, 4), (right(sdo, 4)[0], AY + g(8)))
_, rbl, rbr = horiz2(sh, "RESISTOR_ARRAY_4", "R87", AX + g(20), AY + g(8), "RESISTOR_ARRAY", left=7, unit=2)
sh.wire((right(sdo, 4)[0], AY + g(8)), rbl); glabel_right(sh, "SDATA1", rbr, 2)
sh.wire(sclk, right(sclk, 2), (right(sclk, 2)[0], AY + g(14)))
_, rcl, rcr = horiz2(sh, "RESISTOR_ARRAY_4", "R87", AX + g(20), AY + g(14), "RESISTOR_ARRAY", left=6, unit=3)
sh.wire((right(sclk, 2)[0], AY + g(14)), rcl); glabel_right(sh, "CLK1", rcr, 2)
rd, rdl, rdr = horiz2(sh, "RESISTOR_ARRAY_4", "R87", AX + g(20), AY + g(20), "RESISTOR_ARRAY", left=5, unit=4)
sh.no_connect(*rdl); sh.no_connect(*rdr)
sh.text("R87:D (pads 4/5) has no net in the Proteus layout.", AX + g(26), AY + g(21))
sh.save()
print("sheet09: written")
