#!/usr/bin/env python3
"""v6 step 4 (run once, kipy): DC bus pours to the card terminals, ground on In4 over the freed strips.

  tools/p2k/bin/kipy tools/v6/v6_4_pours.py

V6_PLAN.md section 5 "Copper": DC+ / PGND from the bulk caps to the three primary pairs, ISODC+ / ISOPGND to the
three ISO pairs, >= 10 mm wide on an outer layer and doubled on a second layer; the ISO bus leaves the old band for the
freed strip (wire links removed in step 3); ground on In4 over the freed strips per domain.

Primary (wall y -83.05): bus band y -80.0 ... -66.5 (3 mm from the wall edge), x 9 ... 116 (PGND from x -2):
  F.Cu + In1.Cu DC+, B.Cu + In2.Cu PGND (the layer pair of the v5 pours: DC+ on F, PGND on B); tongues 10 mm wide
  from the band to each terminal and up into the v5 pours (DC+ F pour 5, PGND B pour 0 end at y -57).
ISO (wall y 71.75): bus lane y 61.3 ... 69.2 (2.55 mm from the wall edge), between the pigtail holes (now at 16 mm
  from the wall) and the wall: B.Cu + In1.Cu ISODC+ (x 5 ... 108, to the DAB secondary), F.Cu + In2.Cu ISOPGND
  (x 5 ... 86.5, to inverter leg A), as the v5 pours (ISODC+ B pour 5, ISOPGND F pour 8); tongues to inverter leg B's
  terminals and into those pours west of its header. DAB_GROUND: the F pour at R64 grows to the J42 pigtail.
In4: GND under the primary strip, ISOGND under the ISO strip (north of the CTRL barrier strip at J11).
Every new zone has 2.5 mm clearance (the high-voltage rule of V6_PLAN section 4 inside a domain).
Small part moves (recorded): the header capacitors leave the bus paths; the four pigtails become one hole per net
(schematic footprint changed) and move to 16 mm from the wall.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, T, P, load_fp  # noqa: E402

HV = 2.5
b = Board(6007)
B = b.b
if any(z.GetZoneName().startswith("v6 bus") for z in B.Zones()):
    raise SystemExit("v6 step 4 already applied")


def islands(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    out = {}
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lid in z.GetLayerSet().CuStack():
            f = z.GetFilledPolysList(lid)
            out[(z.GetZoneName(), z.GetNetname().split("/")[-1], board.GetLayerName(lid))] = sum(
                1 for i in range(f.OutlineCount()) if f.Outline(i).Area() > 5e12)
    return out


before = islands(B)


def pads_c(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps)


def put(ref, x, y, rot=None):
    fp = b.fp(ref)
    if rot is not None:
        fp.SetOrientationDegrees(rot)
    cx, cy = pads_c(fp)
    p = fp.GetPosition()
    old = (round(cx, 2), round(cy, 2))
    fp.SetPosition(P(T(p.x) + x - cx, -T(p.y) + y - cy))
    b.log.append(f"{ref} moved {old} -> ({x}, {y})")


# ---- small parts out of the bus paths
for ref, (x, y) in {"C150": (51.0, -55.0), "C151": (56.5, -55.0), "C152": (96.5, -63.0), "C153": (99.5, -63.0),
                    "C154": (18.8, 42.0), "C155": (18.8, 45.0),
                    "C156": (60.0, 45.5), "C157": (65.0, 45.5), "C158": (92.5, 45.5), "C159": (97.5, 45.5)}.items():
    put(ref, x, y)

# ---- pigtails: one hole per net, 16 mm from the wall
PIG = {"J39": (75.0, 55.75), "J40": (83.5, 55.75), "J41": (104.6, 55.75), "J42": (113.1, 55.75)}
for ref, (x, y) in PIG.items():
    old = b.fp(ref)
    c = b.comps[ref]
    if str(old.GetFPID().GetLibItemName()) != c["footprint"].split(":")[1]:
        new = load_fp(c["footprint"])
        new.SetReference(ref)
        new.SetValue(old.GetValue())
        for ftype in (pcbnew.FIELD_T_DATASHEET, pcbnew.FIELD_T_DESCRIPTION):
            new.GetField(ftype).SetText(old.GetField(ftype).GetText())
        new.SetPath(old.GetPath())
        new.SetPosition(old.GetPosition())
        net = next(iter(old.Pads())).GetNetname()
        B.Delete(old)
        B.Add(new)
        for p in new.Pads():
            p.SetNet(b.net(net))
        b.log.append(f"{ref}: footprint {c['footprint']} (one hole), net {net}")
    put(ref, x, y)
# silkscreen labels follow the holes
for t in list(B.Drawings()):
    if t.GetClass() == "PCB_TEXT" and t.GetText() in ("+", "-", "INV A", "DAB SEC") and -T(t.GetPosition().y) > 50:
        B.Delete(t)


def silk(text, x, y, size=1.2):
    t = pcbnew.PCB_TEXT(B)
    t.SetText(text)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(P(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(0.18))
    B.Add(t)


for plus, minus, name in (("J39", "J40", "INV A"), ("J41", "J42", "DAB SEC")):
    (px, py), (mx, my) = PIG[plus], PIG[minus]
    silk("+", px - 4.2, py, 1.6)
    silk("-", mx + 4.2, my, 1.6)
    silk(name, (px + mx) / 2, py - 4.6)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def union_poly(*rs):
    """Outline of a union of axis-parallel rectangles (pcbnew polygon union, IPC frame)."""
    s = pcbnew.SHAPE_POLY_SET()
    for x0, y0, x1, y1 in rs:
        ch = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in rect(x0, y0, x1, y1):
            ch.Append(pcbnew.FromMM(x), pcbnew.FromMM(-y))
        ch.SetClosed(True)
        s.AddOutline(ch)
    s.Simplify()
    o = s.Outline(0)
    return [(T(o.CPoint(i).x), -T(o.CPoint(i).y)) for i in range(o.PointCount())]


def bus(layer, net, name, *rs, prio=6):
    b.zone(layer, union_poly(*rs), net, f"v6 bus {name}", prio, clearance=HV)


# ---- primary
PB = (-80.0, -66.5)
bus("F.Cu", "DC+", "DC+ F", (9.0, PB[0], 116.0, PB[1]),
    (8.5, PB[1] - 0.1, 18.5, -56.0), (72.4, PB[1] - 0.1, 82.4, -56.5), (109.2, PB[1] - 0.1, 116.0, -55.8))
bus("In1.Cu", "DC+", "DC+ In1", (9.0, PB[0], 116.0, PB[1]),
    (8.5, PB[1] - 0.1, 18.5, -57.5), (72.4, PB[1] - 0.1, 82.4, -56.7), (109.2, PB[1] - 0.1, 116.0, -56.0))
bus("B.Cu", "PGND", "PGND B", (-2.0, PB[0], 116.0, PB[1]),
    (-2.0, PB[1] - 0.1, 8.0, -56.0), (61.9, PB[1] - 0.1, 71.9, -56.7), (98.7, PB[1] - 0.1, 108.7, -56.0))
bus("In2.Cu", "PGND", "PGND In2", (-2.0, PB[0], 116.0, PB[1]),
    (-2.0, PB[1] - 0.1, 8.0, -57.5), (61.9, PB[1] - 0.1, 71.9, -56.7), (98.7, PB[1] - 0.1, 108.7, -56.0))

# ---- ISO
IL = (61.3, 69.2)
bus("B.Cu", "ISODC+", "ISODC+ B", (5.0, IL[0], 108.0, IL[1]),
    (5.4, 48.0, 10.2, IL[0] + 0.1), (31.5, 48.0, 36.5, IL[0] + 0.1), (72.0, 53.0, 78.0, IL[0] + 0.1),
    (101.6, 53.0, 107.6, IL[0] + 0.1))
bus("In1.Cu", "ISODC+", "ISODC+ In1", (5.0, IL[0], 108.0, IL[1]),
    (31.5, 48.0, 36.5, IL[0] + 0.1), (72.0, 53.0, 78.0, IL[0] + 0.1), (101.6, 53.0, 107.6, IL[0] + 0.1))
bus("F.Cu", "ISOPGND", "ISOPGND F", (5.0, IL[0], 86.5, IL[1]),
    (5.4, 48.0, 10.2, IL[0] + 0.1), (21.0, 48.0, 26.0, IL[0] + 0.1), (80.5, 53.0, 86.5, IL[0] + 0.1))
bus("In2.Cu", "ISOPGND", "ISOPGND In2", (5.0, IL[0], 86.5, IL[1]),
    (21.0, 48.0, 26.0, IL[0] + 0.1), (80.5, 53.0, 86.5, IL[0] + 0.1))
bus("F.Cu", "DAB_GROUND", "DAB_GROUND F", (110.1, 41.9, 116.1, 58.75), prio=30)

# ---- ground on In4 over the freed strips
b.zone("In4.Cu", rect(-2.0, -80.0, 116.0, -57.0), "GND", "v6 strip In4 GND", 4, clearance=0.3)
# ISO: joins the v5 card-area In4 ISOGND plane (to y 48.8) east of the CTRL barrier and takes the ISOGND pins of the
# headers J24 / J25 / J26
b.zone("In4.Cu", union_poly((5.0, 52.0, 116.0, 69.2), (5.0, 49.0, 39.0, 52.1), (59.0, 48.0, 116.0, 52.1)), "ISOGND",
       "v6 strip In4 ISOGND", 4,
       clearance=0.3)

after = islands(B)
for k in sorted(set(before) | set(after)):
    if before.get(k) != after.get(k):
        b.log.append(f"islands {k[0]} [{k[1]}] {k[2]}: {before.get(k, '-')} -> {after.get(k, '-')}")
b.save("v6 step 4: DC bus pours and strip ground")
