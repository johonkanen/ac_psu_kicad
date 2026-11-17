"""v5 card-area layout, revision 2 (PROPOSAL, user 2026-11-17): nothing here is on the board yet.

The first placement (card_layout.py, v5 step 4) could not be routed: the CTRL column beside J11 was
2.9 mm wide and the CTRL area 12.2 mm high. Revision 2, after the user's proposal:
  - the primary logic block is tightened (ADC and reference groups go to the bottom side), so the
    primary isolators U15/U13/U16 and the C|P line move 10 mm south (y 18.3 -> 8.3);
  - the CTRL area grows south by the same 10 mm;
  - U22 (ISOADA1) leaves the north isolator row for the new east edge of that southern part (x 88);
  - the north row U21/U19/U20 moves 6.6 mm east, so the CTRL column beside J11 is 9.5 mm wide.
Everything not redefined below is card_layout.py. layout_proposal.py --rev2 checks this file and writes
reports/v5_layout/rev2/. After approval this file replaces card_layout.py.
"""
from card_layout import *  # noqa: F401,F403
import card_layout as _L1

Y_CP = 8.3            # C|P barrier centre line (was 18.3)
AREAS = dict(_L1.AREAS)
AREAS["CA"] = ("C", [(44.4, 10.8), (85.5, 10.8), (85.5, 20.8), (95.1, 20.8), (95.1, 33.0), (53.9, 33.0), (53.9, 46.1), (44.4, 46.1)])
AREAS["P"] = ("P", [(42.55, -20.66), (69.65, -20.66), (69.65, -3.36), (85.5, -3.36), (85.5, 5.8), (42.55, 5.8)])
AREAS["I"] = ("I", [(58.9, 38.0), (58.9, 48.8), (118.1, 48.8), (118.1, 8.0), (102.2, 8.0), (102.2, -9.4), (90.5, -9.4),
                    (90.5, 15.7), (95.1, 15.7), (97.0, 15.9), (98.8, 17.0), (100.1, 19.0), (100.1, 38.0)])
PLANE_POLY = {"CA": [(44.4, 10.8), (85.5, 10.8), (85.5, 20.8), (95.1, 20.8), (95.1, 33.0), (44.4, 33.0)]}
I_AROUND_CA = [[(30.0, 22.0), (39.4, 22.0), (39.4, 48.0), (40.2, 49.5), (41.7, 50.45), (42.7, 51.1), (55.6, 51.1),
                (57.2, 50.4), (58.9, 48.0), (58.9, 60.0), (30.0, 60.0)]]
BUS_BAND = (58.9, 43.2, 118.1, 48.8)
LINES = [
    ("B-CP", "C|P", [(41.9, 8.3), (88.0, 8.3)]),
    ("B-CI north", "C|I", [(41.9, 8.3), (41.9, 46.1), (41.95, 47.0), (42.3, 47.8), (43.05, 48.3), (43.6, 48.6), (54.5, 48.6),
                           (55.55, 48.25), (56.2, 47.3), (56.4, 46.6), (56.4, 35.5), (97.6, 35.5)]),
    ("B-CI east", "C|I", [(97.6, 35.5), (97.6, 19.9), (96.95, 18.9), (96.05, 18.35), (95.1, 18.25), (88.0, 18.3), (88.0, 8.3)]),
    ("B-PI", "P|I", [(88.0, 8.3), (88.0, -3.36)]),
] + [l for l in _L1.LINES if l[0].startswith("B-IC")]
SLOTS = [
    ("U15", (48.5, 8.3), (57.5, 8.3)), ("U13", (60.5, 8.3), (69.5, 8.3)), ("U16", (72.5, 8.3), (81.5, 8.3)),
    ("C|P east run", (83.5, 8.3), (85.4, 8.3)),
    ("U21", (59.15, 35.5), (68.15, 35.5)), ("U19", (70.1, 35.5), (79.1, 35.5)), ("U20", (81.05, 35.5), (90.05, 35.5)),
    ("U22", (88.0, 10.95), (88.0, 15.55)), ("U23", (97.6, 27.4), (97.6, 32.0)), ("U24", (97.6, 20.8), (97.6, 25.4)),
    ("U17 (spare)", (88.0, -4.0), (88.0, 5.0)), ("P|I run", (88.0, 7.0), (88.0, 8.95)),
] + [s for s in _L1.SLOTS if s[0].startswith("J12")]

PLACE = dict(_L1.PLACE)
# -- barrier parts ----------------------------------------------------------------------------
PLACE.update({
    "U15": ("CA|P", "F", 53.0, Y_CP, "10 mm south, 3 mm west (was (56.0, 18.3))"),
    "U13": ("CA|P", "F", 65.0, Y_CP, "10 mm south, 3 mm west (was (68.0, 18.28))"),
    "U16": ("CA|P", "F", 77.0, Y_CP, "10 mm south, 3 mm west (was (80.0, 18.3))"),
    "U21": ("CA|I", "B", 63.65, 35.5, "bottom; 6.6 mm east (was x 57.05): the CTRL column beside J11 widens to 9.5 mm"),
    "U19": ("CA|I", "B", 74.6, 35.5, "bottom; 6.6 mm east (was x 68.0)"),
    "U20": ("CA|I", "B", 85.55, 35.5, "bottom; 6.6 mm east (was x 78.95), takes U22's place at the east end of the row"),
    "U22": ("I|CA", "B", 88.0, 13.25, "bottom, on the new east edge of the southern CTRL part; VIN side east, beside the U7 block (ISOADA1)"),
})
# -- CTRL piece at J11 ----------------------------------------------------------------------------
PLACE.update({"C86": ("CA", "F", 58.7, 13.45, "with U15"), "C83": ("CA", "F", 71.0, 13.45, "with U13"),
              "C82": ("CA", "F", 83.2, 16.0, "with U16"),
              "C121": ("CA", "B", 68.1, 28.95, "with U21"), "C117": ("CA", "B", 79.05, 28.95, "with U19"),
              "C119": ("CA", "B", 90.0, 28.95, "with U20"),
              "C124": ("CA", "B", 81.0, 16.5, "bottom, beside U22 pin 8")})
PLACE.update(_L1._blk("U25 R116 R117 R118 R119 R120 R121 R122 R123 C132", "CA", "B", 80.0, 23.5,
                      "ISOADA1/2 difference amplifier, bottom, x 72..88, y 20..27, between U22 and U23; 2.3 mm row pitch"))
PLACE.update(_L1._blk("U26 R124 R125 R126 R127 C133", "CA", "B", 88.5, 24.0, "ISOADA3 difference amplifier, bottom, west of U24"))
PLACE.update(_L1._blk("R128 R129 R130 C129 C130 C131", "CA", "F", 50.5, 20.0,
                      "8.2k + C output filters, 1.6 mm pitch, south-east of J11 pins 1/3/4"))
PLACE.update(_L1._blk("U27 C134 C135 C136", "CA", "B", 62.0, 21.0, "3V3_CTRL LDO block, bottom, x 58..66, y 18..24"))
PLACE.update({"J14": ("CA", "THT", 66.0, 17.5, "5 V link wires; out of the J11 fan-out"),
              "PEC1": ("CA", "THT", 51.0, 17.6, "PE bond terminal; south of the J11 fan-out, 6.6 mm from the area's west edge")})
# -- ISO ----------------------------------------------------------------------------------------
PLACE.update({"C122": ("I", "F", 66.4, 40.15, "with U21, between the Ti60 UART and JTAG tails"), "C118": ("I", "F", 79.05, 40.15, "with U19"),
              "C120": ("I", "F", 90.0, 40.15, "with U20"),
              "C123": ("I", "B", 93.2, 9.5, "bottom, beside U22 pin 1")})
PLACE.update(_L1._blk("R110 R111", "I", "B", 97.0, 12.5, "x0.4 divider at U22 VIN, bottom, under the U7 block"))
# -- primary: the logic block tightened (user 2026-11-17: parts to the bottom, inner layers for routing) --
PLACE.update({"C84": ("P", "F", 57.5, 0.85, "with U15"), "C85": ("P", "F", 69.47, 1.57, "with U13"),
              "C81": ("P", "F", 81.44, 1.5, "with U16"),
              "R22": ("P", "F", 56.6, 1.0, "ADCLK series resistor, at U15 B5")})
PLACE.update(_L1._blk("AD1 R87 C9 R86 C17 U12 L1 C18", "P", "B", 61.1, 0.0,
                      "ADC group as it is, mirrored to the bottom and 5 mm south: x 57.7..64.5, y -5.4..5.5 (top side: U11)"))
PLACE.update(_L1._blk("REF1 C40 C16 R19 R30 C109", "P", "B", 52.0, 3.5,
                      "1.65 V reference group as it is, mirrored to the bottom: x 47.6..56.3, y 1.6..5.5"))
GROUPS = _L1.GROUPS + ["AD1 R87 C9 R86 C17 U12 L1 C18", "REF1 C40 C16 R19 R30 C109"]
