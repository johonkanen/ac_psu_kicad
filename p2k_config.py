"""proteus2kicad configuration of the single_phase_inverter_psu_v3 board (tools in tools/p2k,
see its README). Plain Python; every value here is specific to this board. Coordinates in mm,
IPC frame (Y up).
"""

PROJECT = "ac_psu"  # KiCad project / library name

# Parts of lib/part_map.csv without IPC pads (footprint map note; gen_footprints does not fit them).
OFF_BOARD_PARTS = {"TR1": "not on the board"}

# Sources (relative to the repo root).
CADCAM = "source/cadcam"
IPC = "source/cadcam/single_phase_inverter_psu_v3 - CADCAM Netlist.IPC"

# --- Schematic skeleton (make_skeleton) ----------------------------------------------

# (Proteus page, sheet name, file) - names as in the PDF title blocks
SHEETS = [
    (1, "afe", "01_afe.kicad_sch"),
    (2, "fpga connector", "02_fpga_connector.kicad_sch"),
    (3, "regulators", "03_regulators.kicad_sch"),
    (4, "DC links", "04_dc_links.kicad_sch"),
    (5, "VSI", "05_vsi.kicad_sch"),
    (6, "Dual Active Bridge", "06_dual_active_bridge.kicad_sch"),
    (7, "Auxiliary supply", "07_auxiliary_supply.kicad_sch"),
    (8, "SDM current measurements", "08_sdm_current_measurements.kicad_sch"),
    (9, "primary side ADC", "09_primary_side_adc.kicad_sch"),
    (10, "INU SDM and relay drive", "10_inu_sdm_relay_drive.kicad_sch"),  # untitled in the PDF
    (11, "signal isolators", "11_signal_isolators.kicad_sch"),
]
SCH_TITLE = "Inverter PSU"
SCH_COMPANY = "Inverter PSU"
SCH_REV = "v3"
SCH_COMMENT = "Redrawn from Proteus single_phase_inverter_psu_v3"
SCH_NOTE = ("Inverter PSU v3 - redrawn from Proteus. One sheet per Proteus PDF page.\n"
            "Net names follow the IPC-D-356A netlist (reference/pins_by_net.md).")

# --- IPC-D-356A fix-ups (ipc356) -----------------------------------------------------

# (truncated refdes, x_um, y_um) -> full refdes. Nets confirmed on the PDF:
# AFE_OUT on G3_SOURCE_HI (sheet 1), FILTER_IN on FILTER_INPUT and FILTER_OUT
# on LEMOUT (sheet 1), INU_OUT2 on Q5_S (sheet 5), DAB_PRI_1 on TR1 pin 1 =
# DAB_SOURCE_HI_PRI, DAB_PRI_2 on DAB_CAP_PRI, DAB_SEC_1 on TR1 pin 3 =
# DAB_SOURCE_HI_SEC, DAB_SEC_2 on DAB_CAP_SEC (sheet 6).
TRUNCATED_REFDES = {
    ("AFE_OU", 47500, -73600): "AFE_OUT",
    ("FILTER", -14400, -57300): "FILTER_IN",
    ("FILTER", -33000, -48500): "FILTER_OUT",
    ("INU_OU", 48500, 61500): "INU_OUT2",
    ("DAB_PR", 111250, -70300): "DAB_PRI_1",
    ("DAB_PR", 111250, -63200): "DAB_PRI_2",
    ("DAB_SE", 97900, 61700): "DAB_SEC_1",
    ("DAB_SE", 97900, 55400): "DAB_SEC_2",
}
# Expected net per fixed refdes, used by the self-check.
TRUNCATED_NETS = {
    "AFE_OUT": "G3_SOURCE_HI",
    "FILTER_IN": "FILTER_INPUT",
    "FILTER_OUT": "LEMOUT",
    "INU_OUT2": "Q5_S",
    "DAB_PRI_1": "DAB_SOURCE_HI_PRI",
    "DAB_PRI_2": "DAB_CAP_PRI",
    "DAB_SEC_1": "DAB_SOURCE_HI_SEC",
    "DAB_SEC_2": "DAB_CAP_SEC",
}

NET_ALIASES = {
    "GND=POWER": "GND",
    "VCC/VDD=POWER": "VCC",
}

# Blank-refdes records: vias (0.3 mm) and 4 unnetted plated 3.0 mm mounting holes.
VIA_DRILLS = (0.3,)
HOLE_DRILLS = (3.0,)
HOLES_PLATED = True

# Expected raw counts in the Proteus file (PLAN.md section 1).
EXPECTED_IPC = {
    "nets": 208,          # NNAME declarations
    "records": 1075,
    "refdes_raw": 265,    # distinct refdes fields, incl. the blank one of vias/holes
    "tht_records": 562,   # 317 records (component THT pads + vias + holes)
    "smd_records": 513,   # 327 records
    "smd_top": 341,
    "smd_bottom": 172,
    "nc_pads": 34,
    "vias": 173,
    "free_pads": 0,
    "holes": 4,
    "parts": 267,         # named refdes after the truncation fix-up
}

# --- Gerbers (check_sources) ---------------------------------------------------------

# Proteus copper gerber name -> KiCad copper layer, User layer for the pour outlines.
COPPER = [
    ("Top Copper", "F.Cu", "User.1"),
    ("Inner  1", "In1.Cu", "User.2"),
    ("Inner  2", "In2.Cu", "User.3"),
    ("Bottom Copper", "B.Cu", "User.4"),
]
DRILL_PLATED = "Drill TOP-BOT Plated"
DRILL_NONPLATED = None  # the mounting holes are plated
OUTLINE = "Mechanical 1"
OUTLINE_RECT = (-128.2, -83.0, 246.8, 154.7)  # x, y, width, height

# --- PCB (p2k.build_pcb, gerber_to_tracks, assign_nets, pours_to_zones, check_board, drc) ---
# Paths: kicad/ac_psu.kicad_pcb by default; tools/board_common.py points them at
# build/proteus/ for tools/make_pcb.sh.

# Proteus stack: 4 x 0.036 Cu, 0.32 / 1.483 / 0.32 mm dielectric (CADCAM READ-ME)
PCB_THICKNESS = 2.267
# Rules from the Proteus data: thinnest conductor 0.1016 mm (D69), vias 0.4572 pad / 0.3 drill
# (annular ring 0.0786 mm); clearance and edge clearance see STATUS.md.
PCB_RULES = dict(
    min_track=0.1, min_via=0.45, min_annular=0.075, min_drill=0.3,
    clearance=0.15, hole_clearance=0.15, hole_to_hole=0.25, edge_clearance=0.25,
    track=0.254, via=0.4572, via_drill=0.3,
)
# Unnetted plated mounting holes (IPC 'hole' records): board-only footprints H1..H4.
HOLE_FOOTPRINT = "ac_psu:Terminal_D4.0mm_Drill3.0mm"
HOLE_VALUE = "MountingHole_3.0mm"
# Error-severity DRC types that remain by design (the Proteus layout as it is):
DRC_ACCEPTED = {
    # KiCad library courtyards are larger than the Proteus placement spacing (parts sit
    # where Proteus put them; the Proteus silk outlines do not overlap).
    "courtyards_overlap": "KiCad courtyards vs the Proteus placement",
    "pth_inside_courtyard": "KiCad courtyards vs the Proteus placement",
}
