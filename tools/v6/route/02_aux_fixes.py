#!/usr/bin/env python3
"""Routing chain step 02 (kipy, after 01 = tools/v6/aux_routes.py): fixes to the replayed aux routes.

Planning session "Fable 2026-11-24", points of the helper's report:
  - The DC+ via of R98-1 sat in the pad (68.04, -49.70) and only 0.50 mm from the v5 aux In2 GND pour (its clearance
    was lowered to 0.5 mm by the helper) and 1.85 mm from the PGND B.Cu pour: below the 2.0 mm inner / 2.5 mm rule.
    The via moves out of the pad to (67.6, -51.4), joined by a short B.Cu track, and gets pour keep-outs of
    via radius + 2.5 mm on every layer where another net pours (In1 ... In4, B.Cu); F.Cu is the DC+ pour itself.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(os.path.dirname(HERE)), "v4"),
                os.path.dirname(os.path.dirname(HERE))]
from v4board import Board, T, P  # noqa: E402

OLD, NEW = (68.04, -49.70), (67.6, -51.4)
b = Board(6201)
B = b.b
via = [t for t in B.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "DC+"
       and abs(T(t.GetPosition().x) - OLD[0]) < 0.01 and abs(-T(t.GetPosition().y) - OLD[1]) < 0.01]
if len(via) != 1:
    raise SystemExit(f"02_aux_fixes: expected the R98-1 via at {OLD}, found {len(via)}")
v = via[0]
v.SetPosition(P(*NEW))
b.log.append(f"DC+ via of R98-1 moved {OLD} -> {NEW} (out of the pad)")
pad = next(p for p in b.fp("R98").Pads() if p.GetNumber() == "1")
px, py = T(pad.GetPosition().x), -T(pad.GetPosition().y)
b.track("B.Cu", [(px, -50.0), (px, -50.8), NEW], 0.6, "DC+")
r = T(v.GetWidth(pcbnew.F_Cu)) / 2 + 2.6       # 2.5 plus the chord error of the 32-gon
for layer in ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"):
    b.pour_keepout(layer, NEW[0], NEW[1], round(r, 3), f"v6 route HV keep-out R98-1 via {layer}")
pcbnew.SaveBoard(B.GetFileName(), B)
print("\n".join(["== route 02: aux fixes"] + ["  " + x for x in b.log]))
