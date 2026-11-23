#!/usr/bin/env python3
"""v6 step 2 (run once, kipy): the two card strips are cleared of the old power-stage copper (V6_PLAN.md step 2).

Strips (IPC frame): primary y -84 ... -57, ISO y 49.5 ... 72.5, x 14 ... 124 (the card span; the current-sense
circuits R48 / U5 and R91 / U4 west of x 12 stay as they are until step 3 moves them) (the DC bus band up to y 48.8 and the
aux area down to y -57 are not touched).
  1. tracks and vias with an end in a strip are deleted (the supply and PWM runs to the old gate-card headers;
     step 5 routes the card headers anew);
  2. pours that lie wholly in a strip are deleted;
  3. pours that reach into a strip are cut back to the strip's inner edge (a zone keeps only one outline: every
     further piece becomes a zone of its own);
Island counts of every pour before and after are in the log.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T  # noqa: E402

STRIPS = {"primary": (14.0, -84.0, 124.0, -57.0), "ISO": (14.0, 49.5, 124.0, 72.5)}


def strip_of(x, y):
    for k, (x0, y0, x1, y1) in STRIPS.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return k
    return None


def rect_poly(x0, y0, x1, y1):
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        p.Append(F(x), F(-y))
    return p


def islands(board):
    out = {}
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lay in z.GetLayerSet().Seq():
            out[(z.GetZoneName(), z.GetNetname(), board.GetLayerName(lay))] = z.GetFilledPolysList(lay).OutlineCount()
    return out


b = Board(6002)
zones = b.b.Zones()
pcbnew.ZONE_FILLER(b.b).Fill(zones)
before = islands(b.b)

# -- 1. tracks and vias
n = {}
for t in list(b.b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        k = strip_of(T(t.GetPosition().x), -T(t.GetPosition().y))
    else:
        k = strip_of(T(t.GetStart().x), -T(t.GetStart().y)) or strip_of(T(t.GetEnd().x), -T(t.GetEnd().y))
    if k:
        key = (k, t.GetNetname(), "vias" if t.GetClass() == "PCB_VIA" else "tracks")
        n[key] = n.get(key, 0) + 1
        b.b.Delete(t)
for (k, net, what), c in sorted(n.items()):
    b.log.append(f"{k} strip: {c} {what} of {net} deleted")

# -- 2 .. 4. zones
for z in list(b.b.Zones()):
    bb = z.GetBoundingBox()
    x0, x1, y0, y1 = T(bb.GetLeft()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetTop())
    for k, (a0, b0, a1, b1) in STRIPS.items():
        if x1 < a0 or x0 > a1 or y1 < b0 or y0 > b1:
            continue
        name = f"{z.GetZoneName()} [{z.GetNetname()}]"
        if z.GetIsRuleArea():
            break
        if a0 <= x0 and x1 <= a1 and b0 <= y0 and y1 <= b1:
            b.log.append(f"{k} strip: pour {name} deleted (wholly in the strip)")
            b.b.Delete(z)
            break
        poly = pcbnew.SHAPE_POLY_SET(z.Outline())
        poly.BooleanSubtract(rect_poly(a0 - 200, b0 if k == "ISO" else b0 - 200, a1 + 200, b1 + 200 if k == "ISO" else b1))
        poly.Simplify()
        pieces = poly.OutlineCount()
        if pieces == 0:
            b.log.append(f"{k} strip: pour {name} deleted (nothing left outside the strip)")
            b.b.Delete(z)
            break
        for i in range(pieces):
            if i == 0:
                # change the zone's own outline in place (SetOutline with a temporary crashes at SaveBoard)
                chains = [pcbnew.SHAPE_LINE_CHAIN(poly.Outline(0))] + [pcbnew.SHAPE_LINE_CHAIN(poly.Hole(0, h)) for h in range(poly.HoleCount(0))]
                o = z.Outline()
                o.RemoveAllContours()
                o.AddOutline(chains[0])
                for c in chains[1:]:
                    o.AddHole(c)
                z.UnFill()
            else:
                # a new zone with the settings of the old one (ZONE.Duplicate crashes pcbnew 10.0.7 here)
                o = poly.Outline(i)
                pts = [(T(o.CPoint(j).x), -T(o.CPoint(j).y)) for j in range(o.PointCount())]
                b.zone(b.b.GetLayerName(z.GetLayer()), pts, z.GetNetname(), f"{z.GetZoneName()} (v6 piece {i + 1})",
                       z.GetAssignedPriority(), clearance=T(z.GetLocalClearance()))
        b.log.append(f"{k} strip: pour {name} cut back to the strip edge, {pieces} piece(s)")
        break

pcbnew.SaveBoard(os.path.join(os.path.dirname(os.path.dirname(HERE)), "kicad", "ac_psu.kicad_pcb"), b.b)
b.b = pcbnew.LoadBoard(os.path.join(os.path.dirname(os.path.dirname(HERE)), "kicad", "ac_psu.kicad_pcb"))   # reload before the fill
zones = b.b.Zones()
pcbnew.ZONE_FILLER(b.b).Fill(zones)
after = islands(b.b)
for key in sorted(set(before) | set(after)):
    if before.get(key) != after.get(key):
        b.log.append(f"islands {key[0]} [{key[1]}] {key[2]}: {before.get(key, '-')} -> {after.get(key, '-')}")
b.save("v6 step 2: card strips cleared (tracks, vias, pours of the old power stage)")
