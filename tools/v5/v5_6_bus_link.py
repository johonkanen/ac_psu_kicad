#!/usr/bin/env python3
"""v5 step 6 (run once, kipy): wire link of the isolated DC bus past J11 (user 2026-11-18).

The CTRL domain at J11 with its 5 mm barriers has cut ISODC+ (B.Cu) and ISOPGND (F.Cu) into a west and
an east piece since v5 step 1, and INU_OUT2 cannot move to open a copper path (STATUS.md, v5 step 5).
User: two pieces of 2.5 mm round enamelled copper wire, soldered, on the bottom side (15 mm standoffs).
Four solder holes (ac_psu:Terminal_D4.0mm_Drill3.0mm, schematic sheet 4):

  BUSP1 (ISODC+, west)   - BUSP2 (ISODC+, east, in the bus band under J6)
  BUSN1 (ISOPGND, west)  - BUSN2 (ISOPGND, east, in the bus band under J4)

Each hole sits in a pour of its own net and is joined to it without thermal relief; it keeps 2.5 mm from the
other nets on the outer layers (CLEARANCE and CUT below). The enamel is not safety insulation: the wires are formed to stay >= 5 mm from the
CTRL area and J11's pin tails and clear of the other bottom-side metal (fab/README.md).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, P, load_fp  # noqa: E402
import board_common as bc  # noqa: E402

HOLES = {"BUSP1": (32.5, 38.5), "BUSN1": (33.0, 31.5), "BUSP2": (63.5, 45.5), "BUSN2": (90.5, 45.0)}
# Clearance of each pad to other nets (pad property, all layers). The pads are bare soldered metal at DC-link
# voltage: 2.5 mm to the other bus net on the outer layers, as between the pins of the TO-247 transistors.
#   BUSP1, BUSN1: 2.5 mm (the other bus net's pour is on the opposite outer layer; nothing on the inner layers).
#   BUSP2, BUSN2: in the bus band under the card, through the ISO planes and the In3 signal layer. 0.5 mm there, so
#   that the planes keep their width and the signals of U21 still pass; on the outer layers the 2.5 mm come from
#   the position: BUSN2 is 3 mm from the ISODC+ pour (B.Cu), and the dead end of the ISOPGND pour (F.Cu) west of
#   x 68 is removed (CUT) so that nothing of it is near BUSP2.
# Not used: (64, 59.5) and (64.5, 65.5) between Q6 and Q8 for BUSN2. The first cut the Q6 gate strap on In1 in
# two, the second lies under the body of Q6 and 0.55 mm from the Q7_S pour.
CLEARANCE = {"BUSP1": 2.5, "BUSN1": 2.5, "BUSP2": 0.5, "BUSN2": 0.5}
CUT = ("ISOPGND", "F.Cu", (56.0, 40.5, 68.0, 50.0))

b = Board(5006)
B = b.b
if b.fp("BUSP1") is not None:
    raise SystemExit("v5 step 6 already applied (BUSP1 is on the board)")
for ref, (x, y) in HOLES.items():
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
    fp.SetPosition(P(x, y))
    for pad in fp.Pads():
        net = b.pin_net[(ref, pad.GetNumber())]
        pad.SetNet(b.net(net))
        pad.SetLocalClearance(F(CLEARANCE[ref]))
        pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.log.append(f"{ref}: solder hole 3.0 mm, pad 4.0 mm at ({x}, {y}) on {net}, pad clearance {CLEARANCE[ref]} mm")
net, layer, (x0, y0, x1, y1) = CUT
box = pcbnew.SHAPE_POLY_SET()
box.NewOutline()
for q in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
    box.Append(F(q[0]), F(-q[1]))
ncut = 0
for z in list(B.Zones()):
    if z.GetIsRuleArea() or z.GetNetname().split("/")[-1] != net or B.GetLayerName(z.GetFirstLayer()) != layer:
        continue
    o = z.Outline()
    a0 = o.Area()
    if not o.Collide(box, 0):
        continue
    o.BooleanSubtract(box)
    if o.OutlineCount() != 1:
        raise SystemExit(f"{z.GetZoneName()}: {o.OutlineCount()} outlines after the cut (the file keeps one)")
    z.SetNeedRefill(True)
    z.HatchBorder()
    ncut += 1
    b.log.append(f"zone {z.GetZoneName()} [{net}] {layer}: dead end x {x0}..{x1}, y {y0}..{y1} removed "
                 f"({(a0 - o.Area()) / F(1) / F(1):.0f} mm2), 2.5 mm from BUSP2")
if ncut != 1:
    raise SystemExit(f"{ncut} zones cut, expected 1")
b.save("v5 step 6: DC bus wire link past J11 (four solder holes for 2.5 mm enamelled copper wire)")

# fill once more on the board as read from the file (v5 step 5: a fill in the session of the change can miss items)
B2 = pcbnew.LoadBoard(bc.BOARD)
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(bc.BOARD, B2)
print("  zones filled again on the reloaded board")
