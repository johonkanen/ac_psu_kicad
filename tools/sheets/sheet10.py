#!/usr/bin/env python3
"""Sheet 10 (untitled in the PDF) - INU SDM current measurement isolator U4 (ADuM7701 fed
from the isolated AFE raw voltage via R94/D9) and the two relay drivers Q14 (primary) and
Q13 (isolated side)."""
from _common import *  # noqa: F401,F403

sh = sheet("10_inu_sdm_relay_drive.kicad_sch")

# ---- U4 ADuM7701 sigma-delta modulator on the INU shunt --------------------------------
# v6: U4 with its input filter and supply is on the inverter leg-B power card. Its MDAT comes back on the card's
# CTRL header (sheet 2) and still passes R50 into MDATA_INU; INU_ADCLK goes out on the same header.
part2(sh, "R", "R50", g(150), g(40), "33R", "MDAT_INU_CARD", "MDATA_INU", horizontal=True)
sh.text("v6: the inverter leg-B shunt and its ADuM7701 are on the power card; MDAT_INU_CARD = pin 10 of J24 (sheet 2).", g(56), g(52))


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


relay_drive(sh, g(70), g(104), ("Q14", "2N7000"), ("D5", "ZLLS400TA"), ("D10", "ZLLS400TA"), "15V", "GND",
            ("R89", "2.2k"), ("C44", "100n"), ("R90", "2.2k"), "RELAY_DRIVE", "GPIO_BYPASS_RLY")
relay_drive(sh, g(190), g(104), ("Q13", "2N7000"), ("D3", "ZLLS400TA"), ("D4", "ZLLS400TA"), "15V_ISO", "ISOGND",
            ("R78", "2.2k"), ("C43", "100n"), ("R88", "2.2k"), "RELAY_DRIVE_ISO", "GPIO_BYPASS_RLY_ISO")
sh.text("Relay drivers: RELAY_DRIVE -> R20 coil (sheet 1), RELAY_DRIVE_ISO -> R79 coil (sheet 5).", g(40), g(128))
sh.save()
print("sheet10: written")
