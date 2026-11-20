#!/usr/bin/env python3
"""v5 step 18 (run once, kipy): supply vias of U20 pin 16 and C120, beside the bus wire pad BUSN2
(routing passes 2 .. 6 left 3V3_ISO at U20-16 and ISOGND at C120-2 open; user 2026-11-20: "Go with your
recommendation").

C120 is not moved. Its pads and U20 pin 16 stand at (90, 40.15), 4.85 mm from the centre of BUSN2 (90.5, 45.0;
4 mm pad, vias 2.5 mm from it: 4.73 mm from the centre for a 0.457 mm via). On the board without signal tracks
two legal via sites are right there; the routing passes lost them to signal tracks routed first. This step sets
them as fixed copper:
  - 3V3_ISO: via at (90.0, 38.7) south of U20 pin 16 (to the In2 plane), B.Cu stub from the pin, F.Cu track from
    C120 pad 1;
  - ISOGND: via at (91.3, 40.15) east of C120 pad 2 (to the In1 / In4 planes), F.Cu stub.
Checks here: distance to BUSN2, ISO copper not south of y 38.0 (5 mm line of the barrier). DRC, domain gaps and
the plane islands: tools/check_all.sh.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, VIA_PAD  # noqa: E402

b = Board(5018)
V33, VGND = (90.0, 38.7), (91.3, 40.15)
for t in b.b.GetTracks():
    if t.GetClass() == "PCB_VIA" and math.dist((T(t.GetPosition().x), -T(t.GetPosition().y)), V33) < 0.01:
        raise SystemExit("v5 step 18 already applied (via exists)")


def pad(ref, num):
    q = next(p for p in b.fp(ref).Pads() if p.GetNumber() == num)
    return (round(T(q.GetPosition().x), 3), round(-T(q.GetPosition().y), 3)), q.GetNetname()


(p16, n16), (c1, nc1), (c2, nc2) = pad("U20", "16"), pad("C120", "1"), pad("C120", "2")
if (n16, nc1, nc2) != ("3V3_ISO", "3V3_ISO", "ISOGND"):
    raise SystemExit(f"unexpected nets {n16} {nc1} {nc2}")
bus, _ = pad("BUSN2", "1")
for v in (V33, VGND):
    d = math.dist(v, bus) - 2.0 - VIA_PAD / 2
    b.log.append(f"via at {v}: {d:.2f} mm from the BUSN2 pad")
    if d < 2.5:
        raise SystemExit(f"via at {v}: {d:.2f} mm from the BUSN2 pad, 2.5 needed")
    if v[1] - VIA_PAD / 2 < 38.0:
        raise SystemExit(f"via at {v} south of the ISO line y 38.0")
b.via(*V33, "3V3_ISO")
b.track("B.Cu", [p16, V33], 0.3, "3V3_ISO")
b.track("F.Cu", [c1, (c1[0], V33[1] + 0.48), V33], 0.3, "3V3_ISO")
b.via(*VGND, "ISOGND")
b.track("F.Cu", [c2, VGND], 0.3, "ISOGND")
b.save("v5 step 18: supply vias of U20 pin 16 and C120")
