#!/usr/bin/env python3
"""v5 step 7 (run once, kipy): aux flyback controller ICE5AR0680BZS on the board (user 2026-11-18).

Schematic sheet 7 changed from the UCC28710 + 950 V MOSFET to the Infineon ICE5AR0680BZS (fixed 100 kHz,
integrated 800 V / 0.71 ohm CoolMOS and error amplifier, PG-DIP-7); DC+ is limited to 450 V. The aux
flyback parts are still unplaced in the staging area below the board, so this step only swaps footprints
there:
  - removed: Q15, Q16 (gate buffer), Q17 (MOSFET), R103, R104, R106, R107;
  - new footprint: U18 (SOIC-7 -> DIP-8 without pin 6), C113 (1210 -> 6.3 x 5.4 mm electrolytic);
  - new parts: R136-R138 (start-up chain), R139, R140, C145, C146 (FB network);
  - values and pad nets of all staged sheet-7 parts follow the new netlist (R101/R102 are the VERR divider now).
The new and re-footprinted parts go into one more row at the bottom of the staging area.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, load_fp  # noqa: E402
import v5_parts as V  # noqa: E402

REMOVED = "Q15 Q16 Q17 R103 R104 R106 R107".split()
REPLACED = "U18 C113".split()
NEW = "R136 R137 R138 R139 R140 C145 C146".split()
STAGE_X0, STAGE_TOP = -125.0, -84.0

b = Board(5007)
B = b.b
if b.fp("R136") is not None:
    raise SystemExit("v5 step 7 already applied (R136 is on the board)")
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
b.save("v5 step 7: aux flyback controller ICE5AR0680BZS (staged footprints and nets)")
