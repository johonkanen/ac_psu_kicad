#!/usr/bin/env python3
"""v4 fix 14 (run once, kipy): insulation spacing between the domains of tools/v4/domains.py
(IEC 61010-1, user decision 2026-10-31: P <-> I reinforced 5.0 mm, P/I <-> E basic 2.5 mm of
copper on every layer; measured with tools/v4/domain_gaps.py).

Pours give way: every copper zone loses the part of its outline that lies within the required
gap (+ 0.1 mm) of copper of another domain on its layer (pads, tracks, vias), and of the filled
copper of another domain's zone when that zone is larger (the smaller of two facing pours gives
way). Two passes (the second sees the first pass's fills). The tracks/pads that are too close to
each other are moved by hand below (MOVES)."""
import os
import sys

import pcbnew
from v4board import Board, F, T

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import domains  # noqa: E402
import domain_gaps as dg  # noqa: E402

MARGIN = 0.1
ERR = F(0.005)

b = Board(4114)
if any(z.GetZoneName().endswith("(fix 14)") for z in b.b.Zones()):
    raise SystemExit("fix 14 already applied")
nets = {}
for (ref, pin), net in b.pin_net.items():
    nets.setdefault(net, []).append((ref, pin))
dom = domains.classify(nets)


def nonzone(layer_id):
    out = {}
    for d, parts in dg.item_polys(b.b, layer_id, dom).items():
        keep = [p for p in parts if not p[2].startswith("zone ")]
        if keep:
            out[d] = dg.union(keep)
    return out


def fills(layer_id):
    out = []
    for z in b.b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer_id) or not dom.get(z.GetNetname()):
            continue
        ps = z.GetFilledPolysList(layer_id).CloneDropTriangulation()
        out.append((z, dom[z.GetNetname()], ps, ps.Area()))
    return out


# tracks that pass too close to PE copper: In1 GND past PE3 (1.88 mm) and In2 20V past C22-1
# (1.71 mm). The In1 GND diagonal runs 0.71 mm beside the GPIO_BYPASS_RLY diagonal, so both move
# 0.75 mm away from PE3 together; the In2 20V track dips 0.95 mm under C22. (IPC frame)
MOVES = [
    ("In1.Cu", "GPIO_BYPASS_RLY", [((-103.215, -63.795), (-101.795, -63.795)), ((-101.795, -63.795), (-95.600, -57.600))],
     [(-103.215, -63.795), (-102.855, -63.795), (-96.660, -57.600), (-95.600, -57.600)]),
    ("In1.Cu", "GND", [((-102.471, -65.471), (-95.400, -58.400)), ((-103.412, -65.471), (-102.471, -65.471))],
     [(-103.412, -65.471), (-103.412, -65.352), (-96.460, -58.400), (-95.400, -58.400)]),
    ("In2.Cu", "20V", [((-62.644, -74.056), (-103.244, -74.056))],
     [(-103.244, -74.056), (-102.300, -75.000), (-91.000, -75.000), (-90.056, -74.056), (-62.644, -74.056)]),
]


def _same(t, a, c):
    s, e = t.GetStart(), t.GetEnd()
    pts = {(round(T(s.x), 3), round(-T(s.y), 3)), (round(T(e.x), 3), round(-T(e.y), 3))}
    return pts == {a, c}


for layer, net, old, new in MOVES:
    width = None
    for a, c in old:
        hit = [t for t in b.b.GetTracks() if t.GetClass() != "PCB_VIA"
               and b.b.GetLayerName(t.GetLayer()) == layer and _same(t, a, c)]
        if len(hit) != 1:
            raise SystemExit(f"fix 14: track {net} {a}-{c} on {layer} not found")
        width = T(hit[0].GetWidth())
        b.delete_tracks(lambda t: t is hit[0] or (t.GetClass() != "PCB_VIA" and b.b.GetLayerName(t.GetLayer()) == layer
                                                   and _same(t, a, c)))
    b.track(layer, new, round(width, 4), net)

changed = {}
for npass in (1, 2):
    for lname, lid in dg.LAYERS:
        nz = nonzone(lid)
        zl = fills(lid)
        for z, dz, fill, area in zl:
            obst = pcbnew.SHAPE_POLY_SET()
            for d, u in nz.items():
                g = domains.gap(dz, d)
                if g:
                    obst.Append(dg.grown(u, g + MARGIN))
            for z2, d2, fill2, area2 in zl:
                g = domains.gap(dz, d2)
                if g and z2 is not z and area < area2:
                    obst.Append(dg.grown(fill2, g + MARGIN))
            if not obst.OutlineCount():
                continue
            obst.Simplify()
            hit = dg.overlap(fill, obst)
            if not hit.OutlineCount() or hit.Area() < F(0.01) * F(0.01):
                continue
            ol = z.Outline()
            ol.BooleanSubtract(obst)
            key = (z.GetZoneName(), lname, z.GetNetname())
            for x, y, w, h in dg.clusters(hit):
                changed.setdefault(key, []).append((x, y, w, h))
    pcbnew.ZONE_FILLER(b.b).Fill(b.b.Zones())

for (name, lname, net), cl in sorted(changed.items()):
    for x, y, w, h in cl:
        b.log.append(f"pour {name} ({lname}, {net}) gives way at ({x:.2f},{y:.2f}) {w:.2f} x {h:.2f} mm")
    for z in b.b.Zones():
        if z.GetZoneName() == name and z.GetNetname() == net and not z.GetZoneName().endswith("(fix 14)"):
            z.SetZoneName(name + " (fix 14)")
b.save("fix 14: insulation spacing (pours give way: P-I 5.0 mm, P/I-PE 2.5 mm)")
