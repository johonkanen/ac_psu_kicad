#!/usr/bin/env python3
"""Sheet 2 - fpga connector (PDF page 2): J1 J2 J3 J4 J6 J8 (HB GT connectors), J11, J12."""
from _common import *  # noqa: F401,F403


def hb_connector(sh, ref, x, y, *, top, mid, p25, low, gate, p39, p43, p44, p45, p46, p47, p48):
    """HB GT CONNECTOR. top: label of pins 15-20, mid: 21-26 (p25 separately: None = N/C
    or a label), low: 29-34, gate: 35-40 (p39 separately). 45/46/48 are power nets."""
    j = sh.place("HB_GT_CONNECTOR", ref, x, y, value="HB GT CONNECTOR")
    P = j.pin
    bus_group(sh, [P(15), P(17), P(19)], P(17), "left", label=top)
    bus_group(sh, [P(16), P(18), P(20)], P(18), "right", label=top)
    bus_group(sh, [P(21), P(23)], P(23), "left", label=mid)
    bus_group(sh, [P(22), P(24), P(26)], P(24), "right", label=mid)
    if p25:
        glabel_left(sh, p25, P(25), 4)
    else:
        sh.no_connect(*P(25))
    bus_group(sh, [P(29), P(31), P(33)], P(31), "left", label=low)
    bus_group(sh, [P(30), P(32), P(34)], P(32), "right", label=low)
    bus_group(sh, [P(35), P(37)], P(37), "left", label=gate)
    bus_group(sh, [P(36), P(38), P(40)], P(38), "right", label=gate)
    if p39:
        glabel_left(sh, p39, P(39), 4)
    else:
        sh.no_connect(*P(39))
    glabel_left(sh, p43, P(43), 4)
    glabel_right(sh, p44, P(44), 4)
    power_at(sh, p45, left(P(45), 4), "left")
    sh.wire(P(45), left(P(45), 4))
    power_at(sh, p46, right(P(46), 4), "right")
    sh.wire(P(46), right(P(46), 4))
    glabel_left(sh, p47, P(47), 4)
    power_at(sh, p48, right(P(48), 4), "right")
    sh.wire(P(48), right(P(48), 4))
    return j


sh = sheet("02_fpga_connector.kicad_sch")

X1, X2, X3 = g(52), g(144), g(236)
Y1, Y2 = g(42), g(96)

# Row 1 (primary side, PDF top row): J1, J2, J3
hb_connector(sh, "J1", X1, Y1, top="G2_SOURCE_LO", mid="G2_GATE_LO", p25=None,
             low="G4_SOURCE_LO", gate="G4_GATE_LO", p39=None,
             p43="PWM_G4", p44="PWM_G2", p45="5V", p46="GND", p47="PWM_TRANS1", p48="20V")
hb_connector(sh, "J2", X2, Y1, top="G3_SOURCE_HI", mid="G3_GATE_HI", p25=None,
             low="G1_SOURCE_HI", gate="G1_GATE_HI", p39="SDM_RAW_VOLTAGE",
             p43="PWM_G1", p44="PWM_G3", p45="5V", p46="GND", p47="PWM_TRANS2", p48="20V")
hb_connector(sh, "J3", X3, Y1, top="DAB_SOURCE_HI_PRI", mid="DAB_GATE_HI_PRI", p25=None,
             low="DAB_SOURCE_LO_PRI", gate="DAB_GATE_LO_PRI", p39=None,
             p43="DAB_PWM_PRI_HI", p44="DAB_PWM_PRI_LO", p45="5V", p46="GND", p47="PWM_TRANS3", p48="20V")
# Row 2 (isolated side): J6, J8, J4
hb_connector(sh, "J6", X1, Y2, top="Q8_S", mid="Q8_G", p25=None,
             low="Q6_S", gate="Q6_G", p39=None,
             p43="PWM_Q6", p44="PWM_Q8", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS5", p48="20V_ISO_SEC")
hb_connector(sh, "J8", X2, Y2, top="Q5_S", mid="Q5_G", p25=None,
             low="Q7_S", gate="Q7_G", p39="ISO_AFE_SDM_RAW_VOLTAGE",
             p43="PWM_Q7", p44="PWM_Q5", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS6", p48="20V_ISO_SEC")
hb_connector(sh, "J4", X3, Y2, top="DAB_SOURCE_LO_SEC", mid="DAB_GATE_LO_SEC", p25="ISO_DAB_SDM_RAW_VOLTAGE",
             low="DAB_SOURCE_HI_SEC", gate="DAB_GATE_HI_SEC", p39=None,
             p43="DAB_PWM_HI_SEC", p44="DAB_PWM_LO_SEC", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS4",
             p48="20V_ISO_SEC")

# J11 - 38 pin 50 mil header to the FPGA board (isolated side)
j11 = sh.place("HEADER_38_50MIL", "J11", g(80), g(160), value="38 PIN HEADER 50TH")
J11 = {1: "ISOADA3", 2: "ISOGND", 3: "ISOADA2", 4: "ISOADA1", 5: "ISOGND", 6: "MDATA_ISO",
       7: "ADCLK_ISO", 8: "GPIO_BYPASS_RLY_ISOLATED", 9: "ADASEL2_ISO", 10: "ADASEL1_ISO",
       11: "ADASEL0_ISO", 12: "SDATA1_ISO", 13: "CS1_ISO", 14: "CLK1_ISO", 15: "PWM_TRANS1_ISO",
       16: "PWM_TRANS2_ISO", 17: "PWM_TRANS3_ISO", 18: "PWM_G4_ISO", 19: "PWM_G2_ISO", 20: "PWM_G1_ISO",
       21: "PWM_G3_ISO", 22: "DAB_PWM_PRI_HI_ISO", 23: "DAB_PWM_PRI_LO_ISO", 24: "ADCLK_DAB",
       25: "PWM_TRANS4", 26: "MDATA_DAB", 27: "DAB_PWM_HI_SEC", 28: "PWM_TRANS6", 29: "DAB_PWM_LO_SEC",
       30: "PWM_Q5", 31: "PWM_Q6", 32: "INU_ADCLK", 33: "PWM_Q8", 34: "MDATA_INU", 35: "PWM_TRANS5",
       36: "GPIO_BYPASS_RLY_ISO", 37: "PWM_Q7", 38: None}
for pin, net in J11.items():
    p = j11.pin(pin)
    if net is None:
        sh.no_connect(*p)
    elif net == "ISOGND":
        q = left(p, 2) if pin % 2 else right(p, 2)
        sh.wire(p, q)
        power_at(sh, "ISOGND", q, "left" if pin % 2 else "right")
    elif pin % 2:
        glabel_left(sh, net, p)
    else:
        glabel_right(sh, net, p)

# J12 - 2x3 50 mil power connector (isolated 5 V)
j12 = sh.place("HEADER_2X3_43_48", "J12", g(236), g(156), value="2X3 PIN 50TH CONNECTOR")
P = j12.pin
bus_group(sh, [P(43), P(45), P(47)], P(45), "left", power="ISOGND")
bus_group(sh, [P(44), P(46), P(48)], P(46), "right", power="5V_ISOL")

# Power flags: these supplies enter the board through J1-J4/J6/J8 (20V, 5V, GND) and J12
# (ISOGND). 5V and 5V_ISOL are driven by U9/U8 on sheet 3; 20V, 20V_ISO_SEC, GND, ISOGND are generated on sheet 7, so their
# flags live here until those sheets are drawn, then move there (one flag per net).
sh.text("PWR_FLAGs for the supplies entering through the connectors (temporary, see STATUS.md)", g(150), g(172))
for i, net in enumerate(["GND", "20V", "ISOGND", "20V_ISO_SEC"]):
    flagged_power(sh, net, g(152 + 12 * i), g(182))

sh.save()
print("sheet02: written")
