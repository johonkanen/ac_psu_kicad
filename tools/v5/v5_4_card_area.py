#!/usr/bin/env python3
"""v5 step 4 (run once, kipy): the card area in three isolated domains (V5_LAYOUT_PLAN.md phase 3).

Geometry and decisions: tools/v5/card_layout.py and reports/v5_layout/proposal.md. Steps:
  1. place the 71 v5 parts of the two CTRL pieces and the ISO side, move 32 v4 parts (U7, U2 and U10
     with their parts as rigid groups, with the tracks inside each group);
  2. delete the v4 tracks and vias that no longer fit (other domain in or within 5 mm of an area,
     inside a barrier strip, the J11 fan-out, nets of moved parts, copper under a new pad);
  3. barrier rule areas (5 mm strips, all copper layers) and slots on Edge.Cuts;
  4. plane zones per domain (In1 ground, In2 supply, In4 ground); the old ISO planes are deleted;
  5. every other pour is cut back to 5 mm from the areas of the other domains.
Routing is left open (lib/v5_copper.csv kind unrouted). Check: tools/v5/check_layout.py.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, P  # noqa: E402
import card_layout_r1 as L  # noqa: E402  (revision 1: what this script placed)
import check_layout as CL  # noqa: E402
import domains  # noqa: E402
from layout_proposal import inside  # noqa: E402

b = Board(5004)
B = b.b
if -T(b.fp("U19").GetPosition().y) > CL.STAGING_Y:
    raise SystemExit("v5 step 4 already applied (U19 is placed)")
dom = domains.classify(__import__("board_common").export_netlist()[1])
POLY, DOM = CL.POLY, CL.DOM
PLANES = {"GND", "VCC", "PGND", "ISOGND", "ISOPGND", "3V3_ISO", "15V_ISO", "CTRLGND", "CTRLGND_A", "3V3_CTRL", "5V_CTRL"}
REGION = (30.0, -40.0, 118.65, 54.0)      # where v4 copper is examined
CARD_REGION = (39.0, -22.0, 118.65, 54.0)   # where the nets of moved parts are opened
short = domains.short


def xy(v):
    return T(v.x), -T(v.y)


def pad(ref, num):
    return xy(next(p for p in b.fp(ref).Pads() if p.GetNumber() == num).GetPosition())


def pads_ok(fp):
    n = 0
    for p in fp.Pads():
        d = dom.get(p.GetNetname())
        if d:
            bb = p.GetBoundingBox()
            cs = [(T(bb.GetLeft()), -T(bb.GetBottom())), (T(bb.GetRight()), -T(bb.GetBottom())),
                  (T(bb.GetRight()), -T(bb.GetTop())), (T(bb.GetLeft()), -T(bb.GetTop()))]
            n += any(DOM[k] == d and all(inside(c, POLY[k]) for c in cs) for k in POLY)
    return n


old_pads = []     # pad shapes of the v4 parts at their old places (their stubs are deleted)


def put(ref, x, y, rot=None, side="F", pin1=None, center=False):
    """Place ref with its origin (or pad `pin1`) at (x, y). rot None: the rotation that puts every pad in
    an area of its own domain (barrier parts)."""
    fp = b.fp(ref)
    if -T(fp.GetPosition().y) > CL.STAGING_Y:
        old_pads.extend(CL.pad_poly(p) + (p.GetNetname(),) for p in fp.Pads())
    fp.SetPosition(P(x, y))
    if (side == "B") != fp.IsFlipped():
        fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    if rot is None:
        best = max((0, 90, 180, 270), key=lambda r: (fp.SetOrientationDegrees(r), pads_ok(fp))[1])
        fp.SetOrientationDegrees(best)
        if pads_ok(fp) != sum(1 for p in fp.Pads() if dom.get(p.GetNetname())):
            raise SystemExit(f"{ref}: no rotation puts all pads in their domain areas")
        rot = best
    else:
        fp.SetOrientationDegrees(rot)
    if center:     # the middle of the pads at (x, y)
        ps = [xy(p.GetPosition()) for p in fp.Pads()]
        cx, cy = sum(q[0] for q in ps) / len(ps), sum(q[1] for q in ps) / len(ps)
        fp.SetPosition(P(2 * x - cx, 2 * y - cy))
    fp.Reference().SetVisible(True)
    q = xy(fp.GetPosition())
    b.log.append(f"{ref:5} {side} ({q[0]:8.3f}, {q[1]:8.3f}) rot {rot:5.1f}  {L.PLACE[ref][4][:70]}")


kept = set()      # tracks moved with a rigid group


def move_group(refs, dx, dy, tracks=True):
    fps = [b.fp(r) for r in refs.split()]
    bb = fps[0].GetBoundingBox(False)
    for fp in fps[1:]:
        bb.Merge(fp.GetBoundingBox(False))
    bb.Inflate(F(0.3))
    for fp in fps:
        old_pads.extend(CL.pad_poly(p) + (p.GetNetname(),) for p in fp.Pads())
    n = 0
    if tracks:
        for t in B.GetTracks():
            if bb.Contains(t.GetStart()) and bb.Contains(t.GetEnd()):
                t.Move(pcbnew.VECTOR2I(F(dx), F(-dy)))
                kept.add(t.m_Uuid.AsString())
                n += 1
    for fp in fps:
        q = xy(fp.GetPosition())
        fp.SetPosition(P(q[0] + dx, q[1] + dy))
    b.log.append(f"group {refs.split()[0]} ({len(fps)} parts, {n} tracks/vias) moved by ({dx}, {dy}): {refs}")


# ---- 1. placement -------------------------------------------------------------------------------
put("U16", 80.0, 18.3)
put("C82", 86.2, 23.0, 90)
put("C81", pad("U16", "16")[0], 11.5, 0)
# isolator row on the bottom, ISO pins north (south of the DC bus band)
for u, x, cc, ci in (("U21", 57.05, "C121", "C122"), ("U19", 68.0, "C117", "C118"), ("U20", 78.95, "C119", "C120")):
    put(u, x, 35.5, side="B")
    put(cc, pad(u, "1")[0], 28.95, 0, "B")
    put(ci, *pad(u, "16"), 0)
# AMC1311: U22 in the row, U23/U24 on the east line; all on the bottom
put("U22", 87.75, 35.5, side="B")
put("C123", *pad("U22", "1"), 0)
put("C124", *pad("U22", "8"), 0)
put("R110", 93.3, 41.0, 0, "B")
put("R111", 93.3, 39.3, 0, "B")
for u, y, ci, cc, r1, r2 in (("U23", 29.7, "C125", "C126", "R112", "R113"), ("U24", 23.1, "C127", "C128", "R114", "R115")):
    put(u, 97.6, y, side="B")
    put(ci, 105.1, pad(u, "1")[1], 0, "B")
    put(cc, *pad(u, "8"), 0)
    put(r1, 107.8, y + 0.8, 0, "B")
    put(r2, 107.8, y - 0.9, 0, "B")
# difference amplifiers on the bottom, below the AMC1311 outputs: (Rn, Rf, Rp, Rg) per chain
for (rn, rf, rp, rg), x, ya in ((("R116", "R117", "R118", "R119"), 81.9, 27.6), (("R120", "R121", "R122", "R123"), 88.3, 27.6),
                                (("R124", "R125", "R126", "R127"), 88.3, 24.0)):
    put(rn, x, ya, 0, "B")
    put(rf, x - 3.2, ya, 0, "B")
    put(rp, x, ya - 1.7, 0, "B")
    put(rg, x - 3.2, ya - 1.7, 0, "B")
put("U25", 79.5, 22.9, 0, "B")
put("U26", 73.9, 26.6, 0, "B")
put("C132", 75.3, 22.9, 90, "B")
put("C133", 73.9, 24.1, 0, "B")
for i, (r, c) in enumerate((("R128", "C129"), ("R129", "C130"), ("R130", "C131"))):
    put(r, 53.3 + 1.1 * i, 25.6, 90)
    put(c, 53.3 + 1.1 * i, 27.6, 90)
put("PEC1", 50.1, 26.6, 0)
put("J14", 59.3, 27.0, 90, center=True)
put("U27", 66.0, 25.9, 0, "B")
put("C136", 66.3, 28.5, 0, "B")
put("C135", 69.4, 25.9, 90, "B")
put("C134", 66.0, 22.9, 0, "B")
move_group("U7 C103 C104 C105 C106 C107 C108 C38 R46 R51 R52 R53 R54 R56", 21.2, -26.2)
move_group("U2 C101 C102 C2 C87 R1 R76 R77", 6.0, -32.1)
move_group("U10 C3 C4", -15.0, 2.2)
move_group("U8 C93 C94", -13.36, 0.0, tracks=False)
put("C56", 107.6, 14.5, 90)
# CTRL piece at J12
put("C137", 112.65, -1.6, 0, "B")
put("C138", 112.65, -23.3, 0, "B")
put("L2", 110.8, -10.6, 0, "B")
put("D16", 111.0, -25.8, 0)
put("W1", 112.6, -31.6, 0)
if abs(pad("W1", "1")[0] - 112.6) < 0.1:      # the footprint origin is pad 1: centre the pair
    put("W1", 112.6 - (pad("W1", "2")[0] - pad("W1", "1")[0]) / 2, -31.6, 0)
put("PEC2", 105.6, -30.75, 0)
put("J13", 117.0, -8.3, 0)
put("U28", 112.6, 0.85, 90)
put("C141", 116.3, 1.7, 0)
put("C140", 116.3, -0.1, 0)
put("R134", 108.0, 0.85, 90)
put("R135", 109.6, 0.85, 90)
put("C144", 114.15, -8.15, 90)
put("C139", 112.1, -8.15, 90)
put("R131", 116.6, -21.1, 90)
put("R132", 113.05, -20.5, 90)
put("R133", 114.6, -20.5, 90)
put("C142", 109.9, -20.2, 0)
put("C143", 109.9, -22.7, 0)
left = [r for r in L.PLACE if -T(b.fp(r).GetPosition().y) < CL.STAGING_Y]
if left:
    raise SystemExit("not placed: " + " ".join(left))

# ---- 2. tracks and vias that no longer fit -----------------------------------------------------
strip = CL.strips()
forbidden = {}
for d in "PIC":
    u = pcbnew.SHAPE_POLY_SET()
    for k, poly in POLY.items():
        if DOM[k] != d:
            g = CL.sps(poly)
            g.Inflate(F(L.GAP - 0.001), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, F(0.005))
            u.Append(g)
    u.Simplify()
    forbidden[d] = u
ca = CL.sps(POLY["CA"])
moved_nets = set()
for ref in L.PLACE:
    if ref in b.comps and ref in {r["ref"] for r in __import__("deviations").rows() if r["kind"] == "moved"} | {"C93", "C94", "C101", "C102", "C103", "C104", "C105", "C106", "C107", "C108"}:
        moved_nets.update(short(p.GetNetname()) for p in b.fp(ref).Pads())
moved_nets -= PLANES
moved_nets.discard("")
new_pads = [CL.pad_poly(p) + (p.GetNetname(),) for r in L.PLACE for p in b.fp(r).Pads()]


def hits(t, shp, pads, clr, other_net):
    via = t.GetClass() == "PCB_VIA"
    return any((via or t.GetLayer() in ls) and (not other_net or n != t.GetNetname()) and ps.Collide(shp, F(clr))
               for ps, ls, n in pads)


import collections
why = collections.Counter()
dead = []
for t in B.GetTracks():
    if t.m_Uuid.AsString() in kept:
        continue
    s, e = xy(t.GetStart()), xy(t.GetEnd())
    if not any(REGION[0] <= q[0] <= REGION[2] and REGION[1] <= q[1] <= REGION[3] for q in (s, e)):
        continue
    shp = t.GetEffectiveShape()
    d = dom.get(t.GetNetname())
    r = None
    if strip.Collide(shp, 0):
        r = "inside a barrier strip"
    elif t.GetClass() != "PCB_VIA" and t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In4_Cu) and any(
            k != "P" and (inside(s, POLY[k]) or inside(e, POLY[k])) for k in POLY):
        r = "track on a plane layer of the new areas (In1, In2, In4)"
    elif d in forbidden and forbidden[d].Collide(shp, 0):
        r = f"{d} copper in or within 5 mm of another domain's area"
    elif d == "C" and ca.Collide(shp, 0):
        r = "J11 fan-out (CTRL piece re-routed)"
    elif short(t.GetNetname()) in moved_nets and all(
            CARD_REGION[0] <= q[0] <= CARD_REGION[2] and CARD_REGION[1] <= q[1] <= CARD_REGION[3] for q in (s, e)):
        r = "net of a moved part"
    elif hits(t, shp, new_pads, 0.2, True):
        r = "under a pad of a placed part"
    elif hits(t, shp, old_pads, 0.05, False):
        r = "stub at the old place of a moved part"
    if r:
        why[("via" if t.GetClass() == "PCB_VIA" else "track", r)] += 1
        dead.append(t)
for t in dead:
    B.Delete(t)
for (kind, r), n in sorted(why.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    b.log.append(f"deleted {n:4} {kind:5} {r}")



def prune():
    """Delete track / via groups in the region that reach no pad and no filled zone of their net."""
    zones = B.Zones()
    pcbnew.ZONE_FILLER(B).Fill(zones)
    items = [t for t in B.GetTracks() if any(REGION[0] <= q[0] <= REGION[2] and REGION[1] <= q[1] <= REGION[3]
                                             for q in (xy(t.GetStart()), xy(t.GetEnd())))]
    pts = {}
    for i, t in enumerate(items):
        ends = (t.GetStart(),) if t.GetClass() == "PCB_VIA" else (t.GetStart(), t.GetEnd())
        lays = (None,) if t.GetClass() == "PCB_VIA" else (t.GetLayer(),)
        for q in ends:
            pts.setdefault((t.GetNetname(), round(T(q.x), 2), round(T(q.y), 2)), []).append((i, lays[0]))
    parent = list(range(len(items)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for lst in pts.values():
        for i, la in lst[1:]:
            j, lb = lst[0]
            if la is None or lb is None or la == lb or any(l is None for _, l in lst):
                parent[find(i)] = find(j)
    anchored = set()
    padshapes = [CL.pad_poly(p) + (p.GetNetname(),) for fp in B.GetFootprints() for p in fp.Pads() if p.GetNetname()]
    for i, t in enumerate(items):
        via = t.GetClass() == "PCB_VIA"
        shp = t.GetEffectiveShape()
        ok = any(n == t.GetNetname() and (via or t.GetLayer() in ls) and ps.Collide(shp, 0) for ps, ls, n in padshapes)
        if not ok:
            for z in zones:
                if z.GetIsRuleArea() or z.GetNetname() != t.GetNetname():
                    continue
                for lid in z.GetLayerSet().CuStack():
                    if (via or t.GetLayer() == lid) and z.GetFilledPolysList(lid).Collide(shp, 0):
                        ok = True
        # a group may also hang on copper outside the region
        if not ok and not via and not all(REGION[0] <= q[0] <= REGION[2] and REGION[1] <= q[1] <= REGION[3]
                                          for q in (xy(t.GetStart()), xy(t.GetEnd()))):
            ok = True
        if ok:
            anchored.add(find(i))
    gone = [t for i, t in enumerate(items) if find(i) not in anchored]
    for t in gone:
        B.Delete(t)
    return len(gone)

# ---- 3. barrier rule areas and slots -----------------------------------------------------------
cu = pcbnew.LSET.AllCuMask(6)
for i in range(strip.OutlineCount()):
    z = pcbnew.ZONE(B)
    z.SetIsRuleArea(True)
    z.SetLayerSet(cu)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.Outline().AddOutline(strip.Outline(i))
    for h in range(strip.HoleCount(i)):
        z.Outline().AddHole(strip.Hole(i, h), i if False else z.Outline().OutlineCount() - 1)
    z.SetZoneName(f"v5 barrier strip {i + 1} (5 mm, reinforced)")
    B.Add(z)
    z.thisown = False
b.log.append(f"{strip.OutlineCount()} barrier rule areas (no tracks, vias, pours; all copper layers) along: "
             + ", ".join(n for n, _, _ in L.LINES))


def shape(kind):
    s = pcbnew.PCB_SHAPE(B)
    s.SetShape(kind)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(F(0.1))
    B.Add(s)
    s.thisown = False
    return s


for name, a, c in L.SLOTS:
    r = L.SLOT_W / 2
    ux, uy = (c[0] - a[0]) / math.dist(a, c), (c[1] - a[1]) / math.dist(a, c)
    nx, ny = -uy * r, ux * r
    for sgn in (1, -1):
        s = shape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(a[0] + sgn * nx, a[1] + sgn * ny))
        s.SetEnd(P(c[0] + sgn * nx, c[1] + sgn * ny))
    for q, sgn in ((a, -1), (c, 1)):
        s = shape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(q[0] + nx, q[1] + ny), P(q[0] + sgn * ux * r, q[1] + sgn * uy * r), P(q[0] - nx, q[1] - ny))
    b.log.append(f"slot {name}: ({a[0]}, {a[1]}) - ({c[0]}, {c[1]}), {L.SLOT_W} mm wide")

# ---- 4. plane zones ------------------------------------------------------------------------------
for z in list(B.Zones()):
    if z.GetZoneName() in ("Proteus In1.Cu pour 2", "Proteus In2.Cu pour 2"):
        b.log.append(f"deleted zone {z.GetZoneName()} [{z.GetNetname()}] (replaced by the ISO plane zones)")
        B.Delete(z)
PLANE_ZONES = (("CA", "In1.Cu", "CTRLGND_A"), ("CA", "In2.Cu", "3V3_CTRL"), ("CA", "In4.Cu", "CTRLGND_A"),
               ("CB", "In1.Cu", "CTRLGND"), ("CB", "In2.Cu", "5V_CTRL"), ("CB", "In4.Cu", "CTRLGND"),
               ("I", "In1.Cu", "ISOGND"), ("I", "In2.Cu", "3V3_ISO"), ("I", "In4.Cu", "ISOGND"),
               ("P", "In4.Cu", "GND"))
for i, (area, layer, net) in enumerate(PLANE_ZONES):
    full = next(n for n in b.pin_net.values() if short(n) == net)
    z = b.zone(layer, L.PLANE_POLY.get(area, POLY[area]), full, f"v5 card {area} {layer} {net}", 120 + i, clearance=0.3)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)    # a plane without a pad yet stays; slivers go
    z.SetMinIslandArea(F(1) * F(1) * 5)
    z.SetMinThickness(F(0.2))

# ---- 5. other pours: 5 mm back from the areas of the other domains ---------------------------
for z in list(B.Zones()):
    if z.GetIsRuleArea() or z.GetZoneName().startswith("v5 card"):
        continue
    d = dom.get(z.GetNetname())
    if d not in forbidden or not z.GetBoundingBox().Intersects(forbidden[d].BBox()):
        continue
    o = z.Outline()
    a0 = o.Area()
    o.BooleanSubtract(forbidden[d])
    o.BooleanSubtract(strip)
    if o.OutlineCount() == 0 or o.Area() < F(1) * F(1):
        b.log.append(f"deleted zone {z.GetZoneName()} [{short(z.GetNetname())}] {B.GetLayerName(z.GetFirstLayer())}: inside another domain's area")
        B.Delete(z)
    elif abs(o.Area() - a0) > F(0.1) * F(0.1):
        # one outline per zone (the board file keeps only the first): further pieces become zones of their own
        parts = [(pcbnew.SHAPE_LINE_CHAIN(o.Outline(i)), [pcbnew.SHAPE_LINE_CHAIN(o.Hole(i, h)) for h in range(o.HoleCount(i))])
                 for i in range(o.OutlineCount())]
        parts.sort(key=lambda p: -abs(p[0].Area()))
        for k, (ch, holes) in enumerate(parts):
            zz = z if k == 0 else z.Duplicate(False)
            if k:
                zz = pcbnew.Cast_to_ZONE(zz)
                B.Add(zz)
                zz.thisown = False
                zz.SetZoneName(f"{z.GetZoneName()} (part {k + 1})")
            oo = zz.Outline()
            oo.RemoveAllContours()
            oo.AddOutline(ch)
            for hch in holes:
                oo.AddHole(hch, 0)
            zz.SetNeedRefill(True)
            zz.HatchBorder()
        o = z.Outline()
        b.log.append(f"zone {z.GetZoneName()} [{short(z.GetNetname())}] {B.GetLayerName(z.GetFirstLayer())}: cut back, "
                     f"{len(parts)} piece(s), the largest {o.Area() / F(1) / F(1):.0f} mm2 (was {a0 / F(1) / F(1):.0f})")

n = prune()
b.log.append(f"deleted {n:4} tracks / vias left without a pad or a pour of their net")

b.save("v5 step 4: card area in three domains (placement, barrier strips, slots, planes)")
