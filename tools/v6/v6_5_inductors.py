#!/usr/bin/env python3
"""v6 step 5 (run once, kipy): inductor leads in plain holes, SW landings outside the inductor profiles.

  tools/p2k/bin/kipy tools/v6/v6_5_inductors.py      (zones are refilled with kicad-cli afterwards)

V6_PLAN.md sections 14 / 15 with the planning session's decisions of 2026-11-26 (round profile):
  - AFE choke and inverter inductor: upright toroids, R 26.6 mm, 27.9 mm thick across the wall, centred between their
    leads; AFE centre x -17 (standoff s = 5 mm on a spacer), inverter centre x -72 (s = 5 mm as well: J7S beside H1 needs it, planning session item 5). Under the rim at distance
    d along the wall the free height is s + R - sqrt(R^2 - d^2) (profile in tools/v6/check_layout_v6.py).
  - J5, J7, J9, FILTER_OUT1 become plain soldered holes (2.3 mm, 5 mm pad), positions unchanged.
  - J7S (M4, net SW_INV_B) takes the inverter leg B SW wire outside the inverter profile, joined to the J7 hole by
    copper on F.Cu / In1.Cu / In2.Cu along the wall (5.15 mm between the board edge rule and U30 on three layers).
    U30 moves 3 mm south so that its pins keep 2.5 mm to that copper.
  - J10 (M4, INU_FILTER_INPUT, inverter leg A SW landing) and FILTER_IN1 (FILTER_INPUT, AFE leg 2 SW landing; a
    soldered pigtail hole now: no legal M4 place outside the AFE profile in the filter area) leave the profiles, to the nearest legal place towards CM3 pin 2 / CM1 pin 1 inside their F.Cu pours; a second
    layer (In1.Cu, 8 mm, 2.5 mm clearance) joins each to its choke pin.
  - J5's SW landing (J5S) is not placed yet (no legal place found beside J21; question to the planning session).
All new and changed high-voltage pads carry 2.5 mm local clearance; new zones 2.5 mm.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P, F, load_fp  # noqa: E402

HV = 2.5
R, HALF, TOL = 26.6, 27.9 / 2, 1.0
CHOKES = {"AFE": (-17.0, -63.85, 5.0), "INV": (-72.0, 57.0, 5.0)}     # centre x, centre y (between leads), standoff (both 5 mm: J7S needs it beside H1)
HEIGHT = {"Wuerth_REDCUBE-THR_74650074_M4_PTH": 11.0,                # M4 terminal with lug and screw
          "WirePigtail_D6.0mm_Drill3.0mm": 99.0}                     # a wire rises from it: wholly outside the profile

b = Board(6011)
B = b.b
if b.fp("J7S") is not None:
    raise SystemExit("v6 step 5 already applied (J7S is on the board)")
# J7S is new in the schematic: add it from the netlist (as Board.add_part does for two-pad parts)
c = b.comps["J7S"]
_fp = load_fp(c["footprint"])
_fp.SetReference("J7S")
_fp.SetValue(c["value"])
for _fname, _ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
    _fp.GetField(_ftype).SetText(c["fields"].get(_fname, ""))
_fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
B.Add(_fp)
for _p in _fp.Pads():
    _p.SetNet(b.net(b.pin_net[("J7S", "1")]))      # all pads of the terminal are pin 1 (paste-only pads have no number)


def pads_c(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps)


def move_to(fp, x, y):
    cx, cy = pads_c(fp)
    p = fp.GetPosition()
    fp.SetPosition(P(T(p.x) + x - cx, -T(p.y) + y - cy))


def box(fp):
    fp.BuildCourtyardCaches()
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
    return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())


def tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def profile_free(x0, x1, y0, y1):
    """Smallest free height under the two inductors for a top-side box (99 = not under an inductor)."""
    free = 99.0
    for xc, yc, s in CHOKES.values():
        if y1 <= yc - HALF + TOL or y0 >= yc + HALF - TOL:
            continue
        d = max(x0 - xc, xc - x1, 0.0)
        if d < R:
            free = min(free, s + R - math.sqrt(R * R - d * d))
    return free


SEGS = []      # existing tracks / vias: (net, x0, y0, x1, y1, half width), built once


def segs():
    if not SEGS:
        for t in B.GetTracks():
            a_, c_ = t.GetStart(), t.GetEnd()
            w = T(t.GetWidth(pcbnew.F_Cu)) if t.GetClass() == "PCB_VIA" else T(t.GetWidth())
            SEGS.append((t.GetNetname(), T(a_.x), -T(a_.y), T(c_.x), -T(c_.y), w / 2))
    return SEGS


def rect_seg(rx0, ry0, rx1, ry1, x0, y0, x1, y1):
    """Distance from a segment to an axis-parallel rectangle (square pads are not circles)."""
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
    best = 1e9
    for k in range(n + 1):
        x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
        best = min(best, math.hypot(max(rx0 - x, 0, x - rx1), max(ry0 - y, 0, y - ry1)))
    return best


def seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


def legal(fp, height, skip=()):
    a = box(fp)
    if profile_free(a[0], a[2], a[1], a[3]) < height:
        return "under an inductor"
    for o in B.GetFootprints():
        r = o.GetReference()
        if r == fp.GetReference() or r in skip or -T(o.GetPosition().y) < -88:
            continue
        if not (tht(fp) or tht(o)) and o.IsFlipped() != fp.IsFlipped():
            continue
        c = box(o)
        if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
            return f"overlaps {r}"
    e = B.GetBoardEdgesBoundingBox()
    for p in fp.Pads():
        if not p.GetNumber():
            continue          # paste-only pads of the M4 terminal
        q = p.GetPosition()
        qx, qy = T(q.x), -T(q.y)
        half = max(T(p.GetSize(pcbnew.F_Cu).x), T(p.GetSize(pcbnew.F_Cu).y)) / 2
        if qy + half > -T(e.GetTop()) - 2.5 or qy - half < -T(e.GetBottom()) + 2.5:
            return "within 2.5 mm of a wall edge"
        for o in B.GetFootprints():
            if o.GetReference() == fp.GetReference():
                continue
            for r in o.Pads():
                if not r.GetNetname() or r.GetNetname() == p.GetNetname():
                    continue
                bb = r.GetBoundingBox()
                d = math.hypot(max(T(bb.GetLeft()) - qx, 0, qx - T(bb.GetRight())),
                               max(-T(bb.GetBottom()) - qy, 0, qy + T(bb.GetTop()))) - half
                if d < HV:
                    return f"pad {d:.2f} mm from {o.GetReference()}.{r.GetNumber()}"
        for net, x0, y0, x1, y1, hw in segs():      # through-hole pads meet every layer's tracks
            if net == p.GetNetname() or min(x0, x1) > qx + 9 or max(x0, x1) < qx - 9 or min(y0, y1) > qy + 9 \
                    or max(y0, y1) < qy - 9:
                continue
            pb = p.GetBoundingBox()
            if rect_seg(T(pb.GetLeft()), -T(pb.GetBottom()), T(pb.GetRight()), -T(pb.GetTop()), x0, y0, x1, y1) - hw < HV:
                return f"track {net.split('/')[-1]}"
    return None


def search(fp, target, height, region, skip=()):
    """Nearest legal pad centroid to `target` inside the rectangle `region` (0.5 mm grid)."""
    tx, ty = target
    x0, y0, x1, y1 = region
    cands = sorted(((math.hypot(x - tx, y - ty), x, y) for x in [x0 + 0.5 * i for i in range(int((x1 - x0) / 0.5) + 1)]
                    for y in [y0 + 0.5 * j for j in range(int((y1 - y0) / 0.5) + 1)]))
    import collections
    why = collections.Counter()
    for _, x, y in cands:
        move_to(fp, x, y)
        w = legal(fp, height, skip)
        if w is None:
            return x, y
        why[w.split(" mm")[0][:28] if "pad" not in w else "pad near " + w.split("from ")[-1].split(".")[0]] += 1
    print(f"search {fp.GetReference()}: " + ", ".join(f"{k} {n}" for k, n in why.most_common(10)))
    return None


# ---- 1. inductor lead holes
for ref in ("J5", "J7", "J9", "FILTER_OUT1", "FILTER_IN1"):
    old = b.fp(ref)
    c = b.comps[ref]
    x, y = pads_c(old)
    new = load_fp(c["footprint"])
    new.SetReference(ref)
    new.SetValue(old.GetValue())
    for ftype in (pcbnew.FIELD_T_DATASHEET, pcbnew.FIELD_T_DESCRIPTION):
        new.GetField(ftype).SetText(old.GetField(ftype).GetText())
    new.SetPath(old.GetPath())
    B.Delete(old)
    B.Add(new)
    move_to(new, x, y)
    want = b.pin_net.get((ref, "1"))
    for p in new.Pads():
        if want:
            p.SetNet(b.net(want))
        p.SetLocalClearance(F(HV))
    b.log.append(f"{ref}: {c['footprint']} at ({x:.2f}, {y:.2f}), net {want or 'none'}")

# ---- 3. J10 and FILTER_IN1 out of the profiles, towards their choke pins
moves = {"J10": ((-70.34, 40.41), (-100.0, 24.0, -45.0, 56.0)),
         "FILTER_IN1": ((-64.50, -79.70), (-72.0, -80.5, -8.0, -15.0))}
for ref, (target, region) in moves.items():
    fp = b.fp(ref)
    old = pads_c(fp)
    res = search(fp, target, HEIGHT.get(str(fp.GetFPID().GetLibItemName()), 11.0), region)
    if res is None:
        raise SystemExit(f"{ref}: no legal place found in {region}")
    for p in fp.Pads():
        p.SetLocalClearance(F(HV))
    b.log.append(f"{ref} ({old[0]:.2f}, {old[1]:.2f}) -> ({res[0]:.2f}, {res[1]:.2f}), "
                 f"{math.hypot(res[0] - target[0], res[1] - target[1]):.1f} mm from its choke pin")

# ---- 2. U30 3 mm south (its pins keep 2.5 mm to the SW_INV_B copper along the wall)
u30 = b.fp("U30")
ux, uy = pads_c(u30)
move_to(u30, ux, uy - 3.0)
why = legal(u30, 0.0)
b.log.append(f"U30 ({ux:.2f}, {uy:.2f}) -> ({ux:.2f}, {uy - 3.0:.2f}){'' if why is None else ' CHECK ' + why}")

# ---- 4. J7S beside the wall, east of the inverter profile
j7s = b.fp("J7S")
J7S = (-47.0, 64.6)
move_to(j7s, *J7S)
for p in j7s.Pads():
    p.SetLocalClearance(F(HV))
why = legal(j7s, HEIGHT["Wuerth_REDCUBE-THR_74650074_M4_PTH"])
if why:
    raise SystemExit(f"J7S at {J7S}: {why}")
b.log.append(f"J7S at {J7S}")


# ---- 5. copper
def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


j7 = pads_c(b.fp("J7"))
band = rect(j7[0] - 2.5, 64.1, J7S[0] + 5.5, 69.25)
for layer in ("F.Cu", "In1.Cu", "In2.Cu"):
    b.zone(layer, band, "SW_INV_B", f"v6 SW_INV_B {layer}", 40, clearance=HV)
def union_poly(*rs):
    sp = pcbnew.SHAPE_POLY_SET()
    for x0, y0, x1, y1 in rs:
        ch = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in rect(x0, y0, x1, y1):
            ch.Append(F(x), F(-y))
        ch.SetClosed(True)
        sp.AddOutline(ch)
    sp.Simplify()
    o = sp.Outline(0)
    return [(T(o.CPoint(i).x), -T(o.CPoint(i).y)) for i in range(o.PointCount())]


# links J10 -> CM3 pin 2 and FILTER_IN1 -> CM1 pin 1: an L of 8 mm wide copper (along x at the choke pin, then along
# y to the terminal) on In1.Cu and In2.Cu, 2.5 mm clearance, kept 2.5 mm off the wall-side board edges
for ref, (target, _) in moves.items():
    x, y = pads_c(b.fp(ref))
    tx, ty = target
    lo, hi = -83.05 + 2.5, 71.75 - 2.5
    pts = union_poly((min(x, tx) - 4.0, max(ty - 4.0, lo), max(x, tx) + 4.0, min(ty + 4.0, hi)),
                     (x - 4.0, max(min(y, ty) - 4.0, lo), x + 4.0, min(max(y, ty) + 4.0, hi)))
    net = b.pin_net[(ref, "1")]
    for layer in ("In1.Cu", "In2.Cu"):
        b.zone(layer, pts, net, f"v6 {ref} link {layer}", 40, clearance=HV)
# tracks / vias of other nets closer than 2.5 mm to the changed / new high-voltage pads are deleted (pass-1 routes in
# blocks A / B, which are routed again from clean in the block routing of section 16)
hvpads = [p for r in ("J5", "J7", "J9", "FILTER_OUT1", "FILTER_IN1", "J10", "J7S") for p in b.fp(r).Pads() if p.GetNumber()]
gone = 0
for t in list(B.GetTracks()):
    a_, c_ = t.GetStart(), t.GetEnd()
    w = T(t.GetWidth(pcbnew.F_Cu)) if t.GetClass() == "PCB_VIA" else T(t.GetWidth())
    for p in hvpads:
        if p.GetNetname() == t.GetNetname():
            continue
        pb = p.GetBoundingBox()
        if rect_seg(T(pb.GetLeft()), -T(pb.GetBottom()), T(pb.GetRight()), -T(pb.GetTop()),
                    T(a_.x), -T(a_.y), T(c_.x), -T(c_.y)) - w / 2 < HV:
            b.log.append(f"{'via' if t.GetClass() == 'PCB_VIA' else 'track'} [{t.GetNetname().split('/')[-1]}] near "
                         f"{p.GetParentFootprint().GetReference()} deleted")
            B.Delete(t)
            gone += 1
            break
b.log.append(f"{gone} tracks / vias within 2.5 mm of the high-voltage pads deleted")
pcbnew.SaveBoard(B.GetFileName(), B)
print("\n".join(["== v6 step 5: inductor holes, SW landings outside the inductor profiles"] + ["  " + x for x in b.log]))
