"""v6 part list (stdlib only): the baseboard for six half-bridge power cards (V6_PLAN.md,
~/dev/hb_power_card-rev1/CARD_REV1_PLAN.md section 8 and 9). One place for what leaves the board and what is
added; tools/v6/make_v6_lists.py writes the part_map rows and lib/v6_deviations.csv from it, the sheet scripts
take refdes, nets and values from here.
"""

# ---- removed (V6_PLAN.md section 5, checked against the netlist: every net these parts leave is listed in
# reports/v6/v6_1_schematic.log; nothing on the list serves a part that stays)
SWITCHES = [f"Q{i}" for i in range(1, 13)]
GATE_HEADERS = "J1 J2 J3 J4 J6 J8".split()
DAB_TABS = "DAB_PRI_1 DAB_PRI_2 DAB_SEC_1 DAB_SEC_2".split()
DAB_CAPS = "C1 C35 C45 C46 C47 C48 C49 C50".split()
# switch-node current sense with its input filters and local supplies: AFE leg 1 (U5) and inverter leg B (U4)
SENSE_AFE = "R48 U5 D8 R59 R57 R58 C52 C53 C91 C71 C73 C64".split()
SENSE_INU = "R91 U4 D9 R94 R92 R93 C51 C54 C90 C55 C78 C37".split()
REMOVED = SWITCHES + GATE_HEADERS + DAB_TABS + DAB_CAPS + SENSE_AFE + SENSE_INU
REMOVED_NOTE = {**{r: "v6: switch on the power card" for r in SWITCHES},
                **{r: "v6: gate-card header replaced by the card CTRL header" for r in GATE_HEADERS},
                **{r: "v6: DAB leads go from the card to the transformer" for r in DAB_TABS},
                **{r: "v6: DAB split capacitor on the DAB card" for r in DAB_CAPS},
                **{r: "v6: switch-node current sense on the card (AFE leg 1)" for r in SENSE_AFE},
                **{r: "v6: switch-node current sense on the card (inverter leg B)" for r in SENSE_INU}}

HDR = "ac_psu:Samtec_SHF-105-01-L-D-TH"
TERM = "ac_psu:Wuerth_REDCUBE-PressFit_7462810_M3"
C0603 = "Capacitor_SMD:C_0603_1608Metric"

# ---- the six cards: (name, header, DC+ terminal, DC- terminal, PWM_HI, PWM_LO, PWM_TRANS, 15 V, 5 V, GND,
#                      MCLK, MDAT, DC+ net, DC- net, capacitor on 15 V, capacitor on 5 V)
# BASEBOARD.md section 4; header pinout of CARD_REV1_PLAN.md section 4 (ribbon 1:1).
CARDS = [
    ("AFE leg 1", "J21", "J31", "J32", "PWM_G1", "PWM_G2", "PWM_TRANS1", "15V", "5V", "GND", "ADCLK", "MDAT_AFE", "DC+", "PGND", "C148", "C149"),
    ("AFE leg 2", "J22", "J33", "J34", "PWM_G3", "PWM_G4", "PWM_TRANS2", "15V", "5V", "GND", None, None, "DC+", "PGND", "C150", "C151"),
    ("DAB primary", "J23", "J35", "J36", "DAB_PWM_PRI_HI", "DAB_PWM_PRI_LO", "PWM_TRANS3", "15V", "5V", "GND", None, None, "DC+", "PGND", "C152", "C153"),
    ("Inverter leg B", "J24", "J37", "J38", "PWM_Q7", "PWM_Q8", "PWM_TRANS6", "15V_ISO", "5V_ISOL", "ISOGND", "INU_ADCLK", "MDAT_INU_CARD", "ISODC+", "ISOPGND", "C154", "C155"),
    ("Inverter leg A", "J25", "J39", "J40", "PWM_Q5", "PWM_Q6", "PWM_TRANS5", "15V_ISO", "5V_ISOL", "ISOGND", None, None, "ISODC+", "ISOPGND", "C156", "C157"),
    ("DAB secondary", "J26", "J41", "J42", "DAB_PWM_HI_SEC", "DAB_PWM_LO_SEC", "PWM_TRANS4", "15V_ISO", "5V_ISOL", "ISOGND", None, None, "ISODC+", "DAB_GROUND", "C158", "C159"),
]


def header_nets(card):
    """{pin: net or None} of a card's CTRL header."""
    name, j, tp, tn, hi, lo, tr, v15, v5, gnd, clk, dat = card[:12]
    return {1: hi, 2: gnd, 3: lo, 4: gnd, 5: tr, 6: v15, 7: v5, 8: clk, 9: gnd, 10: dat}


# (ref, sheet, symbol, value, footprint, note)
PARTS = []
for c in CARDS:
    PARTS += [
        (c[1], 2, "HDR_2X5", "CTRL " + c[0], HDR, f"CTRL header of the {c[0]} card: Samtec SHF-105-01-L-D-TH, ribbon 1:1"),
        (c[2], 2, "PIN", "PIN", TERM, f"{c[12]} terminal of the {c[0]} card: Wuerth 7462810, M3 press-fit"),
        (c[3], 2, "PIN", "PIN", TERM, f"{c[13]} terminal of the {c[0]} card: Wuerth 7462810, M3 press-fit"),
        (c[14], 2, "C", "100n", C0603, f"{c[7]} at {c[1]}"),
        (c[15], 2, "C", "100n", C0603, f"{c[8]} at {c[1]}"),
    ]
# U6 side-1 supply from 15V_ISO: the zener regulator of the removed U4 / U5 supplies (R + MM3Z5V1). R257 drops from
# 15V_ISO into the node R75 was fed from, R75 stays in series, D17 clamps VDD1 to 5.1 V against GND1.
# (15..17 V - 5.1 V) / (390 + 470) = 11.5..13.8 mA; ADuM7701 I_DD1 10 mA max.
PARTS += [
    ("R257", 8, "R", "390R", "Resistor_SMD:R_1206_3216Metric", "U6 VDD1 dropper from 15V_ISO (with R75 470R)"),
    ("D17", 8, "D_Zener", "MM3Z5V1T1", "ac_psu:D_SOD-323_AC", "U6 VDD1 5.1 V"),
]
VALUE = {p[0]: p[3] for p in PARTS}
