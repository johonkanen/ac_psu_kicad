# v5 card-area layout, revision 2 (proposal, 2026-11-17)

Not on the board yet. Geometry: `tools/v5/card_layout_r2.py`. Check: `python3 tools/v5/layout_proposal.py --rev2`
(`check.txt`, `parts.csv`, `proposal_*.png` in this folder).

## Why

The routing agent could not finish the first placement (311 -> 87 open connections): the CTRL column
beside J11 was 2.9 mm wide, the CTRL area 12.2 mm high, and PEC1, J14 and the resistor blocks stood in
the J11 fan-out. The user's proposal (2026-11-17): tighten the primary logic block south of the card
connector (parts to the bottom side, inner layers for routing), move the primary isolators south, move
one output-side isolator to the east side, and use the bottom side to pack the isolators.

## What changes

| Item | Revision 1 (on the board) | Revision 2 |
|---|---|---|
| C\|P barrier line, U15/U13/U16 | y 18.3, x 56 / 68 / 80 | y 8.3 (10 mm south), x 53 / 65 / 77 |
| Primary area, top edge | y 15.8 | y 5.8 |
| CTRL area at J11 | 12.2 mm high (y 20.8..33.0), 716 mm2 | 22.2 mm high (y 10.8..33.0), 1154 mm2 |
| CTRL column beside J11 (y 33..46.1) | 2.9 mm wide (x 44.4..47.3) | 9.5 mm wide (x 44.4..53.9) |
| North isolator row (bottom, y 35.5) | U21, U19, U20, U22 from x 52.55 | U21, U19, U20 from x 59.15 (6.6 mm east) |
| U22 (ISOADA1 amplifier) | east end of the north row | bottom, (88.0, 13.25), on the new east edge of the southern CTRL part, beside the U7 block |
| U23, U24 | east line x 97.6 | unchanged |
| DC bus band, west end | x 52.3 | x 58.9 |

Primary logic parts that move (the rest of the block stays):

- ADC group AD1, R87, C9, R86, C17, U12, L1, C18: mirrored to the bottom side as one group, 5 mm south
  (under U11). Ground planes on In1 and In4 lie between it and the isolator pins above.
- 1.65 V reference group REF1, C40, C16, R19, R30, C109: mirrored to the bottom side as one group.
- R22 and the isolator capacitors C84, C85, C81 follow the isolators.
- 114 primary tracks and vias north of y 5.8 are deleted and re-routed (In3 is free in the primary area).

In the CTRL area: PEC1 to (51.0, 17.6) and J14 to (66.0, 17.5), both out of the J11 fan-out; the output
filters at 1.6 mm pitch; the difference-amplifier blocks at 2.3 mm row pitch between U22 and U23/U24.

## Checks (layout_proposal.py --rev2)

- Every pair of areas of different domains: >= 5.00 mm. Barrier lines: 2.50 mm from both sides.
- No fixed pad of another domain inside or within 5 mm of an area.
- 15 slots, 1.2 mm wide, each 1.9 mm from the nearest copper area.
- No moved top-side part under a card tail (Ti135 or Ti60), except U8 and J13 as before.
- The bottom-side positions of the two primary groups are rough; the exact courtyard check comes with
  the placement script.

## Open

- The DC bus is still cut at J11 (open since v5 step 1). With the wider CTRL column the link north of
  J11 is 6.6 mm longer.
- The passage north of J11 still carries only about five tracks; about 16 nets need it. Moving
  INU_OUT2 2-3 mm north would open it for the bus and the signals.
- The first routing attempt (branch worktree-agent-a37d57d89bb23f236) is not merged; its router chain
  can be rerun on the new placement.
