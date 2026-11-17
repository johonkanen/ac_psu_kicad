# v5 card-area layout, revision 2 (on the board since v5 step 5, 2026-11-17)

Geometry: `tools/v5/card_layout.py` (revision 1 is `card_layout_r1.py`). Placement script:
`tools/v5/v5_5_card_area_r2.py`, log `v5_5_card_area_r2.log`. Check: `tools/v5/check_layout.py` (in check_all).

## Why

The routing agent could not finish the first placement (311 -> 87 open connections): the CTRL column
beside J11 was 2.9 mm wide, the CTRL area 12.2 mm high, and PEC1, J14 and the resistor blocks stood in
the J11 fan-out. The user's proposal (2026-11-17): tighten the primary logic block south of the card
connector (parts to the bottom side, inner layers for routing), move the primary isolators south, move
one output-side isolator to the east side, and use the bottom side to pack the isolators. Approved by
the user on 2026-11-17.

## What changed

| Item | Revision 1 | Revision 2 |
|---|---|---|
| C\|P barrier line, U15/U13/U16 | y 18.3, x 56 / 68 / 80 | y 8.3 (10 mm south), x 52.4 / 64.4 / 76.4 |
| Primary area, top edge | y 15.8 | y 5.8 |
| CTRL area at J11 | 12.2 mm high (y 20.8..33.0) | 22.2 mm high (y 10.8..33.0) |
| CTRL column beside J11 (y 33..46.1) | 2.9 mm wide (x 44.4..47.3) | 8.6 mm wide (x 44.4..53.0) |
| North isolator row (bottom, y 35.5) | U21, U19, U20, U22 from x 52.55 | U21, U19, U20 from x 59.15 (6.6 mm east) |
| U22 (ISOADA1 amplifier) | east end of the north row | bottom, (88.0, 13.25), on the new east edge of the southern CTRL part, beside the U7 block |
| U23, U24 | east line x 97.6 | unchanged |
| DC bus band, west end | x 52.3 | x 58.9 |

Different from the proposal the user saw:

- **CTRL column 8.6 mm, not 9.5 mm.** J6 pin 48 (15V_ISO) is at (56.3, 50.7); at 9.5 mm the column's corner
  was less than 5 mm from it. The proposal check looked only at pads inside the card outline. The corner is now
  5.1 mm from the pin.
- **Isolators 3.6 mm west, not 3 mm**: U16's courtyard clears the spare isolator U17.
- **The 1.65 V reference group stays on the top side** and moves 24.75 mm east and 5 mm south (x 70.5..79.2,
  y -2.9..1.0), into the free primary area south of U13/U16. Mirrored to the bottom its through vias came
  under U15's pads. REF_1V65 now runs about 20 mm back to R7/C97/R21/C95 (to route).
- **INU_OUT2 does not move.** The terminal's body (y 54.9..65.1) touches the bodies of Q5/Q6 (from y 65.1),
  and its north pads are 2.06 mm from Q6's gate pad. The passage north of J11 stays as it was.

Primary logic parts that moved (the rest of the block stays, with its routing):

- ADC group AD1, R87, C9, R86, C17, U12, L1, C18: mirrored to the bottom side as one group with its 82
  tracks and vias, 5 mm south (under U11). Ground planes on In1 and In4 lie between it and U11.
- Reference group REF1, C40, C16, R19, R30, C109: see above, with its 38 tracks and vias.
- R22 and the isolator capacitors C84, C85, C81 follow the isolators.
- 143 tracks and vias deleted (primary copper north of y 5.8, nets of the moved parts); they are ratsnest.

In the CTRL area: PEC1 at (51.0, 17.6) and J14 at (66.6, 17.5), both out of the J11 fan-out; the output
filters at 1.6 mm pitch beside J11 pins 1/3/4; the difference-amplifier resistors at 2.3 mm row pitch.

## Checks

`tools/check_all.sh`: ALL CHECKS PASSED (check_layout: 124 placed / moved parts in their domain areas,
15 slots, 10 plane zones, 0 errors; domain_gaps: 0 violations; DRC: 0 shorts).

## Open

- The DC bus is still cut at J11 (open since v5 step 1); its band now ends at x 58.9.
- The passage north of J11 (2.9 mm between the J8 pads and the INU_OUT2 pads) carries about five tracks
  per layer; about 16 nets need it. In3 and In4 are free there.
- Routing: 306 open connections on 120 nets (`routing_list.md`, `routing_brief.md`).
