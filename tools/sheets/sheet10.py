#!/usr/bin/env python3
"""Sheet 10 (untitled in the PDF) - INU SDM current measurement isolator U4 (ADuM7701 fed
from the isolated AFE raw voltage via R94/D9) and the two relay drivers Q14 (primary) and
Q13 (isolated side)."""
from _common import *  # noqa: F401,F403

sh = sheet("10_inu_sdm_relay_drive.kicad_sch")

# ---- U4 ADuM7701 sigma-delta modulator on the INU shunt --------------------------------
adum_block(sh, g(150), g(40), "U4", "ADUM7701-8BRIZ-RL7", "ISO_AFE_SDM_RAW_VOLTAGE", ("R94", "470R"),
           ("D9", "MM3Z5V1T1"), (("C55", "100n"), ("C78", "100n")),
           (("R92", "12.4R"), "INU_SHUNT1", ("C54", "220p")), (("R93", "12.4R"), "INU_SHUNT2", ("C51", "220p")),
           "INU_SHUNT2", "3V3_ISO", "ISOGND", "INU_ADCLK", ("R50", "33R"), "MDATA_INU", ("C37", "100n"),
           note="VDD1/GND1 of U4 float on the INU shunt: VDD1 is 5.1 V from D9 via R94 (Proteus auto-named nets), GND1 = INU_SHUNT2.",
           cdiff=("C90", "100n C0G"))


# ---- relay drivers -----------------------------------------------------------------------
def relay_drive(sh, x, y, q, d_near, d_far, vsup, gnd, r_gate, c_gate, r_pull, lab_drive, lab_gpio):
    """2N7000 low-side switch for a relay coil: drain to the coil (label), two series
    Schottky diodes from the drain back to the supply as a flyback path, RC on the gate."""
    t = sh.place("2N7000", q[0], x, y, value=q[1])
    D, G, S = t.pin(1), t.pin(2), t.pin(3)
    top = (D[0], y - g(10))
    sh.wire(D, top)
    sh.glabel(lab_drive, *top, 90)
    drow = y - g(6)
    sh.junction(D[0], drow)
    _, dn_c, dn_a = horiz2(sh, "D_Schottky", d_near[0], D[0] - g(6), drow, d_near[1], left="C")
    sh.wire((D[0], drow), dn_a)
    _, df_c, df_a = horiz2(sh, "D_Schottky", d_far[0], D[0] - g(16), drow, d_far[1], left="C")
    sh.wire(dn_c, df_a)
    vp = (D[0] - g(22), drow)
    sh.wire(df_c, vp)
    power_at(sh, vsup, vp, "up")
    # gate network
    rail = y + g(12)
    n1 = (x - g(6), y)
    sh.wire(G, n1)
    sh.junction(*n1)
    _, cgt, cgb = vert2(sh, "C", c_gate[0], n1[0], y + g(5), c_gate[1], top=1)
    sh.wire(n1, cgt)
    sh.wire(cgb, (cgb[0], rail))
    _, rgl, rgr = horiz2(sh, "R", r_gate[0], x - g(12), y, r_gate[1], left=2)
    sh.wire(n1, rgr)
    n2 = (x - g(20), y)
    sh.wire(rgl, n2)
    sh.junction(*n2)
    _, rpt, rpb = vert2(sh, "R", r_pull[0], n2[0], y + g(5), r_pull[1], top=1)
    sh.wire(n2, rpt)
    sh.wire(rpb, (rpb[0], rail))
    glabel_left(sh, lab_gpio, n2, 2)
    # source and ground rail
    sh.wire(S, (S[0], rail))
    sh.wire((n2[0], rail), (S[0], rail))
    sh.junction(cgb[0], rail)
    sh.junction(S[0], rail)
    power_at(sh, gnd, (S[0], rail), "down")
    return t


relay_drive(sh, g(70), g(104), ("Q14", "2N7000"), ("D5", "ZLLS400TA"), ("D10", "ZLLS400TA"), "20V", "GND",
            ("R89", "2.2k"), ("C44", "100n"), ("R90", "2.2k"), "RELAY_DRIVE", "GPIO_BYPASS_RLY")
relay_drive(sh, g(190), g(104), ("Q13", "2N7000"), ("D3", "ZLLS400TA"), ("D4", "ZLLS400TA"), "20V_ISO_SEC", "ISOGND",
            ("R78", "2.2k"), ("C43", "100n"), ("R88", "2.2k"), "RELAY_DRIVE_ISO", "GPIO_BYPASS_RLY_ISO")
sh.text("Relay drivers: RELAY_DRIVE -> R20 coil (sheet 1), RELAY_DRIVE_ISO -> R79 coil (sheet 5).", g(40), g(128))
sh.save()
print("sheet10: written")
