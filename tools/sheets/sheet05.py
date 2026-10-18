#!/usr/bin/env python3
"""Sheet 5 - VSI (PDF page 5): SiC half bridges Q5..Q8 on the isolated DC link, INU shunt R91
with J7, output filter CM3 with X/Y caps, output relay R79 to ACOUT1, OPA2353 difference
amplifiers U7:A (filter voltage -> ISOADA1) and U7:B (output voltage -> ISOADA2)."""
from _common import *  # noqa: F401,F403

sh = sheet("05_vsi.kicad_sch")

# ---- half bridges ----------------------------------------------------------------------------
DCP, PG, MID = g(28), g(82), g(55)
for qx, qhi, qlo, g_hi, g_lo, src_hi in (
        (g(40), "Q5", "Q6", "Q5_G", "Q6_G", "Q5_S"),
        (g(80), "Q7", "Q8", "Q7_G", "Q8_G", "Q7_S")):
    hi = sh.place("C3M0065090D", qhi, qx, g(40), value="C3M0065090D")
    lo = sh.place("C3M0065090D", qlo, qx, g(70), value="C3M0065090D")
    col = hi.pin(2)[0]
    sh.wire(hi.pin(2), (col, DCP))
    sh.wire(hi.pin(3), lo.pin(2))
    sh.wire(lo.pin(3), (col, PG))
    glabel_left(sh, g_hi, hi.pin(1), 4)
    glabel_left(sh, g_lo, lo.pin(1), 4)
    sh.junction(col, MID)
    sh.wire((col, MID), (col + g(6), MID))
    if qhi == "Q5":
        sh.glabel(src_hi, col + g(6), MID, 90)
        sh.wire((col + g(6), MID), (col + g(12), MID))
        terminal(sh, "INU_OUT2", col + g(12), MID, "right")
    else:
        sh.glabel(src_hi, col + g(6), MID, 0)
sh.wire((g(40) + 2.54, DCP), (g(80) + 2.54, DCP))
sh.junction(g(60), DCP); flagged_power(sh, "ISODC+", g(60), DCP)
sh.wire((g(40) + 2.54, PG), (g(80) + 2.54, PG))
sh.junction(g(60), PG); power_at(sh, "ISOPGND", (g(60), PG), "down")
sh.text("VSI half bridges on the isolated DC link. Q6/Q8 sources are ISOPGND (Proteus: Q6_S / Q8_S at J6).", g(20), g(92))
sh.text("PDF note: IKZ50N65EH5XKSA1 (alternative switch).", g(20), g(95))

# ---- R91 shunt in the Q7/Q8 leg, sensed by U4 (sheet 10) -----------------------------------
SX, SY = g(118), g(36)
r91 = sh.place("FKK5R0020FE-TR", "R91", SX, SY, value="FKK5R0020FE-TR",
               ref_at=(SX - g(3), SY - 1.27, 0, "right"), value_at=(SX - g(3), SY + 1.27, 0, "right"))
sh.wire(r91.pin(1), up(r91.pin(1), 2)); sh.glabel("INU_SHUNT2", *up(r91.pin(1), 2), 90)
sh.wire(r91.pin(2), down(r91.pin(2), 2)); sh.glabel("INU_SHUNT1", *down(r91.pin(2), 2), 270)
glabel_right(sh, "Q7_S", r91.pin(3), 6)
sh.wire(r91.pin(4), right(r91.pin(4), 6)); terminal(sh, "J7", *right(r91.pin(4), 6), "right")
sh.text("R91 2 mOhm shunt: 3 = Q7/Q8 midpoint, 4 = inductor_input -> J7,", SX - g(16), SY + g(14))
sh.text("1/2 = INU_SHUNT2/INU_SHUNT1 sense -> U4 (sheet 10).", SX - g(16), SY + g(17))

# ---- output filter ---------------------------------------------------------------------------
X0, TOP, BOT = g(170), g(40), g(48)
Y = (TOP + BOT) / 2
terminal(sh, "J10", X0, TOP, "up")
terminal(sh, "J9", X0, BOT, "down")
XA, XB = X0 - g(6), X0 - g(12)
sh.wire((XA, TOP), (X0, TOP)); sh.wire((XB, BOT), (X0, BOT))
sh.label("INU_FILTER_INPUT", X0 - g(4), TOP, 0); sh.label("INDUCTOR_OUTPUT", X0 - g(10), BOT, 0)


def ycap(ref, x, row, up_, val="2n2"):
    _, t, b = vert2(sh, "C", ref, x, row - g(6) if up_ else row + g(6), val, top=1 if up_ else 2)
    if up_:
        sh.wire(b, (x, row)); sh.wire(t, up(t, 2)); return up(t, 2)
    sh.wire(t, (x, row)); sh.wire(b, down(b, 2)); return down(b, 2)


def xcap(ref, x, val="7u"):
    _, t, b = vert2(sh, "C", ref, x, Y, val, top=1)
    sh.wire(t, (x, TOP)); sh.wire(b, (x, BOT))
    sh.junction(x, TOP); sh.junction(x, BOT)


def rows(x1, x2):
    sh.wire((x1, TOP), (x2, TOP)); sh.wire((x1, BOT), (x2, BOT))


c = X0 + g(6)
sh.junction(c, TOP); sh.junction(c, BOT)
sh.glabel("PE6", *ycap("C30", c, TOP, True), 90)
sh.glabel("PE6", *ycap("C29", c, BOT, False), 270)
xcap("C33", X0 + g(12))
cm = sh.place("WE-CMBNC", "CM3", X0 + g(20), Y, value="WE-CMBNC")
for pin, row in ((2, TOP), (1, BOT), (3, TOP), (4, BOT)):
    sh.wire(cm.pin(pin), (cm.pin(pin)[0], row))
cml, cmr = cm.pin(2)[0], cm.pin(3)[0]
rows(X0, cml)
c = cmr + g(6)
sh.junction(c, TOP); sh.junction(c, BOT)
sh.glabel("PE7", *ycap("C32", c, TOP, True), 90)
sh.glabel("PE7", *ycap("C31", c, BOT, False), 270)
xcap("C34", cmr + g(12))
sh.label("AFE_RELAY", cmr + g(1), TOP, 0)
# relay R79: AFE_RELAY (COM_1) -> AC_OUT_1 (NO); coil from 20V_ISO_SEC, driven by Q13 (sheet 10)
xr = cmr + g(28)
E = xr + g(12)
rows(cmr, E)
rl = sh.place("SLA-12VDC-SL-A", "R79", xr, TOP - g(14), value="SLA-12VDC-SL-A")
com1 = rl.pin(1)
sh.wire(com1, (E, com1[1]), (E, TOP))
no = rl.pin(3)
sh.wire(no, (xr + g(26), no[1]))
sh.glabel("AC_OUT_1", xr + g(20), no[1], 90)
terminal(sh, "ACOUT1", xr + g(26), no[1], "right")
glabel_right(sh, "RELAY_DRIVE_ISO", rl.pin(2), 4)
sh.wire(rl.pin(6), left(rl.pin(6), 4)); power_at(sh, "20V_ISO_SEC", left(rl.pin(6), 4), "up")
sh.no_connect(*rl.pin(5))
sh.wire((E, BOT), (xr + g(26), BOT))
sh.glabel("AC_OUT_2", xr + g(20), BOT, 270)
terminal(sh, "ACOUT2", xr + g(26), BOT, "right")
sh.text("Output filter between the inverter (J9/J10, inductor on J7/J9 off-board) and ACOUT1/ACOUT2; R79 connects the output.",
        X0, TOP - g(30))

# ---- difference amplifiers -----------------------------------------------------------------
diff_amp(sh, XB, BOT, 1, ["R60", "R61", "R71"], ["R62", "R63", "R256"], ("R52", "10k"), "REF_1V65_ISO",
         ("R53", "10k"), ("R54", "8.2k"), "ISOADA1", top_plus=TOP, opamp=("OPA2353UA", "U7"))
sh.text("U7:A measures the filter voltage (INU_FILTER_INPUT - INDUCTOR_OUTPUT) around REF_1V65_ISO -> ISOADA1.",
        XB - g(6), BOT + g(50))
r = diff_amp(sh, g(236), g(84), 2, ["R65", "R66", "R67"], ["R70", "R69", "R68"], ("R46", "10k"), "REF_1V65_ISO",
                  ("R51", "10k"), ("R56", "8.2k"), "ISOADA2", opamp=("OPA2353UA", "U7"))
sh.glabel("AC_OUT_2", *r["plus_top"], 90); sh.glabel("AC_OUT_1", *r["minus_top"], 90)
sh.text("U7:B measures the output voltage (AC_OUT_2 - AC_OUT_1) around REF_1V65_ISO -> ISOADA2.", g(230), g(84) + g(50))

# U7 supply pins (unit C), C38 and C56
PX, PY = g(30), g(120)
u7c = sh.place("OPA2353UA", "U7", PX, PY, unit=3, value="OPA2353UA")
sh.wire(u7c.pin(8), up(u7c.pin(8), 2)); power_at(sh, "3V3_ISO", up(u7c.pin(8), 2), "up")
sh.wire(u7c.pin(4), down(u7c.pin(4), 2)); power_at(sh, "ISOGND", down(u7c.pin(4), 2), "down")
for i, ref in enumerate(("C38", "C56")):
    _, ct, cb = vert2(sh, "C", ref, PX + g(14 + 8 * i), PY, "100n", top=2)
    sh.wire(ct, up(ct, 2)); power_at(sh, "3V3_ISO", up(ct, 2), "up")
    sh.wire(cb, down(cb, 2)); power_at(sh, "ISOGND", down(cb, 2), "down")

# PE terminals
for i, ref in enumerate(("PE5", "PE6", "PE7")):
    x = g(20 + 8 * i)
    terminal(sh, ref, x, g(150), "down")
    sh.wire((x, g(150)), (x, g(148)))
    sh.glabel(ref, x, g(148), 90)

sh.save()
print("sheet05: written")
