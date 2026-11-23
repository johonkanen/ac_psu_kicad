#!/usr/bin/env python3
"""v6 step 1 (run once, kipy): the v6 netlist on the board (V6_PLAN.md section 5 and 6).

The schematic change is in tools/sheets (sheets 1, 2, 5, 6, 8, 10) and tools/v6/v6_parts.py. This step makes the
board follow it, without any layout work:
  1. the 54 removed parts leave the board (switches, gate-card headers, DAB tabs and split capacitors, the two
     switch-node current-sense circuits);
  2. tracks, vias and pours of nets that no longer exist are deleted (gate, source and switch-node nets, the
     sense nets); copper of nets that still exist stays where it is, also in the two strips (step 2 clears them);
  3. pads of kept parts follow the netlist (J5, J7, AFE_OUT1, INU_OUT2 lose their nets; R55 / R50 get the card
     MDAT nets);
  4. the 32 new parts (six CTRL headers, twelve M3 terminals, twelve 100 nF, R257, D17) are put in the staging
     area below the board; step 3 places them.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, load_fp  # noqa: E402
import v6_parts as V  # noqa: E402

STAGE_X0, STAGE_Y0, STAGE_W = -125.0, -92.0, 240.0       # staging area top-left (IPC frame), rows grow downwards

b = Board(6001)
if b.fp("J21") is not None:
    raise SystemExit("v6 step 1 already applied (J21 is on the board)")
live = {n for n in set(b.pin_net.values()) if not n.startswith("unconnected-")}

# -- 1. removed parts
for ref in V.REMOVED:
    fp = b.fp(ref)
    b.log.append(f"{ref} ({fp.GetFPID().GetLibItemName()}) at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f}) deleted")
    b.b.Delete(fp)

# -- 2. copper of nets that are gone
dead = {}
for t in list(b.b.GetTracks()):
    n = t.GetNetname()
    if n and n not in live:
        dead.setdefault(n, [0, 0, 0])[1 if t.GetClass() == "PCB_VIA" else 0] += 1
        b.b.Delete(t)
for z in list(b.b.Zones()):
    n = z.GetNetname()
    if not z.GetIsRuleArea() and n and n not in live:
        dead.setdefault(n, [0, 0, 0])[2] += 1
        b.b.Delete(z)
for n in sorted(dead):
    b.log.append(f"net {n} is gone: {dead[n][0]} tracks, {dead[n][1]} vias, {dead[n][2]} zones deleted")

# -- 3. pads of kept parts
for fp in b.b.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        want = b.pin_net.get((ref, pad.GetNumber()))
        have = pad.GetNetname()
        if want is None:
            if have and not have.startswith("unconnected-") and have not in live:
                b.log.append(f"{ref}-{pad.GetNumber()}: {have} -> no net")
                pad.SetNetCode(0)
        elif have != want:
            b.log.append(f"{ref}-{pad.GetNumber()}: {have} -> {want}")
            pad.SetNet(b.net(want))

# -- 4. new parts in the staging area
x, y, rowh = STAGE_X0, STAGE_Y0, 0.0
for ref, sheet, sym, value, fpid, note in V.PARTS:
    c = b.comps[ref]
    fp = load_fp(c["footprint"])
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
        fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
    fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
    fp.SetSheetname(c["sheetname"])
    fp.SetSheetfile(c["sheetfile"])
    b.b.Add(fp)
    fp.thisown = False
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    w, h = T(bb.GetWidth()) + 1.0, T(bb.GetHeight()) + 1.0
    if x + w > STAGE_X0 + STAGE_W:
        x, y, rowh = STAGE_X0, y - rowh, 0.0
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    fp.SetPosition(pcbnew.VECTOR2I(F(x + 0.5) - bb.GetLeft(), F(-(y - 0.5)) - bb.GetTop()))
    for pad in fp.Pads():
        net = b.pin_net.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(b.net(net))
    x += w
    rowh = max(rowh, h)
b.log.append(f"placed {len(V.PARTS)} v6 parts in the staging area (IPC y {STAGE_Y0} .. {y - rowh:.1f})")
b.save("v6 step 1: v6 netlist on the board (parts removed, dead copper deleted, new parts staged)")
