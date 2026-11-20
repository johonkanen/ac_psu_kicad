# Routing pass 4 (step 16 placement): the passage north of J11 as a fanned bus

Branch `routing-pass4`, from 5237c70. A gauge, not a layout. Coordinates: IPC frame, mm, y up. Chain
`tools/v5/route_pass1/chain.sh`; final board `build/route_p4/routed.kicad_pcb` (not committed), refilled copy
`build/pass4/check/ac_psu.kicad_pcb`.

## Verdict

- **The board is legal this time.** 0 shorts, 0 clearance errors, parity 0, domain gaps 0, `check_layout.py` OK,
  no pour lost an island (84 pours compared before / after), no signal on In2, existing copper unchanged.
- **Not everything has a lane.** All 12 signals do (11 drawn on In3, the relay line on In4, found by the router).
  Of the rails, 5V_ISOL (0.8 mm) and ISOGND (0.4 mm) are drawn on In4; **15V_ISO and 3V3_ISO have none**. Room is
  there (about 4 free In4 lanes); what is missing is a drawn entry. The relay line shows one exists: a via east of
  the west pins of J4 at (99.3, 51.75), then In4 north of J4. I did not draw the two rails that way.
- **The ISO side does not close yet: the six divider taps are open** (pass 3: three taps, INU_ADCLK, PWM_Q7).
  Everything else that goes west is closed: PWM_Q5 / Q7 / TRANS6, the sigma-delta pair, the relay line, 5V_ISOL.
  The taps fail in the router, not for lack of room: three have their lane and west end and miss the stretch
  from the U7 / U2 block to the lane entry; for the other three the router deleted the drawn lane after failing.

## Pass 3 against pass 4

| | Pass 3 | Pass 4 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 39 on 17 nets | 25 on 17 nets |
| Signal connections open (of 174) | 9 | 10: six taps, DAB_PWM_PRI_HI_ISO, CLK1, AUX_VIN, AUX_LOVP |
| West-bound signals open (12 nets) | 5 | 6 (the taps) |
| Supply open, CTRL | 0 | 0 |
| Supply open, ISO | 18 | 4: 15V_ISO 2, 3V3_ISO 1, ISOGND 1; 5V_ISOL 0 |
| Supply open, primary | 8 | 8: GND 7, 15V 1 |
| Items on the wire-link nets | 4 (pour cut) | 3 (as placed) |
| Vias on signals, all / new | 212 / 154 | 207 / 149 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps (`domain_gaps.py --board`) | 0 | 0 |
| `check_layout.py --board` | OK | OK |
| Pours whose island count changed | B.Cu ISODC+ 1 -> 2 | none cut (In2 3V3_CTRL 8 -> 1: its slivers join) |
| Signal tracks on In2 in the card planes | 0 | 0 |
| HV spacing (`check_pass.py`, my reading) | 0 | 0 |
| Existing tracks / vias changed | 0 | 0 |

Copper outside the `unrouted` rectangle (`check_pass.py`): the fan itself (In3 / In4 tracks up to y 57.4 north of
J8 and J6; 64 track ends at y 54..55.3, 20 above); 17 ends of 15V on B.Cu at x 59.5..65, y -24.35..-25.25 and 3 of
GPIO_BYPASS_RLY at y -22.05, as in pass 3. The router laid the 15V track at y -74 again; the prune step deleted it.

## Lanes

Counted on the board, drawn and DRC-gated: the pinch at x 42.5..51.5 holds 14 lanes per layer (y 51.25..55.215,
0.152 mm at 0.305 mm), but the neck between the INU_OUT2 west pad (44.06, 57.06) and the corner pin of J8
(41.4, 52.2) passes **11 per layer** (5.54 mm between centres, 3.08 mm for centre lines; the lanes cross it at
28.7 degrees, DRC-gated). The lanes pass the pinch at y 52.165..55.215 and spread over J8 and J6 at
y 52.84..55.89.

| Layer | Lane | Net | Entry | West end |
|---|---|---|---|---|
| In3 | 0 | MDATA_INU | J6 / J4 gap x 77.40, hook from U21-12 | J8 column x 34.39, scripted to a via at R50-2: closed |
| In3 | 1 | INU_ADCLK | x 77.705, hook from U21-14 | column x 34.085, via at U4-7, router: closed |
| In3 | 2 | Net-(U7A-+) | x 78.60 | lane deleted by the router after it failed: open |
| In3 | 3 | Net-(U7A--) | x 78.905 | lane deleted: open |
| In3 | 4 | Net-(U7B--) | x 79.21 | column x 33.17, via on the old In2 track at (22.28, 46.54): west closed, east open |
| In3 | 5 | Net-(U7B-+) | x 79.515 | column x 25.50, via on the old track at (22.44, 47.90): west closed, east open |
| In3 | 6 | Net-(U2--) | x 79.82 | column x 25.195, via on the old track at (21.10, 40.15): west closed, east open |
| In3 | 7 | Net-(U2-+) | x 80.125 | lane deleted: open |
| In3 | 8 | PWM_TRANS6 | x 82.38, hook from U20-10 | column x 24.585, under J8, gap x 21.715, pin J8-47: closed |
| In3 | 9 | PWM_Q7 | x 83.64, hook from U20-11 | column x 24.255, pin J8-43 from the north-east: closed |
| In3 | 10 | PWM_Q5 | x 84.92, hook from U20-12 | gap x 22.985 of the north row, pin J8-44: closed |
| In4 | 0..3 | 5V_ISOL, 0.8 mm | pin J4-45, no via | drops onto J6-45 and J8-45: closed |
| In4 | 3..4 | ISOGND, 0.4 mm | In4 plane edge through the J4 column at x 90.69, no via | around J8 to pin J8-46: closed (one pad, J4-46, left) |
| In4 | about 5 | GPIO_BYPASS_RLY_ISO | router: via (99.3, 51.75), north of J4 at y 57.4 | router: closed |
| In4 | 4 or so spare | - | - | - |

Used 11 of 11 on In3; about 7 of 11 on In4. Sigma-delta pair and taps: there was no choice of layer (In4 can
only be entered by nets that start on a through-hole pin, a plane edge, or far east), so they are on In3, 0.11 mm
above the Q5_S pour; the pair has the two southmost lanes.

Why the rails cannot simply go anywhere on In4: 5V_ISOL has to drop onto the north-row pins J6-45 and J8-45, so
it is the southmost In4 lane from J4-45 to J8; every In4 net that came up through the J6 columns or the J6 / J4
gap would cross it. In4 entries are therefore only possible east of J4-45 (ISOGND, the relay line).

## Nets still open

| Net | Why |
|---|---|
| Net-(U7B--), Net-(U7B-+), Net-(U2--) | lane and west end are there; the router did not make the 60 mm from the U7 / U2 block to the lane entry at (79.2..79.8, 49.3). Its summary counts the west copper as unconnected: it does not see a via set in the middle of an old track segment, and then fails the net as a whole. Impression, from its log |
| Net-(U7A-+), Net-(U7A--), Net-(U2-+) | the same failure, and the router then deleted the drawn lane. Their old tracks do have legal via points ((4.92, 47.22), (4.63, 48.73), (23.58, 47.08)) |
| DAB_PWM_PRI_HI_ISO | found: in the leftovers step PWM_G3_ISO and DAB_PWM_PRI_LO_ISO are routed first and box in its stub end at J11-22 (log names both). Pass 2 happened to route them in another order. Not fixed; the step needs pin order |
| CLK1 | R87 pad 3, unchanged placement |
| AUX_VIN (1), AUX_LOVP (1) | as pass 3 |
| 15V_ISO (2) | no lane: old In2 pieces west of J8 and at J6-48 not joined |
| 3V3_ISO (1) | no lane: west island (U4-8, C37) |
| ISOGND (1) | pin J4-46 to the plane 0.3 mm south of it; the step finished in 49 s (54 of 55) |
| GND (7), 15V (1) | as pass 3 (low-voltage pads next to HV pads in the aux area) |

West ends that were open in pass 3:
- **INU_ADCLK at U4-7**: closed. It needed a via beside the pad, which the router did not place.
- **PWM_Q7 at J8-43**: closed. It needed a 0.152 mm track through a 0.46 mm pin gap, off the router's grid; now
  the lane reaches the pin from the north-east without a gap.
- **Taps at their old In2 ends**: the ends lie under pours, but each old track has legal via points a few
  millimetres along. Three are tied in by script. No old stub was found to block; none is named for deletion.

## Faults of this pass (mine), and tooling changes

- The prune step first deleted In3 / In4 lanes above y 55.3 (it took them for trespassers of the outer-layer
  fence). Fixed; the last chain step was rerun from the board before it. The numbers above are from the rerun.
- The chain was restarted twice: the first HV step was killed by an unknown cause, and the west-end links failed
  on a 0.003 mm margin and were redone.
- New: via keep-out over the J6 / J4 gap and north of y 54; `via_scan.py` now uses the zone's own clearance;
  `check_pass.py` compares the islands of every pour; `scripted.py fan`, `hooks`, `westends`.

## Verified how

- By tool on the final refilled board: the table; `check_layout.py --board` OK; `domain_gaps.py --board` 0;
  kicad-cli DRC with parity; pour islands; the fan, hooks and west ends gated by DRC before routing.
- Seen in a render of the final board: In3 and In4 of the passage (x 15..60, y 49..59), In3 of the isolator row.
- Not looked at: In4 / B.Cu of the isolator row, the west-end window, the other windows.
- Impression: why the router fails the taps; that 15V_ISO and 3V3_ISO would fit by the relay line's way in.
- About 3 h 20 min against the 2 h budget. `tools/check_all.sh` was not run on the routed board.

## Files

- `tools/v5/route_pass1/` and `routing.json`.
- `reports/v5_layout/routing_pass4/`: renders (passage, isorow, west, j11, aux, card), `check_board.txt`,
  `check_pass.txt`, `check_layout.txt`, `domain_gaps.txt`, `via_scan_strict.txt`, `chain_run.log`.
