#!/usr/bin/env python3
"""v5 step 12 (run once, kipy): PE1-PE8 are M3 screw connections (user 2026-11-19: "standoff and a m3 pan head").

  - PE2, PE4 (2.0 mm), PE3 (2.55 mm) and PE8 (1.52 mm hole, 3.0 mm pad) get the footprint of the others,
    ac_psu:Terminal_D4.0mm_Drill3.0mm (3.0 mm hole, 4.0 mm pad).
  - The screw head (top, taken as 6.0 mm) and the standoff (bottom, taken as 6.4 mm: 5.5 mm hexagon across the
    corners) are at PE potential and lie on the solder mask. The pours of other nets are cut back to 2.5 mm
    (basic insulation to PE, tools/v4/domains.py) from those circles: 5.5 mm from the hole centre on F.Cu, 5.7 mm
    on B.Cu. Tracks, pads and vias of other nets inside those circles stop the script; so does a part closer to
    the hole centre than the head on its side, and other copper within 2.5 mm of the pad on an inner layer.
  - PE4 moves 0.8 mm west, to the middle between C24 and R10 (user: "positions are not fixed, move the holes"):
    the head then has 0.2 mm to the drawn body of each. Its F.Cu track is extended to the new position.
  - PE6 and PE7 are NOT touched (they are 3.0 mm holes already): each stands in the middle of a 5.8 / 5.9 mm space
    between the bodies of two Y capacitors, where no position fits a 6.0 mm head. Open, see STATUS.md.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, load_fp  # noqa: E402
import board_common as bc  # noqa: E402

HEAD = {"F.Cu": 6.0, "B.Cu": 6.4}       # mm, diameter of the PE metal lying on the board
GAP = 2.5
NEW = "Terminal_D4.0mm_Drill3.0mm"
ALL = ["PE%d" % i for i in range(1, 9)]
OPEN = {"PE6": "between C29 and C30", "PE7": "between C31 and C32"}     # no room for the head: not changed here
REFS = [r for r in ALL if r not in OPEN]
MOVE = {"PE4": (-89.8, -43.5)}

b = Board(5012)
B = b.b
if all(str(b.fp(r).GetFPID().GetLibItemName()) == NEW for r in ALL):
    raise SystemExit("v5 step 12 already applied (all PE holes are 3.0 mm)")

for ref in REFS:
    old = b.fp(ref)
    name = str(old.GetFPID().GetLibItemName())
    if name == NEW:
        continue
    c = b.comps[ref]
    if c["footprint"].split(":")[-1] != NEW:
        raise SystemExit(f"{ref}: the netlist names {c['footprint']}")
    pad = list(old.Pads())[0]
    pos, net, clr, was = old.GetPosition(), pad.GetNetname(), pad.GetLocalClearance(), (T(pad.GetDrillSize().x), T(pad.GetSizeX()))
    B.Delete(old)
    new = load_fp(c["footprint"])
    new.SetReference(ref)
    new.SetValue(c["value"])
    for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
        new.GetField(ftype).SetText(c["fields"].get(fname, ""))
    new.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
    new.SetSheetname(c["sheetname"])
    new.SetSheetfile(c["sheetfile"])
    B.Add(new)
    new.thisown = False
    new.SetPosition(pos)
    for p in new.Pads():
        p.SetNet(b.net(net))
        if clr is not None:
            p.SetLocalClearance(clr)
    b.log.append(f"{ref} [{net.split('/')[-1]}] at ({T(pos.x):.1f}, {-T(pos.y):.1f}): hole {was[0]:.2f} -> 3.00 mm, pad {was[1]:.1f} -> 4.0 mm")


for ref, (x, y) in MOVE.items():
    fp = b.fp(ref)
    pad = list(fp.Pads())[0]
    old, new = fp.GetPosition(), pcbnew.VECTOR2I(F(x), F(-y))
    ends = [t for t in B.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetNetname() == pad.GetNetname() and old in (t.GetStart(), t.GetEnd())]
    if not ends:
        raise SystemExit(f"{ref}: no track of its net ends at the hole")
    fp.SetPosition(new)
    for layer, width in sorted({(t.GetLayer(), t.GetWidth()) for t in ends}):
        t = pcbnew.PCB_TRACK(B)
        t.SetStart(old)
        t.SetEnd(new)
        t.SetLayer(layer)
        t.SetWidth(width)
        t.SetNet(pad.GetNet())
        B.Add(t)
        t.thisown = False
    b.log.append(f"{ref}: moved from ({T(old.x):.2f}, {-T(old.y):.2f}) to ({x}, {y}); track extended on "
                 + ", ".join(sorted({B.GetLayerName(t.GetLayer()) for t in ends})))

INNER = [l for l in B.GetEnabledLayers().CuStack() if l not in (pcbnew.F_Cu, pcbnew.B_Cu)]


def circle(c, r):
    s = pcbnew.SHAPE_POLY_SET()
    s.NewOutline()
    for k in range(72):
        s.Append(int(c.x + F(r) * math.cos(math.radians(5 * k))), int(c.y + F(r) * math.sin(math.radians(5 * k))))
    return s


for ref in REFS:
    fp = b.fp(ref)
    pad = list(fp.Pads())[0]
    c, net = pad.GetPosition(), pad.GetNetname()
    ring = pcbnew.SHAPE_CIRCLE(c, F(2.0 + GAP))
    for layer in INNER:
        for t in B.GetTracks():
            if t.GetNetname() != net and t.GetClass() != "PCB_VIA" and t.GetLayer() == layer and t.GetEffectiveShape().Collide(ring, 0):
                raise SystemExit(f"{ref}: track of {t.GetNetname()} on {B.GetLayerName(layer)} within {GAP} mm of the pad")
        for z in B.Zones():
            if not z.GetIsRuleArea() and z.GetNetname() != net and z.IsOnLayer(layer) and z.Outline().Collide(ring, 0):
                raise SystemExit(f"{ref}: zone {z.GetZoneName()} on {B.GetLayerName(layer)} within {GAP} mm of the pad")
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
            if o.GetReference() != ref and o.IsFlipped() == (lname == "B.Cu"):
                cy = o.GetCourtyard(pcbnew.B_CrtYd if o.IsFlipped() else pcbnew.F_CrtYd)
                if cy.OutlineCount():
                    d = T(math.sqrt(cy.SquaredDistance(c))) if not cy.Contains(c) else 0.0
                    if d < dia / 2:
                        raise SystemExit(f"{ref}: courtyard of {o.GetReference()} is {d:.2f} mm from the hole centre, under the {dia} mm head")
                    if d < dia / 2 + 1.5:
                        b.log.append(f"   {ref}: courtyard of {o.GetReference()} is {d - dia / 2:.2f} mm from the edge of the {dia} mm head ({lname[0]} side)")
        cut = circle(c, r + 0.02)
        for z in list(B.Zones()):
            if z.GetIsRuleArea() or z.GetNetname() == net or not z.IsOnLayer(layer):
                continue
            o = z.Outline()
            if not o.Collide(cut, 0):
                continue
            if z.GetLayerSet().CuStack().size() != 1:
                raise SystemExit(f"{z.GetZoneName()}: zone on several layers")
            a0 = o.Area()
            o.BooleanSubtract(cut)
            if o.OutlineCount() != 1:
                raise SystemExit(f"{z.GetZoneName()}: {o.OutlineCount()} outlines after the cut at {ref}")
            z.SetNeedRefill(True)
            z.HatchBorder()
            b.log.append(f"{ref}: zone {z.GetZoneName()} [{z.GetNetname().split('/')[-1]}] {lname} cut back to {r} mm from the hole centre "
                         f"({(a0 - o.Area()) / F(1) / F(1):.1f} mm2 of outline)")
b.save("v5 step 12: PE1-PE8 3.0 mm holes for M3 screws, pours 2.5 mm from the screw head and the standoff")

B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
for ref in REFS:
    pad = list(B2.FindFootprintByReference(ref).Pads())[0]
    c, net = pad.GetPosition(), pad.GetNetname()
    res = []
    for lname in ("F.Cu", "B.Cu"):
        layer = B2.GetLayerID(lname)
        d = 0.0
        probe = pcbnew.SHAPE_CIRCLE(c, F(0.01))
        shapes = [z.GetFilledPolysList(layer) for z in B2.Zones() if not z.GetIsRuleArea() and z.GetNetname() != net and z.IsOnLayer(layer)]
        shapes += [t.GetEffectiveShape() for t in B2.GetTracks() if t.GetNetname() != net and (t.GetClass() == "PCB_VIA" or t.GetLayer() == layer)]
        shapes += [p.GetEffectiveShape(layer) for o in B2.GetFootprints() for p in o.Pads() if p.GetNetname() != net and p.IsOnLayer(layer)]
        while d < 12 and not any(s.Collide(probe, F(d)) for s in shapes):
            d += 0.05
        g = d - HEAD[lname] / 2
        res.append(f"{lname} {g:.2f} mm")
        if g < GAP - 0.06:
            raise SystemExit(f"{ref}: {g:.2f} mm from the {HEAD[lname]} mm head to other copper on {lname}")
    print(f"  {ref}: head / standoff to the nearest other copper: " + ", ".join(res))
