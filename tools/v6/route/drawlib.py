"""Drawing helpers of the v6 routing chain's scripted runs (kipy): end vias at pads, grid-router runs on one
layer with avoid / follow costs, straight pieces. Shared by 05_sdm.py and 06_west.py."""
import math
import os
import sys
import time

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import F, T, P, xy  # noqa: E402

IN1, IN2, IN3, IN4, B = pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu
SIG_W, GUARD_W = 0.2, 0.3
AVOID = ["J7", "J9", "INU_OUT2", "CM1", "CM2", "CM3", "FILTER_OUT1", "FILTER_IN1", "J5", "AFE_OUT1"]
LOG = []


def say(s):
    print(s)
    LOG.append(s)


def strip(b, nets):
    dead = [t for t in b.GetTracks() if t.GetNetname() in nets]
    for t in dead:
        b.Delete(t)
    say(f"sdm: {len(dead)} old tracks / vias of {', '.join(sorted(nets))} deleted")


def ring(x, y, r0, r1, step=0.1, n=32):
    r = r0
    while r <= r1 + 1e-9:
        for k in range(n):
            a = 2 * math.pi * k / n
            yield x + r * math.cos(a), y + r * math.sin(a), r
        r += step


def end_via(cx, ref, num, net=None, rmax=4.0, w=SIG_W, prefer=None, made=None):
    """A via with a straight stub from pad ref-num (SMD); returns the via centre. For a through-hole pad the pad
    itself is the end. prefer=(dx, dy): try the ring points in that direction first."""
    p = geo.pad(cx.b, ref, num)
    net = net or p.GetNetname()
    x, y = xy(p.GetPosition())
    if p.HasHole():
        return (x, y)
    layer = B if p.GetParentFootprint().IsFlipped() else pcbnew.F_Cu
    s = p.GetSize(layer)
    r0 = min(T(s.x), T(s.y)) / 2 + geo.VIA / 2 + 0.05
    pts = list(ring(x, y, r0, rmax))
    if prefer:
        pts.sort(key=lambda q: (round(q[2], 1), -(prefer[0] * (q[0] - x) + prefer[1] * (q[1] - y))))
    for vx, vy, r in pts:
        v = cx.via_ok(net, vx, vy)
        if v is None:
            continue
        if p.GetEffectiveShape(layer).Collide(v.GetEffectiveShape(layer), F(0.02)):
            continue
        t = cx.mktrack(net, layer, (x, y), (vx, vy), min(w, 0.25))
        if not cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
            continue
        cx.commit(t, v)
        if made is not None:
            made += [t, v]
        return (vx, vy)
    say(f"sdm: NO via site within {rmax} mm of {ref}-{num} ({net})")
    return None


def via_near(cx, net, x, y, rmax=3.0, made=None):
    for vx, vy, r in ring(x, y, 0.0, rmax, n=24):
        v = cx.via_ok(net, vx, vy)
        if v is not None:
            cx.commit(v)
            if made is not None:
                made.append(v)
            return (vx, vy)
    say(f"sdm: NO via site for {net} within {rmax} mm of ({x:.2f}, {y:.2f})")
    return None


def avoid_cost(g, b, refs, r=4.0, c=1.5):
    for ref in refs:
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            continue
        for p in fp.Pads():
            px, py = xy(p.GetPosition())
            bb = p.GetBoundingBox()
            hx = T(bb.GetWidth()) / 2 + r
            hy = T(bb.GetHeight()) / 2 + r
            ia, ja = g.ij(px - hx, py - hy)
            ib, jb = g.ij(px + hx, py + hy)
            for j in range(max(0, ja), min(g.ny, jb + 1)):
                for i in range(max(0, ia), min(g.nx, ib + 1)):
                    g.cost[j * g.nx + i] = max(g.cost[j * g.nx + i], c)


def follow_cost(g, pts, d0, d1, far=4.0):
    """Cells between d0 and d1 from the polyline cost 0, the rest `far` (side by side with the leader)."""
    for k in range(len(g.cost)):
        g.cost[k] = max(g.cost[k], far) if g.cost[k] < far else g.cost[k]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        ia, ja = g.ij(min(x0, x1) - d1, min(y0, y1) - d1)
        ib, jb = g.ij(max(x0, x1) + d1, max(y0, y1) + d1)
        for j in range(max(0, ja), min(g.ny, jb + 1)):
            for i in range(max(0, ia), min(g.nx, ib + 1)):
                x, y = g.xy(i, j)
                if L < 1e-9:
                    d = math.hypot(x - x0, y - y0)
                else:
                    t = max(0.0, min(1.0, ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / (L * L)))
                    d = math.hypot(x - (x0 + t * (x1 - x0)), y - (y0 + t * (y1 - y0)))
                k = j * g.nx + i
                if d0 <= d <= d1 and g.cost[k] <= far:
                    g.cost[k] = 0.0


def simplify(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) < 1e-6:
            continue
        if len(out) >= 2:
            (ax, ay), (bx, by) = out[-2], out[-1]
            if abs((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)) < 1e-6:
                out[-1] = p
                continue
        out.append(p)
    return out


def run(cx, net, layer, a, c, w, box, leader=None, avoid=(), made=None, what="", step=None):
    t0 = time.time()
    g = geo.Grid(cx, layer, box, w, net, step=step)
    g.cost = [2.0 if v else 0.0 for v in g.soft]
    if avoid:
        avoid_cost(g, cx.b, avoid)
    if leader:
        lw, lpts = leader
        follow_cost(g, lpts, lw / 2 + w / 2 + 0.15 + 0.03, lw / 2 + w / 2 + 0.15 + 0.17)
    pts = g.route(a, c)
    if pts is None:
        say(f"sdm: {net} {what}: NO PATH on {cx.b.GetLayerName(layer)} from ({a[0]:.2f}, {a[1]:.2f}) to ({c[0]:.2f}, {c[1]:.2f}) [{time.time() - t0:.0f} s]")
        return None
    pts = simplify(pts)
    err = cx.poly(net, layer, pts, w)
    if err:
        # the grid ends sit on the exact end points: retry without the first / last grid kink
        say(f"sdm: {net} {what}: path found but {err}")
        return None
    if made is not None:
        made += cx.last
    say(f"sdm: {net} {what}: {geo.plen(pts):.1f} mm on {cx.b.GetLayerName(layer)}, {len(pts) - 1} segments [{time.time() - t0:.0f} s]")
    return pts


def straight(cx, net, layer, pts, w, what=""):
    err = cx.poly(net, layer, pts, w)
    say(f"sdm: {net} {what}: " + (err or f"{geo.plen(pts):.1f} mm on {cx.b.GetLayerName(layer)}"))
    return None if err else pts


def east_pad_of(b, net, west_ref):
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and fp.GetReference() != west_ref:
                return fp.GetReference(), p.GetNumber()
    return None




def remove(b, objs):
    for o in objs:
        try:
            b.Remove(o)
        except Exception:
            pass


def chain(cx, net, start, legs, what, leaders=None):
    """start: (x, y) of a via / pad already on the board; legs: [(layer, w, box, target)], target = (x, y) of the
    next transfer point ('via:' prefix in a tuple ('via', x, y) asks for a new via near x, y) or of an existing end.
    Returns True when every leg is drawn; on a failure the net's new copper of this call is removed."""
    made = []
    cur = start
    cx.paths = []
    for k, (layer, w, box, tgt) in enumerate(legs):
        if box != "straight" and tgt[0] == "via":
            v = via_near(cx, net, tgt[1], tgt[2], rmax=2.5, made=made)
            if v is None:
                break
            tgt = v
        if box == "straight":
            pts = [cur] + list(tgt)
            err = cx.poly(net, layer, pts, w)
            say(f"west: {net} {what} leg {k + 1}: " + (err or f"straight, {geo.plen(pts):.1f} mm"))
            if err:
                break
            made += cx.last
            cx.paths.append(pts)
            cur = pts[-1]
            continue
        fine = 0.05 if box[2] - box[0] < 70 else None      # the pinches west of the corridor need the fine grid
        ld = leaders[k] if leaders and k < len(leaders) else None
        pts = run(cx, net, layer, cur, tgt, w, box, made=made, what=f"{what} leg {k + 1}", step=fine, leader=ld)
        if pts is None:
            break
        cx.paths.append(pts)
        cur = tgt
    else:
        return True
    say(f"west: {net} {what}: NOT drawn ({len(made)} pieces taken out again)")
    for o in made:
        cx.b.Delete(o)
    keep = cx.pierce, cx.via_pierce
    cx.__init__(cx.b)
    cx.pierce, cx.via_pierce = keep
    return False


def end_at_track(cx, net, x, y, made=None, pierce=()):
    """A via at an old track end (x, y), or next to it with a stub on the track's layer, so that an inner-layer leg
    can reach it. pierce: HV pour nets the via may enter (cut back afterwards by geo.hv_holes)."""
    lay = None
    for t in cx.b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vx, vy = xy(t.GetPosition())
            if abs(vx - x) < 0.05 and abs(vy - y) < 0.05:
                return (vx, vy)
            continue
        for q in (t.GetStart(), t.GetEnd()):
            qx, qy = xy(q)
            if abs(qx - x) < 0.02 and abs(qy - y) < 0.02:
                lay = t.GetLayer()
    old = cx.pierce
    cx.pierce = set(old) | set(pierce)
    try:
        from drawlib import ring
        for vx, vy, r in ring(x, y, 0.0, 2.0, n=24):
            v = cx.via_ok(net, vx, vy)
            if v is None:
                continue
            objs = [v]
            if r > 0.01:
                if lay is None:
                    continue
                t = cx.mktrack(net, lay, (x, y), (vx, vy), 0.2)
                if not cx.clear(net, t.GetEffectiveShape(lay), t.GetBoundingBox(), lay):
                    continue
                objs.append(t)
            cx.commit(*objs)
            if made is not None:
                made += objs
            return (vx, vy)
        say(f"west: NO via at or next to the old end ({x:.2f}, {y:.2f}) of {net}")
        return None
    finally:
        cx.pierce = old


