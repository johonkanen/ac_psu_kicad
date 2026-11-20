#!/usr/bin/env python3
"""v5 step 19 (run once, kipy): input resistor R98 and input capacitor C112 of the aux flyback move to T1
(routing pass 6: AUX_VIN, 450 V, had to run about 40 mm from under the card to T1 pin 11 and found no legal
path; user 2026-11-20: "Go with both").

  1. R98 (2512) from the top side at (74.0, -12.3) to the bottom side at (71.0, -48.6): DC+ end west, AUX_VIN end
     east, beside fly-lead hole 11 and 2.5 mm from hole 12 (drain; a first try at y -46.5 left 1.3 mm). C112 (1210) from (69.5, -11.0) to (72.0, -52.3), AUX_VIN end east.
     DC+ -> R98 -> AUX_VIN -> C111 / C112 / T1 pin 11 / D13 is now within a few millimetres.
  2. The 10M chains R136..R138 (start-up) and R141..R143 (line over-voltage) stay under the card; their high end
     is DC+ instead of AUX_VIN (tools/sheets/sheet07.py; the nets are 10R apart). Pad nets follow here.
A scan of the primary aux area found no room for the six 1206 parts of the chains near T1.
Checks here: sides, pad order, no pour split by the new pads. DRC, layout: tools/check_all.sh.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P  # noqa: E402

b = Board(5019)
B = b.b


def at(ref):
    p = b.fp(ref).GetPosition()
    return round(T(p.x), 3), round(-T(p.y), 3)


def pad(ref, num):
    q = next(p for p in b.fp(ref).Pads() if p.GetNumber() == num)
    return round(T(q.GetPosition().x), 3), round(-T(q.GetPosition().y), 3), q.GetNetname()


if at("R98") == (71.0, -48.6):
    raise SystemExit("v5 step 19 already applied (R98 is at (71.0, -48.6))")


def islands(board):
    out = {}
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lid in z.GetLayerSet().CuStack():
            f = z.GetFilledPolysList(lid)
            out[(z.GetZoneName(), z.GetNetname(), board.GetLayerName(lid))] = sum(
                1 for i in range(f.OutlineCount()) if f.Outline(i).Area() > 5e12)
    return out


pcbnew.ZONE_FILLER(B).Fill(B.Zones())
before = islands(B)


def move(ref, x, y, rot, side):
    fp = b.fp(ref)
    old = at(ref) + (fp.GetOrientationDegrees(), "B" if fp.IsFlipped() else "F")
    fp.SetPosition(P(x, y))
    if (side == "B") != fp.IsFlipped():
        fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    b.log.append(f"{ref}: {old} -> {at(ref) + (fp.GetOrientationDegrees(), side)}")


for ref, x, y, hv_east in (("R98", 71.0, -48.6, "2"), ("C112", 72.0, -52.3, "1")):
    for rot in (0, 180):
        n = len(b.log)
        move(ref, x, y, rot, "B")
        other = "1" if hv_east == "2" else "2"
        if pad(ref, hv_east)[0] > pad(ref, other)[0]:
            break
        del b.log[n:]
    else:
        raise SystemExit(f"{ref}: no rotation puts pad {hv_east} east")
    if pad(ref, hv_east)[2] != "AUX_VIN":
        raise SystemExit(f"{ref}-{hv_east} is {pad(ref, hv_east)[2]}, not AUX_VIN")
for ref in ("R136", "R141"):
    b.sync_pads(ref)
    if pad(ref, "1")[2] != "DC+":
        raise SystemExit(f"{ref}-1 is {pad(ref, '1')[2]}: regenerate sheet 7 first")
b.save("v5 step 19: R98 and C112 at T1, chains from DC+")

B2 = pcbnew.LoadBoard(B.GetFileName())
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
after = islands(B2)
bad = [f"{k}: {before.get(k)} -> {v} islands" for k, v in after.items() if v != before.get(k)]
for line in bad:
    print("  pour changed: " + line)
pcbnew.SaveBoard(B2.GetFileName(), B2)
if bad:
    raise SystemExit("a pour changed its island count (board saved; restore it with git if this is not accepted)")
