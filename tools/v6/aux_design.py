#!/usr/bin/env python3
"""Design of the aux flyback routes (V6_PLAN.md section 10): draws every piece on a copy of the board, gates it with
tools/v6/aux_lib.Ctx (explicit HV rule), and writes the pieces that passed to tools/v6/aux_routes_copper.csv, which
tools/v6/aux_routes.py replays onto the main board.

  tools/p2k/bin/kipy tools/v6/aux_design.py IN.kicad_pcb [OUT.kicad_pcb]

Not meant for the main chain: rerun only when the aux routes change (the helper redraws).
"""
import csv
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aux_lib as L  # noqa: E402
from aux_lib import F, T, P, xy  # noqa: E402

CSV = os.path.join(HERE, "aux_routes_copper.csv")
FC, BC, I1, I2, I3, I4 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu
LN = {FC: "F.Cu", BC: "B.Cu", I1: "In1.Cu", I2: "In2.Cu", I3: "In3.Cu", I4: "In4.Cu"}

b = pcbnew.LoadBoard(sys.argv[1])
OUT = sys.argv[2] if len(sys.argv) > 2 else None
OPS = []
FAIL = []

# foreign copper inside the areas: dangling remnants of runs to the v5 gate-card headers (PWM_TRANS2 / PWM_TRANS3 /
# PWM_G1 / 5V on In2, F.Cu, B.Cu) and the dangling GND branch on In1; replayed generically by aux_routes.py
FOREIGN = [("PWM_TRANS2", None), ("PWM_TRANS3", None), ("PWM_G1", None), ("5V", None), ("GND", "In1.Cu")]


def clip_foreign():
    import aux_routes as R
    for line in R.clip_foreign(b, FOREIGN):
        print("clip:", line)


def pad_bb(ref, num):
    p = L.pad_of(b, ref, num)
    bb = p.GetBoundingBox()
    return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())


cx = None


def track(net, layer, pts, w, tag="", area_tol=0.0, force=False, pg=False):
    """Polyline; all segments gated; committed only if every segment is clear. pg: pad-gap exception for the pads of
    the net at the two ends (Ctx.padgap)."""
    ov = cx.padgap(cx.pads_at(net, layer, [pts[0], pts[-1]]), layer) if pg else None
    segs = []
    for a, c in zip(pts, pts[1:]):
        if math.hypot(a[0] - c[0], a[1] - c[1]) < 1e-4:
            continue
        why = []
        t = cx.track_ok(net, layer, a, c, w, why=why, area_tol=area_tol, override=ov)
        if t is None and not force:
            FAIL.append(f"{tag or net} {LN[layer]} ({a[0]:.2f},{a[1]:.2f})-({c[0]:.2f},{c[1]:.2f}) w{w}: {'; '.join(why[:3])}")
            print("  BLOCKED", FAIL[-1])
            return False
        segs.append(t or cx.mktrack(net, layer, a, c, w))
    cx.commit(*segs)
    for t in segs:
        (x1, y1), (x2, y2) = xy(t.GetStart()), xy(t.GetEnd())
        OPS.append(dict(kind="track", net=net, layer=LN[layer], x1=f"{x1:.4f}", y1=f"{y1:.4f}", x2=f"{x2:.4f}", y2=f"{y2:.4f}",
                        w=f"{w:.3f}", tag=tag))
    return True


def via(net, x, y, tag="", force=False, pg=False):
    """pg: via in a pad of its net; the pad-gap exception of that pad holds on every layer it is on."""
    ov = None
    if pg:
        ov = {l: cx.padgap(cx.pads_at(net, l, [(x, y)]), l) for l in cx.layers}
    why = []
    v = cx.via_ok(net, x, y, why=why, override=ov)
    if v is None and not force:
        FAIL.append(f"{tag or net} via ({x:.2f},{y:.2f}): {'; '.join(why[:3])}")
        print("  BLOCKED", FAIL[-1])
        return False
    cx.commit(v or cx.mkvia(net, x, y))
    OPS.append(dict(kind="via", net=net, layer="", x1=f"{x:.4f}", y1=f"{y:.4f}", x2="", y2="", w=f"{L.VIA:.4f}", tag=tag))
    return True


def via_at_pad(ref, num, rmax=2.5, w=0.3, prefer=None, tag=""):
    """Nearest legal via + straight stub beside an SMD pad (not in the pad)."""
    p = L.pad_of(b, ref, num)
    net = p.GetNetname()
    x, y = xy(p.GetPosition())
    fp = p.GetParentFootprint()
    layer = BC if fp.IsFlipped() else FC
    s = p.GetSize(layer)
    smin, smax = min(T(s.x), T(s.y)), max(T(s.x), T(s.y))
    r = smin / 2 + L.VIA / 2 + 0.1
    ov = cx.padgap([(p.GetEffectiveShape(layer), net)], layer)
    best = None
    while r <= rmax and best is None:
        n = 32
        cands = []
        for k in range(n):
            a = 2 * math.pi * k / n
            vx, vy = x + r * math.cos(a), y + r * math.sin(a)
            score = 0 if prefer is None else math.hypot(vx - prefer[0], vy - prefer[1])
            cands.append((score, vx, vy))
        for _, vx, vy in sorted(cands):
            v = cx.via_ok(net, vx, vy)
            if v is None:
                continue
            if p.GetEffectiveShape(layer).Collide(v.GetEffectiveShape(layer), F(0.03)):
                continue
            t = cx.track_ok(net, layer, (x, y), (vx, vy), min(w, smin), override=ov)
            if t is None:
                continue
            best = (vx, vy)
            break
        r += 0.1
    if best is None:
        FAIL.append(f"{tag or net}: no via within {rmax} mm of {ref}-{num}")
        print("  BLOCKED", FAIL[-1])
        return None
    via(net, best[0], best[1], tag=tag or f"{ref}-{num}")
    track(net, layer, [(x, y), best], min(w, smin), tag=tag or f"{ref}-{num}", pg=True)
    return best


def grid_route(net, layer, a, c, w, box, tag=""):
    g = L.Grid(cx, layer, box)
    pts = g.route(g.build(net, w), a, c)
    if pts is None:
        FAIL.append(f"{tag or net} {LN[layer]}: no grid path ({a[0]:.2f},{a[1]:.2f}) -> ({c[0]:.2f},{c[1]:.2f})")
        print("  BLOCKED", FAIL[-1])
        return None
    pts = simplify(pts)
    return pts if track(net, layer, pts, w, tag=tag) else None


def simplify(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if len(out) >= 2:
            (x0, y0), (x1, y1) = out[-2], out[-1]
            if abs((x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0)) < 1e-6:
                out[-1] = p
                continue
        out.append(p)
    return out


def zone(net, layer, pts, name, prio, clr, minw=0.2, conn="full"):
    OPS.append(dict(kind="zone", net=net, layer=LN[layer], x1=name, y1=str(prio), x2=f"{clr:.3f}", y2=f"{minw:.3f}", w=conn,
                    tag=";".join(f"{x:.3f} {y:.3f}" for x, y in pts)))
    import aux_routes as R
    R.add_zone(b, OPS[-1])


def move(ref, x, y, rot, side):
    global cx
    r = dict(kind="move", net="", layer="", x1=f"{x:.4f}", y1=f"{y:.4f}", x2=f"{rot:.1f}", y2=side, w="", tag=ref)
    OPS.append(r)
    import aux_routes as R
    R.move(b, r)
    cx = L.Ctx(b)
    print(f"  moved {ref} to ({x}, {y}) rot {rot} side {side}: " + ", ".join(
        f"{p.GetNumber()} [{p.GetNetname()}] ({xy(p.GetPosition())[0]:.3f}, {xy(p.GetPosition())[1]:.3f})" for p in b.FindFootprintByReference(ref).Pads()))


def zone_clearance(name, old, new):
    r = dict(kind="zoneclr", net="", layer="", x1=name, y1=f"{old:.3f}", x2=f"{new:.3f}", y2="", w="", tag="")
    OPS.append(r)
    import aux_routes as R
    R.zone_clearance(b, r)


def pxy(ref, num):
    return L.pad_xy(b, ref, num)


# ------------------------------------------------------------------------------------------------------------------
clip_foreign()
import aux_routes as R  # noqa: E402
cx = L.Ctx(b)

exec(open(os.path.join(HERE, "aux_design_steps.py")).read())

print(f"\n{len(OPS)} pieces, {len(FAIL)} blocked")
for f in FAIL:
    print("  blocked:", f)
with open(CSV, "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=["kind", "net", "layer", "x1", "y1", "x2", "y2", "w", "tag"])
    wr.writeheader()
    for o in OPS:
        wr.writerow(o)
print("written", CSV)
if OUT:
    pcbnew.SaveBoard(OUT, b)
    print("saved", OUT)
