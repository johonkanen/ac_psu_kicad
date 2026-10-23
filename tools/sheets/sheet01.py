#!/usr/bin/env python3
"""Sheet 1 - afe (PDF page 1): SiC half-bridges Q1..Q4 on the DC link, AFE shunt R48 with
J5, EMI filter CM1/CM2 with X/Y caps, inrush resistor R10 bypassed by relay R20, the two
OPA2353 difference amplifiers (filter voltage -> ADA3, mains voltage -> ADA2), PE terminals."""
from _common import *  # noqa: F401,F403

sh = sheet("01_afe.kicad_sch")

# ---- half bridges ----------------------------------------------------------------------------
DCP, PG, MID = g(28), g(82), g(55)
for qx, qhi, qlo, g_hi, g_lo, src_hi, src_lo in (
        (g(40), "Q1", "Q2", "G1_GATE_HI", "G2_GATE_LO", "G1_SOURCE_HI", "G2_SOURCE_LO"),
        (g(80), "Q3", "Q4", "G3_GATE_HI", "G4_GATE_LO", "G3_SOURCE_HI", "G4_SOURCE_LO")):
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
    if qhi == "Q1":
        sh.glabel(src_hi, col + g(6), MID, 0)
        pass
    else:
        sh.glabel(src_hi, col + g(6), MID, 90)
        sh.wire((col + g(6), MID), (col + g(12), MID))
        terminal(sh, "AFE_OUT", col + g(12), MID, "right")
        pass
sh.wire((g(40) + 2.54, DCP), (g(80) + 2.54, DCP))
sh.junction(g(60), DCP); flagged_power(sh, "DC+", g(60), DCP)
sh.wire((g(40) + 2.54, PG), (g(80) + 2.54, PG))
sh.junction(g(60), PG); flagged_power(sh, "PGND", g(60), PG)
sh.text("AFE half bridges. Q2/Q4 sources are PGND (Proteus calls them G2_Source_LO / G4_Source_LO at J1).", g(20), g(92))

# ---- R48 shunt in the Q1/Q2 leg, sensed by U5 (sheet 8) ------------------------------------
SX, SY = g(118), g(36)
r48 = sh.place("FKK5R0020FE-TR", "R48", SX, SY, value="FKK5R0020FE-TR",
               ref_at=(SX - g(3), SY - 1.27, 0, "right"), value_at=(SX - g(3), SY + 1.27, 0, "right"))
j5 = right(r48.pin(3), 16)
# v4: Kelvin connection restored - pin 1 (sense) = SHUNT1 to U5 only, pin 3 (force) = SHUNT1_FORCE -> J5
sh.wire(r48.pin(1), up(r48.pin(1), 2)); sh.glabel("SHUNT1", *up(r48.pin(1), 2), 90)
sh.wire(r48.pin(2), down(r48.pin(2), 2)); sh.glabel("SHUNT2", *down(r48.pin(2), 2), 270)
sh.wire(r48.pin(3), j5); terminal(sh, "J5", *j5, "right")
sh.label("SHUNT1_FORCE", *right(r48.pin(3), 2))
glabel_right(sh, "G1_SOURCE_HI", r48.pin(4), 6)
sh.text("R48 2 mOhm shunt: 4 = Q1/Q2 midpoint (force), 3 = SHUNT1_FORCE -> J5 (afe_1_out_measured),", SX - g(16), SY + g(14))
sh.text("1/2 = SHUNT1/SHUNT2 sense to U5 (sheet 8), which floats on SHUNT1.", SX - g(16), SY + g(17))
sh.text("v4: pins 1 and 3 are no longer tied (v3: both on SHUNT1, Kelvin sense defeated).", SX - g(16), SY + g(20))

# ---- EMI filter ---------------------------------------------------------------------------
X0, TOP, BOT = g(170), g(40), g(48)
Y = (TOP + BOT) / 2
terminal(sh, "FILTER_OUT", X0, TOP, "up")
terminal(sh, "FILTER_IN", X0, BOT, "down")
XA, XB = X0 - g(6), X0 - g(12)                      # divider columns for U1:B
sh.wire((XA, TOP), (X0, TOP)); sh.wire((XB, BOT), (X0, BOT))
sh.label("LEMOUT", X0 - g(4), TOP, 0); sh.label("FILTER_INPUT", X0 - g(10), BOT, 0)


def ycap(ref, x, row, up_, val="2n2"):
    """Y capacitor from a filter row to a PE label (pin 1 = PE side)."""
    _, t, b = vert2(sh, "C", ref, x, row - g(6) if up_ else row + g(6), val, top=1 if up_ else 2)
    if up_:
        sh.wire(b, (x, row)); sh.wire(t, up(t, 2)); return up(t, 2)
    sh.wire(t, (x, row)); sh.wire(b, down(b, 2)); return down(b, 2)


def xcap(ref, x, val="7u"):
    _, t, b = vert2(sh, "C", ref, x, Y, val, top=1)
    sh.wire(t, (x, TOP)); sh.wire(b, (x, BOT))
    sh.junction(x, TOP); sh.junction(x, BOT)


def choke(ref, x):
    cm = sh.place("WE-CMBNC", ref, x, Y, value="WE-CMBNC")
    for pin, row in ((2, TOP), (1, BOT), (3, TOP), (4, BOT)):
        sh.wire(cm.pin(pin), (cm.pin(pin)[0], row))
    return cm.pin(2)[0], cm.pin(3)[0]


def rows(x1, x2):
    sh.wire((x1, TOP), (x2, TOP)); sh.wire((x1, BOT), (x2, BOT))


c = X0 + g(6)
sh.junction(c, TOP); sh.junction(c, BOT)
sh.glabel("PE1", *ycap("C19", c, TOP, True), 90)
sh.glabel("PE1", *ycap("C20", c, BOT, False), 270)
xcap("C21", X0 + g(12))
cm1l, cm1r = choke("CM1", X0 + g(20))
rows(X0, cm1l)
c = cm1r + g(6)
sh.junction(c, TOP); sh.junction(c, BOT)
sh.glabel("PE3", *ycap("C22", c, TOP, True), 90)
sh.glabel("PE1", *ycap("C23", c, BOT, False), 270)
xcap("C24", cm1r + g(12))
sh.label("CMFILT1", cm1r + g(1), TOP, 0); sh.label("CMFILT2", cm1r + g(1), BOT, 0)
cm2l, cm2r = choke("CM2", cm1r + g(20))
rows(cm1r, cm2l)
xcap("C25", cm2r + g(8))
c = cm2r + g(14)
sh.junction(c, TOP); sh.junction(c, BOT)
sh.glabel("PE4", *ycap("C13", c, TOP, True), 90)
sh.glabel("PE2", *ycap("C14", c, BOT, False), 270)
sh.label("JEE", cm2r + g(1), TOP, 0)
E = cm2r + g(20)
rows(cm2r, E)
# inrush resistor R10 up to the mains input, relay R20 in parallel
RT = TOP - g(24)
_, r10t, r10b = vert2(sh, "R", "R10", E, TOP - g(12), "TWW10J15RE", top=1)
sh.wire(r10b, (E, TOP)); sh.wire(r10t, (E, RT))
sh.junction(E, RT)
rl = sh.place("SLA-12VDC-SL-A", "R20", E - g(22), RT + 2.54, value="SLA-12VDC-SL-A")
sh.wire(rl.pin(3), (E, RT))                                      # NO -> AC_IN_1
com1 = rl.pin(1)
sh.wire(com1, right(com1, 2), (right(com1, 2)[0], TOP))          # COM_1 -> JEE
sh.junction(right(com1, 2)[0], TOP)
glabel_right(sh, "RELAY_DRIVE", rl.pin(2), 4)                    # COIL_1
sh.wire(rl.pin(6), left(rl.pin(6), 4)); power_at(sh, "20V", left(rl.pin(6), 4), "up")   # COIL_2
sh.no_connect(*rl.pin(5))
# mains terminals
sh.wire((E, RT), (E + g(8), RT)); sh.glabel("AC_IN_1", E + g(4), RT, 90)
terminal(sh, "ACIN1", E + g(8), RT, "right")
sh.wire((E, BOT), (E + g(8), BOT)); sh.glabel("AC_IN2", E + g(4), BOT, 270)
terminal(sh, "ACIN2", E + g(8), BOT, "right")
sh.text("EMI filter between the mains (ACIN1/ACIN2) and FILTER_IN/FILTER_OUT; R10 limits inrush until R20 closes.",
        X0, TOP - g(30))


# ---- difference amplifiers -----------------------------------------------------------------
diff_amp(sh, XB, BOT, 2, ["R4", "R5", "R6"], ["R11", "R2", "R3"], ("R7", "1k"), "REF_1V65",
         ("R8", "10k"), ("R9", "100"), "ADA3", top_plus=TOP)
sh.text("U1:B measures the filter voltage (LEMOUT - FILTER_INPUT) around REF_1V65 -> ADA3.", XB - g(6), BOT + g(50))
r = diff_amp(sh, g(236), g(84), 1, ["R95", "R12", "R13"], ["R14", "R15", "R16"], ("R21", "10k"), "REF_1V65",
                  ("R17", "10k"), ("R18", "100"), "ADA2")
sh.glabel("AC_IN2", *r["plus_top"], 90); sh.glabel("AC_IN_1", *r["minus_top"], 90)
sh.text("U1:A measures the mains voltage (AC_IN2 - AC_IN_1) around REF_1V65 -> ADA2.", g(230), g(84) + g(50))

# U1 supply pins (unit C) and C26
PX, PY = g(30), g(120)
u1c = sh.place("OPA2353UA", "U1", PX, PY, unit=3, value="OPA2353UA")
sh.wire(u1c.pin(8), up(u1c.pin(8), 2)); power_at(sh, "VCC", up(u1c.pin(8), 2), "up")
sh.wire(u1c.pin(4), down(u1c.pin(4), 2)); power_at(sh, "GND", down(u1c.pin(4), 2), "down")
_, ct, cb = vert2(sh, "C", "C26", PX + g(14), PY, "100n", top=2)
sh.wire(ct, up(ct, 2)); power_at(sh, "VCC", up(ct, 2), "up")
sh.wire(cb, down(cb, 2)); power_at(sh, "GND", down(cb, 2), "down")
sh.text("3V3 / DC- in the Proteus schematic = VCC / GND", PX - g(6), PY + g(12))

# PE terminals
for i, ref in enumerate(("PE1", "PE2", "PE3", "PE4")):
    x = g(20 + 8 * i)
    terminal(sh, ref, x, g(150), "down")
    sh.wire((x, g(150)), (x, g(148)))
    sh.glabel(ref, x, g(148), 90)

sh.save()
print("sheet01: written")
