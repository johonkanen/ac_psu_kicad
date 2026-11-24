#!/usr/bin/env python3
"""v6 step 4d (run once, kipy): the sense-supply modules U29 / U30 go to the bottom side; AFE_OUT1 / INU_OUT2 deleted.

Decision "Fable 2026-11-24" (planning session): the inverter inductor is a toroid of about 55 mm diameter standing
upright over J7 / J9, the AFE chokes stand near J5 / FILTER_OUT1; the 10.2 mm Mornsun B0512S modules move to the
bottom side so they are clear of the inductors wherever those stand. The baseboard is on 15 mm standoffs; bottom parts
may be 10 mm tall (V5_LAYOUT_PLAN.md), the 10.2 mm of the module is an accepted exception. Each module stays within
about 25 mm of its sense group, its pins keep 2.5 mm to other-net pads (its output side floats on the shunt node),
its courtyard clears every bottom part and every through-hole part, and 4 mm around the mounting holes stay free.
The placement is searched outward from a target in 0.5 mm steps; the result is logged. U30's pins come up between
J9 and J10 and keep 2.5 mm to their pads and to their M4 lug circles (10 mm) on top.
User 2026-11-24: one AFE choke between J5 and FILTER_OUT1, one inverter inductor between J7 and J9; the SW wire of the
AFE leg 2 card lands on FILTER_IN1, that of the inverter leg A card on J10: AFE_OUT1 and INU_OUT2 are deleted here.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P  # noqa: E402

TARGET = {"U29": ((-24.0, -72.0), (-36.0, -62.4)), "U30": ((-59.0, 55.0), (-83.5, 48.3))}   # east of J9, between J9 and J10   # target, its shunt
b = Board(6010)
B = b.b
if all(b.fp(r).IsFlipped() for r in TARGET):
    raise SystemExit("v6 step 4d already applied")
# floating (line-potential) node groups: side 1 of each sense group and the shunt force nodes; a module pin keeps
# 2.5 mm to every pad of another group or of another high-voltage net, 0.2 mm (DRC) inside its own group
SIDE1 = {"U30": ("R91", "D9", "R94", "R92", "R93", "C51", "C54", "C90", "C55", "C78", "C163"),
         "U29": ("R48", "D8", "R59", "R57", "R58", "C52", "C53", "C91", "C71", "C73", "C161")}
IGNORE = set(os.environ.get("IGNORE", "").split(","))
LIMIT = float(os.environ.get("LIMIT", "27"))   # about 25 mm (planning); the J9 / J10 lug circles push U30 to 26.5
HV = {"DC+", "PGND", "ISODC+", "ISOPGND", "DAB_GROUND", "AFE_CHOKE1", "INU_CHOKE"}
GROUP = {}
for mod, refs in SIDE1.items():
    for r in refs:
        for p in b.fp(r).Pads():
            if p.GetNetname():
                GROUP[p.GetNetname()] = mod
    for p in b.fp({"U30": "U4", "U29": "U5"}[mod]).Pads():
        if p.GetNumber() in ("1", "2", "3", "4"):
            GROUP[p.GetNetname()] = mod


def needs_hv(a, c):
    if a == c:
        return False
    ga, gc = GROUP.get(a), GROUP.get(c)
    if ga and ga == gc:
        return False
    return bool(ga or gc or a in HV or c in HV or "LEMOUT" in a or "LEMOUT" in c
                or "INDUCTOR_OUTPUT" in a or "INDUCTOR_OUTPUT" in c)


HOLES = [(T(f.GetPosition().x), -T(f.GetPosition().y)) for f in B.GetFootprints() if f.GetReference().startswith("H")]


def pads_c(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps)


def box(fp):
    """Courtyard box (rebuilt: the cache is stale after a move), the body box when there is no courtyard."""
    fp.BuildCourtyardCaches()
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
    return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())


def tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def ok(fp):
    a = box(fp)
    for o in B.GetFootprints():
        if o.GetReference() == fp.GetReference() or -T(o.GetPosition().y) < -88 or o.GetReference() in IGNORE:
            continue
        if not (o.IsFlipped() or tht(o)):
            continue
        c = box(o)
        if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
            return f"overlaps {o.GetReference()}"
    for hx, hy in HOLES:
        if a[0] - 4 < hx < a[2] + 4 and a[1] - 4 < hy < a[3] + 4:
            return "mounting hole"
    for p in fp.Pads():
        q = p.GetPosition()
        for o in B.GetFootprints():
            if o.GetReference() == fp.GetReference():
                continue
            for r in o.Pads():
                if not r.GetNetname() or r.GetNetname() == p.GetNetname():
                    continue
                need = 2.5 if needs_hv(p.GetNetname(), r.GetNetname()) else 0.2
                bb = r.GetBoundingBox()
                d = math.hypot(max(T(bb.GetLeft()) - T(q.x), 0, T(q.x) - T(bb.GetRight())),
                               max(-T(bb.GetBottom()) + T(q.y), 0, -T(q.y) - T(bb.GetTop()))) - 0.8
                if d < need:
                    return f"pin {p.GetNumber()} {d:.2f} mm from {o.GetReference()}.{r.GetNumber()}"
    return None


# AFE_OUT1 and INU_OUT2 deleted (user 2026-11-24): the AFE leg 2 / inverter leg A SW wires land on FILTER_IN1 / J10
for ref in ("AFE_OUT1", "INU_OUT2"):
    fp = b.fp(ref)
    if fp is not None:
        b.log.append(f"{ref} at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f}) deleted")
        B.Delete(fp)

# M4 lug circles (about 10 mm) on top of the landing terminals beside U30: its pins come up between J9 and J10
LUGS = []
for ref in ("J7", "J9", "J10"):
    ps = [p.GetPosition() for p in b.fp(ref).Pads()]
    LUGS.append((ref, sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps), 5.0))


def lug_ok(fp):
    for p in fp.Pads():
        q = p.GetPosition()
        for ref, lx, ly, r in LUGS:
            if math.hypot(T(q.x) - lx, -T(q.y) - ly) - r - 0.8 < 2.5:
                return f"pin {p.GetNumber()} within 2.5 mm of the {ref} lug circle"
    return None


for ref, ((tx, ty), (sx, sy)) in TARGET.items():
    fp = b.fp(ref)
    old = pads_c(fp)
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    done = None
    for r in [0.0] + [0.5 * k for k in range(1, 50)]:
        n = max(1, int(2 * math.pi * r / 0.5))
        for k in range(n):
            for rot in (90, 0):
                a = 2 * math.pi * k / n
                x, y = tx + r * math.cos(a), ty + r * math.sin(a)
                fp.SetOrientationDegrees(rot)
                cx, cy = pads_c(fp)
                p0 = fp.GetPosition()
                fp.SetPosition(P(T(p0.x) + x - cx, -T(p0.y) + y - cy))
                if math.hypot(x - sx, y - sy) <= LIMIT and ok(fp) is None and lug_ok(fp) is None:
                    done = (x, y, rot)
                    break
            if done:
                break
        if done:
            break
    if not done and os.environ.get("SCAN") == ref:
        hits = []
        for xi in range(-115, -40):
            for yi in range(28, 71):
                for rot in (0, 90):
                    fp.SetOrientationDegrees(rot)
                    cx, cy = pads_c(fp)
                    p0 = fp.GetPosition()
                    fp.SetPosition(P(T(p0.x) + xi - cx, -T(p0.y) + yi - cy))
                    if ok(fp) is None:
                        hits.append((math.hypot(xi - sx, yi - sy), xi, yi, rot))
        print(sorted(hits)[:15])
    if not done and os.environ.get("WHY"):
        import collections
        why = collections.Counter()
        for r in [0.5 * k for k in range(0, 50, 4)]:
            for k in range(16):
                a = 2 * math.pi * k / 16
                x, y = tx + r * math.cos(a), ty + r * math.sin(a)
                cx, cy = pads_c(fp)
                p0 = fp.GetPosition()
                fp.SetPosition(P(T(p0.x) + x - cx, -T(p0.y) + y - cy))
                why[(ok(fp) or "ok").split(" mm")[0][:40]] += 1
        print(why.most_common(12))
    if not done:
        raise SystemExit(f"{ref}: no legal place on the bottom side within 25 mm of its shunt")
    x, y, rot = done
    b.log.append(f"{ref} top ({old[0]:.2f}, {old[1]:.2f}) -> bottom ({x:.2f}, {y:.2f}) rot {rot}, "
                 f"{math.hypot(x - sx, y - sy):.1f} mm from its shunt")
pcbnew.SaveBoard(B.GetFileName(), B)
print("\n".join(["== v6 step 4d: U29 / U30 on the bottom side"] + ["  " + x for x in b.log]))
