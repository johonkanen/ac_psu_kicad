#!/usr/bin/env python3
"""v5 step 5 (run once, kipy): card-area placement, revision 2 (user 2026-11-17).

Why: the first placement (v5 step 4) could not be routed (CTRL column beside J11 2.9 mm wide, CTRL area
12.2 mm high). Geometry and decisions: tools/v5/card_layout.py (revision 2) and
reports/v5_layout/proposal_r2.md. Steps:
  0. the barrier rule areas, slots and plane zones of step 4 are removed (rebuilt below);
  1. U15/U13/U16 10 mm south and 3.6 mm west; U21/U19/U20 6.6 mm east; U22 to (88.0, 13.25); the CTRL
     blocks re-placed in the larger CTRL area; the primary ADC group mirrored to the bottom side and the
     1.65 V reference group moved east (top side), both as rigid groups with the tracks inside them;
  2. tracks and vias that no longer fit are deleted (same rules as step 4);
  3. barrier rule areas and slots; 4. plane zones; 5. pours cut back 5 mm from the other domains' areas.
Routing is left open (lib/v5_copper.csv kind unrouted). Check: tools/v5/check_layout.py.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, P  # noqa: E402
import card_layout as L  # noqa: E402
import card_layout_r1 as L1  # noqa: E402
import check_layout as CL  # noqa: E402
import domains  # noqa: E402
from layout_proposal import inside, seg_pt  # noqa: E402

b = Board(5005)
B = b.b
if -T(b.fp("U15").GetPosition().y) < 12.0:
    raise SystemExit("v5 step 5 already applied (U15 is at the revision 2 place)")
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


old_pads = []     # pad shapes of the parts at their old places (their stubs are deleted)
touched = set()   # parts moved by this step
kept = set()      # tracks moved with a rigid group

# ---- 0. step 4's rule areas, slots and plane zones go (rebuilt from revision 2 below) -------------
n = 0
for z in list(B.Zones()):
    if z.GetZoneName().startswith(("v5 barrier strip", "v5 card ")):
        B.Delete(z)
        n += 1
b.log.append(f"removed {n} rule areas / plane zones of step 4")
n = 0
for d in list(B.GetDrawings()):
    if d.GetLayer() != pcbnew.Edge_Cuts or d.GetClass() != "PCB_SHAPE":
        continue
    pts = [xy(d.GetStart()), xy(d.GetEnd())]
    if any(all(seg_pt(q, a, c) < L1.SLOT_W / 2 + 0.05 for q in pts) for _, a, c in L1.SLOTS):
        B.Delete(d)
        n += 1
if n != 4 * len(L1.SLOTS):
    raise SystemExit(f"step 4 slots: {n} outline items found, expected {4 * len(L1.SLOTS)}")
b.log.append(f"removed the {len(L1.SLOTS)} slots of step 4 ({n} outline items)")


def put(ref, x, y, rot=None, side="F", center=False):
    """Place ref with its origin at (x, y). rot None: the rotation that puts every pad in an area of its
    own domain (barrier parts)."""
    fp = b.fp(ref)
    touched.add(ref)
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
    q = xy(fp.GetPosition())
    b.log.append(f"{ref:5} {side} ({q[0]:8.3f}, {q[1]:8.3f}) rot {rot:5.1f}  {L.PLACE[ref][4][:70]}")


def shift(ref, dx, dy):
    fp = b.fp(ref)
    q = xy(fp.GetPosition())
    put(ref, q[0] + dx, q[1] + dy, fp.GetOrientationDegrees(), "B" if fp.IsFlipped() else "F")


def flip_group(refs, dx, dy):
    """Mirror a group of top-side parts to the bottom about the vertical axis through the group's middle,
    then move it by (dx, dy). The tracks and vias inside the group's box on the group's nets go with it
    (F.Cu <-> B.Cu)."""
    fps = [b.fp(r) for r in refs.split()]
    bb = fps[0].GetBoundingBox(False)
    for fp in fps[1:]:
        bb.Merge(fp.GetBoundingBox(False))
    bb.Inflate(F(0.3))
    c = bb.Centre()
    nets = {p.GetNetname() for fp in fps for p in fp.Pads() if p.GetNetname()}
    mv = pcbnew.VECTOR2I(F(dx), F(-dy))
    n = 0
    for t in B.GetTracks():
        if t.GetNetname() in nets and bb.Contains(t.GetStart()) and bb.Contains(t.GetEnd()):
            if t.GetClass() == "PCB_ARC":
                raise SystemExit("flip_group: arc track in the group")
            # mirrored by hand (PCB_VIA.Flip left a via that the zone filler no longer cleared)
            s, e = t.GetStart(), t.GetEnd()
            t.SetStart(pcbnew.VECTOR2I(2 * c.x - s.x, s.y))
            t.SetEnd(pcbnew.VECTOR2I(2 * c.x - e.x, e.y))
            if t.GetClass() != "PCB_VIA" and t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
                t.SetLayer(pcbnew.B_Cu if t.GetLayer() == pcbnew.F_Cu else pcbnew.F_Cu)
            t.Move(mv)
            kept.add(t.m_Uuid.AsString())
            n += 1
    for fp in fps:
        if fp.IsFlipped():
            raise SystemExit(f"{fp.GetReference()} is on the bottom already")
        touched.add(fp.GetReference())
        old_pads.extend(CL.pad_poly(p) + (p.GetNetname(),) for p in fp.Pads())
        fp.Flip(c, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.Move(mv)
    b.log.append(f"group {refs.split()[0]} ({len(fps)} parts, {n} tracks/vias) mirrored to the bottom about x {T(c.x):.2f}, "
                 f"moved by ({dx}, {dy}): {refs}")


def move_group(refs, dx, dy):
    """Move a group of parts as it is, with the tracks and vias inside the group's box on the group's nets."""
    fps = [b.fp(r) for r in refs.split()]
    bb = fps[0].GetBoundingBox(False)
    for fp in fps[1:]:
        bb.Merge(fp.GetBoundingBox(False))
    bb.Inflate(F(0.3))
    nets = {p.GetNetname() for fp in fps for p in fp.Pads() if p.GetNetname()}
    mv = pcbnew.VECTOR2I(F(dx), F(-dy))
    n = 0
    for t in B.GetTracks():
        if t.GetNetname() in nets and bb.Contains(t.GetStart()) and bb.Contains(t.GetEnd()):
            t.Move(mv)
            kept.add(t.m_Uuid.AsString())
            n += 1
    for fp in fps:
        touched.add(fp.GetReference())
        old_pads.extend(CL.pad_poly(p) + (p.GetNetname(),) for p in fp.Pads())
        fp.Move(mv)
    b.log.append(f"group {refs.split()[0]} ({len(fps)} parts, {n} tracks/vias) moved by ({dx}, {dy}): {refs}")


# ---- 1. placement ---------------------------------------------------------------------------------
# primary isolators: 10 mm south, 3.6 mm west (U16 clear of U17), with their capacitors
for u in ("U15", "U13", "U16"):
    shift(u, -3.6, L.Y_CP - xy(b.fp(u).GetPosition())[1])
for c in ("C86", "C83", "C84", "C81"):
    shift(c, -3.6, -10.0)
put("C85", 68.87, 1.2, 90)
put("C82", 83.2, 12.2, 90)
# primary logic: the ADC group to the bottom (under U11). The reference group stays on the top side and moves
# to the free primary area south of U13/U16: on the bottom its through vias came under U15's pads.
flip_group("AD1 R87 C9 R86 C17 U12 L1 C18", 0.0, -5.0)
move_group("REF1 C40 C16 R19 R30 C109", 24.75, -5.0)
put("R22", 55.6, 1.0, -90)
# north isolator row (bottom): 6.6 mm east
for u, cc, ci, cix in (("U21", "C121", "C122", 67.2), ("U19", "C117", "C118", None), ("U20", "C119", "C120", None)):
    shift(u, 6.6, 0.0)
    put(cc, pad(u, "1")[0], 28.95, 0, "B")
    put(ci, cix or pad(u, "16")[0], 40.15, 0)
# U22 to the east edge of the southern CTRL part (bottom), its capacitors and divider beside it
put("U22", 88.0, 13.25, side="B")
put("C124", pad("U22", "8")[0] - 2.4, pad("U22", "8")[1], 0, "B")
put("C123", pad("U22", "1")[0] + 2.4, pad("U22", "1")[1], 0, "B")
put("R110", 98.0, 12.6, 0, "B")
put("R111", 98.0, 10.9, 0, "B")
# difference amplifiers (bottom): (Rn, Rf, Rp, Rg) per chain, 2.3 mm row pitch
for (rn, rf, rp, rg), pos in ((("R116", "R117", "R118", "R119"), ((77.2, 16.9), (74.0, 16.9), (77.2, 14.6), (74.0, 14.6))),
                              (("R120", "R121", "R122", "R123"), ((88.3, 27.6), (85.1, 27.6), (88.3, 25.3), (85.1, 25.3))),
                              (("R124", "R125", "R126", "R127"), ((88.3, 23.0), (85.1, 23.0), (81.9, 23.0), (81.9, 25.3)))):
    for r, q in zip((rn, rf, rp, rg), pos):
        put(r, q[0], q[1], 0, "B")
put("U25", 78.0, 19.9, 0, "B")
put("C132", 73.4, 19.9, 90, "B")
put("U26", 76.5, 26.0, 0, "B")
put("C133", 76.5, 23.6, 0, "B")
# output filters beside J11 pins 1/3/4, 1.6 mm pitch
for i, (r, c) in enumerate((("R128", "C129"), ("R129", "C130"), ("R130", "C131"))):
    put(r, 48.6 + 1.6 * i, 23.6, 90)
    put(c, 48.6 + 1.6 * i, 25.6, 90)
put("PEC1", 51.0, 17.6, 0)
put("J14", 66.6, 17.5, 90, center=True)
put("U27", 62.0, 21.5, 0, "B")
put("C136", 62.3, 24.1, 0, "B")
put("C135", 65.4, 21.5, 90, "B")
put("C134", 62.0, 18.5, 0, "B")

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
for ref in sorted(touched):
    moved_nets.update(short(p.GetNetname()) for p in b.fp(ref).Pads())
moved_nets -= PLANES
moved_nets.discard("")
new_pads = [CL.pad_poly(p) + (p.GetNetname(),) for r in sorted(touched) for p in b.fp(r).Pads()]


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


# ---- 4. plane zones --------------------------------------------------------------------------------
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

b.save("v5 step 5: card-area placement revision 2 (primary isolators south, U22 east, wider J11 column)")

# The fill made in this session does not see the moved vias (one SDATA1 via of the ADC group stayed inside
# the GND pours on In1 and In4): fill once more on the board as it is read from the file.
import board_common as bc  # noqa: E402
B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
