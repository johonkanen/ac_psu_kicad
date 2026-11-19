#!/usr/bin/env python3
"""v5 step 11 (run once, kipy): cable-tie anchors removed, vertical blade tabs for the DAB transformer wires
(user 2026-11-19).

User: "remove the cable ties lets put vertical blade type connectors in"; "the pe connections are screws"; "the
blade tabs should be in dab transformer wires and ac input and output and rest of the connections are soldered
wires that connect different parts of the circuit together".
  - The eight board-only anchors TIE_* of v4 fix 15 are deleted (16 unplated 3.0 mm holes); the pours refill.
  - ACIN1, ACIN2, ACOUT1 and ACOUT2 already have the footprint of a vertical 6.35 mm blade tab (two 1.4 mm holes
    5.00 mm apart): nothing changes on the board, TE 62409-1 tabs are fitted there (fab/hand_fit.csv).
  - DAB_PRI_1, DAB_PRI_2, DAB_SEC_1 and DAB_SEC_2 (one 3.0 mm hole each) get the two-post tab footprint
    ac_psu:Tab_FASTON250_TE_62409-1_Vertical, each at the position within 3 mm of the old hole (0.5 mm steps,
    0 or 90 degrees) that keeps the largest distance to the other nets without a courtyard overlap, with both
    posts inside a pour of the net.
  - PE1-PE8 are screw connections; AFE_OUT1 and the other wire holes are soldered links inside the unit. They stay.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, load_fp  # noqa: E402
import board_common as bc  # noqa: E402

b = Board(5011)
B = b.b
ties = [fp for fp in B.GetFootprints() if fp.IsBoardOnly() and fp.GetReference().startswith("TIE_")]
if not ties:
    raise SystemExit("v5 step 11 already applied (no cable-tie anchors on the board)")
for fp in sorted(ties, key=lambda f: f.GetReference()):
    b.log.append(f"{fp.GetReference()}: cable-tie anchor at ({T(fp.GetPosition().x):.2f}, {-T(fp.GetPosition().y):.2f}) deleted")
    B.Delete(fp)

edge = B.GetBoardEdgesBoundingBox()
edge.Inflate(-F(0.5))
# DAB_SEC_1 stands between C47 pad 1 (ISODC+, edge at x 92.1) and C50 pad 1 (DAB_CAP_SEC, edge at x 103.2): centred
# between them, with the 2.0 mm pad variant of the footprint. Turned 90 degrees the receptacle would touch Q11.
FIXED = {"DAB_SEC_1": (97.65, 61.7, 0)}
LEADS = ("DAB_PRI_1", "DAB_PRI_2", "DAB_SEC_1", "DAB_SEC_2")
info = {}
for ref in LEADS:
    old = b.fp(ref)
    if str(old.GetFPID().GetLibItemName()) != "Terminal_D4.0mm_Drill3.0mm":
        raise SystemExit(f"{ref}: unexpected footprint {old.GetFPID().GetLibItemName()}")
    info[ref] = (old.GetPosition(), list(old.Pads())[0].GetNetname())
    B.Delete(old)


def copper_of_others(net):
    out = [(t.GetNetname(), t.GetEffectiveShape()) for t in B.GetTracks() if t.GetNetname() != net]
    for fp in B.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net:
                out.append((p.GetNetname(), p.GetEffectiveShape(p.GetPrincipalLayer())))
    return out


def gap(shape, copper):
    lo = 0.0
    while lo < 8.0 and not any(s.Collide(shape, F(lo)) for n, s in copper):
        lo += 0.1
    return lo


def near(fp, copper):
    """Net of the nearest other copper."""
    best = (9.0, "-")
    for p in fp.Pads():
        shp = p.GetEffectiveShape(pcbnew.F_Cu)
        for n, sh2 in copper:
            lo = 0.0
            while lo < best[0] and not sh2.Collide(shp, F(lo)):
                lo += 0.1
            if lo < best[0]:
                best = (lo, n.split("/")[-1] or "(no net)")
    return best[1]


for ref in LEADS:
    pos, net = info[ref]
    c = b.comps[ref]
    copper = copper_of_others(net)
    before = gap(pcbnew.SHAPE_CIRCLE(pos, F(2.0)), copper)
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
    for p in new.Pads():
        p.SetNet(b.net(net))
        p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    others = [o for o in B.GetFootprints() if o.GetReference() != ref and not o.IsFlipped()]
    own = [z.GetFilledPolysList(l) for z in B.Zones() if not z.GetIsRuleArea() and z.GetNetname() == net for l in z.GetLayerSet().CuStack()]
    best = None
    for rot in (() if ref in FIXED else (0, 90)):
        for i in range(-6, 7):
            for j in range(-6, 7):
                dx, dy = 0.5 * i, 0.5 * j
                new.SetOrientationDegrees(rot)
                new.SetPosition(pcbnew.VECTOR2I(int(pos.x + F(dx)), int(pos.y - F(dy))))
                cy = new.GetCourtyard(pcbnew.F_CrtYd)
                hit = [o.GetReference() for o in others if o.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() and o.GetCourtyard(pcbnew.F_CrtYd).Collide(cy, 0)]
                if hit or not edge.Contains(cy.BBox()):
                    continue
                if not all(any(f.Contains(p.GetPosition()) for f in own) for p in new.Pads()):
                    continue        # both posts in a pour of the net
                g = min(gap(p.GetEffectiveShape(pcbnew.F_Cu), copper) for p in new.Pads())
                key = (-round(g, 1), math.hypot(dx, dy))
                if best is None or key < best[0]:
                    best = (key, rot, dx, dy, g)
    if ref in FIXED:
        fx, fy, rot = FIXED[ref]
        dx, dy = fx - T(pos.x), fy + T(pos.y)
        new.SetOrientationDegrees(rot)
        new.SetPosition(pcbnew.VECTOR2I(F(fx), F(-fy)))
        cy = new.GetCourtyard(pcbnew.F_CrtYd)
        if any(o.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() and o.GetCourtyard(pcbnew.F_CrtYd).Collide(cy, 0) for o in others):
            raise SystemExit(f"{ref}: courtyard overlap at its fixed position")
        best = (None, rot, dx, dy, min(gap(p.GetEffectiveShape(pcbnew.F_Cu), copper) for p in new.Pads()))
    if best is None:
        raise SystemExit(f"{ref}: no position without a courtyard overlap within 3 mm")
    _, rot, dx, dy, g = best
    hit = []
    new.SetOrientationDegrees(rot)
    new.SetPosition(pcbnew.VECTOR2I(int(pos.x + F(dx)), int(pos.y - F(dy))))
    b.log.append(f"   {ref}: nearest other net there: {near(new, copper)}")
    if hit:
        raise SystemExit(f"{ref}: the tab's courtyard overlaps {hit} in every position tried")
    b.log.append(f"{ref} [{net.split('/')[-1]}]: Terminal_D4.0mm_Drill3.0mm -> blade tab at ({T(new.GetPosition().x):.2f}, "
                 f"{-T(new.GetPosition().y):.2f}), {rot} degrees; nearest other net {g:.1f} mm (the 4.0 mm pad had {before:.1f} mm)")
b.save("v5 step 11: cable-tie anchors removed, vertical blade tabs for the four DAB transformer wires")

B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
