#!/usr/bin/env python3
"""Dead copper of block E (kipy; block_E_chain.sh step 40): track / via groups of signal nets that touch no pad and do
not reach the E edge (a port). They are pieces of the kept v4 / v5 copper that ended at copper the clean start
removed, and the pass-1 pieces left inside block G by the cut at the E edge.

  kipy block_E_dead.py IN OUT BOARD03

A group is deleted when every item lies inside E (E minus G) or is a pass-1 item inside G (not on BOARD03). A group
of a pour / plane net that touches a fill of its net is alive (BOARD must be filled). block_E_make.py copper turns the deletions into
"deadtrack" / "deadvia" rows.
"""
import collections
import os
import sys

import pcbnew

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import block_E as BE  # noqa: E402
from blocks import POUR_NETS  # noqa: E402

F = pcbnew.FromMM


def inE(p):
    x, y = p
    return BE.E[0] <= x <= BE.E[2] and BE.E[1] <= y <= BE.E[3] and not (
        BE.G[0] < x < BE.G[2] and BE.G[1] < y < BE.G[3])


def on_edge(p):
    x, y = p
    return abs(x - BE.E[0]) < 1e-3 or abs(x - BE.E[2]) < 1e-3 or abs(y - BE.E[1]) < 1e-3 or abs(y - BE.E[3]) < 1e-3


def inG(p):
    return BE.G[0] <= p[0] <= BE.G[2] and BE.G[1] <= p[1] <= BE.G[3]


def main():
    src, dst, b3p = sys.argv[1:4]
    b, b3 = pcbnew.LoadBoard(src), pcbnew.LoadBoard(b3p)
    old = collections.Counter(BE.item_key(b3, t) for t in b3.GetTracks())
    bynet = collections.defaultdict(list)
    for t in b.GetTracks():
        n = t.GetNetname()
        if n:
            bynet[n].append(t)
    fills = collections.defaultdict(list)       # pour nets: (layer, filled polygons)
    for z in b.Zones():
        if not z.GetIsRuleArea():
            for l in z.GetLayerSet().Seq():
                fills[z.GetNetname()].append((l, z.GetFilledPolysList(l)))
    pads = collections.defaultdict(list)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads[p.GetNetname()].append(p)
    dead = []
    for n, ts in bynet.items():
        parent = list(range(len(ts)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, c = ts[i], ts[j]
                if a.Type() != pcbnew.PCB_VIA_T and c.Type() != pcbnew.PCB_VIA_T and a.GetLayer() != c.GetLayer():
                    continue
                la = a.GetLayer() if a.Type() != pcbnew.PCB_VIA_T else c.GetLayer()
                if a.GetEffectiveShape(la).Collide(c.GetEffectiveShape(la), 0):
                    parent[find(i)] = find(j)
        groups = collections.defaultdict(list)
        for i, t in enumerate(ts):
            groups[find(i)].append(t)
        for g in groups.values():
            pts = []
            ok = True
            for t in g:
                q = [BE.xy(t.GetPosition())] if t.Type() == pcbnew.PCB_VIA_T else [BE.xy(t.GetStart()), BE.xy(t.GetEnd())]
                pts += q
                if not all(inE(p) or (inG(p) and old[BE.item_key(b, t)] == 0) for p in q):
                    ok = False
            if not ok or any(on_edge(p) for p in pts):
                continue
            hit = False
            for p in pads.get(n, []):
                for t in g:
                    L = t.GetLayer() if t.Type() != pcbnew.PCB_VIA_T else (pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu)
                    if p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(t.GetEffectiveShape(L), 0):
                        hit = True
                        break
                if hit:
                    break
            if not hit and n.split("/")[-1] in POUR_NETS:
                for t in g:
                    for l, fp in fills.get(n, []):
                        if (t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == l) and fp.OutlineCount() and \
                                fp.Collide(t.GetEffectiveShape(l if t.Type() == pcbnew.PCB_VIA_T else t.GetLayer()), 0):
                            hit = True
                            break
                    if hit:
                        break
            if not hit:
                dead.append((n, g))
    k = 0
    for n, g in dead:
        print(f"dead: {n}: {len(g)} items at " + ", ".join(f"({BE.xy(t.GetPosition())[0]:.2f}, {BE.xy(t.GetPosition())[1]:.2f})" for t in g[:3]))
        for t in g:
            b.Delete(t)
            k += 1
    b.Save(dst)
    print(f"dead: {k} items in {len(dead)} groups deleted")


if __name__ == "__main__":
    main()
