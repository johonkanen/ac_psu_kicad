#!/usr/bin/env python3
"""v6 step 5c (run once, kipy, after v6_5_inductors.py / v6_5b_orphans.py): J5S, the AFE leg 1 SW landing.

  tools/p2k/bin/kipy tools/v6/v6_5c_j5s.py      (zones are refilled with kicad-cli afterwards)

No legal M4 place north of the bus band beside J21 (5 mm between the band and the C79 / C11 cans). User
2026-11-27: a soldered pigtail hole (6 mm pad, like FILTER_IN1) between J32 and the wall. It sits under the AFE
choke's rim, where the wire needs about 8 mm (it is soldered in and bends out towards the wall); placed west enough
(about x -1.5) that the PGND band on B / In2 keeps feeding J32 at full width east of it. J5S joins the J5 lead hole
by 8 mm copper along the wall on F.Cu and In1.Cu, 2.5 mm from everything else (net SW_AFE_1).
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


b = Board(6013)
B = b.b
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



if b.fp("J5S") is not None:
    raise SystemExit("v6 step 5c already applied (J5S is on the board)")
c = b.comps["J5S"]
fp = load_fp(c["footprint"])
fp.SetReference("J5S")
fp.SetValue(c["value"])
for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
    fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
B.Add(fp)
for p in fp.Pads():
    p.SetNet(b.net(b.pin_net[("J5S", "1")]))
    p.SetLocalClearance(F(HV))
WIRE_H = 8.0      # soldered SW wire bending out under the choke rim towards the wall
# westmost legal spot, low against the wall-edge rule (keeps J32's PGND feed east of it)
res = None
for x in [-4.0 + 0.5 * i for i in range(21)]:
    for y in (-77.5, -77.0, -76.5, -76.0):
        move_to(fp, x, y)
        if legal(fp, WIRE_H) is None:
            res = (x, y)
            break
    if res:
        break
if res is None:
    raise SystemExit("J5S: no legal place between x -4 and 6")
b.log.append(f"J5S (pigtail) at ({res[0]:.2f}, {res[1]:.2f})")
j5 = pads_c(b.fp("J5"))
for p in b.fp("J5").Pads():            # the lead hole joins the switch node (was unconnected since step 5)
    p.SetNet(b.net(b.pin_net[("J5", "1")]))
    p.SetLocalClearance(F(HV))
yc = max((j5[1] + res[1]) / 2, -83.05 + 2.5 + 4.0)
band = [(j5[0] - 2.5, yc - 4.0), (res[0] + 3.0, yc - 4.0), (res[0] + 3.0, yc + 4.0), (j5[0] - 2.5, yc + 4.0)]
for layer in ("F.Cu", "In1.Cu"):
    b.zone(layer, band, "SW_AFE_1", f"v6 SW_AFE_1 {layer}", 40, clearance=HV)
pcbnew.SaveBoard(B.GetFileName(), B)
print("\n".join(["== v6 step 5c: J5S pigtail, SW_AFE_1 link to J5"] + ["  " + x for x in b.log]))
