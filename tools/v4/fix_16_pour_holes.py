#!/usr/bin/env python3
"""v4 fix 16 (run once, kipy): pours without cut-outs (user 2026-11-05: "remove the holes from
copper pours so KiCad automatically draws the clearances to the inner parts").

The Proteus pours came over with Proteus' own clearance cut-outs as zone holes (pours_to_zones.py):
406 holes in 80 zones, 132 around other-net copper, 274 around same-net pads/vias (thermal
cut-outs bridged by spoke tracks, or same-net isolation). This fix:
  1. clearance per zone: the smallest gap Proteus left between the pour and other-net copper inside
     its holes, rounded down to 0.05 mm (at least the 0.15 mm board default). KiCad then keeps at
     least the Proteus gap everywhere inside the pour; the IEC domain gaps come from the DRC rules
     of tools/v4/domain_rules.py (net classes DOM_P/I/E, kicad/ac_psu.kicad_dru);
  2. every zone keeps only its outer outline(s): no holes;
  3. priorities: a zone that lay inside a hole of an other-net zone on the same layer must now win
     over it: priority = 1000 x nesting depth + the Proteus draw order;
  4. fill. A pour that now covers ground it did not cover before may lie over copper of the other
     power domain on an adjacent layer (P over I or I over P: the prepreg is thinner than the
     0.4 mm reinforced solid insulation, tools/v4/domain_gaps.py). Those spots get a pour keep-out
     rule area (the overlap grown by 0.3 mm) on the pour's layer; repeated until none is left.
Same-net cut-outs disappear: those pads/vias now connect solid (the zones already use solid pad
connection; the Proteus spoke tracks stay, harmless)."""
import os
import sys

import pcbnew
from v4board import Board, F, T

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import domains  # noqa: E402
import domain_gaps as dg  # noqa: E402

ERR = F(0.005)
MIN_CLR = 0.15
KEEPOUT_GROW = 0.3

b = Board(4116)
copper = [z for z in b.b.Zones() if not z.GetIsRuleArea()]
nholes = sum(z.Outline().HoleCount(i) for z in copper for i in range(z.Outline().OutlineCount()))
if nholes == 0:
    raise SystemExit("fix 16 already applied (no zone has holes)")
nets = {}
for (ref, pin), net in b.pin_net.items():
    nets.setdefault(net, []).append((ref, pin))
dom = domains.classify(nets)


def items(lid):
    out = []
    for fp in b.b.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(lid):
                ps = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(ps, lid, 0, ERR, pcbnew.ERROR_INSIDE)
                out.append((pad.GetNetname(), ps))
    for t in b.b.GetTracks():
        if t.IsOnLayer(lid):
            ps = pcbnew.SHAPE_POLY_SET()
            t.TransformShapeToPolygon(ps, lid, 0, ERR, pcbnew.ERROR_INSIDE)
            out.append((t.GetNetname(), ps))
    return out


def hit(a, c, eps=0.005):
    o = dg.overlap(a, c)
    return o.OutlineCount() and o.Area() > F(eps) * F(eps)


# -- 1. Proteus gaps inside the holes -> zone clearance ------------------------------------
old_fill = {}
clearance = {}
nforeign = nsame = ncross = 0
for lname, lid in dg.LAYERS:
    its = items(lid)
    for z in copper:
        if not z.IsOnLayer(lid):
            continue
        fill = z.GetFilledPolysList(lid).CloneDropTriangulation()
        old_fill[id(z)] = fill
        ol = z.Outline()
        gaps = []
        for oi in range(ol.OutlineCount()):
            for hi in range(ol.HoleCount(oi)):
                hole = pcbnew.SHAPE_POLY_SET()
                hole.AddOutline(ol.Hole(oi, hi))
                hb = ol.Hole(oi, hi).BBox()
                inside = [(n, ps) for n, ps in its if n != z.GetNetname() and ps.BBox().Intersects(hb) and hit(ps, hole, 0.01)]
                if not inside:
                    nsame += 1
                    continue
                nforeign += 1
                # gaps to another domain are set by the DRC rules (domain_rules.py), not the zone
                zd = dom.get(z.GetNetname())
                inside = [(n, ps) for n, ps in inside if not domains.gap(zd, dom.get(n))]
                if not inside:
                    ncross += 1
                    continue
                u = pcbnew.SHAPE_POLY_SET()
                for _, ps in inside:
                    u.Append(ps)
                u.Simplify()
                lo, hi_ = 0.0, 3.0
                if not hit(dg.grown(u, hi_), fill):
                    continue
                for _ in range(10):
                    m = (lo + hi_) / 2
                    lo, hi_ = (lo, m) if hit(dg.grown(u, m), fill) else (m, hi_)
                gaps.append(lo)
        clr = max(MIN_CLR, int((min(gaps) + 0.01) / 0.05) * 0.05) if gaps else MIN_CLR
        clearance[id(z)] = clr
        if abs(clr - T(z.GetLocalClearance())) > 1e-6:
            b.log.append(f"zone {z.GetZoneName()} ({lname}, {z.GetNetname()}): clearance {clr:.2f} mm "
                         f"(Proteus gaps in {len(gaps)} holes: min {min(gaps):.2f} mm)")
        z.SetLocalClearance(F(clr))
b.log.append(f"{nholes} holes: {nforeign} around other-net copper, {nsame} around same-net copper only, "
              f"{ncross} only around copper of another domain (DRC rules)")

# -- 2. outer outlines only ---------------------------------------------------------------
for z in copper:
    ol = z.Outline()  # edited in place: ZONE.SetOutline() takes ownership of a Python-owned poly
    outers = [pcbnew.SHAPE_LINE_CHAIN(ol.Outline(oi)) for oi in range(ol.OutlineCount())]
    ol.RemoveAllContours()
    for ch in outers:
        ol.AddOutline(ch)

# -- 3. priorities by nesting -------------------------------------------------------------
outer = {id(z): z.Outline().CloneDropTriangulation() for z in copper}
inside_of = {id(z): [] for z in copper}
partial = []
for i, za in enumerate(copper):
    for zb in copper[i + 1:]:
        if za.GetLayer() != zb.GetLayer() or za.GetNetname() == zb.GetNetname():
            continue
        oa, ob = outer[id(za)], outer[id(zb)]
        if not oa.BBox().Intersects(ob.BBox()):
            continue
        o = dg.overlap(oa, ob)
        if not o.OutlineCount() or o.Area() < F(0.01) * F(0.01):
            continue
        if o.Area() >= 0.999 * ob.Area():
            inside_of[id(zb)].append(za)
        elif o.Area() >= 0.999 * oa.Area():
            inside_of[id(za)].append(zb)
        else:
            partial.append((za, zb, T(T(o.Area()))))
depth = {}


def get_depth(z, seen=()):
    if id(z) not in depth:
        if id(z) in seen:
            raise SystemExit(f"fix 16: zone nesting cycle at {z.GetZoneName()}")
        depth[id(z)] = 1 + max((get_depth(c, seen + (id(z),)) for c in inside_of[id(z)]), default=-1)
    return depth[id(z)]


for z in copper:
    d = get_depth(z)
    if d:
        prio = 1000 * d + z.GetAssignedPriority()
        b.log.append(f"zone {z.GetZoneName()} ({b.b.GetLayerName(z.GetLayer())}, {z.GetNetname()}) inside "
                     + ", ".join(c.GetNetname() for c in inside_of[id(z)])
                     + f": priority {z.GetAssignedPriority()} -> {prio}")
        z.SetAssignedPriority(prio)
for za, zb, area in partial:
    b.log.append(f"note: zones {za.GetZoneName()} ({za.GetNetname()}) and {zb.GetZoneName()} ({zb.GetNetname()}) "
                 f"overlap partly ({area:.2f} mm^2): the higher priority one wins")

# -- 4. fill, keep-outs against adjacent-layer overlaps of the other power domain ------------
stack = [lid for _, lid in dg.LAYERS]
nko = 0
for npass in range(1, 5):
    pcbnew.ZONE_FILLER(b.b).Fill(b.b.Zones())
    found = 0
    for k, lid in enumerate(stack):
        for adj in stack[max(0, k - 1):k] + stack[k + 1:k + 2]:
            other = dg.item_polys(b.b, adj, dom)
            for z in copper:
                d = dom.get(z.GetNetname())
                if d not in ("P", "I") or not z.IsOnLayer(lid):
                    continue
                opp = {"P": "I", "I": "P"}[d]
                if opp not in other:
                    continue
                fill = z.GetFilledPolysList(lid).CloneDropTriangulation()
                ov = dg.overlap(fill, dg.union(other[opp]))
                if not ov.OutlineCount() or ov.Area() < F(0.01) * F(0.01):
                    continue
                for oi in range(ov.OutlineCount()):
                    piece = pcbnew.SHAPE_POLY_SET()
                    piece.AddOutline(ov.Outline(oi))
                    if piece.Area() < F(0.01) * F(0.01):
                        continue
                    g = dg.grown(piece, KEEPOUT_GROW)
                    ko = pcbnew.ZONE(b.b)
                    ko.SetIsRuleArea(True)
                    ko.SetLayer(lid)
                    ko.SetDoNotAllowZoneFills(True)
                    ko.SetDoNotAllowTracks(False)
                    ko.SetDoNotAllowVias(False)
                    ko.SetDoNotAllowPads(False)
                    ko.SetDoNotAllowFootprints(False)
                    ko.Outline().Append(g)
                    nko += 1
                    bb = piece.BBox()
                    name = f"v4 fix 16 keep-out {nko}: {d} pour over {opp} on {b.b.GetLayerName(adj)}"
                    ko.SetZoneName(name)
                    b.b.Add(ko)
                    ko.thisown = False
                    found += 1
                    b.log.append(f"{name}: {z.GetNetname()} at ({T(bb.Centre().x):.2f},{-T(bb.Centre().y):.2f}) "
                                 f"{T(bb.GetWidth()):.2f} x {T(bb.GetHeight()):.2f} mm")
    if not found:
        break
else:
    raise SystemExit("fix 16: adjacent-layer overlaps remain after 4 passes")

# -- report: copper gained/lost per layer ---------------------------------------------------
for lname, lid in dg.LAYERS:
    gain = lost = 0.0
    for z in copper:
        if not z.IsOnLayer(lid):
            continue
        new = z.GetFilledPolysList(lid).CloneDropTriangulation()
        old = old_fill[id(z)]
        a = new.CloneDropTriangulation()
        a.BooleanSubtract(old)
        c = old.CloneDropTriangulation()
        c.BooleanSubtract(new)
        gain += T(T(a.Area()))
        lost += T(T(c.Area()))
        for oi in range(c.OutlineCount()):
            piece = pcbnew.SHAPE_POLY_SET()
            piece.AddOutline(c.Outline(oi))
            if T(T(piece.Area())) >= 1.0:
                bb = piece.BBox()
                b.log.append(f"  {lname} {z.GetNetname()}: -{T(T(piece.Area())):.1f} mm^2 at "
                             f"({T(bb.Centre().x):.2f},{-T(bb.Centre().y):.2f}) {T(bb.GetWidth()):.2f} x {T(bb.GetHeight()):.2f} mm")
    b.log.append(f"{lname}: pour copper +{gain:.1f} mm^2 / -{lost:.1f} mm^2")
b.save("fix 16: pours without holes (KiCad clearances; IEC domain gaps as DRC rules)")
