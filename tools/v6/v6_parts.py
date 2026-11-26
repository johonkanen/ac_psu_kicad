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
BUS_LINKS = ["BUSP1", "BUSP2", "BUSN1", "BUSN2"]
# user 2026-11-24: the leg 2 / leg A SW wires land on FILTER_IN1 / J10; their own landing terminals go
LANDINGS = ["AFE_OUT1", "INU_OUT2"]   # v6 step 3: the ISO DC bus runs as copper in the freed strip
REMOVED = SWITCHES + GATE_HEADERS + DAB_TABS + DAB_CAPS + BUS_LINKS + LANDINGS
REMOVED_NOTE = {**{r: "v6: switch on the power card" for r in SWITCHES},
                **{r: "v6: gate-card header replaced by the card CTRL header" for r in GATE_HEADERS},
                **{r: "v6: DAB leads go from the card to the transformer" for r in DAB_TABS},
                **{r: "v6: DAB split capacitor on the DAB card" for r in DAB_CAPS},
                **{r: "v6: ISO DC bus wire link replaced by copper in the freed card strip" for r in BUS_LINKS},
                **{r: "v6: SW landing terminal deleted, the card's SW wire lands on FILTER_IN1 / J10 (user 2026-11-24)"
                   for r in LANDINGS}}
# Proteus / v5 parts that v6 step 3 places elsewhere (the two current-sense groups go to the choke-lead terminals,
# INU_OUT2 leaves the passage north of J11)
MOVED = {**{r: "v6: AFE current sense at the choke-lead terminal FILTER_OUT1" for r in
            ("R48", "U5", "D8", "R59", "R57", "R58", "C52", "C53", "C91", "C71", "C73", "C64", "R55")},
         **{r: "v6: inverter current sense at the choke-lead terminal J9" for r in
            ("R91", "U4", "D9", "R94", "R92", "R93", "C51", "C54", "C90", "C55", "C78", "C37", "R50")},
}
MOVED_NOT_PROTEUS = ("C90", "C91")

# V6_PLAN.md section 9 (user 2026-11-23): the two current-sense circuits R48 / U5 and R91 / U4 STAY on the board
# with all their parts. Each shunt moves to the other end of its choke (the end that does not switch):
#   R48: between the choke lead on terminal FILTER_OUT1 (new net AFE_CHOKE1) and the filter node LEMOUT
#   R91: between the choke lead on terminal J9 (new net INU_CHOKE) and the filter node INDUCTOR_OUTPUT
# Side 1 of U5 / U4 was fed from the gate cards (header pin 39): now one isolated DC/DC module each.

# pins of kept parts that change net (KiCad refdes): stated here, because nets this small cannot be matched by members
PIN_TO = {("R48", "3"): "LEMOUT", ("R48", "4"): "AFE_CHOKE1", ("FILTER_OUT1", "1"): "AFE_CHOKE1",
          ("R91", "3"): "INDUCTOR_OUTPUT", ("R91", "4"): "INU_CHOKE", ("J9", "1"): "INU_CHOKE"}

HDR = "ac_psu:Samtec_SHF-105-01-L-D-TH"
TERM = "ac_psu:Wuerth_REDCUBE-PressFit_7462810_M3"
# Inverter leg A and DAB secondary: the control card (5.3 mm above the board, outline to y 46.36) leaves no room for
# a REDCUBE and its lug on the ISO wall east of x 42.6, so their DC wires are pigtails soldered into two plated holes
# per net (planning session 2026-11-23); the pigtail carries a ring lug to the card's own screw terminal.
# One hole per net (step 4): with a spare hole per net the pads fill y 53..64 and leave no 8 mm lane for the ISO DC
# bus between the holes and the wall; with one hole at 16 mm from the wall the lane y 61.25 ... 69.25 is free.
PIGTAIL = "ac_psu:WirePigtail_D6.0mm_Drill3.0mm"
PIGTAIL_CARDS = ("Inverter leg A", "DAB secondary")
C0603 = "Capacitor_SMD:C_0603_1608Metric"

# ---- the six cards: (name, header, DC+ terminal, DC- terminal, PWM_HI, PWM_LO, PWM_TRANS, 15 V, 5 V, GND,
#                      MCLK, MDAT, DC+ net, DC- net, capacitor on 15 V, capacitor on 5 V)
# BASEBOARD.md section 4; header pinout of CARD_REV1_PLAN.md section 4 (ribbon 1:1).
CARDS = [
    ("AFE leg 1", "J21", "J31", "J32", "PWM_G1", "PWM_G2", "PWM_TRANS1", "15V", "5V", "GND", None, None, "DC+", "PGND", "C148", "C149"),
    ("AFE leg 2", "J22", "J33", "J34", "PWM_G3", "PWM_G4", "PWM_TRANS2", "15V", "5V", "GND", None, None, "DC+", "PGND", "C150", "C151"),
    ("DAB primary", "J23", "J35", "J36", "DAB_PWM_PRI_HI", "DAB_PWM_PRI_LO", "PWM_TRANS3", "15V", "5V", "GND", None, None, "DC+", "PGND", "C152", "C153"),
    ("Inverter leg B", "J24", "J37", "J38", "PWM_Q7", "PWM_Q8", "PWM_TRANS6", "15V_ISO", "5V_ISOL", "ISOGND", None, None, "ISODC+", "ISOPGND", "C154", "C155"),
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
        (c[2], 2, "PIN", "PIN", PIGTAIL if c[0] in PIGTAIL_CARDS else TERM,
         f"{c[12]} pigtail holes of the {c[0]} card (wire soldered, ring lug to the card)" if c[0] in PIGTAIL_CARDS else
         f"{c[12]} terminal of the {c[0]} card: Wuerth 7462810, M3 press-fit"),
        (c[3], 2, "PIN", "PIN", PIGTAIL if c[0] in PIGTAIL_CARDS else TERM,
         f"{c[13]} pigtail holes of the {c[0]} card (wire soldered, ring lug to the card)" if c[0] in PIGTAIL_CARDS else
         f"{c[13]} terminal of the {c[0]} card: Wuerth 7462810, M3 press-fit"),
        (c[14], 2, "C", "100n", C0603, f"{c[7]} at {c[1]}"),
        (c[15], 2, "C", "100n", C0603, f"{c[8]} at {c[1]}"),
    ]
# U6 side-1 supply from 15V_ISO: the zener regulator of the removed U4 / U5 supplies (R + MM3Z5V1). R257 drops from
# 15V_ISO into the node R75 was fed from, R75 stays in series, D17 clamps VDD1 to 5.1 V against GND1.
# (15..17 V - 5.1 V) / (390 + 470) = 11.5..13.8 mA; ADuM7701 I_DD1 10 mA max.
PARTS += [
    ("R257", 8, "R", "390R", "Resistor_SMD:R_1206_3216Metric", "U6 VDD1 dropper from 15V_ISO (with R75 470R)"),
    # planning session 2026-11-24: the inverter sigma-delta clock gets a series resistor at the driving end (U21
    # pin 14), like ADCLK has R22 at U15; the run to U4 at J9 is over 100 mm
    ("R258", 11, "R", "33R", "Resistor_SMD:R_0603_1608Metric", "INU_ADCLK series resistor at the U21 output"),
    ("D17", 8, "D_Zener", "MM3Z5V1T1", "ac_psu:D_SOD-323_AC", "U6 VDD1 5.1 V"),
]
# Side-1 supplies of U5 / U4: Mornsun B0512S-1WR3 (5 V in, 12 V out, 1 W, 1.5 kV; JLC C7465188, 10680 in stock on
# 2026-11-23) into the existing 470R + 5.1 V zener (R59 / D8, R94 / D9): 12 .. 14 V unloaded-ish, 15 .. 19 mA, as the
# gate cards gave before. Pins as the B_S-1WR3 data sheet (to verify): 1 Vin, 2 GND, 4 0V, 6 +Vo.
DCDC = "ac_psu:Converter_DCDC_Mornsun_B05xxS-1WR3_SIP-4"
C0603_ = "Capacitor_SMD:C_0603_1608Metric"
PARTS += [
    ("U29", 8, "B05XXS", "B0512S-1WR3", DCDC, "U5 side-1 supply from 5V (AFE current sense at the choke's filter end)"),
    ("C160", 8, "C", "1u", C0603_, "U29 input"),
    ("C161", 8, "C", "1u 25V", C0603_, "U29 output"),
    ("U30", 10, "B05XXS", "B0512S-1WR3", DCDC, "U4 side-1 supply from 5V_ISOL (inverter current sense at the choke's output end)"),
    ("C162", 10, "C", "1u", C0603_, "U30 input"),
    ("C163", 10, "C", "1u 25V", C0603_, "U30 output"),
]
# V6_PLAN section 15 (user / planning session 2026-11-26): the inductor leads go into plain soldered holes again
# (2.3 mm finished, 5 mm pad); the inverter leg B SW wire lands on J7S (M4) outside the inductor profile
HOLE = "ac_psu:WireHole_D5.0mm_Drill2.3mm"
FOOTPRINT = {"J7": HOLE, "J9": HOLE, "J5": HOLE, "FILTER_OUT": HOLE,     # Proteus refdes -> new footprint
             # the AFE leg 2 SW wire lands on FILTER_IN1: no legal place for an M4 terminal outside the AFE choke
             # profile in the crowded filter area, so it is a soldered pigtail hole like the ISO pigtails (step 5)
             "FILTER_IN": "ac_psu:WirePigtail_D6.0mm_Drill3.0mm"}
RENAME = {"INDUCTOR_INPUT": "SW_INV_B"}   # J7 (inductor lead) + J7S (leg B SW wire): the switch node, section 15
FOOTPRINT_NOTE = "v6: plain soldered hole for the inductor lead (2.0 mm wire), V6_PLAN section 15"
PARTS += [("J7S", 5, "PIN", "PIN", "ac_psu:Wuerth_REDCUBE-THR_74650074_M4_PTH",
           "SW wire landing of the inverter leg B card, joined to the inductor lead hole J7 (net SW_INV_B)")]
VALUE = {p[0]: p[3] for p in PARTS}
