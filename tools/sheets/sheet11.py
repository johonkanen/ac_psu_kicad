#!/usr/bin/env python3
"""Sheet 11 - signal isolators (PDF page 11): U15, U13, U16 Si866x digital isolators between
the VCC (3V3) side and the 3V3_ISO side, U17 unpopulated spare, R22 series resistor in ADCLK."""
from _common import *  # noqa: F401,F403

ISO_PINS_L = [15, 14, 13, 12, 11, 10]   # B1..B6 (VCC side)
ISO_PINS_R = [2, 3, 4, 5, 6, 7]         # A1..A6 (isolated side)


def isolator(sh, ref, sym, x, y, left, right, cl, cr, series=None, rail=40):
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
    power_at(sh, "3V3_ISO", (xr, VDD1[1]), "up")
    sh.wire(GND1, (xr, GND1[1]))
    power_at(sh, "ISOGND", (xr, GND1[1]), "down")
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
sh.save()
print("sheet11: written")
