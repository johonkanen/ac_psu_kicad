#!/usr/bin/env python3
"""v6 step 3c (run once, kipy): the landing terminal AFE_OUT1 leaves the AFE leg 2 card envelope.

AFE_OUT1 (soldered landing pin, no net: the SW wire of the AFE leg 2 card meets the choke lead there) stood at
(47.5, -73.6), about 10 mm from the primary wall under the AFE leg 2 card (planning session 2026-11-23: move it out of
the envelopes, 20 mm or more from the wall, near J5 / FILTER_IN1). New place (-4.0, -62.5): outside the card spans,
20.55 mm from the wall, between FILTER_IN1 and the AFE leg 1 pair J32 / J31; its pad (switch-node voltage through
the wire) keeps 2.7 mm to J32's PGND pad and 3.9 mm to FILTER_IN1. The script checks courtyards and pad gaps.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P  # noqa: E402

NEW = (-4.0, -62.5)
b = Board(6006)
fp = b.fp("AFE_OUT1")
old = (round(T(fp.GetPosition().x), 3), round(-T(fp.GetPosition().y), 3))
if old == NEW:
    raise SystemExit("v6 step 3c already applied")
fp.SetPosition(P(*NEW))
b.log.append(f"AFE_OUT1 moved from {old} to {NEW}")

err = []
mine = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
for o in b.b.GetFootprints():
    if o.GetReference() == "AFE_OUT1" or -T(o.GetPosition().y) < -88:
        continue
    c = o.GetCourtyard(pcbnew.B_CrtYd if o.IsFlipped() else pcbnew.F_CrtYd)
    if c.OutlineCount() and c.BBox().Intersects(mine):
        err.append(f"courtyard overlaps {o.GetReference()}")
    for p in o.Pads():
        q = p.GetBoundingBox()
        d = math.hypot(max(T(q.GetLeft()) - NEW[0], 0, NEW[0] - T(q.GetRight())),
                       max(-T(q.GetBottom()) - NEW[1], 0, NEW[1] + T(q.GetTop()))) - 2.0
        if d < 2.5 and p.GetNetname():
            err.append(f"pad gap {d:.2f} mm to {o.GetReference()}.{p.GetNumber()} [{p.GetNetname()}]")
for e in err:
    b.log.append("CHECK " + e)
if err:
    print("\n".join(b.log))
    raise SystemExit("NOT SAVED")
b.save("v6 step 3c: AFE_OUT1 out of the card envelope")
