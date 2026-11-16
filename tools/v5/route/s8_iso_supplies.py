#!/usr/bin/env python3
"""Routing stage 8: ISO supplies that the planes do not carry (routing list group 8).

  python3 tools/v5/route/s8_iso_supplies.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

The ISO planes cover only the card-area polygon (y -9.4 .. 48.8). Outside it:
  * U8 (K7805) and its ISOGND / 15V_ISO pours lie south of the planes: ISOGND from U8 pin 2 on In3 to a via
    in the planes; 5V_ISOL from U8 pin 3 on In3 to U10; C93 / C94 to the pins of U8;
  * the supply pins of J4 and J6 (15V_ISO pin 48, 5V_ISOL pin 45, ISOGND pin 46) lie north of the DC bus band:
    In3 under the band (no via in the band, none between the isolator pads and the band).
NOT routed: the same three pins of J8 and the supply of U4 / C37 west of J11 (no In3 track left north of J11).
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
GP = ["In1.Cu", "In4.Cu"]
DENT = [(52.0, 41.3, 100.2, 43.7)]
ISO = (52.0, -26.0, 118.6, 54.0)
IN3 = ("In3.Cu",)


def wide(net, a, b, widths, **kw):
    for w in widths:
        if r.connect(net, a, b, w=w, quiet=(w != widths[-1]), **kw):
            r.log(f"  {net}: {a} -> {b} at {w} mm")
            return True
    return False


r.log("== U8: capacitors, ISOGND to the planes, 5V_ISOL to U10")
wide("15V_ISO", "C93-1", "U8-1", (0.8, 0.5), layers=("B.Cu",), margin=3.0)
wide("15V_ISO", "U8-1", None, (0.8, 0.5), layers=("F.Cu", "B.Cu"), box=(87.0, -26.0, 103.0, -9.0))
wide("5V_ISOL", "C94-1", "U8-3", (0.8, 0.5), layers=("B.Cu",), margin=3.0)
wide("ISOGND", "U8-2", None, (0.8, 0.5), layers=IN3, box=(87.0, -26.0, 103.0, 9.0), plane=GP)
wide("5V_ISOL", "U8-3", "U10-1", (0.8, 0.5), layers=("In3.Cu", "F.Cu"), lcost={"F.Cu": 1.5}, via=1.0, box=(87.0, -26.0, 103.0, 9.0))
wide("5V_ISOL", "C4-2", "U10-1", (0.4, 0.25), layers=("F.Cu",), margin=3.0)

r.log("== J4 / J6 supply pins, In3 under the bus band")
for pad in ("J4-46", "J6-46"):
    wide("ISOGND", pad, None, (0.5, 0.3), layers=IN3, margin=14.0, plane=GP, avoid=DENT)
LONG = dict(layers=IN3, box=ISO, cost=[(IN3, (52.0, 38.0, 100.5, 41.3), 2.0)])
wide("5V_ISOL", "J4-45", "U10-1", (0.8, 0.5, 0.3), layers=("In3.Cu", "F.Cu"), lcost={"F.Cu": 3.0}, via=3.0, box=ISO)
wide("5V_ISOL", "J6-45", "J4-45", (0.8, 0.5, 0.3), **LONG)
wide("15V_ISO", "J4-48", "U8-1", (0.5, 0.3), layers=("In3.Cu", "F.Cu", "B.Cu"), lcost={"F.Cu": 3.0, "B.Cu": 3.0}, via=3.0, box=ISO)
wide("15V_ISO", "J6-48", "J4-48", (0.5, 0.3), **LONG)

r.save(sys.argv[2])
r.log(f"stage 8: {len(r.failed)} failed: {sorted(set(str(f[:3]) for f in r.failed))}")
