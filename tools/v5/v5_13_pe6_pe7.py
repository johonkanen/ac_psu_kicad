#!/usr/bin/env python3
"""v5 step 13 (run once, kipy): PE6 and PE7, the two PE screws between Y capacitors (user 2026-11-19: "We will go
with 3 for now" = accept that the 6.0 mm pan head touches the bodies of C29 / C30 and C31 / C32).

The holes stay where they are. Only the copper rule of v5 step 12 is applied to them: pours of other nets 2.5 mm
from the 6.0 mm head (F.Cu) and the 6.4 mm standoff (B.Cu). Tracks, pads and vias of other nets inside those
circles stop the script. The distance from the head to the neighbouring part bodies is logged, not checked.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T  # noqa: E402
import board_common as bc  # noqa: E402

HEAD = {"F.Cu": 6.0, "B.Cu": 6.4}
GAP = 2.5
REFS = ("PE6", "PE7")
b = Board(5013)
B = b.b


def nearest(board, c, net, layer):
    probe = pcbnew.SHAPE_CIRCLE(c, F(0.01))
    shapes = [z.GetFilledPolysList(layer) for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() != net and z.IsOnLayer(layer)]
    shapes += [t.GetEffectiveShape() for t in board.GetTracks() if t.GetNetname() != net and (t.GetClass() == "PCB_VIA" or t.GetLayer() == layer)]
    shapes += [p.GetEffectiveShape(layer) for o in board.GetFootprints() for p in o.Pads() if p.GetNetname() != net and p.IsOnLayer(layer)]
    d = 0.0
    while d < 12 and not any(s.Collide(probe, F(d)) for s in shapes):
        d += 0.05
    return d


if all(nearest(B, list(b.fp(r).Pads())[0].GetPosition(), list(b.fp(r).Pads())[0].GetNetname(), B.GetLayerID(l)) - d / 2 >= GAP - 0.06
       for r in REFS for l, d in HEAD.items()):
    raise SystemExit("v5 step 13 already applied (PE6 and PE7 have 2.5 mm to other copper)")
ncut = 0
for ref in REFS:
    pad = list(b.fp(ref).Pads())[0]
    c, net = pad.GetPosition(), pad.GetNetname()
    probe = pcbnew.SHAPE_CIRCLE(c, F(0.01))
    for o in B.GetFootprints():
        fab = [g.GetEffectiveShape() for g in o.GraphicalItems() if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE"]
        if o.GetReference() != ref and not o.IsFlipped() and any(s.Collide(probe, F(4.5)) for s in fab):
            d = 0.0
            while not any(s.Collide(probe, F(d)) for s in fab):
                d += 0.05
            b.log.append(f"   {ref}: drawn body of {o.GetReference()} is {d:.2f} mm from the hole centre, {d - HEAD['F.Cu'] / 2:+.2f} mm "
                         "from the edge of the 6.0 mm head (accepted by the user)")
    for lname, dia in HEAD.items():
        layer = B.GetLayerID(lname)
        r = dia / 2 + GAP
        keep = pcbnew.SHAPE_CIRCLE(c, F(r))
        for t in B.GetTracks():
            if t.GetNetname() != net and (t.GetClass() == "PCB_VIA" or t.GetLayer() == layer) and t.GetEffectiveShape().Collide(keep, 0):
                raise SystemExit(f"{ref}: {t.GetClass()} of {t.GetNetname()} on {lname} within {r} mm of the hole centre")
        for o in B.GetFootprints():
            for p in o.Pads():
                if p.GetNetname() != net and p.IsOnLayer(layer) and p.GetEffectiveShape(layer).Collide(keep, 0):
                    raise SystemExit(f"{ref}: pad {o.GetReference()}-{p.GetNumber()} of {p.GetNetname()} on {lname} within {r} mm of the hole centre")
        cut = pcbnew.SHAPE_POLY_SET()
        cut.NewOutline()
        for k in range(72):
            cut.Append(int(c.x + F(r + 0.02) * math.cos(math.radians(5 * k))), int(c.y + F(r + 0.02) * math.sin(math.radians(5 * k))))
        for z in list(B.Zones()):
            if z.GetIsRuleArea() or z.GetNetname() == net or not z.IsOnLayer(layer):
                continue
            o = z.Outline()
            if not o.Collide(cut, 0):
                continue
            a0 = o.Area()
            o.BooleanSubtract(cut)
            if o.OutlineCount() != 1:
                raise SystemExit(f"{z.GetZoneName()}: {o.OutlineCount()} outlines after the cut at {ref}")
            z.SetNeedRefill(True)
            z.HatchBorder()
            ncut += 1
            b.log.append(f"{ref}: zone {z.GetZoneName()} [{z.GetNetname().split('/')[-1]}] {lname} cut back to {r} mm from the hole centre "
                         f"({(a0 - o.Area()) / F(1) / F(1):.1f} mm2 of outline)")
if not ncut:
    raise SystemExit("no zone cut")
b.save("v5 step 13: PE6 / PE7 pours 2.5 mm from the screw head and the standoff")
B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
bb = B2.GetBoardEdgesBoundingBox()
for ref in REFS:
    pad = list(B2.FindFootprintByReference(ref).Pads())[0]
    c = pad.GetPosition()
    res = []
    for lname, dia in HEAD.items():
        g = nearest(B2, c, pad.GetNetname(), B2.GetLayerID(lname)) - dia / 2
        res.append(f"{lname} {g:.2f} mm")
        if g < GAP - 0.06:
            raise SystemExit(f"{ref}: {g:.2f} mm to other copper on {lname}")
    e = min(T(c.x - bb.GetLeft()), T(bb.GetRight() - c.x), T(c.y - bb.GetTop()), T(bb.GetBottom() - c.y))
    print(f"  {ref}: head / standoff to the nearest other copper: " + ", ".join(res) + f"; hole centre {e:.2f} mm from the board edge")
