#!/usr/bin/env python3
"""Sheet 2 - fpga connector (PDF page 2): J1 J2 J3 J4 J6 J8 (HB GT connectors), J11, J12."""
from _common import *  # noqa: F401,F403


def hb_connector(sh, ref, x, y, *, top, mid, p25, low, gate, p39, p43, p44, p45, p46, p47, p48,
                 top_power=None, low_power=None):
    """HB GT CONNECTOR. top: label of pins 15-20, mid: 21-26 (p25 separately: None = N/C
    or a label), low: 29-34, gate: 35-40 (p39 separately). 45/46/48 are power nets.
    top_power/low_power: the source group is a power net (PGND, ISOPGND, DAB_GROUND) in the
    IPC; it gets power symbols and `top`/`low` is only shown as a note (Proteus label)."""
    j = sh.place("HB_GT_CONNECTOR", ref, x, y, value="HB GT CONNECTOR")
    P = j.pin
    if top_power:
        bus_group(sh, [P(15), P(17), P(19)], P(17), "left", power=top_power)
        bus_group(sh, [P(16), P(18), P(20)], P(18), "right", power=top_power)
        sh.text(f"({top})", P(16)[0] + g(10), P(19)[1] + 0.6)
    else:
        bus_group(sh, [P(15), P(17), P(19)], P(17), "left", label=top)
        bus_group(sh, [P(16), P(18), P(20)], P(18), "right", label=top)
    bus_group(sh, [P(21), P(23)], P(23), "left", label=mid)
    bus_group(sh, [P(22), P(24), P(26)], P(24), "right", label=mid)
    if p25:
        glabel_left(sh, p25, P(25), 4)
    else:
        sh.no_connect(*P(25))
    if low_power:
        bus_group(sh, [P(29), P(31), P(33)], P(31), "left", power=low_power)
        bus_group(sh, [P(30), P(32), P(34)], P(32), "right", power=low_power)
        sh.text(f"({low})", P(30)[0] + g(10), P(33)[1] + 0.6)
    else:
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
             p43="PWM_G4", p44="PWM_G2", p45="5V", p46="GND", p47="PWM_TRANS1", p48="15V",
             top_power="PGND", low_power="PGND")
hb_connector(sh, "J2", X2, Y1, top="G3_SOURCE_HI", mid="G3_GATE_HI", p25=None,
             low="G1_SOURCE_HI", gate="G1_GATE_HI", p39="SDM_RAW_VOLTAGE",
             p43="PWM_G1", p44="PWM_G3", p45="5V", p46="GND", p47="PWM_TRANS2", p48="15V")
hb_connector(sh, "J3", X3, Y1, top="DAB_SOURCE_HI_PRI", mid="DAB_GATE_HI_PRI", p25=None,
             low="DAB_SOURCE_LO_PRI", gate="DAB_GATE_LO_PRI", p39=None,
             p43="DAB_PWM_PRI_HI", p44="DAB_PWM_PRI_LO", p45="5V", p46="GND", p47="PWM_TRANS3", p48="15V",
             low_power="PGND")
# Row 2 (isolated side): J6, J8, J4
hb_connector(sh, "J6", X1, Y2, top="Q8_S", mid="Q8_G", p25=None,
             low="Q6_S", gate="Q6_G", p39=None,
             p43="PWM_Q6", p44="PWM_Q8", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS5", p48="15V_ISO",
             top_power="ISOPGND", low_power="ISOPGND")
hb_connector(sh, "J8", X2, Y2, top="Q5_S", mid="Q5_G", p25=None,
             low="Q7_S", gate="Q7_G", p39="ISO_AFE_SDM_RAW_VOLTAGE",
             p43="PWM_Q7", p44="PWM_Q5", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS6", p48="15V_ISO")
hb_connector(sh, "J4", X3, Y2, top="DAB_SOURCE_LO_SEC", mid="DAB_GATE_LO_SEC", p25="ISO_DAB_SDM_RAW_VOLTAGE",
             low="DAB_SOURCE_HI_SEC", gate="DAB_GATE_HI_SEC", p39=None,
             p43="DAB_PWM_HI_SEC", p44="DAB_PWM_LO_SEC", p45="5V_ISOL", p46="ISOGND", p47="PWM_TRANS4",
             p48="15V_ISO", top_power="DAB_GROUND")

sh.text("Source pins of the gate-driver connectors are power nets in the layout (PGND, ISOPGND, DAB_GROUND);", g(20), g(130))
sh.text("the Proteus labels (G2_SOURCE_LO, Q8_S, DAB_SOURCE_LO_SEC, ...) are shown in brackets.", g(20), g(133))

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
