#!/usr/bin/env python3
"""v5 step 15 (run once, kipy): placement and channel changes after routing pass 1
(reports/v5_layout/routing_pass1.md on branch routing-pass1; user 2026-11-19: "Go with your recommendation").

  1. U19 and U21 change places in the north isolator row (U19 to x 63.65, U21 to x 74.6), and the channels of
     U19 / U20 are reordered (tools/sheets/sheet11.py): west to east the ISO pins now carry the J6 nets, the J8
     nets, the sigma-delta lines, the relay and the J4 nets, each under the gap it leaves through. The decoupling
     capacitors stay where they are (C121 / C122 now stand at U19, C117 / C118 at U21; same nets).
  2. J14 (5 V link holes) leaves the diagonal of the J11 fan-out: pad 1 to (69.0, 23.5), between the LDO block
     and the difference amplifiers.
  3. Clamp of the aux flyback: D13 goes to the bottom side south of D12, anode below fly-lead hole 11 (AUX_VIN),
     cathode below D12's cathode; D12 moves 1.0 mm north to make room (1.5 mm stay between its
     drain pad and R105). The clamp loop was 25 mm long.
  4. R139 (FB RSel) moves from under the card to U18 pin 3, between T1 pins 1 and 2 on the bottom side.
R87 (CLK1 open in pass 1) is not changed: see STATUS.md. No routing. Checks: tools/v5/check_layout.py and the DRC (tools/check_all.sh).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board, F, T, P  # noqa: E402

b = Board(5015)
B = b.b


def at(ref):
    p = b.fp(ref).GetPosition()
    return round(T(p.x), 3), round(-T(p.y), 3)


def pad(ref, num):
    p = next(q for q in b.fp(ref).Pads() if q.GetNumber() == num).GetPosition()
    return round(T(p.x), 3), round(-T(p.y), 3)


if at("U19") == (63.65, 35.5):
    raise SystemExit("v5 step 15 already applied (U19 is at x 63.65)")
if (at("U19"), at("U21")) != ((74.6, 35.5), (63.65, 35.5)):
    raise SystemExit(f"U19 / U21 not where step 5 put them: {at('U19')} {at('U21')}")


def move(ref, x, y, rot=None, side=None, why=""):
    fp = b.fp(ref)
    old = at(ref) + (fp.GetOrientationDegrees(), "B" if fp.IsFlipped() else "F")
    fp.SetPosition(P(x, y))
    if side and (side == "B") != fp.IsFlipped():
        fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    if rot is not None:
        fp.SetOrientationDegrees(rot)
    new = at(ref) + (fp.GetOrientationDegrees(), "B" if fp.IsFlipped() else "F")
    b.log.append(f"{ref}: {old} -> {new}  {why}")


# 1. isolator row
move("U19", 63.65, 35.5, why="west end of the row")
move("U21", 74.6, 35.5, why="middle of the row")
for ref in ("U19", "U20", "U21"):
    b.sync_pads(ref)
want = {("U19", "10"): "PWM_TRANS5", ("U19", "15"): "PWM_TRANS6", ("U20", "13"): "PWM_TRANS4", ("U20", "15"): "DAB_PWM_HI_SEC",
        ("U20", "12"): "GPIO_BYPASS_RLY_ISO", ("U21", "14"): "INU_ADCLK"}
for (ref, num), net in want.items():
    have = next(q for q in b.fp(ref).Pads() if q.GetNumber() == num).GetNetname()
    if have != net:
        raise SystemExit(f"{ref}-{num}: {have}, expected {net} (regenerate sheet 11 first)")
if pad("U19", "10")[0] > pad("U19", "15")[0]:
    raise SystemExit("U19 pin 10 is not at the west end")

# 2. J14
move("J14", 69.0, 23.5, why="out of the J11 fan-out")

# 3. clamp
move("D12", 80.9, -47.2, why="1.0 mm north, room for D13")
move("D13", 79.2, -53.3, rot=180, side="B", why="bottom side, south of D12")
if pad("D13", "A")[0] > pad("D13", "C")[0]:
    raise SystemExit(f"D13: anode not at the west end {pad('D13', 'A')}")

# 4. R139
move("R139", 80.7, -35.1, rot=0, why="at U18 pin 3 / C146, GND end at T1 pin 2")
if pad("R139", "1")[0] > pad("R139", "2")[0]:
    raise SystemExit("R139: pad 1 (AUX_COMP) not at the west end")

# no copper of another net on a pad of a moved / re-netted part
bad = []
for ref in ("U19", "U20", "U21", "J14", "D12", "D13", "R139"):
    for q in b.fp(ref).Pads():
        for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu):
            if not q.IsOnLayer(lid):
                continue
            for t in B.GetTracks():
                if t.GetNetCode() != q.GetNetCode() and t.IsOnLayer(lid) and \
                        t.GetEffectiveShape(lid).Collide(q.GetEffectiveShape(lid), F(0.15)):
                    bad.append(f"{ref}-{q.GetNumber()} [{q.GetNetname()}]: {t.GetClass()} [{t.GetNetname()}] on "
                               f"{B.GetLayerName(lid)} at ({T(t.GetStart().x):.2f}, {-T(t.GetStart().y):.2f})")
if bad:
    raise SystemExit("copper of another net at a moved pad:\n  " + "\n  ".join(sorted(set(bad))))
b.save("v5 step 15: placement after routing pass 1")

B2 = pcbnew.LoadBoard(B.GetFileName())
pcbnew.ZONE_FILLER(B2).Fill(B2.Zones())
pcbnew.SaveBoard(B2.GetFileName(), B2)
