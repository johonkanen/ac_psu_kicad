#!/usr/bin/env python3
"""v5 step 8 (run once, kipy): aux flyback on the EEL19 with the SMD controller ICE5AR0680AG (user 2026-11-18).

A rough placement showed that the EE25 transformer and the DIP controller of step 7 do not fit the space of
the aux supply (between C12, U8, U9 and J3). Schematic sheet 7 changed to the EEL19 bobbin of the tube PSU
(fly-lead holes beside the body) and to the ICE5AR0680AG in PG-DSO-12; C115 is dropped (C28 is the 15V output
capacitor); R141-R144 and C147 add the line over-voltage stop at about 478 V. The aux parts are still unplaced
in the staging area below the board, so this step only swaps footprints there:
  - removed: C115;
  - new footprint: T1 (EE25 -> EEL19), U18 (DIP-7 -> PG-DSO-12);
  - new parts: R141, R142, R143, R144, C147;
  - values and pad nets of all staged sheet-7 parts follow the new netlist.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, load_fp  # noqa: E402
import v5_parts as V  # noqa: E402

REMOVED = "C115".split()
REPLACED = "T1 U18".split()
NEW = "R141 R142 R143 R144 C147".split()
STAGE_X0, STAGE_TOP = -125.0, -84.0

b = Board(5008)
B = b.b
if b.fp("R141") is not None:
    raise SystemExit("v5 step 8 already applied (R141 is on the board)")
for ref in REMOVED + REPLACED:
    fp = b.fp(ref)
    if fp is None or -T(fp.GetPosition().y) > STAGE_TOP:
        raise SystemExit(f"{ref}: not in the staging area")
    b.log.append(f"{ref}: {fp.GetFPID().GetLibItemName()} removed from the staging area"
                 + (" (new footprint below)" if ref in REPLACED else ""))
    B.Delete(fp)
staged = [fp for fp in B.GetFootprints() if -T(fp.GetPosition().y) < STAGE_TOP]
y = min(-T(fp.GetBoundingBox(False).GetBottom()) for fp in staged) - 4.0
x = STAGE_X0
for ref in REPLACED + NEW:
    c = b.comps[ref]
    fp = load_fp(c["footprint"])
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
        fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
    fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
    fp.SetSheetname(c["sheetname"])
    fp.SetSheetfile(c["sheetfile"])
    B.Add(fp)
    fp.thisown = False
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    fp.SetPosition(pcbnew.VECTOR2I(F(x + 0.5) - bb.GetLeft(), F(-(y - 0.5)) - bb.GetTop()))
    b.log.append(f"{ref}: {c['footprint']} staged at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f})")
    x += T(bb.GetWidth()) + 1.0
n = 0
for ref in sorted(p[0] for p in V.PARTS if p[1] == 7):
    fp = b.fp(ref)
    if fp.GetValue() != b.comps[ref]["value"]:
        b.log.append(f"{ref}: value {fp.GetValue()} -> {b.comps[ref]['value']}")
        fp.SetValue(b.comps[ref]["value"])
    for pad in fp.Pads():
        net = b.pin_net.get((ref, pad.GetNumber()))
        old = pad.GetNetname()
        if net and old != net:
            pad.SetNet(b.net(net))
            b.log.append(f"{ref}-{pad.GetNumber()}: {old or '(none)'} -> {net}")
            n += 1
b.log.append(f"{n} pad nets changed")
b.save("v5 step 8: aux flyback on the EEL19 with the ICE5AR0680AG (staged footprints and nets)")
