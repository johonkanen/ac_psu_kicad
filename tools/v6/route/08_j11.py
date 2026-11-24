#!/usr/bin/env python3
"""Routing chain step 08 (kipy): J11 west-row escape stubs (from the v5 pass-7 prep.py, unchanged placement).

  kipy 08_j11.py IN OUT

J11 (2 x 19, 1.27 mm, pads 0.81 mm): the west row (even pins, x 44.90) is 0.1 mm from the west edge of the CTRL
area, so its only way out is east, between the pads of the east row: a 0.46 mm gap, which holds exactly one
0.152 mm track at 0.154 mm clearance. The router's grid cannot hit that, so the stubs are drawn here: from the pad
45 degrees north-east into the gap above the pin (y + 0.635), then east to x 47.0. Pins 4..22 (to U15 / U13 / U16
and the filters, top side) on F.Cu, pins 24..36 (to U21 / U19 / U20, bottom side) on B.Cu. Each stub is tested by
geo.Ctx (MARGIN 0.002 here: the gap leaves 0.004 mm over the rule).
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import xy  # noqa: E402


def main():
    src, dst = sys.argv[1:3]
    b = pcbnew.LoadBoard(src)
    cx = geo.Ctx(b)
    geo.MARGIN = 0.002
    j11 = b.FindFootprintByReference("J11")
    n, bad = 0, []
    for pad in j11.Pads():
        num = int(pad.GetNumber())
        net = pad.GetNetname()
        if num % 2 or num < 4 or num > 36 or net.startswith("unconnected") or net in ("CTRLGND_A", "3V3_CTRL"):
            continue
        x, y = xy(pad.GetPosition())
        lay = pcbnew.F_Cu if num <= 22 else pcbnew.B_Cu
        err = cx.poly(net, lay, [(x, y), (x + 0.635, y + 0.635), (47.0, y + 0.635)], 0.152)
        if err:
            bad.append(f"{num} {net}: {err}")
        else:
            n += 1
    print(f"j11: {n} west-row escape stubs drawn" + ("; NOT: " + "; ".join(bad) if bad else ""))
    b.Save(dst)


if __name__ == "__main__":
    main()
