#!/usr/bin/env python3
"""Compare the tracks / vias of two boards by net, layer and geometry (kipy): proves a replay equals the chain board.

  kipy block_E_same.py A.kicad_pcb B.kicad_pcb
"""
import collections
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_E as BE  # noqa: E402

a, b = pcbnew.LoadBoard(sys.argv[1]), pcbnew.LoadBoard(sys.argv[2])
ka = collections.Counter(BE.item_key(a, t) for t in a.GetTracks())
kb = collections.Counter(BE.item_key(b, t) for t in b.GetTracks())
only_a, only_b = ka - kb, kb - ka
fa = {f.GetReference(): BE.xy(f.GetPosition()) for f in a.GetFootprints()}
fb = {f.GetReference(): BE.xy(f.GetPosition()) for f in b.GetFootprints()}
moved = [r for r in fa if r in fb and max(abs(fa[r][0] - fb[r][0]), abs(fa[r][1] - fb[r][1])) > 0.001]
print(f"same: {sum(ka.values())} / {sum(kb.values())} items; only in A {sum(only_a.values())}, only in B "
      f"{sum(only_b.values())}; footprints differing {len(moved)} {moved[:10]}")
for k in list(only_a)[:5]:
    print("  A:", k)
for k in list(only_b)[:5]:
    print("  B:", k)
