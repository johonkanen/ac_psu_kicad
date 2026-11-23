#!/usr/bin/env python3
"""Sheet 2 - fpga connector (PDF page 2): J11, J12 and, since v6, the joints of the six half-bridge power cards
(CTRL headers J21..J26, DC terminals J31..J42) in place of the gate-card headers J1 J2 J3 J4 J6 J8."""
from _common import *  # noqa: F401,F403


sys.path.insert(0, os.path.join(TOOLS, "v6"))
import v6_parts as V6  # noqa: E402

sh = sheet("02_fpga_connector.kicad_sch")


def card(c, x, y):
    """Baseboard side of one half-bridge power card (v6): CTRL header (ribbon 1:1 to the card), the DC+ and DC-
    terminals for the twisted wire pair, 100 nF on 15 V and 5 V at the header."""
    name, j, tp, tn = c[:4]
    sh.text(name, x - g(14), y - g(12), size=2.0)
    ic(sh, "HDR_2X5", j, x, y, V6.header_nets(c), value=V6.VALUE[j], n=4)
    for ref, net, dy in ((tp, c[12], -g(4)), (tn, c[13], g(8))):
        t = terminal(sh, ref, x + g(44), y + dy, "right")
        net_at(sh, t.pin(1), net, "left", 4)
        if c in (V6.CARDS[0], V6.CARDS[3]) and net in ("DC+", "PGND", "ISODC+"):
            # the DC rails are fed from off-board parts: their power flags (were on sheets 1 and 5 at the switches)
            q = left(t.pin(1), 2)
            sh.junction(*q)
            sh.wire(q, down(q, 2))
            sh.pwr_flag(*down(q, 2), 180)
    part2(sh, "C", c[14], x + g(66), y + g(2), "100n", c[7], c[9])
    part2(sh, "C", c[15], x + g(80), y + g(2), "100n", c[8], c[9])


# v6: the six gate-card headers J1 J2 J3 J4 J6 J8 are replaced by the joints of the six power cards
X1, X2, X3 = g(40), g(150), g(260)
Y1, Y2 = g(40), g(92)
for c, (x, y) in zip(V6.CARDS, ((X1, Y1), (X2, Y1), (X3, Y1), (X1, Y2), (X2, Y2), (X3, Y2))):
    card(c, x, y)
sh.text("v6: header pins 1 PWM_HI, 2 GND, 3 PWM_LO, 4 GND, 5 PWM_TRANS, 6 15 V, 7 5 V, 8 MCLK, 9 GND, 10 MDAT "
        "(CARD_REV1_PLAN.md section 4). Top row: primary wall, bottom row: ISO wall.", g(20), g(126))
sh.text("MCLK / MDAT are used by AFE leg 1 and inverter leg B only. The DC- terminal of the DAB secondary card is "
        "DAB_GROUND (R64 to ISOPGND, sheet 8).", g(20), g(129))

# J11 - 38 pin 50 mil header to the control card. v5: CTRL island A (CTRLGND_A); the ISO-side
# PWMs, the U4/U6 sigma-delta lines and ISOADA1-3 now pass the isolators on sheet 11 (*_CTRL nets).
j11 = sh.place("HEADER_38_50MIL", "J11", g(80), g(160), value="38 PIN HEADER 50TH")
J11 = {1: "ISOADA3_CTRL", 2: "CTRLGND_A", 3: "ISOADA2_CTRL", 4: "ISOADA1_CTRL", 5: "CTRLGND_A", 6: "MDATA_ISO",
       7: "ADCLK_ISO", 8: "GPIO_BYPASS_RLY_ISOLATED", 9: "ADASEL2_ISO", 10: "ADASEL1_ISO",
       11: "ADASEL0_ISO", 12: "SDATA1_ISO", 13: "CS1_ISO", 14: "CLK1_ISO", 15: "PWM_TRANS1_ISO",
       16: "PWM_TRANS2_ISO", 17: "PWM_TRANS3_ISO", 18: "PWM_G4_ISO", 19: "PWM_G2_ISO", 20: "PWM_G1_ISO",
       21: "PWM_G3_ISO", 22: "DAB_PWM_PRI_HI_ISO", 23: "DAB_PWM_PRI_LO_ISO", 24: "ADCLK_DAB_CTRL",
       25: "PWM_TRANS4_CTRL", 26: "MDATA_DAB_CTRL", 27: "DAB_PWM_HI_SEC_CTRL", 28: "PWM_TRANS6_CTRL",
       29: "DAB_PWM_LO_SEC_CTRL", 30: "PWM_Q5_CTRL", 31: "PWM_Q6_CTRL", 32: "INU_ADCLK_CTRL", 33: "PWM_Q8_CTRL",
       34: "MDATA_INU_CTRL", 35: "PWM_TRANS5_CTRL", 36: "GPIO_BYPASS_RLY_ISO_CTRL", 37: "PWM_Q7_CTRL", 38: None}
for pin, net in J11.items():
    p = j11.pin(pin)
    if net is None:
        sh.no_connect(*p)
    elif net == "CTRLGND_A":
        q = left(p, 2) if pin % 2 else right(p, 2)
        sh.wire(p, q)
        power_at(sh, "CTRLGND_A", q, "left" if pin % 2 else "right")
    elif pin % 2:
        glabel_left(sh, net, p)
    else:
        glabel_right(sh, net, p)

# J12 - 2x3 50 mil power connector of the control card. v5: CTRL island B, 5V_CTRL from the CTRL
# winding buck on sheet 7 (was 5V_ISOL / ISOGND)
j12 = sh.place("HEADER_2X3_43_48", "J12", g(236), g(156), value="2X3 PIN 50TH CONNECTOR")
P = j12.pin
bus_group(sh, [P(43), P(45), P(47)], P(45), "left", power="CTRLGND")
bus_group(sh, [P(44), P(46), P(48)], P(46), "right", power="5V_CTRL")

# Power flag: ISOGND is the isolated DC-link negative (R97 to ISOPGND); flagged here.
# GND, 15V, 15V_ISO, CTRLGND and 5V_CTRL are flagged on sheet 7 (aux supply).
sh.text("v5: J11 = CTRL island A (CTRLGND_A), J12 = CTRL island B (CTRLGND, 5V_CTRL); the islands meet on the card and "
        "through the J13/J14 link.", g(150), g(169))
sh.text("ISOGND: PWR_FLAG here; GND, 15V, 15V_ISO, CTRLGND, 5V_CTRL are flagged on sheet 7.",
        g(150), g(172))
flagged_power(sh, "ISOGND", g(152), g(182))

sh.save()
print("sheet02: written")
