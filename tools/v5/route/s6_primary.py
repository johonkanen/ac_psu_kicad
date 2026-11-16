#!/usr/bin/env python3
"""Routing stage 6: primary side of U16 (routing list group 7).

  python3 tools/v5/route/s6_primary.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

U16 pins 10..15 to the v4 routing that is left: PWM_G1 and DAB_PWM_PRI_HI end as F.Cu tracks; PWM_G2, G3, G4
and DAB_PWM_PRI_LO end as In2 tracks whose via was deleted with the card-area copper: a via goes back on the
end of each In2 track. The runs are In3 (over the new In4 GND plane) inside the primary area.
VCC of U16 / C81: the VCC pour does not reach x 84 any more, a 0.4 mm track to the nearest VCC copper.
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
PA = (42.0, -22.0, 86.0, 16.2)
LONG = dict(layers=("In3.Cu", "F.Cu", "B.Cu"), lcost={"F.Cu": 2.0, "B.Cu": 2.0}, via=2.0, box=PA)

r.log("== vias back on the In2 track ends")
END = {"PWM_G4": (62.6709, -20.4124), "PWM_G2": (63.5877, -21.3389), "PWM_G3": (66.6, -21.6), "DAB_PWM_PRI_LO": (69.0, -21.4)}
for net, (x, y) in END.items():
    r.add_via(net, x, y)

r.log("== U16 pins 10..15, west to east (the order of the track ends)")
for net, pad, tgt in (("PWM_G4", "U16-10", END["PWM_G4"]), ("PWM_G2", "U16-11", END["PWM_G2"]), ("PWM_G1", "U16-12", None),
                      ("PWM_G3", "U16-13", END["PWM_G3"]), ("DAB_PWM_PRI_HI", "U16-14", None), ("DAB_PWM_PRI_LO", "U16-15", END["DAB_PWM_PRI_LO"])):
    r.connect(net, pad, tgt, w=0.2, **LONG)

r.log("== VCC of U16 and C81")
r.connect("VCC", "C81-2", "U16-16", w=0.4, layers=("F.Cu",), box=PA) or r.connect("VCC", "C81-2", "U16-16", w=0.25, layers=("F.Cu", "B.Cu"), box=PA)
r.connect("VCC", "U16-16", None, w=0.4, layers=("F.Cu", "B.Cu", "In3.Cu"), box=(60.0, 0.0, 86.0, 16.2), via=1.5) or \
    r.connect("VCC", "U16-16", None, w=0.25, layers=("F.Cu", "B.Cu", "In3.Cu"), box=(60.0, 0.0, 86.0, 16.2), via=1.5)

r.save(sys.argv[2])
r.log(f"stage 6: {len(r.failed)} failed: {r.failed}")
