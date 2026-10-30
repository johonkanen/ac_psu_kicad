#!/usr/bin/env python3
"""Sheet 4 - DC links (PDF page 4): primary DC link C11/C12/C79 (DC+/PGND) with Y caps C7/C10 to
PE8, isolated DC link C61/C72/C8 (ISODC+/ISOPGND) with C59/C60 to PE5, TLV316 difference
amplifiers U14 (DC+ - PGND -> ADA1) and U2 (ISODC+ - ISOPGND -> ISOADA3), 0 R measurement
links R96 (PGND-GND) and R97 (ISOPGND-ISOGND)."""
from _common import *  # noqa: F401,F403

sh = sheet("04_dc_links.kicad_sch")


def dc_link(y0, caps, yc, pos_net, neg_net, pe_label=None, pe_terminal=None):
    """Three snap-in capacitors (pin 1 = positive rail) and the two Y caps `yc` (upper: pin 2 =
    positive rail, pin 1 = PE node; lower: pin 2 = PE node, pin 1 = negative rail)."""
    T, B, M = y0, y0 + g(24), y0 + g(12)
    xs = [g(20), g(36), g(52)]
    for x, ref in zip(xs, caps):
        _, t, b = vert2(sh, "C_Polarized", ref, x, M, "SNAP_IN_35MM", top=1)
        sh.wire(t, (x, T)); sh.wire(b, (x, B))
    xy = g(64)
    _, t, b = vert2(sh, "C", yc[0], xy, y0 + g(6), "2n2", top=2)
    sh.wire(t, (xy, T)); sh.wire(b, (xy, M))
    _, t, b = vert2(sh, "C", yc[1], xy, y0 + g(18), "2n2", top=2)
    sh.wire(t, (xy, M)); sh.wire(b, (xy, B))
    sh.wire((xs[0], T), (xy, T)); sh.wire((xs[0], B), (xy, B))
    for x in xs[1:]:
        sh.junction(x, T); sh.junction(x, B)
    power_at(sh, pos_net, (g(44), T), "up"); sh.junction(g(44), T)
    power_at(sh, neg_net, (g(44), B), "down"); sh.junction(g(44), B)
    sh.wire((xy, M), (xy + g(6), M))
    if pe_terminal:
        terminal(sh, pe_terminal, xy + g(6), M, "right")
    else:
        sh.glabel(pe_label, xy + g(6), M, 0)


dc_link(g(24), ("C11", "C12", "C79"), ("C7", "C10"), "DC+", "PGND", pe_terminal="PE8")
dc_link(g(84), ("C61", "C72", "C8"), ("C59", "C60"), "ISODC+", "ISOPGND", pe_label="PE5")
sh.text("Primary and isolated DC links. PE8 terminal is on this sheet; PE5 is on sheet 5.", g(16), g(118))

# 0 R measurement connections between the power grounds and the signal grounds
for y, ref, left_net, right_net in ((g(126), "R96", "PGND", "GND"), (g(134), "R97", "ISOPGND", "ISOGND")):
    _, l, r = horiz2(sh, "R", ref, g(40), y, "0R", left=2)
    sh.wire(l, left(l, 4)); power_at(sh, left_net, left(l, 4), "left")
    sh.wire(r, right(r, 4)); power_at(sh, right_net, right(r, 4), "right")
sh.text("Measurement connections (0 R)", g(26), g(122))

# DC-link voltage measurement amplifiers
r = diff_amp(sh, g(150), g(24), 1, ["R41", "R27", "R35"], ["R42", "R28", "R36"], ("R37", "10k"), None,
             ("R38", "10k"), ("R39", "8.2k"), "ADA1", opamp=("TLV316IDBVR", "U14"), pins=(3, 4, 1),
             ref_power="GND", out_cap=("C42", "10n C0G", "GND"), top_power=("DC+", "PGND"),
             par_caps=("C99", "C100", "1n C0G"))
u = r["u"]
sh.wire(u.pin(5), up(u.pin(5), 2)); power_at(sh, "VCC", up(u.pin(5), 2), "up")
sh.wire(u.pin(2), down(u.pin(2), 2)); power_at(sh, "GND", down(u.pin(2), 2), "down")
sh.text("U14: (DC+ - PGND) / 3 x 91K, output -> ADA1 (sheet 9). DC- in the PDF = GND.", g(144), g(24) + g(56))
r = diff_amp(sh, g(150), g(84), 1, ["R81", "R80", "R82"], ["R83", "R84", "R85"], ("R1", "10k"), None,
             ("R76", "10k"), ("R77", "8.2k"), "ISOADA3", opamp=("TLV316IDBVR", "U2"), pins=(3, 4, 1),
             ref_power="ISOGND", out_cap=("C2", "10n C0G", "ISOGND"), top_power=("ISODC+", "ISOPGND"),
             par_caps=("C101", "C102", "1n C0G"))
u = r["u"]
sh.wire(u.pin(5), up(u.pin(5), 2)); power_at(sh, "3V3_ISO", up(u.pin(5), 2), "up")
sh.wire(u.pin(2), down(u.pin(2), 2)); power_at(sh, "ISOGND", down(u.pin(2), 2), "down")
sh.text("U2: (ISODC+ - ISOPGND) / 3 x 91K, output -> ISOADA3 (J11).", g(144), g(84) + g(56))
sh.text("v4: C99-C102 1n C0G across the 10k legs (15.9 kHz); C42/C2 10n (v3 1n) -> 8.2k/10n = 1.9 kHz DC-link filters.",
        g(144), g(84) + g(60))

# decoupling
for x, ref, vdd, gnd in ((g(210), "C27", "VCC", "GND"), (g(210), "C87", "3V3_ISO", "ISOGND")):
    y = g(44) if ref == "C27" else g(104)
    _, ct, cb = vert2(sh, "C", ref, x, y, "100n", top=2)
    sh.wire(ct, up(ct, 2)); power_at(sh, vdd, up(ct, 2), "up")
    sh.wire(cb, down(cb, 2)); power_at(sh, gnd, down(cb, 2), "down")
sh.save()
print("sheet04: written")
