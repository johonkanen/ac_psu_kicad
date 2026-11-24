#!/usr/bin/env python3
"""v6 step 4b (run once, kipy): bus lanes on more layers, high-voltage clearance on the new DC pads.

  tools/p2k/bin/kipy tools/v6/v6_4b_lanes.py        (then the zones are refilled with kicad-cli)

Decision "Fable 2026-11-24" (planning session) after the current-rating estimate of step 4:
  - ISO lane on all six layers, three per net: ISOPGND F.Cu + In2.Cu + In4.Cu, ISODC+ In1.Cu + In3.Cu + B.Cu; the In4
    strip ISOGND gives way under the lane only (the new In4 ISOPGND zone has the higher priority).
  - Primary bus: DC+ also on In3.Cu (DC+ F + In1 + In3, PGND B + In2).
  - Design case 23 A RMS in the lane section inverter A - west: about 20 K rise (IPC-2221, layers of one net as one
    conductor); the 32 A row is an upper bound, not a physical case.
Found while replaying the aux script: the pads of the card terminals and pigtails had no local clearance, so other-net
pours (PGND B.Cu pour 0, the In4 strip GND) filled to 0.3 ... 0.6 mm from DC+ pads. Every pad of J31 ... J42 now has
the 2.5 mm high-voltage clearance (as card_layout.HV_PADS does for the aux pads); tracks of other nets that came closer
than that are deleted (they lie in the open-layout strips and are routed again).
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, F, P  # noqa: E402

HV = 2.5
b = Board(6008)
B = b.b
names = {z.GetZoneName() for z in B.Zones()}
if "v6 bus ISODC+ In3" in names:
    raise SystemExit("v6 step 4b already applied")


def outline(name):
    z = next(z for z in B.Zones() if z.GetZoneName() == name)
    o = z.Outline().Outline(0)
    return [(T(o.CPoint(i).x), -T(o.CPoint(i).y)) for i in range(o.PointCount())], z.GetAssignedPriority()


for src, layer, net, name, prio in (("v6 bus ISODC+ In1", "In3.Cu", "ISODC+", "v6 bus ISODC+ In3", None),
                                    ("v6 bus ISOPGND In2", "In4.Cu", "ISOPGND", "v6 bus ISOPGND In4", 6),
                                    ("v6 bus DC+ In1", "In3.Cu", "DC+", "v6 bus DC+ In3", None)):
    pts, p0 = outline(src)
    b.zone(layer, pts, net, name, prio if prio is not None else p0, clearance=HV)
# the In4 strip ISOGND below the new In4 ISOPGND lane
z = next(z for z in B.Zones() if z.GetZoneName() == "v6 strip In4 ISOGND")
b.log.append(f"zone v6 strip In4 ISOGND priority {z.GetAssignedPriority()} (the In4 ISOPGND lane has 6 and wins)")

# header capacitors that would sit within 2.5 mm of a DC pad once the pads carry the HV clearance
for ref, (x, y) in {"C154": (8.5, 41.5), "C155": (8.5, 44.5), "C152": (93.5, -63.3), "C153": (96.5, -63.3)}.items():
    fp = b.fp(ref)
    ps = [q.GetPosition() for q in fp.Pads()]
    cx, cy = sum(T(q.x) for q in ps) / len(ps), -sum(T(q.y) for q in ps) / len(ps)
    p0 = fp.GetPosition()
    fp.SetPosition(P(T(p0.x) + x - cx, -T(p0.y) + y - cy))
    b.log.append(f"{ref} moved ({cx:.2f}, {cy:.2f}) -> ({x}, {y})")

# high-voltage clearance on the card DC pads
hv = []
for ref in [f"J{n}" for n in range(31, 43)]:
    fp = b.fp(ref)
    for p in fp.Pads():
        p.SetLocalClearance(F(HV))
        hv.append(p)
b.log.append(f"local clearance {HV} mm on {len(hv)} pads of J31 ... J42")
gone = 0
for t in list(B.GetTracks()):
    w = T(t.GetWidth(pcbnew.F_Cu)) if t.GetClass() == "PCB_VIA" else T(t.GetWidth())
    for p in hv:
        if t.GetNetname() == p.GetNetname() or not (t.GetClass() == "PCB_VIA" or p.IsOnLayer(t.GetLayer())):
            continue
        bb = p.GetBoundingBox()
        x0, x1, y0, y1 = T(bb.GetLeft()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetTop())
        a, c = t.GetStart(), t.GetEnd()
        ax, ay, cx, cy = T(a.x), -T(a.y), T(c.x), -T(c.y)
        n = max(1, int(math.hypot(cx - ax, cy - ay) / 0.1))
        d = min(math.hypot(max(x0 - (ax + (cx - ax) * k / n), 0, ax + (cx - ax) * k / n - x1),
                           max(y0 - (ay + (cy - ay) * k / n), 0, ay + (cy - ay) * k / n - y1)) for k in range(n + 1)) - w / 2
        if d < HV:
            b.log.append(f"{'via' if t.GetClass() == 'PCB_VIA' else 'track'} [{t.GetNetname()}] {d:.2f} mm from "
                         f"{p.GetParentFootprint().GetReference()} [{p.GetNetname()}] deleted")
            B.Delete(t)
            gone += 1
            break
b.log.append(f"{gone} tracks / vias closer than {HV} mm to the card DC pads deleted")
pcbnew.SaveBoard(b.b.GetFileName(), B)
print("\n".join(["== v6 step 4b: bus lanes on more layers, HV clearance on the card DC pads"] + ["  " + x for x in b.log]))
