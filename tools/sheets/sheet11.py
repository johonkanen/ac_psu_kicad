#!/usr/bin/env python3
"""Sheet 11 - signal isolators (PDF page 11): U15, U13, U16 Si866x digital isolators between
the VCC (3V3) side and the isolated side, U17 unpopulated spare, R22 series resistor in ADCLK.
v5 (CTRL_ISOLATION_PLAN.md): their isolated side is CTRL island A (3V3_CTRL / CTRLGND_A at J11),
and the island's new parts are drawn here: U19/U20 ISO7760F (ISO-side PWMs and relay), U21
CA-IS3742 (U4/U6 sigma-delta clock and data), U22-U24 AMC1311 + U25/U26 difference amplifiers
(ISOADA1-3), U27 3V3_CTRL LDO, J14 (5V_CTRL_A link from island B) and PEC1 (PE bond)."""
import os
import sys

from _common import *  # noqa: F401,F403

sys.path.insert(0, os.path.join(TOOLS, "v5"))
from v5_parts import VALUE as V  # noqa: E402

ISO_PINS_L = [15, 14, 13, 12, 11, 10]   # B1..B6 (VCC side)
ISO_PINS_R = [2, 3, 4, 5, 6, 7]         # A1..A6 (isolated side)


def isolator(sh, ref, sym, x, y, left, right, cl, cr, series=None, rail=40, vdd_r="3V3_CTRL", gnd_r="CTRLGND_A"):
    """Si866x with decoupling caps (pin 1 of every cap is the ground pin). `left`/`right`
    are the six labels for B1..B6 / A1..A6. `series` = (pin, (ref, value), label) puts a
    resistor between that left pin and its label."""
    u = sh.place(sym, ref, x, y, value=sym)
    VDD2, GND2, VDD1, GND1 = u.pin(16), u.pin(9), u.pin(1), u.pin(8)
    # VCC side rail + cap
    xl = x - g(rail)
    sh.wire(VDD2, (xl, VDD2[1]))
    power_at(sh, "VCC", (xl, VDD2[1]), "up")
    sh.wire(GND2, (xl, GND2[1]))
    power_at(sh, "GND", (xl, GND2[1]), "down")
    c, ct, cb = vert2(sh, "C", cl[0], x - g(rail - 6), y - g(1), cl[1], top=2)
    sh.wire(ct, (ct[0], VDD2[1]))
    sh.wire(cb, (cb[0], GND2[1]))
    sh.junction(ct[0], VDD2[1])
    sh.junction(cb[0], GND2[1])
    # isolated side rail + cap
    xr = x + g(rail)
    sh.wire(VDD1, (xr, VDD1[1]))
    power_at(sh, vdd_r, (xr, VDD1[1]), "up")
    sh.wire(GND1, (xr, GND1[1]))
    power_at(sh, gnd_r, (xr, GND1[1]), "down")
    c, ct, cb = vert2(sh, "C", cr[0], x + g(rail - 6), y - g(1), cr[1], top=2)
    sh.wire(ct, (ct[0], VDD1[1]))
    sh.wire(cb, (cb[0], GND1[1]))
    sh.junction(ct[0], VDD1[1])
    sh.junction(cb[0], GND1[1])
    # signals
    for pin, lab in zip(ISO_PINS_L, left):
        if series and series[0] == pin:
            r, rl, rr = horiz2(sh, "R", series[1][0], x - g(36), u.pin(pin)[1], series[1][1], left=2)
            sh.wire(u.pin(pin), rr)
            glabel_left(sh, series[2], rl, 2)
        else:
            glabel_left(sh, lab, u.pin(pin))
    for pin, lab in zip(ISO_PINS_R, right):
        glabel_right(sh, lab, u.pin(pin))
    return u


sh = sheet("11_signal_isolators.kicad_sch")
from p2k.sexpr import find  # noqa: E402
find(sh.tree, "paper")[1] = "A2"   # v5: room for the CTRL island A parts
X = g(120)
isolator(sh, "U15", "Si8661BD-B-IS", X, g(40),
         ["ADASEL0", "ADASEL1", "ADASEL2", "GPIO_BYPASS_RLY", None, "MDATA"],
         ["ADASEL0_ISO", "ADASEL1_ISO", "ADASEL2_ISO", "GPIO_BYPASS_RLY_ISOLATED", "ADCLK_ISO", "MDATA_ISO"],
         ("C85", "100n"), ("C86", "100n"), series=(11, ("R22", "39R"), "ADCLK"), rail=52)
isolator(sh, "U13", "Si8661BD-B-IS", X, g(76),
         ["PWM_TRANS3", "PWM_TRANS2", "PWM_TRANS1", "CLK1", "CS1", "SDATA1"],
         ["PWM_TRANS3_ISO", "PWM_TRANS2_ISO", "PWM_TRANS1_ISO", "CLK1_ISO", "CS1_ISO", "SDATA1_ISO"],
         ("C84", "100n"), ("C83", "100n"))
isolator(sh, "U16", "Si8660BD-B-IS", X, g(112),
         ["DAB_PWM_PRI_LO", "DAB_PWM_PRI_HI", "PWM_G3", "PWM_G1", "PWM_G2", "PWM_G4"],
         ["DAB_PWM_PRI_LO_ISO", "DAB_PWM_PRI_HI_ISO", "PWM_G3_ISO", "PWM_G1_ISO", "PWM_G2_ISO", "PWM_G4_ISO"],
         ("C81", "100n"), ("C82", "100n"))
# U17: footprint only, nothing connected (all 16 pins N/C in Proteus)
u17 = sh.place("Si8661BD-B-IS", "U17", X, g(148), value="Si8661BD-B-IS")
for pin in u17.pins:
    sh.no_connect(*u17.pin(pin))
sh.text("U17: spare isolator footprint, not connected (all pins N/C in Proteus).", X + g(12), g(150))
sh.text("3V3 / DC- terminals in the Proteus schematic = nets VCC / GND.", g(20), g(170))
sh.text("v5: the isolated side of U15/U13/U16 is CTRL island A (3V3_CTRL / CTRLGND_A; was 3V3_ISO / ISOGND).",
        g(20), g(173))


# ---- v5: CTRL island A ---------------------------------------------------------------------------
def row(y, x0, parts, step=10):
    for i, (sym, ref, val, na, nb, a) in enumerate(parts):
        part2(sh, sym, ref, x0 + g(step * i), y, val, na, nb, a=a)


sh.text("v5 CTRL island A: ISO-side PWMs / relay (U19, U20), U4/U6 sigma-delta lines (U21), ISOADA1-3 (U22-U26). "
        "Side 1 = CTRL (J11), side 2 = ISO.", g(220), g(14))
PW = [("PWM_Q5", "PWM_Q6", "PWM_Q7", "PWM_Q8", "PWM_TRANS4", "PWM_TRANS5"),
      ("PWM_TRANS6", "DAB_PWM_HI_SEC", "DAB_PWM_LO_SEC", "GPIO_BYPASS_RLY_ISO", None, None)]
for ref, y, sig in (("U19", g(36), PW[0]), ("U20", g(76), PW[1])):
    nets = {1: "3V3_CTRL", 8: "CTRLGND_A", 16: "3V3_ISO", 9: "ISOGND"}
    for k, s_ in enumerate(sig):
        nets[2 + k] = f"{s_}_CTRL" if s_ else "CTRLGND_A"   # unused inputs tied low
        nets[15 - k] = s_                                    # unused outputs open
    ic(sh, "ISO7760F", ref, g(262), y, nets, value=V[ref])
sh.text("U20 INE/INF unused (tied to CTRLGND_A), OUTE/OUTF open.", g(240), g(92))
ic(sh, "CA-IS3742", "U21", g(262), g(118),
   {1: "3V3_CTRL", 2: "CTRLGND_A", 8: "CTRLGND_A", 3: "INU_ADCLK_CTRL", 4: "ADCLK_DAB_CTRL", 5: "MDATA_INU_CTRL",
    6: "MDATA_DAB_CTRL", 7: "3V3_CTRL", 16: "3V3_ISO", 9: "ISOGND", 15: "ISOGND", 14: "INU_ADCLK", 13: "ADCLK_DAB",
    12: "MDATA_INU", 11: "MDATA_DAB", 10: "3V3_ISO"}, value=V["U21"])
sh.text("U21: clocks CTRL -> ISO (U4/U6 MCLKIN), data ISO -> CTRL; firmware samples MDATA_INU/MDATA_DAB with the "
        "same phase offset as MDATA_ISO.", g(220), g(136))
row(g(30), g(330), [(("C"), r, V[r], vdd, gnd, 1) for r, vdd, gnd in (
    ("C117", "3V3_CTRL", "CTRLGND_A"), ("C118", "3V3_ISO", "ISOGND"), ("C119", "3V3_CTRL", "CTRLGND_A"),
    ("C120", "3V3_ISO", "ISOGND"), ("C121", "3V3_CTRL", "CTRLGND_A"), ("C122", "3V3_ISO", "ISOGND"))])
sh.text("C117/C119/C121: CTRL sides of U19/U20/U21, C118/C120/C122: ISO sides.", g(326), g(44))

# ISOADA1-3: ISO divider (x0.4 with the 8.2k source) -> AMC1311 -> CTRL difference amp (x2.49) -> 8.2k + C
for ch, (u, y) in enumerate((("U22", g(160)), ("U23", g(200)), ("U24", g(240))), 1):
    a = f"ISOADA{ch}"
    ic(sh, "AMC1311", u, g(262), y, {1: "3V3_ISO", 2: f"{a}_AIN", 3: "ISOGND", 4: "ISOGND",
                                    8: "3V3_CTRL", 7: f"{a}_P", 6: f"{a}_N", 5: "CTRLGND_A"}, value=V[u])
    c1, c2 = f"C{123 + 2 * (ch - 1)}", f"C{124 + 2 * (ch - 1)}"
    rd, rb = f"R{110 + 2 * (ch - 1)}", f"R{111 + 2 * (ch - 1)}"
    ri, rf, rp, rr = (f"R{116 + 4 * (ch - 1) + k}" for k in range(4))
    ro, co = f"R{127 + ch}", f"C{128 + ch}"
    row(y - g(6), g(300), [
        ("R", rd, V[rd], a, f"{a}_AIN", 1), ("R", rb, V[rb], f"{a}_AIN", "ISOGND", 1),
        ("C", c1, V[c1], "3V3_ISO", "ISOGND", 1), ("C", c2, V[c2], "3V3_CTRL", "CTRLGND_A", 1),
        ("R", ri, V[ri], f"{a}_N", f"{a}_M", 1), ("R", rf, V[rf], f"{a}_M", f"{a}_OUT", 1),
        ("R", rp, V[rp], f"{a}_P", f"{a}_PL", 1), ("R", rr, V[rr], f"{a}_PL", "CTRLGND_A", 1),
        ("R", ro, V[ro], f"{a}_OUT", f"{a}_CTRL", 1), ("C", co, V[co], f"{a}_CTRL", "CTRLGND_A", 1)])
for ref, unit, ch in (("U25", 1, 1), ("U25", 2, 2), ("U26", 1, 3)):
    a = f"ISOADA{ch}"
    pins = {1: (3, 2, 1), 2: (5, 6, 7)}[unit]
    ic(sh, "OPA2350EA", ref, g(420), g(160 + 40 * (ch - 1)),
       {pins[0]: f"{a}_PL", pins[1]: f"{a}_M", pins[2]: f"{a}_OUT"}, value=V[ref], unit=unit)
ic(sh, "OPA2350EA", "U26", g(420), g(270), {5: "CTRLGND_A", 6: "OPA_SPARE", 7: "OPA_SPARE"}, value=V["U26"], unit=2)
for ref, x in (("U25", g(220)), ("U26", g(235))):
    ic(sh, "OPA2350EA", ref, x, g(290), {8: "3V3_CTRL", 4: "CTRLGND_A"}, value=V[ref], unit=3)
row(g(290), g(250), [("C", "C132", V["C132"], "3V3_CTRL", "CTRLGND_A", 1),
                     ("C", "C133", V["C133"], "3V3_CTRL", "CTRLGND_A", 1)])
sh.text("ISOADAn (U7/U2 output via 8.2k + filter C, sheets 4/5) -> 6.8k/10k (x0.4, <= 1.32 V) -> AMC1311 (gain 1) ->",
        g(220), g(258))
sh.text("difference amp 24.9k/10k (x2.49) -> 8.2k + 4.7n/4.7n/10n -> J11: overall x0.996, 0-3.3 V as before.",
        g(220), g(261))
sh.text("U26B spare: + to CTRLGND_A, follower.", g(400), g(280))

# island A supply: J14 link from island B, 3V3_CTRL LDO, PE bond
ic(sh, "CONN_2", "J14", g(40), g(200), {1: "5V_CTRL_A", 2: "CTRLGND_A"}, value=V["J14"])
flagged_power(sh, "5V_CTRL_A", g(60), g(196))
flagged_power(sh, "CTRLGND_A", g(70), g(212))
ic(sh, "TPS73033DBVT", "U27", g(110), g(200), {1: "5V_CTRL_A", 2: "CTRLGND_A", 3: "5V_CTRL_A", 4: "CTRL_NR",
                                               5: "3V3_CTRL"}, value=V["U27"])
row(g(230), g(90), [("C", "C136", V["C136"], "5V_CTRL_A", "CTRLGND_A", 1),
                    ("C", "C135", V["C135"], "3V3_CTRL", "CTRLGND_A", 1),
                    ("C", "C134", V["C134"], "CTRL_NR", "CTRLGND_A", 1)])
terminal(sh, "PEC1", g(160), g(196), "up")
net_at(sh, (g(160), g(196)), "CTRLGND_A", "down")
sh.text("J14 <- J13 (sheet 7): 5V_CTRL from island B over a double-insulated two-wire link; PEC1 bonds CTRLGND_A to PE.",
        g(20), g(250))
sh.save()
print("sheet11: written")
