#!/usr/bin/env python3
"""Chain step 44 (kipy): no tracks on In1 / In4 inside the control-card outline (tools/v5/check_layout.py rule 6).

  kipy block_E_strip.py IN OUT

The bottom fan (step 09, all six layers) put three pieces of PWM_Q6_CTRL (In1) and INU_ADCLK_CTRL (In4) in the J11
column. They are deleted here; step 45 routes the two nets again on F / In2 / In3 / B and step 46 removes vias left
without a purpose.
"""
import sys

import pcbnew

CARD = (42.599, -18.766, 118.599, 46.361)
T = pcbnew.ToMM


def inside(v):
    x, y = T(v.x), -T(v.y)
    return CARD[0] <= x <= CARD[2] and CARD[1] <= y <= CARD[3]


b = pcbnew.LoadBoard(sys.argv[1])
gone = []
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() not in (pcbnew.In1_Cu, pcbnew.In4_Cu):
        continue
    if inside(t.GetStart()) or inside(t.GetEnd()):
        gone.append(f"{b.GetLayerName(t.GetLayer())} {t.GetNetname()} ({T(t.GetStart().x):.2f}, {-T(t.GetStart().y):.2f})"
                    f"-({T(t.GetEnd().x):.2f}, {-T(t.GetEnd().y):.2f})")
        b.Delete(t)
b.Save(sys.argv[2])
print(f"strip: {len(gone)} In1 / In4 tracks inside the card outline deleted: " + "; ".join(gone))
