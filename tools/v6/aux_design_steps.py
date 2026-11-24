# Steps of tools/v6/aux_design.py (exec'd there: track / via / via_at_pad / grid_route / zone / move / pxy / cx / b).
# Order (V6_PLAN 10): part moves, ground and supplies, then the HV nets, then the signals. Coordinates IPC mm.

# ---- pads of the areas: the replay checks them (positions before any move) -----------------------------------------
for fp in b.GetFootprints():
    for p in fp.Pads():
        x, y = xy(p.GetPosition())
        if L.in_area(x, y) and p.GetNetname() and not p.GetNetname().startswith("unconnected"):
            OPS.append(dict(kind="pad", net=p.GetNetname(), layer="", x1=f"{x:.4f}", y1=f"{y:.4f}", x2="", y2="", w="",
                            tag=f"{fp.GetReference()}-{p.GetNumber()}"))
for n, l in FOREIGN:
    OPS.append(dict(kind="foreign", net=n, layer=l or "", x1="", y1="", x2="", y2="", w="", tag=""))

# ---- part moves -----------------------------------------------------------------------------------------------------
# C68 (DC+ 100n, v4 part): at (72.0, -51.5) its DC+ pad stood above C112's AUX_VIN pad (bottom side) with its GND pad
# between it and the DC+ pour: no legal way to DC+ (F.Cu blocked by its own GND pad at 2.5 mm, a via lands in C112-1).
# Moved north, out of the courtyard of the bulk capacitor C12 (35 mm snap-in, courtyard to y -18.8) and 2 mm from the card tails at y -16.4, onto the DC+
# feed of the 10M chains (F.Cu, x 68.85), turned 180 degrees: DC+ pad on that feed, GND pad east with a via.
print("== moves")
move("C68", 70.4, -13.0, 180.0, "F")

# ---- GND ------------------------------------------------------------------------------------------------------------
print("== GND")
# In2: the v5 step 17 pour covers PX south of y -21.6; north of it a second zone up to y -4.2 (x >= 70.0: the card-P
# VCC plane ends at 69.55), notched round the mounting hole H4 (2.5 mm from its pad). In4: a GND zone over the north
# part that overlaps the card-P In4 GND plane (x <= 69.65) by 0.65 mm: this is where the aux GND meets the main GND.
NOTCH = [(82.9, -19.2), (76.3, -19.2), (76.3, -9.8), (82.9, -9.8)]
zone("GND", I2, [(70.0, -21.6), (82.9, -21.6)] + NOTCH + [(82.9, -4.2), (70.0, -4.2)], "v6 aux P In2.Cu GND north", 131, 0.5)
zone("GND", I4, [(69.0, -26.0), (82.9, -26.0)] + NOTCH + [(82.9, -4.2), (69.0, -4.2)], "v6 aux P In4.Cu GND north", 132, 0.5)

# U18-12, C114-2, C147-2: one via north of U18 between the pads
via("GND", 72.6, -32.0, "U18-12 / C114-2 / C147-2")
track("GND", BC, [pxy("U18", "12"), (72.2, -32.805), (72.6, -32.0)], 0.3, "U18-12")
track("GND", BC, [pxy("C114", "2"), (72.6, -32.0)], 0.3, "C114-2")
track("GND", BC, [pxy("C147", "2"), (74.0, -32.0), (72.6, -32.0)], 0.3, "C147-2")
via("GND", 73.1, -12.5, "C68-1")
track("GND", FC, [pxy("C68", "1"), (73.1, -12.5)], 0.4, "C68-1", pg=True)
# (the In2 pour reaches this via only with its clearance at 0.5 mm: zone_clearance below)
via("GND", 79.45, -32.6, "R102-2")
track("GND", BC, [pxy("R102", "2"), (79.45, -32.6)], 0.3, "R102-2")
zone_clearance("v5 aux P In2.Cu GND", 1.0, 0.5)
track("GND", BC, [pxy("R139", "2"), (81.3, -36.2)], 0.4, "R139-2 -> T1-2")
via("GND", 79.1, -38.1, "C146-2")
track("GND", BC, [pxy("C146", "2"), (79.1, -38.1)], 0.3, "C146-2")
via("GND", 81.6, -40.35, "R105-2")
track("GND", BC, [pxy("R105", "2"), (81.6, -40.35)], 0.6, "R105-2")
# primary return C111-2 -> R105-2 on F.Cu (the switching loop closes on the top side, beside T1)
track("GND", FC, [(81.6, -40.35), (81.3, -40.9), (81.3, -50.6), pxy("C111", "2")], 0.8, "C111-2 -> R105-2")
via("GND", 71.15, -54.3, "C112-2")
track("GND", BC, [pxy("C112", "2"), (70.8, -53.6), (71.15, -54.3)], 0.4, "C112-2")
via("GND", 79.45, -26.4, "R144-2")
track("GND", BC, [pxy("R144", "2"), (79.45, -26.4)], 0.3, "R144-2")
via("GND", 75.1, -22.4, "C113-2")
track("GND", BC, [pxy("C113", "2"), (75.1, -22.4)], 0.6, "C113-2")
via("GND", 77.3, -21.3, "C145-2")
track("GND", BC, [pxy("C145", "2"), (77.3, -21.3)], 0.3, "C145-2")
via("GND", 81.4, -24.4, "R108-2")
track("GND", BC, [pxy("R108", "2"), (81.4, -24.4)], 0.4, "R108-2")
via("GND", 76.5, -11.4, "C41-2")
track("GND", BC, [pxy("C41", "2"), (76.5, -8.9), (76.5, -11.4)], 0.5, "C41-2")
via("GND", 72.0, -17.5, "C28-2")
track("GND", BC, [pxy("C28", "2"), (71.4, -16.5), (72.0, -17.1), (72.0, -17.5)], 0.6, "C28-2")

# ---- 15V ------------------------------------------------------------------------------------------------------------
print("== 15V")
track("AUX_W1", BC, [pxy("D14", "A"), pxy("T1", "1")], 1.0, "D14-A -> T1-1")
track("15V", BC, [pxy("D14", "C"), (80.45, -25.0), (80.45, -23.0)], 0.5, "D14-C -> R108-1")
track("15V", BC, [(80.6, -27.6), (79.3, -28.9), (78.6, -29.475)], 0.4, "D14-C -> R101-1")
via("15V", 80.3, -21.65, "R108-1 / R100-1")
track("15V", BC, [pxy("R108", "1"), (80.3, -21.65)], 0.5, "R108-1")
track("15V", FC, [(80.3, -21.65), (81.6, -21.65), pxy("R100", "1")], 0.4, "R100-1")
# trunk south on F.Cu beside T1's primary row to the south edge of PX (-> J23 / U9, the old 15V run at y -53.8)
track("15V", FC, [pxy("R100", "1"), (82.45, -21.4), (82.45, -54.6)], 0.4, "15V trunk south", area_tol=0.21)
# north: round H4 to C28-1 and C41-1 on B.Cu (grid)
track("15V", BC, [(80.3, -21.65), (79.6, -20.95), (79.6, -19.6), (78.4, -18.6), (77.0, -17.6), (75.9, -16.5), pxy("C28", "1")], 0.5, "R108-1 -> C28-1")
track("15V", BC, [pxy("C28", "1"), (74.45, -15.2), (73.338, -10.0), pxy("C41", "1")], 0.5, "C28-1 -> C41-1")
# west exit under C28 (-> J21 / J22)
track("15V", BC, [pxy("C28", "1"), (73.6, -17.4), (73.6, -18.8), (72.6, -19.8), (67.0, -19.8)], 0.5, "15V exit west", area_tol=0.26)

# ---- HV -------------------------------------------------------------------------------------------------------------
print("== AUX_DRAIN")
# under the package: pins 7 / 8 to 5 / 6 (bar from the inner pad ends), pins joined pairwise
track("AUX_DRAIN", BC, [(71.9, -40.425), (71.9, -41.695)], 0.6, "U18-8 / 7", pg=True)
track("AUX_DRAIN", BC, [(72.0, -41.06), (75.4, -41.06)], 1.2, "U18 pins 7/8 -> 5/6", pg=True)
track("AUX_DRAIN", BC, [(75.5, -40.425), (75.5, -41.695)], 0.6, "U18-5 / 6", pg=True)
track("AUX_DRAIN", BC, [(76.3, -41.6), pxy("T1", "12")], 1.5, "U18-5/6 -> T1-12", pg=True)
track("AUX_DRAIN", BC, [pxy("T1", "12"), (77.6, -45.4), (80.4, -45.4)], 0.8, "T1-12 -> D12-A", pg=True)
# inner-layer copper under T1 (V6_PLAN 10: area reached in the report): In1 and In4, fed by the T1-12 pin;
# clearance 2.0 mm (IPC-2221 B1 internal conductors, > 500 V: 0.0025 mm/V for ~750 V peak at the drain)
DRAIN_POLY = [(73.0, -38.4), (82.4, -38.4), (82.4, -51.2), (73.0, -51.2)]
zone("AUX_DRAIN", I1, DRAIN_POLY, "v6 aux P In1.Cu AUX_DRAIN", 140, 2.0, 0.3)
zone("AUX_DRAIN", I4, DRAIN_POLY, "v6 aux P In4.Cu AUX_DRAIN", 141, 2.0, 0.3)

print("== AUX_CLAMP")
track("AUX_CLAMP", BC, [pxy("D12", "C"), (81.0, -50.4), (81.2, -52.2), pxy("D13", "C")], 1.0, "D12-C -> D13-C", pg=True)

print("== AUX_VIN")
track("AUX_VIN", BC, [pxy("R98", "2"), (75.0, -48.9), pxy("T1", "11")], 0.8, "R98-2 -> T1-11", pg=True)
track("AUX_VIN", BC, [(73.7, -50.0), (73.7, -51.4)], 0.6, "R98-2 -> C112-1", pg=True)
track("AUX_VIN", BC, [pxy("T1", "11"), (77.0, -50.4), (77.0, -52.4)], 0.8, "T1-11 -> D13-A", pg=True)
track("AUX_VIN", FC, [pxy("T1", "11"), (77.4, -51.6)], 0.8, "T1-11 -> C111-1", pg=True)

print("== DC+")
# R98-1: via in its pad (JLC 6-layer: vias in pads filled and capped) to the F.Cu DC+ pour; the pad's own clearance
# (1.5 mm) keeps the PGND pour on B.Cu away from it
via("DC+", 68.04, -49.7, "R98-1 via in pad -> F.Cu DC+ pour", pg=True)
# chains R136 / R141: F.Cu trunk from the pads south into the DC+ pour (2.5 mm from the PWM_G1 via at 65.87)
track("DC+", FC, [pxy("R141", "1"), (68.85, -6.1), pxy("C68", "2")], 0.4, "R136-1 / R141-1 -> C68-2", pg=True)
track("DC+", FC, [pxy("C68", "2"), (68.85, -32.5)], 0.4, "C68-2 -> DC+ pour", pg=True)
track("DC+", FC, [pxy("R136", "1"), (68.85, -7.7)], 0.4, "R136-1", pg=True)
print("== chains")
track("AUX_ST1", FC, [pxy("R136", "2"), pxy("R137", "1")], 0.4, pg=True)
track("AUX_ST2", FC, [pxy("R137", "2"), pxy("R138", "1")], 0.4, pg=True)
track("AUX_LV1", FC, [pxy("R141", "2"), pxy("R142", "1")], 0.4, pg=True)
track("AUX_LV2", FC, [pxy("R142", "2"), pxy("R143", "1")], 0.4, pg=True)

# ---- signals --------------------------------------------------------------------------------------------------------
print("== signals")
track("AUX_VDDR", FC, [pxy("D11", "A"), pxy("R100", "2")], 0.4)
track("AUX_COMPC", BC, [pxy("R140", "2"), pxy("C145", "1")], 0.3)
track("AUX_VERR", BC, [pxy("U18", "2"), pxy("R102", "1")], 0.3, "U18-2 -> R102-1")
track("AUX_VERR", BC, [pxy("R101", "2"), (77.6, -31.35), (77.55, -31.4), (77.55, -33.9), (77.975, -34.175)], 0.2, "R101-2 -> R102-1")
track("AUX_LOVP", BC, [pxy("C147", "1"), (76.0, -32.805)], 0.3, "C147-1 -> U18-1")
track("AUX_LOVP", BC, [pxy("C147", "1"), (76.0, -29.1), (77.0, -28.1), pxy("R144", "1")], 0.25, "C147-1 -> R144-1")
track("AUX_COMP", BC, [pxy("U18", "3"), pxy("C146", "1")], 0.3, "U18-3 -> C146-1")
track("AUX_COMP", BC, [pxy("C146", "1"), (78.9, -35.3), pxy("R139", "1")], 0.3, "C146-1 -> R139-1")
track("AUX_CS", BC, [pxy("U18", "4"), (77.0, -36.4), (79.75, -36.4), (79.75, -38.0), (80.6, -38.85), pxy("R105", "1")], 0.25, "U18-4 -> R105-1")
# AUX_VDD: U18-11 west round pin 12 to C114-1, on to C113-1, via to F.Cu, up to D11-C
track("AUX_VDD", BC, [pxy("U18", "11"), (69.75, -34.075), (69.75, -31.0), pxy("C114", "1")], 0.3, "U18-11 -> C114-1")
track("AUX_VDD", BC, [pxy("C114", "1"), (70.825, -30.4), (72.4, -28.8), (73.6, -28.8)], 0.3, "C114-1 -> C113-1")
via("AUX_VDD", 73.6, -25.2, "C113-1 -> D11-C")
track("AUX_VDD", BC, [pxy("C113", "1"), (73.6, -25.2)], 0.4, "C113-1")
grid_route("AUX_VDD", FC, (73.6, -25.2), pxy("D11", "C"), 0.3, (70.05, -30.05, 80.05, -18.05), "via -> D11-C")
# AUX_COMP to R140-1 on In4 (the B.Cu corridor east of the R column is crossed by 15V)
via("AUX_COMP", 79.7, -34.05, "R139-1 via")
track("AUX_COMP", BC, [pxy("R139", "1"), (79.7, -34.05)], 0.25, "R139-1")
via("AUX_COMP", 79.35, -24.95, "R140-1 via")
track("AUX_COMP", BC, [pxy("R140", "1"), (79.35, -24.95)], 0.25, "R140-1")
grid_route("AUX_COMP", I4, (79.7, -34.05), (79.35, -24.95), 0.2, (74.05, -37.05, 82.85, -22.05), "R139-1 -> R140-1 In4")
# AUX_GATE and AUX_LOVP: In3 from vias at the chain ends to U18
via("AUX_GATE", 82.05, -7.7, "R138-2 via")
track("AUX_GATE", FC, [pxy("R138", "2"), (82.05, -7.7)], 0.3, "R138-2", pg=True)
via("AUX_GATE", 73.0, -35.345, "U18-10 via")
track("AUX_GATE", BC, [pxy("U18", "10"), (73.0, -35.345)], 0.3, "U18-10")
grid_route("AUX_GATE", I3, (82.05, -7.7), (73.0, -35.345), 0.2, (67.05, -40.05, 82.85, -4.05), "R138-2 -> U18-10 In3")
via("AUX_LOVP", 82.05, -5.3, "R143-2 via")
track("AUX_LOVP", FC, [pxy("R143", "2"), (82.05, -5.3)], 0.3, "R143-2", pg=True)
via("AUX_LOVP", 77.0, -28.1, "R144-1 via")
grid_route("AUX_LOVP", I3, (82.05, -5.3), (77.0, -28.1), 0.2, (67.05, -40.05, 82.85, -4.05), "R143-2 -> R144-1 In3")

# ---- ISO side (IA) ---------------------------------------------------------------------------------------------------
print("== IA")
track("AUX_W2", BC, [pxy("D15", "A"), (94.4, -29.4), pxy("T1", "10")], 1.0, "D15-A -> T1-10")
track("15V_ISO", BC, [pxy("D15", "C"), (90.5, -29.4), pxy("R109", "1")], 0.8, "D15-C -> R109-1")
track("15V_ISO", BC, [pxy("R109", "1"), (91.9, -33.2), (91.9, -36.4), pxy("C116", "1")], 0.8, "R109-1 -> C116-1")
track("15V_ISO", BC, [pxy("D15", "C"), (90.95, -25.5)], 0.8, "15V_ISO exit north", area_tol=0.41)
track("ISOGND", BC, [pxy("R109", "2"), (90.3, -44.0), (91.75, -45.45), pxy("C116", "2")], 0.8, "R109-2 -> C116-2")
track("ISOGND", BC, [pxy("T1", "9"), (95.9, -34.55), (95.9, -43.8), (94.25, -45.45), pxy("C116", "2")], 0.8, "T1-9 -> C116-2")
track("ISOGND", BC, [(95.9, -34.55), (96.9, -33.55), (96.9, -25.5)], 0.6, "ISOGND exit north", area_tol=0.31)
