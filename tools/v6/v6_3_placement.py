#!/usr/bin/env python3
"""v6 step 3 (run once, kipy): card terminals, CTRL headers, the moved current-sense groups, the new small parts.

  tools/p2k/bin/kipy tools/v6/v6_3_placement.py [--dry]

Decisions (planning session, "Fable 2026-11-23", option A of the step-3 question):
  - REDCUBE terminals stay. Card envelope: nothing taller than 4 mm within 18 mm of a wall inside the card spans;
    terminal and header bodies may start 20 mm from the wall, terminal screw centres >= 22 mm from the wall.
  - Primary: AFE leg 1 pair beside the bulk caps C10 / C7 (PGND west at C10.1, DC+ east at C7.2); AFE leg 2 pair
    about 24 mm from the wall; DAB primary pair at about 25 mm. Headers beside each pair on the DC- side.
  - ISO: pairs at about 24 mm from the wall (just clear of the isolators U19 / U21 / U20 on the bottom side); the
    ISO DC bus leaves the old band for the freed strip in step 4, the wire links BUSP / BUSN are removed.
  - The two current-sense groups move to their choke-lead terminals: R48 / U5 and parts to FILTER_OUT1, R91 / U4
    and parts to J9, each turned by 90 degrees as a rigid group. INU_OUT2 leaves the passage north of J11.
  - Lug circle (8 mm, on the 7 mm terminal top) >= 2.5 mm in plan view from the courtyard of every part taller than
    5 mm (headers, other terminals, THT parts) and from other lugs; flat pads and parts under 2 mm tall below the lug
    do not count (planning session 2026-11-23). DC+ / DC- pad centres >= 10.5 mm apart.

Positions are of the terminal / header pad centroid (IPC frame, mm, Y up). The script refuses to save if a
courtyard overlaps another one on the same side (THT counts on both sides) or leaves the board.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P, load_fp  # noqa: E402

DRY = "--dry" in sys.argv
WALL_P, WALL_I = -83.05, 71.75      # board edges along the heatsink walls (IPC y)
CARD_X = (15.2, 117.3)              # x span of the three cards on each wall
LUG_R = 4.0

# ref: (x, y, rotation, side) of the pad centroid; header rotation 90 = rows along x
PLACE = {
    # ---- primary wall (y -83.05)
    # AFE leg 1: the bulk caps C10 / C7 (tall discs) fill the band in the card span, so the pair stands west of
    # them in the area the AFE sense group left; header north of the pair between the arcs of C79 and C11
    "J31": (13.5, -60.3, 0, "F"), "J32": (3.0, -60.3, 0, "F"), "J21": (4.0, -50.5, 90, "F"),
    # AFE leg 2: header west (beside C7), DC- next, DC+ east (clear of C12's arc)
    "J22": (53.75, -59.5, 90, "F"), "J34": (66.9, -59.5, 0, "F"), "J33": (77.4, -59.5, 0, "F"),
    # DAB primary: header west, DC-, DC+
    "J23": (90.55, -58.8, 90, "F"), "J36": (103.7, -58.8, 0, "F"), "J35": (114.2, -58.8, 0, "F"),
    # ---- ISO wall (y 71.75). Inverter leg B: DC+ lug 5 mm from J11 (CTRL); header vertical west of the pair
    "J24": (13.9, 44.8, 0, "F"), "J38": (23.5, 48.0, 0, "F"), "J37": (34.0, 48.0, 0, "F"),
    # inverter leg A and DAB secondary (under the control card's reach, which stands 5.3 mm up with its outline to
    # y 46.36): DC pigtail holes below the card's own DC terminals (card x 29 -> card centre + 12.5), 10.75 / 15.75 mm
    # from the wall; headers horizontal between the control card edge and the 18 mm line
    "J25": (62.5, 50.3, 90, "F"), "J39": (74.45, 58.5, 0, "F"), "J40": (82.95, 58.5, 0, "F"),
    "J26": (94.7, 50.3, 90, "F"), "J41": (104.6, 58.5, 0, "F"), "J42": (113.1, 58.5, 0, "F"),
}
# Accepted findings (planning session to confirm, STATUS.md): ref -> reason. A finding of an accepted ref is logged,
# it does not stop the save.
ACCEPT = {
    "J25": "header body 18.65 mm from the wall: between the control card edge and the 18 mm line (Fable 2026-11-23)",
    "J26": "header body 18.65 mm from the wall: between the control card edge and the 18 mm line (Fable 2026-11-23)",
}
# rigid groups: refs, rotation (deg, counter-clockwise in the IPC frame) about the anchor part, anchor target.
# The shunts carry the choke current: each goes beside its choke-lead terminal, the rest of its group behind it.
GROUPS = {
    "AFE sense": (("R48", "U5", "D8", "R59", "R57", "R58", "C52", "C53", "C91", "C71", "C73"),
                  180, "R48", (-36.0, -62.4)),
    "INV sense": (("R91", "U4", "D9", "R94", "R92", "R93", "C51", "C54", "C90", "C55", "C78", "C37", "R50"),
                  180, "R91", (-83.5, 48.3)),
}
# small parts: spiral search for a free place near a target (x, y, rotation, side)
AUTO = {
    # header capacitors on the wall side of their header (parts under 4 mm may stand there)
    "C148": (2.0, -46.0, 0, "F"), "C149": (6.0, -46.0, 0, "F"),
    "C150": (51.0, -64.3, 0, "F"), "C151": (56.5, -64.3, 0, "F"),
    "C152": (88.0, -63.8, 0, "F"), "C153": (93.0, -63.8, 0, "F"),
    "C154": (9.0, 42.0, 90, "F"), "C155": (9.0, 46.5, 90, "F"),
    "C156": (60.0, 55.5, 0, "F"), "C157": (65.0, 55.5, 0, "F"),
    "C158": (92.5, 55.5, 0, "F"), "C159": (97.5, 55.5, 0, "F"),
    # U5 side 2: MDATA resistor and VCC decoupling beside U5 (they left the rigid group: no room at the board edge)
    "R55": (-28.0, -76.0, 0, "B"), "C64": (-28.0, -78.5, 0, "B"),
    "U29": (-24.0, -72.0, 90, "F"), "C160": (-21.0, -66.0, 0, "B"), "C161": (-27.0, -66.0, 0, "B"),
    "U30": (-98.0, 56.0, 90, "F"), "C162": (-101.0, 50.0, 0, "B"), "C163": (-95.0, 50.0, 0, "B"),
    "D17": (102.0, 39.0, 0, "F"), "R257": (100.5, 40.5, 0, "F"),
    "INU_OUT2": (-56.0, 62.0, 0, "F"),
}

b = Board(6004)
B = b.b
if not DRY and abs(T(b.fp("J31").GetPosition().x) - PLACE["J31"][0]) < 5:
    raise SystemExit("v6 step 3 already applied (J31 is placed)")


def pads_c(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps)


def set_side(fp, side):
    if (side == "B") != fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)


def put(fp, x, y, rot, side):
    """Place so that the pad centroid lands on (x, y)."""
    set_side(fp, side)
    fp.SetOrientationDegrees(rot)
    cx, cy = pads_c(fp)
    p = fp.GetPosition()
    fp.SetPosition(P(T(p.x) + x - cx, -T(p.y) + y - cy))


def tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def poly(fp):
    """Courtyard outline (IPC frame) of the footprint's side; the bounding box when it has none."""
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if c.OutlineCount() == 0:
        x0, y0, x1, y1 = court(fp)
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    o = c.Outline(0)
    return [(T(o.CPoint(i).x), -T(o.CPoint(i).y)) for i in range(o.PointCount())]


def inside(px, py, pts):
    n, res = len(pts), False
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            res = not res
    return res


def seg_d(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def pt_poly(px, py, pts):
    if inside(px, py, pts):
        return 0.0
    return min(seg_d(px, py, *pts[i], *pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < -1e-9 and o(c, d, a) * o(c, d, b) < -1e-9


def poly_overlap(pa, pb):
    if any(cross(pa[i], pa[(i + 1) % len(pa)], pb[j], pb[(j + 1) % len(pb)]) for i in range(len(pa)) for j in range(len(pb))):
        return True
    ca = (sum(p[0] for p in pa) / len(pa), sum(p[1] for p in pa) / len(pa))
    cb = (sum(p[0] for p in pb) / len(pb), sum(p[1] for p in pb) / len(pb))
    return inside(*ca, pb) or inside(*cb, pa)


def court(fp):
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if c.OutlineCount() == 0:
        bb = fp.GetBoundingBox(False)
        return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())
    bb = c.BBox()
    return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())


def sides(fp):
    return {"F", "B"} if tht(fp) else {"B" if fp.IsFlipped() else "F"}


EDGE = B.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = T(EDGE.GetLeft()), -T(EDGE.GetBottom()), T(EDGE.GetRight()), -T(EDGE.GetTop())


def conflicts(fp, others):
    a = court(fp)
    if a[0] < EX0 + 0.5 or a[2] > EX1 - 0.5 or a[1] < EY0 + 0.5 or a[3] > EY1 - 0.5:
        return ["board edge"]
    out = []
    for o in others:
        if o.GetReference() == fp.GetReference() or not (sides(fp) & sides(o)):
            continue
        g = GROUP_OF.get(fp.GetReference())
        if g and GROUP_OF.get(o.GetReference()) == g:
            continue      # parts of one group keep their relative places (Proteus placement)
        c = court(o)
        if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3] and poly_overlap(poly(fp), poly(o)):
            out.append(o.GetReference())
    return out


def staged(fp):
    return -T(fp.GetPosition().y) < -88.0       # parts of v6 step 1 still in the staging area


for ref in ("BUSP1", "BUSP2", "BUSN1", "BUSN2"):      # v6: removed from the schematic (V6_PLAN section 5)
    fp = b.fp(ref)
    b.log.append(f"{ref} ({next(iter(fp.Pads())).GetNetname()}) at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f}) deleted")
    B.Delete(fp)

PIGTAILS = ("J39", "J40", "J41", "J42")
for ref in PIGTAILS:                       # REDCUBE of step 1 -> pigtail holes (schematic footprint changed)
    old = b.fp(ref)
    c = b.comps[ref]
    if str(old.GetFPID().GetLibItemName()) == c["footprint"].split(":")[1]:
        continue
    new = load_fp(c["footprint"])
    new.SetReference(ref)
    new.SetValue(old.GetValue())
    for ftype in (pcbnew.FIELD_T_DATASHEET, pcbnew.FIELD_T_DESCRIPTION):
        new.GetField(ftype).SetText(old.GetField(ftype).GetText())
    new.SetPath(old.GetPath())
    new.SetPosition(old.GetPosition())
    net = next(iter(old.Pads())).GetNetname()
    B.Delete(old)
    B.Add(new)
    for p in new.Pads():
        p.SetNet(b.net(net))
    b.log.append(f"{ref}: footprint {c['footprint']} (pigtail holes) instead of the REDCUBE, net {net}")

moved = set()
for ref, (x, y, rot, side) in PLACE.items():
    put(b.fp(ref), x, y, rot, side)
    moved.add(ref)
    b.log.append(f"{ref} pads centred at ({x:.2f}, {y:.2f}), rotation {rot}, side {side}")

GROUP_OF = {}
for name, (refs, rot, anchor, (nx, ny)) in GROUPS.items():
    fps = [b.fp(r) for r in refs]
    pts = [pads_c(f) for f in fps]
    ox, oy = pts[refs.index(anchor)]
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for f, (px, py) in zip(fps, pts):
        dx, dy = px - ox, py - oy
        x, y = nx + dx * c - dy * s_, ny + dx * s_ + dy * c
        put(f, x, y, (f.GetOrientationDegrees() + rot) % 360, "B" if f.IsFlipped() else "F")
        moved.add(f.GetReference())
        GROUP_OF[f.GetReference()] = name
    b.log.append(f"group {name}: {len(fps)} parts turned by {rot} degrees about {anchor}, {anchor} -> ({nx}, {ny}): "
                 + " ".join(f"{p.GetNumber()}[{p.GetNetname().split('/')[-1]}]@({T(p.GetPosition().x):.1f}, {-T(p.GetPosition().y):.1f})"
                            for p in b.fp(anchor).Pads()))

allfp = list(B.GetFootprints())
for ref, (x, y, rot, side) in AUTO.items():
    fp = b.fp(ref)
    others = [o for o in allfp if o.GetReference() != ref and not (staged(o) and o.GetReference() not in moved)]
    done = False
    for r in [0.0] + [0.5 * k for k in range(1, 41)]:
        n = max(1, int(2 * math.pi * r / 0.5))
        for k in range(n):
            a = 2 * math.pi * k / n
            put(fp, x + r * math.cos(a), y + r * math.sin(a), rot, side)
            if not conflicts(fp, others):
                done = True
                break
        if done:
            break
    moved.add(ref)
    cx, cy = pads_c(fp)
    b.log.append(f"{ref} near ({x}, {y}) side {side}: at ({cx:.2f}, {cy:.2f})" + ("" if done else " NO FREE PLACE"))

# ---- silkscreen at the pigtail holes: polarity and card name
def silk(text, x, y, size=1.2):
    t = pcbnew.PCB_TEXT(B)
    t.SetText(text)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(P(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(0.18))
    B.Add(t)


for plus, minus, name in (("J39", "J40", "INV A"), ("J41", "J42", "DAB SEC")):
    (px, py), (mx, my) = pads_c(b.fp(plus)), pads_c(b.fp(minus))
    silk("+", px, py - 6.2, 1.6)
    silk("-", mx, my - 6.2, 1.6)
    silk(name, (px + mx) / 2, py + 6.8)
    b.log.append(f"silkscreen + / - / {name} at the pigtail holes {plus} / {minus}")

# ---- copper: tracks and vias of other nets under the new pads, and the copper the moved groups left behind
def pad_boxes(fp):
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        yield p.GetNetname(), T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop()), p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, p


def seg_box_d(t, x0, y0, x1, y1):
    """Distance from a track centre line (or via centre) to a box, minus half the track width."""
    a, c = t.GetStart(), t.GetEnd()
    ax, ay, cx, cy = T(a.x), -T(a.y), T(c.x), -T(c.y)
    n = max(1, int(math.hypot(cx - ax, cy - ay) / 0.1))
    best = min(math.hypot(max(x0 - (ax + (cx - ax) * k / n), 0, ax + (cx - ax) * k / n - x1),
                          max(y0 - (ay + (cy - ay) * k / n), 0, ay + (cy - ay) * k / n - y1)) for k in range(n + 1))
    w = T(t.GetWidth(pcbnew.F_Cu)) if t.GetClass() == "PCB_VIA" else T(t.GetWidth())
    return best - w / 2


boxes = [(ref, bx) for ref in moved for bx in pad_boxes(b.fp(ref))]
hit = {}
for t in list(B.GetTracks()):
    lay = t.GetLayer()
    for ref, (net, x0, y0, x1, y1, pth, pad) in boxes:
        if t.GetNetname() == net:
            continue
        if not (pth or t.GetClass() == "PCB_VIA" or pad.IsOnLayer(lay)):
            continue
        if seg_box_d(t, x0, y0, x1, y1) < 0.25:
            hit[t.m_Uuid.AsString()] = (t, ref)
            break
for t, ref in hit.values():
    b.log.append(f"{'via' if t.GetClass() == 'PCB_VIA' else 'track'} [{t.GetNetname()}] under {ref} deleted")
    B.Delete(t)
# the private nets of the moved groups: every track and via of them goes (they are re-routed at the new place)
private = set()
for name, (refs, *_rest) in GROUPS.items():
    for r in refs:
        for p in b.fp(r).Pads():
            n = p.GetNetname()
            if n and all(q.GetParentFootprint().GetReference() in refs for q in B.GetPads() if q.GetNetname() == n):
                private.add(n)
gone = 0
for t in list(B.GetTracks()):
    if t.GetNetname() in private:
        B.Delete(t)
        gone += 1
b.log.append(f"{gone} tracks / vias of the moved groups' own nets deleted: {' '.join(sorted(n.split('/')[-1] for n in private))}")

# ---- checks
err = []
allfp = list(B.GetFootprints())
for ref in sorted(moved):
    fp = b.fp(ref)
    c = conflicts(fp, [o for o in allfp if not staged(o)])
    if c:
        err.append(f"{ref}: courtyard overlaps {', '.join(sorted(set(c)))}")
    x0, y0, x1, y1 = court(fp)
    for wall, sgn in ((WALL_P, 1), (WALL_I, -1)):
        d = min(abs(y0 - wall), abs(y1 - wall))
        if CARD_X[0] < (x0 + x1) / 2 < CARD_X[1] and d + 0.3 < 20.0 and ref in PLACE and ref not in PIGTAILS:
            err.append(f"{ref}: body {d + 0.3:.2f} mm from the wall (>= 20; courtyard margin 0.3)")
# lug circles (8 mm, on the 7 mm terminal top): 2.5 mm in plan view from the courtyards of tall parts (THT parts,
# taken as taller than 5 mm) and from other lugs; flat SMD parts below the lug do not count
TERMS = [r for r in PLACE if r.startswith(("J3", "J4")) and r not in PIGTAILS]
for ref in TERMS:
    fp = b.fp(ref)
    cx, cy = pads_c(fp)
    net = next(iter(fp.Pads())).GetNetname()
    wall_d = min(abs(cy - WALL_P), abs(cy - WALL_I))
    if wall_d < 22.0:
        err.append(f"{ref}: screw centre {wall_d:.1f} mm from the wall (>= 22)")
    worst = (99.0, "")
    for o in allfp:
        oref = o.GetReference()
        if staged(o) or oref == ref or not tht(o):
            continue
        if oref in TERMS:
            ox, oy = pads_c(o)
            d = math.hypot(ox - cx, oy - cy) - 2 * LUG_R
            what = f"{oref} lug"
        else:
            d = pt_poly(cx, cy, poly(o)) - LUG_R
            what = f"{oref} courtyard"
        if d < worst[0]:
            worst = (d, what)
    b.log.append(f"{ref} [{net}]: lug circle {worst[0]:.2f} mm from {worst[1]}; screw {wall_d:.1f} mm from the wall")
    if worst[0] < 2.5:
        err.append(f"{ref}: lug circle {worst[0]:.2f} mm from {worst[1]} (>= 2.5)")

acc = [e for e in err if e.split(":")[0] in ACCEPT]
err = [e for e in err if e not in acc]
for e in acc:
    b.log.append("ACCEPTED " + e + " -- " + ACCEPT[e.split(":")[0]])
for e in err:
    b.log.append("CHECK " + e)
if DRY or err:
    print("\n".join(b.log))
    raise SystemExit(f"{'dry run' if DRY else 'NOT SAVED'}: {len(err)} findings")
b.save("v6 step 3: terminals, headers, sense groups placed")
