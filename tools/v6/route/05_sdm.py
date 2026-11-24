#!/usr/bin/env python3
"""Routing chain step 05 (kipy): the two sigma-delta links drawn by script (planning session rule 2, 2026-11-24).

  kipy 05_sdm.py IN OUT

Clock and data of one modulator side by side on In3, each pair with its domain's ground and supply as guard tracks
where no ground plane lies under it (In4 has a plane only in the card areas and in the ISO strip):

- ISO link: U21 (MDATA_INU pin 12, INU_ADCLK from pin 14 through R258 when the board has it) -> U4 / R50 west of J9.
  In3 from U21 through the passage north of J11 (over the In4 ISOGND planes) to x 40.4, In2 past J37 (its DC+ tongue
  is on In1 / In3 / B), the via column x 28.75 between the J37 and J38 tongues, In3 north of J38 (over the In4 ISOGND
  strip) and on west to U4 with ISOGND and 3V3_ISO (U4 VDD2) beside the pair.
- AFE link: U15 B5 (MDATA, pin 10) / R22 (ADCLK, 39R at U15) -> R55 / U5 below FILTER_OUT1. In3 from the primary
  card area (over its In4 GND plane) to U5, with GND and VCC (U5 VDD2) beside the pair.

Every piece is tested by geo.Ctx (2.5 mm to high-voltage nets, domain gaps, pours, keep-outs) before it is added; a
via or stub inside a high-voltage pour near U5 cuts that pour back by 2.5 mm (geo.hv_holes keep-outs). The old copper
of the four nets is deleted first. Prints length and what each run passes over.
"""
import math
import os
import sys
import time

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import F, T, P, xy  # noqa: E402

IN2, IN3, B = pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu
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


def run(cx, net, layer, a, c, w, box, leader=None, avoid=(), made=None, what=""):
    t0 = time.time()
    g = geo.Grid(cx, layer, box, w, net)
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


def iso_link(b):
    cx = geo.Ctx(b)
    cx.pierce = {"ISOGND", "3V3_ISO", "/05 VSI/INDUCTOR_OUTPUT", "/05 VSI/INU_FILTER_INPUT"}   # ISO planes: antipads by
    total = {}                                 # the refill; the HV pours at U4: cut back by hv_holes
    made = []
    # east ends
    ck = east_pad_of(b, "INU_ADCLK", "U4")
    e_clk = end_via(cx, *ck, prefer=(0, 1))
    e_dat = end_via(cx, "U21", "12", prefer=(0, 1))
    e_3v3 = via_near(cx, "3V3_ISO", 61.0, 46.8)
    if None in (e_clk, e_dat, e_3v3):
        return cx, total, made
    # transition vias: In3 -> In2 east of J37 (x 40.4), In2 -> In3 in the column between the tongues (x 28.75)
    ys = {"ISOGND": 54.6, "INU_ADCLK": 55.25, "MDATA_INU": 55.9, "3V3_ISO": 56.55}
    tv, cv = {}, {}
    for n in ("INU_ADCLK", "MDATA_INU", "3V3_ISO"):
        v = cx.via_ok(n, 40.4, ys[n])
        c = cx.via_ok(n, 28.75, ys[n])
        if v is None or c is None:
            say(f"sdm: transition via of {n} at x 40.4 / 28.75, y {ys[n]} NOT legal")
            return cx, total, made
        cx.commit(v, c)
        tv[n], cv[n] = (40.4, ys[n]), (28.75, ys[n])
    g = cx.via_ok("ISOGND", 28.75, ys["ISOGND"])
    if g is None:
        say("sdm: ISOGND column via NOT legal")
        return cx, total, made
    cx.commit(g)
    box_e = (37.0, 36.0, 82.0, 60.0)
    p_clk = run(cx, "INU_ADCLK", IN3, e_clk, tv["INU_ADCLK"], SIG_W, box_e, what="east, U21 side -> x 40.4")
    p_dat = p_clk and run(cx, "MDATA_INU", IN3, e_dat, tv["MDATA_INU"], SIG_W, box_e, leader=(SIG_W, p_clk), what="east, U21 -> x 40.4")
    p_3v3 = p_dat and run(cx, "3V3_ISO", IN3, e_3v3, tv["3V3_ISO"], GUARD_W, box_e, leader=(SIG_W, p_dat), what="east, plane -> x 40.4")
    if not p_3v3:
        return cx, total, made
    for n, w in (("INU_ADCLK", SIG_W), ("MDATA_INU", SIG_W), ("3V3_ISO", GUARD_W)):
        if not straight(cx, n, IN2, [tv[n], cv[n]], w, "past J37 on In2"):
            return cx, total, made
    # west ends at U4
    w_clk = end_via(cx, "U4", "7", prefer=(1, 0), made=made)
    w_dat = end_via(cx, "R50", "2", prefer=(0, 1), made=made)
    w_gnd = end_via(cx, "U30", "2", made=made)          # through-hole: the ISOGND of U4 / C37 / C162 is routed from it
    w_3v3 = end_via(cx, "C37", "2", net="3V3_ISO", prefer=(0, -1), w=0.25, made=made)
    if None in (w_clk, w_dat, w_gnd, w_3v3):
        return cx, total, made
    box_w = (-101.0, 38.0, 31.0, 71.4)
    q_clk = run(cx, "INU_ADCLK", IN3, cv["INU_ADCLK"], w_clk, SIG_W, box_w, avoid=AVOID, what="west, column -> U4-7")
    q_dat = q_clk and run(cx, "MDATA_INU", IN3, cv["MDATA_INU"], w_dat, SIG_W, box_w, leader=(SIG_W, q_clk), avoid=AVOID, what="west, column -> R50")
    q_gnd = q_dat and run(cx, "ISOGND", IN3, (28.75, ys["ISOGND"]), w_gnd, GUARD_W, box_w, leader=(SIG_W, q_clk), avoid=AVOID, what="guard, column -> U30-2")
    q_3v3 = q_gnd and run(cx, "3V3_ISO", IN3, cv["3V3_ISO"], w_3v3, GUARD_W, box_w, leader=(SIG_W, q_dat), avoid=AVOID, what="guard, column -> C37-2")
    if q_clk and q_dat:
        total["INU_ADCLK"] = geo.plen(p_clk) + 11.65 + geo.plen(q_clk)
        total["MDATA_INU"] = geo.plen(p_dat) + 11.65 + geo.plen(q_dat)
    return cx, total, made


def afe_link(b):
    cx = geo.Ctx(b)
    cx.pierce = {"GND", "VCC", "FILTER_INPUT", "/01 afe/FILTER_INPUT", "/01 afe/LEMOUT", "LEMOUT"}
    total = {}
    made = []
    e_dat = end_via(cx, "U15", "10", prefer=(0, -1), made=made)
    e_clk = end_via(cx, "R22", "2", prefer=(0, -1), made=made)
    e_gnd = via_near(cx, "GND", 51.0, -1.2, made=made)
    e_vcc = via_near(cx, "VCC", 53.0, -2.4, made=made)
    w_dat = end_via(cx, "R55", "2", prefer=(1, 0), made=made)
    w_clk = end_via(cx, "U5", "7", prefer=(0, 1), made=made)
    w_gnd = end_via(cx, "C64", "1", net="GND", prefer=(0, -1), w=0.25, made=made)
    w_vcc = end_via(cx, "C64", "2", net="VCC", prefer=(1, 0), w=0.25, made=made)
    if None in (e_dat, e_clk, e_gnd, e_vcc, w_dat, w_clk, w_gnd, w_vcc):
        return cx, total, made
    box = (-46.0, -83.6, 62.0, 6.0)
    q_clk = run(cx, "ADCLK", IN3, e_clk, w_clk, SIG_W, box, avoid=AVOID, made=made, what="R22 -> U5-7")
    q_dat = q_clk and run(cx, "MDATA", IN3, e_dat, w_dat, SIG_W, box, leader=(SIG_W, q_clk), avoid=AVOID, made=made, what="U15-10 -> R55")
    q_gnd = q_dat and run(cx, "GND", IN3, e_gnd, w_gnd, GUARD_W, box, leader=(SIG_W, q_clk), avoid=AVOID, made=made, what="guard -> C64-1")
    q_vcc = q_gnd and run(cx, "VCC", IN3, e_vcc, w_vcc, GUARD_W, box, leader=(SIG_W, q_dat), avoid=AVOID, made=made, what="guard -> C64-2")
    if q_clk and q_dat:
        total["ADCLK"], total["MDATA"] = geo.plen(q_clk), geo.plen(q_dat)
    return cx, total, made


def main():
    src, dst = sys.argv[1:3]
    b = pcbnew.LoadBoard(src)
    strip(b, {"MDATA", "ADCLK", "MDATA_INU", "INU_ADCLK", "INU_ADCLK_U21"})
    cxi, ti, madei = iso_link(b)
    n = geo.hv_holes(cxi, madei, "sdm")
    cx, ta, made = afe_link(b)
    n += geo.hv_holes(cx, made, "sdm")
    say(f"sdm: {n} HV keep-outs (pour cut back 2.5 mm) for the link vias / stubs in HV pours")
    for k, v in {**ti, **ta}.items():
        say(f"sdm: length {k} {v:.1f} mm")
    b.Save(dst)


if __name__ == "__main__":
    main()
