#!/usr/bin/env python3
"""v5 step 9 (run once, kipy): placement of the aux flyback area (user 2026-11-18).

Geometry and positions: tools/v5/card_layout.py (AUX_AREAS, AUX_LINES, PLACE). The aux flyback (EEL19 T1,
controller U18 ICE5AR0680AG and 29 more parts) leaves the staging area:
  1. T1 between U8 and J3, across the 5 mm gap between the primary aux area PX and the ISO aux area IA;
     the ISO parts (D15, C116, R109) at T1's pins 9 / 10; the primary parts west of T1, most on the bottom
     side: U18 next to fly-lead hole 12, its small parts around it, D14 and C28 at T1's pins 1 / 2; the two
     10M chains and R98 on the top side in the free strip under the card. C28 and C41 (v4 parts) move: they
     stood in T1's slot. The high-voltage pads get their own clearance (card_layout.HV_PADS).
  2. tracks and vias that no longer fit are deleted (in the aux barrier strip, primary copper within 5 mm of
     IA or ISO copper within 5 mm of PX, under a new pad, stubs at the old places of C28 / C41);
  3. a barrier rule area along the P|I line of the aux area (no slot: T1 has 10.8 mm between its pad rows);
  4. every pour is cut back 5 mm from the other domain's aux area.
Routing is left open (lib/v5_copper.csv kind unrouted). Check: tools/v5/check_layout.py.
"""
import collections
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, P, load_fp  # noqa: E402
import board_common as bc  # noqa: E402
import card_layout as L  # noqa: E402
import check_layout as CL  # noqa: E402
import domains  # noqa: E402

b = Board(5009)
B = b.b
if -T(b.fp("T1").GetPosition().y) > CL.STAGING_Y:
    raise SystemExit("v5 step 9 already applied (T1 is placed)")
dom = domains.classify(bc.export_netlist()[1])
short = domains.short
REGION = (60.0, -62.0, 118.65, -2.0)      # where copper is examined
AUX = {k: v for k, v in L.PLACE.items() if v[0] in ("PX", "IA", "PX|IA")}


def xy(v):
    return T(v.x), -T(v.y)


def pad(ref, num):
    return xy(next(p for p in b.fp(ref).Pads() if p.GetNumber() == num).GetPosition())


old_pads = []     # pad shapes of the moved v4 parts at their old places (their stubs are deleted)


def put(ref, axis=None, pin=None, toward=None, rot=None):
    """Place ref at its card_layout position and side. rot given: that rotation. Otherwise the rotation with the
    pads along `axis` ('h' or 'v') that brings pad `pin` nearest to the point `toward`."""
    area, side, x, y, note = L.PLACE[ref]
    fp = b.fp(ref)
    if -T(fp.GetPosition().y) > CL.STAGING_Y:
        old_pads.extend(CL.pad_poly(p) + (p.GetNetname(),) for p in fp.Pads())
    fp.SetPosition(P(x, y))
    if (side == "B") != fp.IsFlipped():
        fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    if rot is None:
        best = None
        for r in (0, 90, 180, 270):
            fp.SetOrientationDegrees(r)
            ps = [xy(p.GetPosition()) for p in fp.Pads()]
            horizontal = max(q[0] for q in ps) - min(q[0] for q in ps) >= max(q[1] for q in ps) - min(q[1] for q in ps)
            if axis and horizontal != (axis == "h"):
                continue
            d = math.dist(pad(ref, pin), toward) if pin else 0.0
            if best is None or d < best[0] - 1e-6:
                best = (d, r)
        rot = best[1]
    fp.SetOrientationDegrees(rot)
    fp.Reference().SetVisible(True)
    b.log.append(f"{ref:5} {side} ({x:7.2f}, {y:7.2f}) rot {rot:3d}  {note[:80]}")


# ---- 1. placement -------------------------------------------------------------------------------
# T1's footprint changed after step 8 (fly-lead holes 4.8 mm apart, hole 12 = drain next to the body's middle):
# take the new one from the library
old = b.fp("T1")
c = b.comps["T1"]
new = load_fp(c["footprint"])
new.SetReference("T1")
new.SetValue(c["value"])
for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
    new.GetField(ftype).SetText(c["fields"].get(fname, ""))
new.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
new.SetSheetname(c["sheetname"])
new.SetSheetfile(c["sheetfile"])
new.SetPosition(old.GetPosition())
B.Delete(old)
B.Add(new)
new.thisown = False
for q in new.Pads():
    q.SetNet(b.net(b.pin_net[("T1", q.GetNumber())]))
b.log.append("T1: footprint taken again from the library (fly-lead holes 12 / 11, 4.8 mm apart)")
put("T1", rot=0)
for num, want in (("1", (81.15, -33.35)), ("2", (81.15, -36.85)), ("9", (93.65, -34.55)), ("10", (93.65, -31.85)),
                  ("12", (76.8, -44.1)), ("11", (76.8, -48.9))):
    if math.dist(pad("T1", num), want) > 0.02:
        raise SystemExit(f"T1 pin {num} at {pad('T1', num)}, expected {want}")
p1, p2, p9, p10, l11, l12 = (pad("T1", n) for n in ("1", "2", "9", "10", "11", "12"))
put("D15", "h", "A", p10)
put("C116", "v", "1", (93.0, -30.0))
put("R109", "v", "1", (90.3, -30.0))
put("U18", "v", "5", l12)                 # DRAIN pins 5-8 at the south end, at fly-lead hole 12
u = {n: pad("U18", str(n)) for n in range(1, 13)}
put("C113", "v", "1", u[11])
put("C114", "h", "1", u[11])
put("C147", "h", "1", u[1])
put("D14", "v", "A", p1)
put("C28", "h", "1", pad("D14", "C"))
put("C41", "h", "1", (72.2, -16.5))
put("R108", "h")
put("R102", "v", "1", u[2])
put("C146", "v", "1", u[3])
put("R101", "v", "2", u[2])
put("R144", "v", "1", u[1])
put("R140", "v", "1", u[3])
put("C145", "v", "1", pad("R140", "2"))
put("R139", "h", "1", u[3])
put("R105", "v", "1", u[4])
put("D12", "v", "A", l12)
put("D13", "h", "A", l11)
put("C111", "h", "1", l11)                # AUX_VIN pad west, at fly-lead hole 11
put("C68", "h", "2", l11)                 # v4 part, turned: DC+ pad east (was GND, 1.1 mm from hole 11)
put("C112", "h", "1", (60.0, -11.0))      # AUX_VIN pad west, GND pad towards R139
put("D11", "h", "C", u[11])
put("R100", "h", "2", pad("D11", "A"))
put("R98", "h", "1", (60.0, -12.3))       # DC+ pad west
for r in ("R136", "R137", "R138", "R141", "R142", "R143"):
    put(r, "h", "1", (60.0, L.PLACE[r][3]))      # both chains run west -> east from AUX_VIN
for (ref, num), c in L.HV_PADS.items():
    next(p for p in b.fp(ref).Pads() if p.GetNumber() == num).SetLocalClearance(F(c))
b.log.append("pad clearance of the high-voltage pads: " + ", ".join(f"{r}-{n} {c}" for (r, n), c in L.HV_PADS.items()))
left = [r for r in AUX if -T(b.fp(r).GetPosition().y) < CL.STAGING_Y]
if left:
    raise SystemExit("not placed: " + " ".join(left))

# ---- 2. tracks and vias that no longer fit -----------------------------------------------------
strip = CL.strips(L.AUX_LINES)
forbidden = {}
for d, keys in (("P", ("IA",)), ("I", ("PX",)), ("C", ("PX", "IA"))):
    g = pcbnew.SHAPE_POLY_SET()
    for k in keys:
        q = CL.sps(L.AUX_AREAS[k][1])
        q.Inflate(F(L.GAP - 0.001), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, F(0.005))
        g.Append(q)
    g.Simplify()
    forbidden[d] = g
new_pads = [CL.pad_poly(p) + (p.GetNetname(),) for r in AUX for p in b.fp(r).Pads()]
hv_pads = {c: [CL.pad_poly(p) + (p.GetNetname(),) for (r, n), cc in L.HV_PADS.items() if cc == c
               for p in b.fp(r).Pads() if p.GetNumber() == n] for c in (1.5, 2.0, 2.5)}


def hits(t, shp, pads, clr, other_net):
    via = t.GetClass() == "PCB_VIA"
    return any((via or t.GetLayer() in ls) and (not other_net or n != t.GetNetname()) and ps.Collide(shp, F(clr))
               for ps, ls, n in pads)


why = collections.Counter()
dead = []
for t in B.GetTracks():
    s, e = xy(t.GetStart()), xy(t.GetEnd())
    if not any(REGION[0] <= q[0] <= REGION[2] and REGION[1] <= q[1] <= REGION[3] for q in (s, e)):
        continue
    shp = t.GetEffectiveShape()
    d = dom.get(t.GetNetname())
    r = None
    if strip.Collide(shp, 0):
        r = "inside the aux barrier strip"
    elif d in forbidden and forbidden[d].Collide(shp, 0):
        r = f"{d} copper in or within 5 mm of the other domain's aux area"
    elif hits(t, shp, new_pads, 0.2, True):
        r = "under a pad of a placed part"
    elif hits(t, shp, hv_pads[2.5], 2.5, True) or hits(t, shp, hv_pads[2.0], 2.0, True) or hits(t, shp, hv_pads[1.5], 1.5, True):
        r = "within the clearance of a high-voltage pad"
    elif hits(t, shp, old_pads, 0.05, False):
        r = "stub at the old place of C28 / C41"
    if r:
        why[("via" if t.GetClass() == "PCB_VIA" else "track", r, short(t.GetNetname()))] += 1
        dead.append(t)
for t in dead:
    B.Delete(t)
tot = collections.Counter()
nets = collections.defaultdict(set)
for (kind, r, net), n in why.items():
    tot[(kind, r)] += n
    nets[r].add(net)
for (kind, r), n in sorted(tot.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    b.log.append(f"deleted {n:4} {kind:5} {r} ({', '.join(sorted(nets[r]))})")


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


# the small GND pour at C68's old GND pad lies between the new high-voltage pads: it goes with its via
for z in list(B.Zones()):
    if z.GetZoneName() == "Proteus F.Cu pour 17" and short(z.GetNetname()) == "GND":
        b.log.append("deleted zone Proteus F.Cu pour 17 [GND] F.Cu (C68's old GND pad; under the clamp and input parts now)")
        B.Delete(z)

# ---- 3. barrier rule area ----------------------------------------------------------------------------
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
    z.SetZoneName(f"v5 barrier strip aux {i + 1} (5 mm, reinforced)")
    B.Add(z)
    z.thisown = False
b.log.append(f"{strip.OutlineCount()} barrier rule area (no tracks, vias, pours; all copper layers) along: "
             + ", ".join(n for n, _, _ in L.AUX_LINES))

# ---- 4. pours: 5 mm back from the other domain's aux area ---------------------------
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

b.save("v5 step 9: aux flyback area placed (T1 across the P|I gap, controller and parts around it)")

# fill once more on the board as read from the file (a fill in the session of the change can miss moved items)
B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
