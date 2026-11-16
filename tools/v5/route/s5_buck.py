#!/usr/bin/env python3
"""Routing stage 5: CTRL piece at J12, the buck converter (routing list group 6).

  python3 tools/v5/route/s5_buck.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

CTRL_W -> D16 -> CTRL_RAW (C138 right under D16: two vias between the two pads) and CTRL_SW (U28 pin 2 -> L2)
1 mm wide; CTRL_RAW on to C137 / U28 / C139; CTRL_FB, CTRL_EN, CTRL_BOOT thin. 5V_CTRL and CTRLGND go to the
planes in stage 7 (PEC2, W1 pin 2, J12 and J13 are through-hole pads inside the planes).
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
P = r.pads
CB = (102.0, -35.0, 118.6, 3.5)
ALL = ("F.Cu", "B.Cu", "In3.Cu")


def wide(net, a, b, widths=(1.0, 0.6, 0.4), layers=ALL, **kw):
    for w in widths:
        if r.connect(net, a, b, w=w, layers=layers, box=CB, quiet=(w != widths[-1]), **kw):
            r.log(f"  {net}: {a} -> {b} at {w} mm")
            return True
    return False


# pin 5 (EN) sits between pins 4 and 6 at the area edge: a via between the two pin rows of U28 (placed first, so
# that the switch node keeps clear of it), then In3
r.add_via("CTRL_EN", P["U28-5"]["x"], 0.85)
r.add_track("CTRL_EN", "F.Cu", [(P["U28-5"]["x"], P["U28-5"]["y"]), (P["U28-5"]["x"], 0.85)], 0.25)

r.log("== rectifier loop: W1 -> D16 -> C138")
wide("CTRL_W", "D16-A", "W1-1", layers=("F.Cu",))
ya = (P["D16-C"]["bb"][3] + P["C138-1"]["bb"][1]) / 2          # between the pad of D16 (F) and the pad of C138 (B)
for x in (108.4, 109.4):
    r.add_via("CTRL_RAW", x, ya, in_pad=True)
    r.add_track("CTRL_RAW", "F.Cu", [(x, ya), (x, P["D16-C"]["y"])], 0.8, check=False)
    r.add_track("CTRL_RAW", "B.Cu", [(x, ya), (x, P["C138-1"]["y"])], 0.8, check=False)

r.log("== switch node")
wide("CTRL_SW", "U28-2", "L2-1", via=1.0)
r.connect("CTRL_SW", "C141-2", "U28-2", w=0.4, layers=("F.Cu",), box=CB) or r.connect("CTRL_SW", "C141-2", "U28-2", w=0.25, layers=ALL, box=CB)

r.log("== CTRL_RAW: C138 -> C139 -> C137 / U28 / C140, preload and EN divider")
wide("CTRL_RAW", "C139-1", "C138-1", via=1.0)
wide("CTRL_RAW", "U28-3", "C139-1", via=1.0)
wide("CTRL_RAW", "C137-1", "U28-3", via=1.0)
wide("CTRL_RAW", "C140-1", "U28-3", widths=(0.6, 0.4, 0.25), layers=("F.Cu",))
wide("CTRL_RAW", "R131-1", "D16-C", widths=(0.6, 0.4, 0.25))
wide("CTRL_RAW", "R132-1", "R131-1", widths=(0.4, 0.25))

r.log("== CTRL_BOOT, CTRL_FB (away from L2 and the switch node), CTRL_EN")

KEEP = [(ALL, (106.5, -14.5, 111.5, -6.5), 2.5)]          # L2 and the switch node
r.connect("CTRL_EN", "R133-1", "R132-2", w=0.2, layers=ALL, box=CB)
r.connect("CTRL_EN", "U28-5", "R132-2", w=0.2, layers=("In3.Cu", "F.Cu", "B.Cu"), lcost={"F.Cu": 2.0, "B.Cu": 2.0}, box=CB, cost=KEEP)
# along the north edge of the area, past pins 5 and 4: 0.35 mm between the pads and the edge
r.connect("CTRL_BOOT", "U28-6", "C141-1", w=0.152, layers=("F.Cu",), box=(110.5, 0.5, 118.6, 3.5)) or \
    r.connect("CTRL_BOOT", "U28-6", "C141-1", w=0.2, layers=ALL, box=CB, via=1.0)
r.connect("CTRL_FB", "U28-4", "R135-1", w=0.2, layers=ALL, box=CB, cost=KEEP)
r.connect("CTRL_FB", "R134-2", "R135-1", w=0.2, layers=ALL, box=CB, cost=KEEP)
r.connect("CTRL_FB", "C144-2", "U28-4", w=0.2, layers=ALL, box=CB, cost=KEEP)

r.save(sys.argv[2])
r.log(f"stage 5: {len(r.failed)} failed: {r.failed}")
