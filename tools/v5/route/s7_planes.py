#!/usr/bin/env python3
"""Routing stage 7: supply and ground vias to the planes (routing list groups 5, 6, 7, 8; brief rule 7).

  python3 tools/v5/route/s7_planes.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

Every SMD pad of a plane net in the card area gets a stub (0.4 mm, 0.25 mm where the neighbours are close)
to a via of its own that lands in the planes of its net: a placed / moved part always (unless a via of
the net already sits within 1 mm of the pad), a v4 part only if its copper does not reach the plane yet.
No via between the isolator ISO pads and the DC bus band (y 41.3 .. 43.2): the ISODC+ pour would retreat
1.95 mm from it, into the band.
Not done here: the ISO parts west of J11 (U4, C37) have no plane any more; see the report.
"""
import os
import sys

import router

sys.path.insert(0, os.path.join(router.ROOT, "tools", "v5"))
import card_layout as L  # noqa: E402

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
r.prepare_planes()

PLANES = {"CTRLGND_A": ["In1.Cu", "In4.Cu"], "3V3_CTRL": ["In2.Cu"], "CTRLGND": ["In1.Cu", "In4.Cu"], "5V_CTRL": ["In2.Cu"],
          "ISOGND": ["In1.Cu", "In4.Cu"], "3V3_ISO": ["In2.Cu"], "GND": ["In4.Cu"]}      # VCC: no plane left at U16, stage 6
BOX = {"CTRLGND_A": (44.0, 20.5, 95.5, 33.2), "3V3_CTRL": (44.0, 20.5, 95.5, 33.2),
       "CTRLGND": (102.0, -35.0, 118.5, 3.5), "5V_CTRL": (102.0, -35.0, 118.5, 3.5),
       "ISOGND": (52.0, -9.5, 118.5, 49.0), "3V3_ISO": (52.0, -9.5, 118.5, 49.0),
       "GND": (74.0, 9.0, 86.0, 16.0)}        # primary: U16 and C81 only
DENT = [(52.0, 41.3, 100.2, 43.7)]
placed = set(L.PLACE)
done = todo = 0
for net, layers in PLANES.items():
    r.log(f"== {net} -> {' + '.join(layers)}")
    x0, y0, x1, y1 = BOX[net]
    pads = [k for k, p in r.pads.items() if p["net"] == net and p["drill"][0] == 0 and x0 <= p["x"] <= x1 and y0 <= p["y"] <= y1]
    # IC pins first (they have the least room), then the two-pin parts
    pads.sort(key=lambda k: (not k.startswith("U"), k))
    for k in pads:
        ref = k.split("-")[0]
        if r.on_plane(k, layers, own=1.2 if ref in placed else None):
            continue
        todo += 1
        ly = [ln for ln in ("F.Cu", "B.Cu") if ln in r.pads[k]["layers"]]
        ok = r.plane_via(k, layers, w=0.4, w_min=0.2, maxlen=1.6, avoid=DENT) or \
            r.connect(net, k, None, w=0.2, layers=ly, margin=4.0, plane=layers, avoid=DENT) or \
            r.connect(net, k, None, w=0.2, layers=("F.Cu", "B.Cu", "In3.Cu"), margin=4.0, via=1.0)      # to a neighbour pad that has its via
        done += bool(ok)

r.save(sys.argv[2])
r.log(f"stage 7: {done} of {todo} plane vias; {len(r.failed)} failed: {sorted(set(str(f[1]) for f in r.failed))}")
