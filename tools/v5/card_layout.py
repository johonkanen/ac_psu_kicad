"""v5 card-area layout data (stdlib only): the three isolated domains under the control card
(V5_LAYOUT_PLAN.md). Coordinates: mm, IPC frame (Y up; KiCad y = -y).

PROPOSAL (phase 1, reports/v5_layout/proposal.md): nothing here is on the board yet. After the
user's approval this file is the single source for tools/v5/check_layout.py (phase 2) and
tools/v5/v5_4_card_area.py (phase 3).
"""
CARD = (42.599, -18.766, 118.599, 46.361)      # card outline x0, y0, x1, y1
BOARD_EDGE_X = 118.6
GAP = 5.0                                      # reinforced, P-I / P-C / I-C, every copper layer

# Copper areas: where a domain's pads, tracks, vias and zones may be, on all six layers.
# Every pair of areas is >= 5.0 mm apart (layout_proposal.py checks it), so the strip between
# two areas is the barrier; its centre line is 2.5 mm from both.
AREAS = {
    # CTRL piece at J11 (CTRLGND_A / 3V3_CTRL / 5V_CTRL_A)
    "CA": ("C", [(44.4, 20.8), (90.0, 20.8), (90.0, 39.0), (47.3, 39.0), (47.3, 46.1), (44.4, 46.1)]),
    # CTRL piece at J12 (CTRLGND / 5V_CTRL / CTRL_RAW); open to nothing: board edge on the east
    "CB": ("C", [(107.2, 3.0), (118.1, 3.0), (118.1, -34.5), (102.5, -34.5), (102.5, -27.0), (107.2, -27.0)]),
    # primary logic (GND / VCC): the card-area part; west and south it joins the primary power stage
    "P": ("P", [(42.55, -20.66), (69.65, -20.66), (69.65, -3.36), (85.5, -3.36), (85.5, 15.8), (42.55, 15.8)]),
    # ISO (ISOGND / 3V3_ISO): the card-area part; north it joins J4/J6/J8 and the ISO power stage,
    # south (x 87.9 .. 102.2, below y -9.4) the 15V_ISO / U8 copper of the aux area
    "I": ("I", [(52.3, 44.0), (52.3, 46.38), (118.1, 46.38), (118.1, 8.0), (102.2, 8.0), (102.2, -9.4),
                (90.5, -9.4), (90.5, 15.7), (93.0, 16.2), (95.0, 18.0), (95.0, 44.0)]),
}
# ISO copper outside the card that bounds CA (for the gap check and the pour pull-back):
# west of J11 the ISODC+ pours end at x 39.4; north of J11 ISO copper starts at y 51.1.
I_AROUND_CA = [[(30.0, 10.0), (39.4, 10.0), (39.4, 48.0), (40.2, 49.5), (41.7, 50.45), (42.7, 51.1), (49.0, 51.1),
                (50.6, 50.4), (52.3, 48.0), (52.3, 60.0), (30.0, 60.0)]]

# Barrier centre lines (name, domains, polyline)
LINES = [
    ("B-CP", "C|P", [(41.9, 18.3), (87.75, 18.3)]),
    ("B-CI north", "C|I", [(41.9, 18.3), (41.9, 46.8), (43.3, 48.5), (47.2, 48.6), (49.3, 47.6), (49.8, 46.1),
                           (49.8, 41.5), (92.5, 41.5)]),
    ("B-CI east", "C|I", [(92.5, 41.5), (92.5, 19.4), (90.8, 18.3), (87.75, 18.3)]),
    ("B-PI", "P|I", [(87.75, 18.3), (88.0, 15.8), (88.0, -3.36)]),
    ("B-IC J12 north", "I|C", [(104.7, 5.5), (118.6, 5.5)]),
    ("B-IC J12 west", "I|C", [(104.7, 5.5), (104.7, -27.0), (100.0, -27.0), (100.0, -34.5)]),
]

# Slots (Edge.Cuts, 1.2 mm wide, rounded ends): (name, (x0, y0), (x1, y1)). >= 2 mm FR4 web between slots.
SLOT_W = 1.2
SLOTS = [
    ("U15", (51.5, 18.3), (60.5, 18.3)), ("U13", (63.5, 18.3), (72.5, 18.3)), ("U16", (75.5, 18.3), (84.5, 18.3)),
    ("U21", (52.8, 41.5), (61.8, 41.5)), ("U19", (64.0, 41.5), (73.0, 41.5)), ("U20", (75.2, 41.5), (84.2, 41.5)),
    ("U22", (92.5, 34.4), (92.5, 39.0)), ("U23", (92.5, 27.6), (92.5, 32.2)), ("U24", (92.5, 20.8), (92.5, 25.4)),
    ("U17 (spare)", (88.0, -4.0), (88.0, 5.0)), ("P|I run", (88.0, 7.0), (88.0, 13.5)),
    ("C|P west run", (44.5, 18.3), (49.5, 18.3)),
    ("J12 north", (107.0, 5.5), (116.0, 5.5)), ("J12 west a", (104.7, -11.0), (104.7, 2.5)),
    ("J12 west b", (104.7, -25.0), (104.7, -13.0)),
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
# -- barrier parts --------------------------------------------------------------------------
PLACE.update({
    "U16": ("CA|P", "F", 80.0, 18.3, "in line with U15/U13, rot -90 (was -135 at (81.8, 14.0))"),
    "U21": ("CA|I", "B", 57.3, 41.5, "bottom (Ti60 JTAG/UART tails above); C pins south, ISO pins north; U4 path leaves west above J11"),
    "U19": ("CA|I", "B", 68.5, 41.5, "bottom (Ti60 JTAG/UART tails above); PWM_Q5-Q8, TRANS4/5 -> J8/J6/J4 straight north"),
    "U20": ("CA|I", "B", 79.7, 41.5, "bottom (Ti60 JTAG/UART tails above); DAB_PWM_HI/LO_SEC -> J4, TRANS6, relay"),
    "U22": ("I|CA", "F", 92.5, 36.7, "ISOADA1: VIN side east, output side west"),
    "U23": ("I|CA", "F", 92.5, 29.9, "ISOADA2"),
    "U24": ("I|CA", "F", 92.5, 23.1, "ISOADA3"),
})
# -- CTRL piece at J11 ----------------------------------------------------------------------
PLACE.update({"C121": ("CA", "B", 61.75, 34.7, "bottom, south of U21 pin 1"), "C117": ("CA", "B", 72.95, 34.7, "bottom, south of U19 pin 1"),
              "C119": ("CA", "B", 84.15, 34.7, "bottom, south of U20 pin 1"),
              "C82": ("CA", "B", 84.4, 23.0, "under U16 pin 1 (U16 moved)"),
              "C124": ("CA", "B", 87.2, 34.8, "under U22 pin 8"), "C126": ("CA", "B", 87.2, 28.0, "under U23 pin 8"),
              "C128": ("CA", "B", 87.2, 21.2, "under U24 pin 8")})
PLACE.update(_blk("U25 R116 R117 R118 R119 R120 R121 R122 R123 C132", "CA", "F", 80.0, 32.4,
                  "ISOADA1/2 difference amplifier block x 74.5..85.4, y 29.8..35.0, next to U22/U23 outputs"))
PLACE.update(_blk("U26 R124 R125 R126 R127 C133", "CA", "F", 80.0, 26.9,
                  "ISOADA3 difference amplifier block x 74.5..85.4, y 24.5..29.4, next to U24 outputs"))
PLACE.update(_blk("R128 R129 R130 C129 C130 C131", "CA", "F", 49.3, 27.5,
                  "8.2k + C output filters at J11 pins 1/3/4: block x 48.0..50.4, y 24.6..30.5"))
PLACE.update(_blk("U27 C134 C135 C136", "CA", "B", 62.5, 30.0, "3V3_CTRL LDO block, bottom, x 59..66, y 27..33"))
PLACE.update({"J14": ("CA", "B", 55.5, 30.0, "5 V link header, THT from the bottom (see open items: height)"),
              "PEC1": ("CA", "THT", 50.3, 33.0, "PE bond terminal; lug and screw on the bottom")})
# -- ISO --------------------------------------------------------------------------------------
PLACE.update({"C122": ("I", "B", 61.75, 48.3, "bottom, north of U21 pin 16"), "C118": ("I", "B", 72.95, 48.3, "bottom, north of U19 pin 16"),
              "C120": ("I", "B", 84.15, 48.3, "bottom, north of U20 pin 16"),
              "C123": ("I", "B", 97.8, 34.8, "under U22 pin 1"), "C125": ("I", "B", 97.8, 28.0, "under U23 pin 1"),
              "C127": ("I", "B", 97.8, 21.2, "under U24 pin 1")})
PLACE.update(_blk("R110 R111", "I", "F", 100.0, 36.7, "x0.4 divider at U22 VIN, column x 99.2..100.8"))
PLACE.update(_blk("R112 R113", "I", "F", 100.0, 29.9, "x0.4 divider at U23 VIN"))
PLACE.update(_blk("R114 R115", "I", "F", 100.0, 23.1, "x0.4 divider at U24 VIN"))
PLACE.update(_blk("U7 C103 C104 C105 C106 C107 C108 C38 C56 R46 R51 R52 R53 R54 R56", "I", "F", 100.7, 17.4,
                  "VSI voltage block (ISOADA1/2), x 95.5..106.0, y 14.5..20.3; the 1n caps may go to the bottom"))
PLACE.update(_blk("U2 C101 C102 C2 C87 R1 R76 R77", "I", "F", 99.7, 11.2,
                  "ISO DC-link block (ISOADA3), x 95.5..104.0, y 8.5..13.8; next to REF2 (fixed)"))
PLACE.update(_blk("U10 C3 C4", "I", "F", 97.5, 0.8, "3V3_ISO LDO block x 94.5..100.5, y -2.5..4.0 (leaves the J12 piece)"))
PLACE.update({"R97": ("I", "F", 99.6, 43.0, "ISOGND-ISOPGND link, moved 2.8 mm east (U22 courtyard)"),
              "U8": ("I", "F", 91.0, -20.1, "moved 13.36 mm west along its 15V_ISO / ISOGND pours (was 1.9 mm from J12)"),
              "C93": ("I", "B", 92.04, -22.9, "moves with U8"), "C94": ("I", "B", 96.08, -23.3, "moves with U8")})
# -- primary ----------------------------------------------------------------------------------
PLACE.update({"C81": ("P", "F", 84.4, 11.3, "south of U16 pin 16 (U16 moved)")})
# -- CTRL piece at J12 --------------------------------------------------------------------------
PLACE.update({
    "C137": ("CB", "B", 112.6, -1.6, "polymer 8x10, bottom, under the card"),
    "C138": ("CB", "B", 112.6, -10.6, "polymer 8x10, bottom, under the card"),
    "L2": ("CB", "B", 111.0, -23.5, "4.5 mm high, bottom"),
    "D16": ("CB", "F", 109.5, -24.5, "top, south of the card edge, vertical"),
    "W1": ("CB", "THT", 107.2, -31.2, "CTRL winding leads, at the aux-area side (final position with T1)"),
    "PEC2": ("CB", "THT", 115.3, -31.6, "PE bond terminal"),
    "J13": ("CB", "B", 116.0, -23.0, "5 V link header, same side as J14"),
})
PLACE.update(_blk("U28 C139 C140 C141 C144 R131 R132 R133 R134 R135", "CB", "B", 109.0, -17.5,
                  "TPS54202 block, bottom, x 107.4..110.8, y -21..-13.5 and x 107.4..117.9, y -28.5..-27 "))
PLACE.update(_blk("C142 C143", "CB", "B", 115.0, -27.7, "buck output capacitors next to L2 / J13"))

# v4 tracks to delete in phase 3: every track/via in the card area on a net of these parts' moved
# pads, plus all CTRL-domain tracks of the J11 fan-out (they cross the new U19-U21 pads).
HEIGHT_NOTE = "SOIC-16W / SOIC-8W 2.65 mm; VSSOP 1.1; SOT-23 1.45; 0402 0.55; 0603 0.9; 1206 1.8; SMA 2.3 (not under the card)"
