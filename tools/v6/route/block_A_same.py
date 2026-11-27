#!/usr/bin/env python3
"""Compare the tracks / vias / zones of two boards by net, layer and geometry (kipy): proves the block A replay
equals the drawn board of block_A_make.py.

  kipy block_A_same.py A.kicad_pcb B.kicad_pcb
"""
import collections
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_A as BA  # noqa: E402

a, b = pcbnew.LoadBoard(sys.argv[1]), pcbnew.LoadBoard(sys.argv[2])
ka = collections.Counter(BA.item_key(a, t) for t in a.GetTracks())
kb = collections.Counter(BA.item_key(b, t) for t in b.GetTracks())
only_a, only_b = ka - kb, kb - ka
fa = {f.GetReference(): BA.xy(f.GetPosition()) for f in a.GetFootprints()}
fb = {f.GetReference(): BA.xy(f.GetPosition()) for f in b.GetFootprints()}
moved = [r for r in fa if r in fb and max(abs(fa[r][0] - fb[r][0]), abs(fa[r][1] - fb[r][1])) > 0.001]


def zkey(brd, z):
    ol = z.Outline()
    pts = tuple((round(BA.T(ol.CVertex(i).x), 2), round(BA.T(ol.CVertex(i).y), 2)) for i in range(ol.TotalVertices()))
    return (z.GetZoneName(), z.GetNetname(), tuple(brd.GetLayerName(l) for l in z.GetLayerSet().Seq()), pts)


za = collections.Counter(zkey(a, z) for z in a.Zones())
zb = collections.Counter(zkey(b, z) for z in b.Zones())
print(f"same: {sum(ka.values())} / {sum(kb.values())} tracks + vias; only in A {sum(only_a.values())}, only in B "
      f"{sum(only_b.values())}; zones {sum(za.values())} / {sum(zb.values())}, only in A {sum((za - zb).values())}, "
      f"only in B {sum((zb - za).values())}; footprints differing {len(moved)} {moved[:10]}")
for k in list(only_a)[:5]:
    print("  A:", k)
for k in list(only_b)[:5]:
    print("  B:", k)
for k in list(za - zb)[:5]:
    print("  A zone:", k[:3])
for k in list(zb - za)[:5]:
    print("  B zone:", k[:3])
sys.exit(1 if only_a or only_b or (za - zb) or (zb - za) or moved else 0)
