#!/usr/bin/env python3
"""Routing stage 2: ISO-side measurement chain (routing list group 2, the part east of J11).

  python3 tools/v5/route/s2_iso_analog.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

ISOADA1-3 from the difference amplifiers (U7, U2) to the x0.4 dividers at U22-U24, the divider nodes, and
REF_1V65_ISO. The long runs go on In3 (under the ISOGND plane), the divider nodes stay on B.Cu.
The six divider taps from the west (R67/R68/R71/R82/R85/R256, In2 tracks ending at x 19..25, y 36..47) are NOT
routed: north of J11 only five In3 tracks fit inside the `unrouted` rectangles, and stage 1 uses them.
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
BL = ("B.Cu",)
LONG = dict(layers=("In3.Cu", "F.Cu", "B.Cu"), lcost={"F.Cu": 2.5, "B.Cu": 2.5}, via=2.0)

r.log("== divider nodes (B.Cu)")
for net, a, b, c in (("ISOADA1_AIN", "R111-1", "R110-2", "U22-2"), ("ISOADA2_AIN", "R113-1", "R112-2", "U23-2"),
                     ("ISOADA3_AIN", "R115-1", "R114-2", "U24-2")):
    r.connect(net, a, b, layers=BL, margin=3.0)
    r.connect(net, a, c, layers=BL, margin=3.0)

r.log("== ISOADA1-3: op amp outputs to the dividers")
r.connect("ISOADA1", "C107-1", "R54-1", layers=("F.Cu", "B.Cu"), margin=3.0, via=1.0)
r.connect("ISOADA1", "R110-1", "R54-1", box=(90.0, 12.0, 112.0, 43.0), **LONG)
r.connect("ISOADA2", "R112-1", "R56-1", box=(99.0, 12.0, 112.0, 34.0), **LONG)
r.connect("ISOADA3", "R114-1", "R77-1", box=(92.0, 4.0, 112.0, 27.0), **LONG)

r.log("== REF_1V65_ISO")
r.connect("REF_1V65_ISO", "R32-2", "R40-1", layers=("F.Cu",), margin=3.0)
r.connect("REF_1V65_ISO", "R40-1", "C110-1", layers=("F.Cu",), margin=3.0)
r.connect("REF_1V65_ISO", "R32-2", "R46-1", box=(96.0, 6.0, 118.0, 16.0), **LONG)

r.save(sys.argv[2])
r.log(f"stage 2: {len(r.failed)} failed: {r.failed}")
