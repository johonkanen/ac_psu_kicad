#!/usr/bin/env python3
"""Routing chain step 47 (kipy): keep the pass's new copper inside the open-layout rows.

  kipy 47_confine.py IN OUT BASE

V6_PLAN section 13 (user 2026-11-24): a legal board first; the open-layout rows of lib/v5_copper.csv /
lib/v6_copper.csv excuse open connections, and they are not widened to excuse copper. So every track or via that
this chain added (not on BASE, the step-03 board) and that reaches outside those rows (tools/deviations.py in_area,
per layer; sampled every 0.5 mm) is deleted, and then new copper left with a free end is pulled back to its last
pad / junction / same-net pour, repeatedly (as 03_prune.py). The connections they made stay open (pending).
Zones must be filled (the chain refills before every step). Prints what it deletes per net.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path[:0] = [os.path.join(R, "tools")]
import deviations  # noqa: E402

T = pcbnew.ToMM


def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return ("v", t.GetPosition().x, t.GetPosition().y, t.GetNetname())
    a, c = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    return ("t", t.GetLayer(), min(a, c), max(a, c), t.GetNetname())


def outside(b, t):
    if t.Type() == pcbnew.PCB_VIA_T:
        x, y = T(t.GetPosition().x), -T(t.GetPosition().y)
        return not deviations.in_area("*", x, y)
    lay = b.GetLayerName(t.GetLayer())
    (x0, y0), (x1, y1) = (T(t.GetStart().x), -T(t.GetStart().y)), (T(t.GetEnd().x), -T(t.GetEnd().y))
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.5))
    return any(not deviations.in_area(lay, x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1))


def main():
    src, dst, base = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    old = {key(t) for t in pcbnew.LoadBoard(base).GetTracks()}
    new = [t for t in b.GetTracks() if key(t) not in old]
    dead = [t for t in new if outside(b, t)]
    nets = {}
    for t in dead:
        nets[t.GetNetname().split("/")[-1]] = nets.get(t.GetNetname().split("/")[-1], 0) + 1
        b.Delete(t)
    print(f"confine: {len(dead)} new tracks / vias outside the open-layout rows deleted: " +
          " ".join(f"{k} ({v})" for k, v in sorted(nets.items())))
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    zones = [z for z in b.Zones() if not z.GetIsRuleArea()]

    def touched(net, layer, pt, me, items):
        for p in pads:
            if p.GetNetname() == net and p.IsOnLayer(layer) and p.HitTest(pt):
                return True
        for z in zones:
            if z.GetNetname() == net and z.IsOnLayer(layer) and z.HitTestFilledArea(layer, pt):
                return True
        for t in items.get(net, ()):
            if t is me or t.m_Uuid == me.m_Uuid:
                continue
            if t.GetClass() == "PCB_VIA":
                if t.HitTest(pt):
                    return True
            elif t.GetLayer() == layer and (t.HitTest(pt, 1) or (me.GetClass() == "PCB_VIA" and me.HitTest(t.GetStart()))
                                            or (me.GetClass() == "PCB_VIA" and me.HitTest(t.GetEnd()))):
                return True
        return False
    total, pnets = 0, {}
    for rnd in range(300):
        items = {}
        for t in b.GetTracks():
            items.setdefault(t.GetNetname(), []).append(t)
        kill = []
        for t in b.GetTracks():
            net = t.GetNetname()
            if not net or key(t) in old:
                continue
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                if sum(1 for L in t.GetLayerSet().CuStack() if touched(net, L, p, t, items)) <= 1:
                    kill.append(t)
            elif any(not touched(net, t.GetLayer(), p, t, items) for p in (t.GetStart(), t.GetEnd())):
                kill.append(t)
        if not kill:
            break
        for t in kill:
            pnets[t.GetNetname().split("/")[-1]] = pnets.get(t.GetNetname().split("/")[-1], 0) + 1
            b.Delete(t)
        total += len(kill)
    print(f"confine: {total} new items left dangling pulled back in {rnd} rounds: " +
          " ".join(f"{k} ({v})" for k, v in sorted(pnets.items())))
    b.Save(dst)


if __name__ == "__main__":
    main()
