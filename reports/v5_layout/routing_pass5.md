# Routing pass 5 (step 16 placement): the runs to and from the fanned bus drawn by script

Branch `routing-pass5`, from 559175a. A gauge, not a layout. Coordinates: IPC frame, mm, y up. Chain
`tools/v5/route_pass1/chain.sh` (new: `maze.py`); final board `build/route_p5/routed.kicad_pcb` (not committed),
refilled copy `build/pass5/check/ac_psu.kicad_pcb`. One chain run, no rerun.

## Verdict

- **The ISO signals close.** All 12 nets that go west past J11 are connected: the six divider taps, the
  sigma-delta pair, the relay line, PWM_Q5 / Q7 / TRANS6. So are the PWM bundle, the measurement chain and 5V_ISOL.
- **The board is legal.** 0 shorts, 0 clearance errors, parity 0, domain gaps 0, `check_layout.py` OK, no pour
  lost an island, no signal on In2, existing copper unchanged, HV check 0.
- **Open besides CLK1:** DAB_PWM_PRI_HI_ISO, AUX_VIN, AUX_LOVP, and supply pads: 15V_ISO 7, 15V 6, GND 7,
  3V3_ISO 1, ISOGND 1. Both 15V steps were skipped whole because I had cut their time budget to 300 s to save
  time (pass 4 needed 206 s and 260 s); that is my doing, not a finding. 15V_ISO and 3V3_ISO now have their In4
  lanes; 3V3_ISO reaches U4 / C37 through its lane, the 15V_ISO lane is drawn but not all of its ends are joined.

## Pass 4 against pass 5

| | Pass 4 | Pass 5 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 25 on 17 nets | 29 on 11 nets |
| Signal connections open (of 174) | 10 | 4: DAB_PWM_PRI_HI_ISO, CLK1, AUX_VIN, AUX_LOVP |
| West-bound signals open (12 nets) | 6 | 0 |
| Supply open, CTRL | 0 | 0 |
| Supply open, ISO | 4 | 9: 15V_ISO 7 (step skipped), 3V3_ISO 1, ISOGND 1; 5V_ISOL 0 |
| Supply open, primary | 8 | 13: GND 7, 15V 6 (step skipped) |
| Items on the wire-link nets | 3 | 3 |
| Vias on signals, all / new | 207 / 149 | 220 / 162 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps (`domain_gaps.py --board`) | 0 | 0 |
| `check_layout.py --board` | OK | OK |
| Pours whose island count changed (84 compared) | none cut | none cut (In2 3V3_CTRL 8 -> 1: slivers join) |
| Signal tracks on In2 in the card planes | 0 | 0 |
| HV spacing (`check_pass.py`, my reading) | 0 | 0 |
| Existing tracks / vias changed | 0 | 0 |

Copper outside the `unrouted` rectangle: the fan (80 track ends at y 54..55.3, 24 above, In3 / In4 only) and 3
ends of GPIO_BYPASS_RLY at y -22.05. The stray 15V track at y -74 did not come back (its step did not finish).

## Lanes (all drawn and DRC-gated before any router step)

| Layer | Lane | Net | East end | West end |
|---|---|---|---|---|
| In3 | 0 | GPIO_BYPASS_RLY_ISO | scripted from U19-15 | router |
| In3 | 1 | MDATA_INU | scripted from U21-12 | router (to the scripted via at R50-2) |
| In3 | 2 | INU_ADCLK | scripted from U21-14 | scripted, via at U4-7 |
| In3 | 3 | Net-(U2-+) | scripted, 64.6 mm from the U2 block | router |
| In3 | 4 | Net-(U2--) | router | scripted, via on the old In2 track at (23.22, 45.62) |
| In3 | 5 | Net-(U7A-+) | scripted, 56.1 mm | scripted, via on the old track at (4.92, 47.22) |
| In3 | 6 | Net-(U7A--) | router | scripted, via at (4.63, 48.73) |
| In3 | 7 | Net-(U7B-+) | scripted, 57.2 mm | scripted, via at (22.44, 47.90) |
| In3 | 8..10 | PWM_TRANS6, PWM_Q7, PWM_Q5 | scripted from U20-10..12 | scripted to pins J8-47 / 43 / 44 |
| In4 | 0..3 | 5V_ISOL 0.8 mm | pin J4-45 | pins J6-45, J8-45 |
| In4 | 3..4 | ISOGND 0.4 mm | plane edge, J4 column x 90.69; J4-46 tied to the plane edge | pin J8-46 |
| In4 | 5 | Net-(U7B--) | scripted, 41 mm on In3 to the J4 column x 99.58, via (98.65, 51.9) | scripted, via on the old track at (22.46, 46.72) |
| In4 | 6..7 | 15V_ISO 0.4 mm | scripted, 76.4 mm on In3 from pin U8-1, via (99.45, 51.9) | scripted, via on the old In2 track at (21.96, 49.24) |
| In4 | 8..9 | 3V3_ISO 0.4 mm | scripted from a plane via at (109.05, 39.85), via (100.25, 51.9) | scripted, via at U4-8 |

In3 11 of 11 used, In4 about 10 of 11. The three In4 entries stand north of J4 at its missing pin column
(x 99.58), east of J4-45, so they do not cross the 5V_ISOL lane; no pour is cut (tool-checked). They turn west at
y 52.55..53.65 and climb to their lanes only west of x 93.3, because the pads of DAB_SEC_2 stand at
(95.4..100.4, 55.9). The relay line moved to In3 and one tap (U7B--) to In4: with the taps drawn, a net that starts
west of the tap risers cannot reach an In4 entry east of J4.

Taps as pairs: the pairs have neighbouring lanes, except U7B (one member on In4). Whether they run side by side
from the block to the lane entries was not checked; the second member of the U2 and U7A pairs was routed by the
router because my grid router found no path beside its partner (the per-tap ceilings under the U20 pins were
0.45 mm apart, too tight for its 0.1 mm grid; 0.6 mm is the next thing to try).

## Nets still open

| Net | Why |
|---|---|
| CLK1 | R87 pad 3, left as told |
| DAB_PWM_PRI_HI_ISO | still open with the leftovers in pin order; not analysed further |
| AUX_VIN (1), AUX_LOVP (1) | the aux-links script skipped both pads because a stub already touches them. Tooling gap |
| GND (7) | aux area: R105-2 linked by script; for C68-1, C112-2, C114-2, R102-2, C145-2 the script's straight / one-bend links found no legal place under the per-pad HV rule. Not shown impossible |
| 15V (6) | supply step skipped at my 300 s budget; R101-1: no legal simple link |
| 15V_ISO (7) | supply step skipped at my 300 s budget: the lane's ends at J4-48, at the J6-48 piece and at the old track (23.0, 31.9), and the aux ISO pads R109 / C116 / C93 / D15 |
| 3V3_ISO (1), ISOGND (1) | U20-16 and C120-2, both inside the 2.5 mm zone of BUSN2 (no place for a plane via) |

Lane deletion of pass 4: it happened in the last three supply steps (between step boards 27 and 30 of pass 4).
A restore step now runs after every router step; it had nothing to put back in this run.

## Verified how

- By tool on the final refilled board: the table; `check_layout.py --board` OK; `domain_gaps.py --board` 0;
  kicad-cli DRC with parity; pour islands; every scripted piece gated by DRC before the router ran.
- Seen in a render of the final board: In3 of the passage (all 11 lanes through the neck) and the In3 tap run
  from the U7 / U2 block to the lane entries.
- Rendered but not looked at: In4 of the passage, the isolator row, the west ends, the aux area.
- Impression: none of the open-net reasons above was checked in a render.
- About 2 h 20 min since the resume, against the 90 minutes asked. `tools/check_all.sh` was not run on the routed board.

## Files

- `tools/v5/route_pass1/` (`maze.py`: fan, grid router, aux links; `prep.py restore`), `routing.json`.
- `reports/v5_layout/routing_pass5/`: renders (passage, taprun, isorow, west, aux), `check_board.txt`,
  `check_pass.txt`, `check_layout.txt`, `domain_gaps.txt`, `chain_run.log`.
