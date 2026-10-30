#!/usr/bin/env python3
"""v4 fix 11 (run once, kipy): measurement filters from reports/noise (findings 1-5).

- C95-C106 1n C0G 0402 across every 10k leg of the six difference amplifiers (U1A/U1B, U14,
  U2, U7A/U7B): 15.9 kHz, low tap-node impedance at the switching edges. Top side beside the
  resistor with two short tracks where there is room; otherwise bottom side with vias.
- C107/C108 4.7n C0G on ISOADA1/ISOADA2 (with R54/R56 8.2k: 4.1 kHz), a via to the In1 ISOGND
  plane or an existing ISOGND via.
- C109/C110 100n decoupling REF_1V65 / REF_1V65_ISO, beside R30 / R40.
- Values: R7 1k -> 10k (U1B + leg matched), R18/R9 100R -> 8.2k, C88/C89 -> 4.7n C0G,
  C42/C2 -> 10n C0G.
- The schematic's new capacitors rename six amplifier-output nets (KiCad auto names); copper and
  pads are renamed to match.
Pad coordinates are IPC frame (Y up), pad 1 first."""
from v4board import Board

b = Board(4111)
if b.fp("C95") is not None:
    raise SystemExit("fix 11 already applied")

# KiCad auto net names that change with the new capacitor pins (schematic order)
for old, new in (("Net-(R17-Pad1)", "Net-(C96-Pad1)"), ("Net-(R8-Pad1)", "Net-(C98-Pad1)"),
                 ("Net-(R38-Pad1)", "Net-(C100-Pad1)"), ("Net-(R76-Pad1)", "Net-(C102-Pad1)"),
                 ("Net-(R53-Pad1)", "Net-(C104-Pad1)"), ("Net-(R51-Pad1)", "Net-(C106-Pad1)")):
    b.renet(old, new)
for ref in ("R17", "R18", "U1", "R8", "R9", "R38", "R39", "U14", "R76", "R77", "U2", "R53", "R54", "U7", "R51", "R56"):
    b.sync_pads(ref)

for ref, val in (("R7", "10k"), ("R18", "8.2k"), ("R9", "8.2k"), ("C88", "4.7n C0G"), ("C89", "4.7n C0G"),
                 ("C42", "10n C0G"), ("C2", "10n C0G")):
    b.set_value(ref, val)


def beside(ref, rpad1, rpad2, q1, q2):
    """Top-side cap beside a resistor: cap pad 1 tracked to resistor pad rpad1, pad 2 to rpad2."""
    b.add_part(ref, "top", q1, q2)
    b.track("F.Cu", [rpad1, q1], 0.25, b.pin_net[(ref, "1")])
    b.track("F.Cu", [rpad2, q2], 0.25, b.pin_net[(ref, "2")])


# ---- top side, beside the resistor (C pad 1 = the net of the resistor pad named first)
beside("C95", (54.01, -5.439), (52.99, -5.439), (54.23, -6.439), (53.27, -6.439))     # R21: REF_1V65 / U1A+
beside("C97", (54.01, -1.139), (52.99, -1.139), (54.23, -0.139), (53.27, -0.139))     # R7:  REF_1V65 / U1B+
beside("C101", (89.787, 38.91), (89.787, 37.89), (88.787, 38.63), (88.787, 37.67))    # R1:  ISOGND / U2+
beside("C102", (93.987, 36.41), (93.987, 35.39), (94.987, 36.38), (94.987, 35.42))    # R76: U2 out / U2-
beside("C103", (75.487, 36.427), (75.487, 37.447), (74.487, 36.457), (74.487, 37.417))  # R52: REF_1V65_ISO / U7A+
beside("C104", (75.487, 39.347), (75.487, 38.327), (74.487, 39.317), (74.487, 38.357))  # R53: U7A out / U7A-
beside("C105", (78.877, 36.237), (79.897, 36.237), (78.657, 35.237), (79.617, 35.237))  # R46: REF_1V65_ISO / U7B+
beside("C109", (52.89, 3.89), (52.89, 4.91), (53.89, 3.92), (53.89, 4.88))            # R30: REF_1V65 / GND
beside("C110", (114.723, 11.395), (113.703, 11.395), (114.443, 12.395), (113.483, 12.395))  # R40: REF_1V65_ISO / ISOGND

# ---- C108 (ISOADA2): pad 1 tracked to R56 pad 1, pad 2 to a via on the In1 ISOGND plane
b.add_part("C108", "top", (84.787, 40.717), (84.787, 39.757))
b.track("F.Cu", [(83.287, 41.247), (84.787, 40.717)], 0.25, "ISOADA2")
b.via(84.787, 39.007, "ISOGND")
b.track("F.Cu", [(84.787, 39.757), (84.787, 39.007)], 0.3, "ISOGND")

# ---- bottom side with vias
# C96 (R17, U1A feedback): via on the U1-1 -> R17-1 track, existing U1A- via at (51.52, -7.679)
b.add_part("C96", "bottom", (50.2, -6.9), (51.16, -6.9))
b.via(49.7, -6.41, "Net-(C96-Pad1)")
b.track("B.Cu", [(49.7, -6.41), (50.2, -6.9)], 0.25, "Net-(C96-Pad1)")
b.track("B.Cu", [(51.16, -6.9), (51.5201, -7.679)], 0.25, "Net-(U1A--)")
# C98 (R8, U1B feedback): via between R8-1 and R9-2 (same net), existing U1B- via at (52.07, 0.372)
b.add_part("C98", "bottom", (51.2, 1.58), (51.2, 0.62))
b.via(50.29, 0.961, "Net-(C98-Pad1)")
b.track("B.Cu", [(50.29, 0.961), (51.2, 1.58)], 0.25, "Net-(C98-Pad1)")
b.track("B.Cu", [(51.2, 0.62), (52.0701, 0.372)], 0.25, "Net-(U1B--)")
# C99 (R37, U14 + leg to GND): existing GND via and existing U14+ via
b.add_part("C99", "bottom", (61.95, -13.8), (61.95, -14.76))
b.track("B.Cu", [(61.6373, -12.6895), (61.95, -13.8)], 0.25, "GND")
b.track("B.Cu", [(61.95, -14.76), (62.2756, -15.8738)], 0.25, "Net-(U14-+)")
# C100 (R38, U14 feedback): via on the R38-1 -> U14-1 track, pad 2 on the B.Cu U14- trace
b.add_part("C100", "bottom", (59.81, -15.3), (58.85, -15.3))
b.via(60.4, -14.5, "Net-(C100-Pad1)")
b.track("B.Cu", [(60.4, -14.5), (59.81, -15.3)], 0.25, "Net-(C100-Pad1)")
# C106 (R51, U7B feedback): vias on the U7B output and U7B- tracks
b.add_part("C106", "bottom", (82.93, 38.0), (82.93, 37.04))
b.via(82.552, 38.502, "Net-(C106-Pad1)")
b.via(83.316, 36.521, "Net-(U7B--)")
b.track("B.Cu", [(82.552, 38.502), (82.93, 38.0)], 0.25, "Net-(C106-Pad1)")
b.track("B.Cu", [(82.93, 37.04), (83.316, 36.521)], 0.25, "Net-(U7B--)")
# C107 (ISOADA1): via on the ISOADA1 track left of R54, existing ISOGND via at (79.006, 40.895)
b.add_part("C107", "bottom", (77.36, 41.02), (78.32, 41.02))
b.via(76.674, 41.137, "ISOADA1")
b.track("B.Cu", [(76.674, 41.137), (77.36, 41.02)], 0.25, "ISOADA1")
b.track("B.Cu", [(78.32, 41.02), (79.0058, 40.8953)], 0.3, "ISOGND")
b.save("fix 11: measurement filters (C95-C110, R7/R18/R9, C88/C89/C42/C2 values)")
