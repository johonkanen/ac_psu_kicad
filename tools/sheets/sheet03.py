#!/usr/bin/env python3
"""Sheet 3 - regulators (PDF page 3): U3/U10 TPS73033 LDOs, U9/U8 VXO7805 switchers,
REF1/REF2 REF3025 references with 1.65 V dividers."""
from _common import *  # noqa: F401,F403


def ldo(sh, ref, x, y, vin, gnd, vout, cin, cout):
    """TPS73033 block drawn like the PDF: input rail with Cin, EN tied to IN, GND rail
    below, Cout on the output, NR unconnected."""
    u = sh.place("TPS73033DBVT", ref, x, y, value="TPS73033DBVT")
    IN, GND, EN, NR, OUT = u.pin(1), u.pin(2), u.pin(3), u.pin(4), u.pin(5)
    rail_y = y + g(10)
    # input rail
    vin_p = (x - g(24), IN[1])
    power_at(sh, vin, vin_p, "up")
    sh.wire(vin_p, IN)
    c1, c1t, c1b = vert2(sh, "C", cin[0], x - g(18), y + g(4), cin[1], top=2)  # pin 1 = ground
    sh.wire(c1t, (c1t[0], IN[1]))
    sh.junction(c1t[0], IN[1])
    sh.wire(c1b, (c1b[0], rail_y))
    # EN tied to IN (the vertical crosses the GND wire without a junction, as in the PDF)
    en_x = x - g(10)
    sh.wire(EN, (en_x, EN[1]), (en_x, IN[1]))
    sh.junction(en_x, IN[1])
    # GND pin to the ground rail
    gnd_x = x - g(14)
    sh.wire(GND, (gnd_x, GND[1]), (gnd_x, rail_y))
    sh.junction(gnd_x, rail_y)
    # output
    c2, c2t, c2b = vert2(sh, "C", cout[0], x + g(16), y + g(6), cout[1], top=2)
    sh.wire(OUT, (c2t[0], OUT[1]), c2t)
    sh.junction(c2t[0], OUT[1])
    sh.wire(c2b, (c2b[0], rail_y))
    vout_p = (x + g(20), OUT[1])
    sh.wire((c2t[0], OUT[1]), vout_p)
    power_at(sh, vout, vout_p, "up")
    sh.no_connect(*NR)
    # ground rail
    sh.wire((c1b[0], rail_y), (c2b[0], rail_y))
    power_at(sh, gnd, (x, rail_y), "down")
    sh.junction(x, rail_y)
    return u


def vref(sh, ref, x, y, vin, gnd, out_label, cin, cout, rtop, rbot):
    """REF3025 block: Cin on the input, Cout on the output, divider rtop/rbot to a 1.65 V
    reference label. Pin ids follow Proteus (1=GND 2=VIN 3=VOUT), see STATUS.md."""
    u = sh.place("REF3025", ref, x, y, value="REF3025")
    VIN, VOUT, GND = u.pin(2), u.pin(3), u.pin(1)
    rail_y = y + g(14)
    vin_p = (x - g(24), VIN[1])
    power_at(sh, vin, vin_p, "up")
    sh.wire(vin_p, VIN)
    c1, c1t, c1b = vert2(sh, "C", cin[0], x - g(18), y + g(6), cin[1], top=2)  # pin 1 = ground
    sh.wire(c1t, (c1t[0], VIN[1]))
    sh.junction(c1t[0], VIN[1])
    sh.wire(c1b, (c1b[0], rail_y))
    sh.wire(GND, (GND[0], rail_y))
    sh.junction(GND[0], rail_y)
    power_at(sh, gnd, (GND[0], rail_y), "down")
    c2, c2t, c2b = vert2(sh, "C", cout[0], x + g(14), y + g(6), cout[1], top=2)
    r1, r1l, r1r = horiz2(sh, "R", rtop[0], x + g(22), y, rtop[1], left=1)  # 1 = ref out, 2 = REF_1V65
    sh.wire(VOUT, r1l)
    sh.wire(c2t, (c2t[0], VOUT[1]))
    sh.junction(c2t[0], VOUT[1])
    sh.wire(c2b, (c2b[0], rail_y))
    r2, r2t, r2b = vert2(sh, "R", rbot[0], x + g(30), y + g(6), rbot[1], top=1)  # 1 = REF_1V65, 2 = gnd
    sh.wire(r1r, (r2t[0], VOUT[1]), r2t)
    sh.junction(r2t[0], VOUT[1])
    sh.wire(r2b, (r2b[0], rail_y))
    lab = (x + g(34), VOUT[1])
    sh.wire((r2t[0], VOUT[1]), lab)
    sh.glabel(out_label, *lab, 0)
    sh.wire((c1b[0], rail_y), (r2b[0], rail_y))
    sh.junction(c2b[0], rail_y)
    return u


def vxo(sh, ref, sym, x, y, vin, gnd, vout):
    """VXO7805 module (all pins on the left): +VIN from a supply, GND down, +VOUT to a
    supply symbol pointing left."""
    u = sh.place(sym, ref, x, y, value=sym)
    VIN, GND, VOUT = u.pin(1), u.pin(2), u.pin(3)
    vin_p = (VIN[0] - g(14), VIN[1])
    sh.wire(VIN, vin_p)
    power_at(sh, vin, vin_p, "up")
    gnd_p = (GND[0] - g(10), GND[1] + g(6))
    sh.wire(GND, (gnd_p[0], GND[1]), gnd_p)
    power_at(sh, gnd, gnd_p, "down")
    vout_p = (VOUT[0] - g(6), VOUT[1])
    sh.wire(VOUT, vout_p)
    power_at(sh, vout, vout_p, "left")
    return u


sh = sheet("03_regulators.kicad_sch")

# primary side
ldo(sh, "U3", g(80), g(40), "5V", "GND", "VCC", ("C70", "100n"), ("C69", "100n"))
vxo(sh, "U9", "VXO7805-500", g(84), g(68), "20V", "GND", "5V")
vref(sh, "REF1", g(160), g(40), "VCC", "GND", "REF_1V65", ("C16", "1u"), ("C40", "1u"),
     ("R19", "420R"), ("R30", "820R"))
# isolated side
ldo(sh, "U10", g(80), g(110), "5V_ISOL", "ISOGND", "3V3_ISO", ("C4", "100n"), ("C3", "100n"))
vxo(sh, "U8", "VXO7805-1000", g(84), g(138), "20V_ISO_SEC", "ISOGND", "5V_ISOL")
vref(sh, "REF2", g(160), g(110), "3V3_ISO", "ISOGND", "REF_1V65_ISO", ("C5", "1u"), ("C6", "1u"),
     ("R32", "420R"), ("R40", "820R"))

sh.text("3V3 / 3v3 in the Proteus schematic = net VCC (VCC/VDD=POWER); 3V3_ISO is the isolated 3.3 V.",
        g(20), g(166))
sh.text("REF3025 pin ids follow Proteus (1=GND 2=VIN 3=VOUT), not the TI datasheet - see STATUS.md.",
        g(20), g(170))
sh.save()
print("sheet03: written")
