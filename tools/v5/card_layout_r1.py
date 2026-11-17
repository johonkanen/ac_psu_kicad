"""v5 card-area layout data (stdlib only): the three isolated domains under the control card
(V5_LAYOUT_PLAN.md). Coordinates: mm, IPC frame (Y up; KiCad y = -y).

Revision 1: the placement of tools/v5/v5_4_card_area.py (v5 step 4). Superseded on 2026-11-17 by
revision 2 (card_layout.py, which imports this file and redefines what changed).
"""
CARD = (42.599, -18.766, 118.599, 46.361)      # card outline x0, y0, x1, y1
BOARD_EDGE_X = 118.6
GAP = 5.0                                      # reinforced, P-I / P-C / I-C, every copper layer

# Copper areas: where a domain's pads, tracks, vias and zones may be, on all six layers.
# Every pair of areas is >= 5.0 mm apart (layout_proposal.py checks it), so the strip between
# two areas is the barrier; its centre line is 2.5 mm from both.
AREAS = {
    # CTRL piece at J11 (CTRLGND_A / 3V3_CTRL / 5V_CTRL_A)
    "CA": ("C", [(44.4, 20.8), (95.1, 20.8), (95.1, 33.0), (47.3, 33.0), (47.3, 46.1), (44.4, 46.1)]),
    # CTRL piece at J12 (CTRLGND / 5V_CTRL / CTRL_RAW); open to nothing: board edge on the east
    "CB": ("C", [(107.2, 3.0), (118.1, 3.0), (118.1, -34.5), (102.5, -34.5), (102.5, -27.0), (107.2, -27.0)]),
    # primary logic (GND / VCC): the card-area part; west and south it joins the primary power stage
    "P": ("P", [(42.55, -20.66), (69.65, -20.66), (69.65, -3.36), (85.5, -3.36), (85.5, 15.8), (42.55, 15.8)]),
    # ISO (ISOGND / 3V3_ISO): the card-area part; north it joins J4/J6/J8 and the ISO power stage,
    # south (x 87.9 .. 102.2, below y -9.4) the 15V_ISO / U8 copper of the aux area
    # The band y 43.2 .. 48.8 stays free of parts: it carries the DC bus between the ISO DC link and the
    # DAB secondary (ISOPGND pour on F.Cu, ISODC+ pour on B.Cu). The isolator ISO pins sit south of it
    # (y 38 .. 43), and their signals reach J4/J6/J8 on In3 under the bus.
    "I": ("I", [(52.3, 38.0), (52.3, 48.8), (118.1, 48.8), (118.1, 8.0), (102.2, 8.0), (102.2, -9.4), (90.5, -9.4),
                (90.5, 15.7), (95.1, 15.7), (97.0, 15.9), (98.8, 17.0), (100.1, 19.0), (100.1, 38.0)]),
}
# Plane zones (In1 ground, In2 supply, In4 ground): CA without the J11 pin column above y 33
PLANE_POLY = {"CA": [(44.4, 20.8), (95.1, 20.8), (95.1, 33.0), (44.4, 33.0)]}
# ISO copper south of the card part: U8 (moved), C15, C36 and the 15V_ISO / ISOGND pours, trimmed to this
AREAS["IS"] = ("I", [(87.9, -9.4), (102.2, -9.4), (102.2, -21.6), (97.5, -21.6), (97.5, -25.5), (87.9, -25.5)])
# ISO copper outside the card that bounds CA (for the gap check and the pour pull-back):
# west of J11 the ISODC+ pours end at x 39.4; north of J11 ISO copper starts at y 51.1.
I_AROUND_CA = [[(30.0, 10.0), (39.4, 10.0), (39.4, 48.0), (40.2, 49.5), (41.7, 50.45), (42.7, 51.1), (49.0, 51.1),
                (50.6, 50.4), (52.3, 48.0), (52.3, 60.0), (30.0, 60.0)]]

# Barrier centre lines (name, domains, polyline)
BUS_BAND = (52.3, 43.2, 118.1, 48.8)   # no parts here, on either side (DC bus F.Cu ISOPGND / B.Cu ISODC+)
LINES = [
    ("B-CP", "C|P", [(41.9, 18.3), (88.0, 18.3)]),
    ("B-CI north", "C|I", [(41.9, 18.3), (41.9, 46.1), (41.95, 47.0), (42.3, 47.8), (43.05, 48.3), (43.6, 48.6), (47.9, 48.6),
                           (48.95, 48.25), (49.6, 47.3), (49.8, 46.6), (49.8, 35.5), (97.6, 35.5)]),
    ("B-CI east", "C|I", [(97.6, 35.5), (97.6, 19.9), (96.95, 18.9), (96.05, 18.35), (95.1, 18.25), (88.0, 18.3)]),
    ("B-PI", "P|I", [(88.0, 18.3), (88.0, -3.36)]),
    ("B-IC J12 north", "I|C", [(104.7, 5.5), (118.6, 5.5)]),
    ("B-IC J12 west", "I|C", [(104.7, 5.5), (104.7, -24.4), (100.0, -24.4), (100.0, -34.5)]),
]

# Slots (Edge.Cuts, 1.2 mm wide, rounded ends): (name, (x0, y0), (x1, y1)). >= 2 mm FR4 web between slots.
SLOT_W = 1.2
SLOTS = [
    ("U15", (51.5, 18.3), (60.5, 18.3)), ("U13", (63.5, 18.3), (72.5, 18.3)), ("U16", (75.5, 18.3), (84.5, 18.3)),
    ("U21", (52.55, 35.5), (61.55, 35.5)), ("U19", (63.5, 35.5), (72.5, 35.5)), ("U20", (74.45, 35.5), (83.45, 35.5)),
    ("U22", (85.45, 35.5), (90.05, 35.5)), ("U23", (97.6, 27.4), (97.6, 32.0)), ("U24", (97.6, 20.8), (97.6, 25.4)),
    ("U17 (spare)", (88.0, -4.0), (88.0, 5.0)), ("P|I run", (88.0, 7.0), (88.0, 13.5)),
    ("C|P west run", (44.5, 18.3), (49.5, 18.3)),
    ("J12 north", (107.0, 5.5), (116.0, 5.5)), ("J12 west a", (104.7, -11.0), (104.7, 2.5)),
    ("J12 west b", (104.7, -23.0), (104.7, -13.0)),
]

# Through-hole tails of the control card (baseboard IPC frame), read from the card board
# ~/dev/efinix_soc_board/kicad/ti135_card.kicad_pcb on 2026-11-15 (card KiCad -> IPC: x - 88.932,
# 98.054 - y). No top-side baseboard part within KEEP_R of a hole centre. (ref, x, y, drill)
CARD_HOLES = (
    [("J1", 103.71 + 2.54 * i, -3.35, 1.0) for i in range(5)] + [("J2", 103.69 + 2.54 * i, -7.45, 1.0) for i in range(3)]
    + [("J101", 111.59, -12.9, 1.0), ("J101", 114.13, -12.9, 1.0)]
    + [("J5", 63.98 + 2.54 * i, -16.4, 1.0) for i in range(14)]
    + [("J9", 103.15 if i % 2 == 0 else 105.69, 30.71 + 1.27 * i, 0.89) for i in range(10)]
    + [("J9", 116.94, y, 1.02) for y in (29.8, 32.34, 40.51, 43.05)]
    + [("J9", 108.99, 44.17, 1.63), ("J9", 108.99, 28.68, 1.63), ("J9", 112.04, 42.14, 3.25), ("J9", 112.04, 30.71, 3.25)])
KEEP_MARGIN = 1.5      # mm beyond the drill radius (pad ring + 1 mm)
# The Ti60F225 card must fit too (user 2026-11-15). Its plated holes, from the IPC-D-356 netlist of
# "ti60f225_psu_control_card - CADCAM.ZIP" (Ti60 frame + (11.068, -1.946)): JTAG, UART, 5 V header, LCD, RJ45.
TI60_HOLES = ([("Ti60 J1 JTAG", 69.40, 27.68 + 2.54 * i, 1.016) for i in range(5)]
              + [("Ti60 J8 UART", 63.50, 32.86 + 2.54 * i, 1.016) for i in range(3)]
              + [("Ti60 J3 5V", 108.96 + 2.54 * i, -13.0, 1.016) for i in range(3)]
              + [("Ti60 J4 LCD", 63.98 + 2.54 * i, -16.4, 0.8) for i in range(13)]
              + [("Ti60 J2 RJ45", 107.40 if i % 2 == 0 else 104.86, 31.95 + 1.27 * i, 0.75) for i in range(8)]
              + [("Ti60 J2 RJ45", 116.8, 28.6, 1.6), ("Ti60 J2 RJ45", 116.8, 44.2, 1.6),
                 ("Ti60 J2 RJ45", 113.75, 30.68, 3.25), ("Ti60 J2 RJ45", 113.75, 42.11, 3.25)])
H_TOP_UNDER_CARD, H_BOTTOM = 2.65, 10.0
MOUNT_HOLE_R = 4.0     # bottom side: nothing within 4 mm of H1-H4 (H4 at (81.0, -14.5))

# Proposed rough positions: ref -> (area, side, x, y, note). Barrier parts name both areas.
# Exact positions and rotations come in phase 3 (tools/v5/v5_4_card_area.py), checked by check_layout.py.
def _blk(refs, area, side, x, y, note):
    return {r: (area, side, x, y, note) for r in refs.split()}

PLACE = {}
# -- barrier parts (all new ones on the bottom: Ti60 tails above U19/U21, AMC1311 DWV up to 2.8 mm) ----------
PLACE.update({
    "U16": ("CA|P", "F", 80.0, 18.3, "in line with U15/U13, rot -90 (was -135 at (81.8, 14.0))"),
    "U21": ("CA|I", "B", 57.05, 35.5, "bottom; U4/U6 sigma-delta clock and data; ISO pins north, south of the DC bus band"),
    "U19": ("CA|I", "B", 68.0, 35.5, "bottom; PWM_Q5-Q8, TRANS4/5 -> J8/J6/J4 on In3 under the DC bus"),
    "U20": ("CA|I", "B", 78.95, 35.5, "bottom; DAB_PWM_HI/LO_SEC -> J4, TRANS6, relay"),
    "U22": ("I|CA", "B", 87.75, 35.5, "bottom, in the isolator row (VIN side north); ISOADA1"),
    "U23": ("I|CA", "B", 97.6, 29.7, "bottom; ISOADA2: VIN side east"),
    "U24": ("I|CA", "B", 97.6, 23.1, "bottom; ISOADA3: VIN side east"),
})
# -- CTRL piece at J11 ----------------------------------------------------------------------
PLACE.update(_blk("C117 C119 C121", "CA", "B", 68.0, 28.95, "bottom, just south of pin 1 of U19 / U20 / U21"))
PLACE.update({"C82": ("CA", "F", 86.2, 23.0, "east of U16 pin 1 (U16 moved)"),
              "C124": ("CA", "F", 88.0, 30.2, "top, opposite U22 pin 8"), "C126": ("CA", "F", 91.5, 29.7, "top, opposite U23 pin 8"),
              "C128": ("CA", "F", 91.5, 23.1, "top, opposite U24 pin 8")})
PLACE.update(_blk("U25 R116 R117 R118 R119 R120 R121 R122 R123 C132", "CA", "B", 82.0, 25.5,
                  "ISOADA1/2 difference amplifier, bottom, x 75..90, y 21..28.4, below the AMC1311 outputs"))
PLACE.update(_blk("U26 R124 R125 R126 R127 C133", "CA", "B", 82.0, 24.0,
                  "ISOADA3 difference amplifier, bottom, same block"))
PLACE.update(_blk("R128 R129 R130 C129 C130 C131", "CA", "F", 54.4, 26.6,
                  "8.2k + C output filters towards J11 pins 1/3/4: x 52.8..56.0, y 24.7..28.6"))
PLACE.update(_blk("U27 C134 C135 C136", "CA", "B", 67.0, 26.0, "3V3_CTRL LDO block, bottom, x 64..70.2, y 22.4..29.3"))
PLACE.update({"J14": ("CA", "THT", 59.3, 27.0, "5 V link: two wires soldered into the holes from the bottom, no header (user 2026-11-15)"),
              "PEC1": ("CA", "THT", 50.1, 26.6, "PE bond terminal; lug and screw on the bottom")})
# -- ISO --------------------------------------------------------------------------------------
PLACE.update(_blk("C118 C120 C122", "I", "F", 68.0, 40.15, "top, opposite pin 16 of U19 / U20 / U21 (two vias each)"))
PLACE.update({"C123": ("I", "F", 88.0, 40.8, "top, opposite U22 pin 1"),
              "C125": ("I", "B", 104.3, 29.7, "bottom, beside U23 pin 1"), "C127": ("I", "B", 104.3, 23.1, "bottom, beside U24 pin 1")})
PLACE.update(_blk("R110 R111", "I", "B", 93.3, 40.15, "x0.4 divider at U22 VIN, bottom"))
PLACE.update(_blk("R112 R113", "I", "B", 107.0, 29.65, "x0.4 divider at U23 VIN, bottom"))
PLACE.update(_blk("R114 R115", "I", "B", 107.0, 23.05, "x0.4 divider at U24 VIN, bottom"))
PLACE.update(_blk("U7 C103 C104 C105 C108 C38 R46 R51 R52 R53 R54 R56", "I", "F", 100.8, 12.0,
                  "VSI voltage block (ISOADA1/2), moved as it is to x 95.2..106.5, y 8.5..15.5"))
PLACE.update({"C106": ("I", "B", 104.1, 11.3, "VSI voltage block, bottom as before"),
              "C107": ("I", "B", 99.0, 14.8, "VSI voltage block, bottom as before"),
              "C56": ("I", "F", 107.6, 14.5, "U7 supply capacitor (was alone at (63.4, 25.4), now CTRL area)")})
PLACE.update(_blk("U2 C101 C102 C2 C87 R1 R76 R77", "I", "F", 97.9, 5.0,
                  "ISO DC-link block (ISOADA3), moved as it is to x 94.3..101.5, y 1.7..8.2"))
PLACE.update(_blk("U10 C3 C4", "I", "F", 97.1, -2.3, "3V3_ISO LDO block, moved to x 95.3..98.8, y -5.7..1.1 (leaves the J12 piece)"))
PLACE.update({"U8": ("I", "F", 91.0, -20.1, "moved 13.36 mm west along its 15V_ISO / ISOGND pours (was 1.9 mm from J12)"),
              "C93": ("I", "B", 92.04, -22.9, "moves with U8"), "C94": ("I", "B", 96.08, -23.3, "moves with U8")})
# -- primary ----------------------------------------------------------------------------------
PLACE.update({"C81": ("P", "F", 84.4, 11.3, "south of U16 pin 16 (U16 moved)")})
# -- CTRL piece at J12 --------------------------------------------------------------------------
PLACE.update({
    "C137": ("CB", "B", 112.65, -1.6, "polymer 8x10, bottom, under the card"),
    "C138": ("CB", "B", 112.65, -23.3, "polymer 8x10, bottom, right under D16 (rectifier loop)"),
    "L2": ("CB", "B", 110.8, -10.6, "4.5 mm high, bottom, between J12 and C137"),
    "D16": ("CB", "F", 111.0, -25.8, "top, south of the card edge, above C138"),
    "W1": ("CB", "THT", 112.6, -31.6, "CTRL winding leads (final position with T1)"),
    "PEC2": ("CB", "THT", 105.6, -30.75, "PE bond terminal"),
    "J13": ("CB", "THT", 116.8, -9.6, "5 V link: two wires soldered into the holes from the bottom, no header (user 2026-11-15)"),
})
PLACE.update(_blk("U28 C140 C141 R134 R135", "CB", "F", 112.6, 0.85, "TPS54202 with its capacitors and FB divider, top, north of the J1 tail row"))
PLACE.update(_blk("C139 C144", "CB", "F", 113.0, -8.15, "buck input capacitor and FB capacitor, top, between the J1 and J101 tail rows"))
PLACE.update(_blk("R131 R132 R133", "CB", "F", 114.8, -20.8, "CTRL_RAW preload and EN divider, top, south of J12"))
PLACE.update(_blk("C142 C143", "CB", "F", 110.0, -21.4, "buck output capacitors, top, south of J12"))

# Parts moved as rigid groups (their mutual courtyard overlaps are the accepted v4 ones)
GROUPS = ["U7 C103 C104 C105 C106 C107 C108 C38 R46 R51 R52 R53 R54 R56", "U2 C101 C102 C2 C87 R1 R76 R77", "U10 C3 C4", "U8 C93 C94"]
# Placed parts without the card-tail check, and why
TAIL_EXEMPT = {"U8": "same y as before (pins 1.33 mm south of the card edge); its body stands beside the card, not under it",
               "J13": "wires soldered from the bottom", "J14": "wires soldered from the bottom"}

# v4 tracks to delete in phase 3: every track/via in the card area on a net of these parts' moved
# pads, plus all CTRL-domain tracks of the J11 fan-out (they cross the new U19-U21 pads).
HEIGHT_NOTE = "SOIC-16W / SOIC-8W 2.65 mm; VSSOP 1.1; SOT-23 1.45; 0402 0.55; 0603 0.9; 1206 1.8; SMA 2.3 (not under the card)"

# Height (mm) per footprint, for the limits above (tools/v5/check_layout.py). Maximum body heights from the
# data sheets or the JEDEC outline; SOIC-8 wide (DWV) is 2.8 mm, above the 2.65 mm top-side limit.
HEIGHT = {
    "C_0402_1005Metric": 0.55, "C_0603_1608Metric": 0.9, "C_0805_2012Metric": 1.35, "C_1206_3216Metric": 1.8,
    "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder": 1.8, "C_1210_3225Metric": 2.7,
    "R_0402_1005Metric": 0.4, "R_0603_1608Metric": 0.55, "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder": 0.65,
    "R_1206_3216Metric": 0.65, "R_1206_3216Metric_Pad1.30x1.75mm_HandSolder": 0.65, "R_Array_Convex_4x0402_Proteus": 0.45,
    "R_Shunt_FKK5R0020FE": 1.0, "L_0805_2012Metric": 1.35, "L_Sunlord_SWPA6045S": 4.5, "D_SMA_AC": 2.3,
    "CP_Elec_8x10": 10.0, "CP_Elec_6.3x7.7_EEEFTE221XAP": 7.7,
    "SOIC-16W_7.5x10.3mm_P1.27mm": 2.65, "SOIC-16W_7.5x10.3mm_P1.27mm_Proteus": 2.65,
    "SOIC-8_7.5x5.85mm_P1.27mm": 2.8, "SOIC-8W_7.5x5.85mm_P1.27mm_ADuM7701": 2.8,
    "SOT-23-5": 1.45, "SOT-23-5_TLV316": 1.45, "SOT-23-5_TPS73033": 1.45, "SOT-23-6": 1.1, "SOT-23_Proteus": 1.12,
    "TSSOP-16_4.4x5mm_P0.65mm_Proteus": 1.2, "TSSOP-8_3x3mm_P0.65mm_Proteus": 1.1, "VSSOP-8_3x3mm_P0.65mm": 1.1,
    "X2QFN-8_1.5x1.5mm_P0.5mm_ADS7056": 0.4,
}
# Through-hole / hand-fit parts without a height check, and why
NO_HEIGHT = {
    "J11": "mates with the card", "J12": "mates with the card", "H4": "mounting hole",
    "J13": "wires soldered from the bottom, no header", "J14": "wires soldered from the bottom, no header",
    "PEC1": "lug and screw on the bottom, pin trimmed on top", "PEC2": "lug and screw on the bottom",
    "W1": "flying leads of T1, soldered", "U8": "outside the card outline (pins at y -20.1)",
}
