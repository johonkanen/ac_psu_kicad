# Routing pass 7 (v5 steps 18 and 19: R98 / C112 moved, fixed vias beside BUSN2)

Branch `routing-pass7`, from 36d3da7. A gauge, not a layout. Coordinates: IPC frame, mm, y up. Chain
`tools/v5/route_pass1/chain.sh`; final board `build/route_p7/routed.kicad_pcb` (not committed), refilled copy
`build/pass7/check/ac_psu.kicad_pcb`.

## Verdict

- **Not legal: the B.Cu ISODC+ pour is in two islands again** ("Proteus B.Cu pour 5 (fix 14) (part 2)", 1 -> 2;
  DRC shows one more unconnected ISODC+ item). The via keep-out of pass 4 covers only the gap x 76.5..87; this
  time the router set vias just outside it and at the pour's lower edge: Net-(U2-+) at (76.10, 49.75) and
  (88.95, 51.95), Net-(U7A--) at (82.65, 42.80) and (85.45, 42.80), ISOGND at (90.70, 52.95) and (68.55, 50.30).
  Which of them cut it was not determined. The keep-out has to follow the whole pour with its 1.95 mm clearance.
- Everything else passes: 0 shorts, 0 clearance errors, parity 0, domain gaps 0, `check_layout.py` OK, HV check 0,
  no track on In2 in the planes, existing copper unchanged.
- **16 unconnected items on 10 nets**, the same count as pass 6 but a different set (table below). The sigma-delta
  pair to U6 is open for the first time; the three J11 nets of pass 6 are closed, DAB_PWM_PRI_HI_ISO is open again.
- This was not one clean run: two starts were stopped (the HV step ran out of its budget with DC+ in the group;
  my change to the tap band shut out other nets) and the chain was resumed from the scripted runs.

## Pass 6 against pass 7

| | Pass 6 | Pass 7 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 16 on 10 nets | 16 on 10 nets |
| Signal connections open | 6 | 6: ADCLK_DAB, MDATA_DAB, DAB_PWM_PRI_HI_ISO, AUX_GATE, AUX_LOVP, DC+ (R98-1) |
| West-bound ISO signals open (12 nets) | 0 | 0 |
| Supply open, CTRL | 0 | 0 |
| Supply open, ISO | 2 (U20-16, C120-2) | 1: 5V_ISOL (J4-45 to its source side) |
| Supply open, primary | 5 (GND) | 5 (GND) |
| Items on the wire-link nets | 3 | 4 (the cut pour) |
| Vias on signals, all / new | 226 / 168 | 221 / 163 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps | 0 | 0 |
| `check_layout.py --board` | OK | OK |
| Pours whose island count changed | none cut | **B.Cu ISODC+ (part 2) 1 -> 2** |
| HV spacing (`check_pass.py`, my reading) | 0 | 0 |
| Existing tracks / vias changed | 0 | 0 |

## Did the changes do what they were meant to?

- **R98 / C112 moved, R136-1 / R141-1 on DC+: yes for AUX_VIN**, which is closed (it had 2 open). DC+ reaches the
  two chain ends; one connection is left: R98-1 (68.0, -48.6, bottom) to the DC+ track on F.Cu at (68.7, -56.3),
  7.7 mm, needs a via. With DC+ in the group the HV step ran out of 600 s; in a step of its own it took 310 s.
- **Fixed vias beside BUSN2: yes for their pads** (U20-16, C120-1, C120-2 are connected; my plane-via script added
  no second via). **But the 3V3_ISO via at (90.0, 38.7) stands in the In3 band south of the U20 pins** (y 38.3..40.9),
  the only east-west way on In3 between the isolator row and the barrier. In the first start four of the five
  scripted taps found no path there, and the sigma-delta pair to U6 (ADCLK_DAB, MDATA_DAB), which used that strip
  in pass 6, stays open in every try. That the via is the cause is my reading; no render was looked at.
- **J11 bottom fan**: the cause of the pass 6 regression is found by tool: DAB_PWM_PRI_HI_ISO, routed alone and
  first, ran 34 mm on In3 from a via at (53.1, 34.9) across the CTRL area, where the bottom-fan nets go. With the
  bottom fan first, all 14 of its nets close and DAB_PWM_PRI_HI_ISO does not (alone, and again in the leftovers
  step). With this router one order closes the one and the other order the others; it needs a drawn route.

## Nets still open

| Net | Open item | Why |
|---|---|---|
| ADCLK_DAB, MDATA_DAB | U21-13 / U21-11 to U6-7 / R72-2 | see above (band south of the U20 pins) |
| DAB_PWM_PRI_HI_ISO | J11-22 stub to U16-3 | see above |
| DC+ (1) | R98-1 bottom to the F.Cu track at (68.7, -56.3) | needs a via; the aux script draws none |
| AUX_GATE | via (71.5, -35.0) to R138-2 (80.6, -7.7), 28.8 mm | no legal F.Cu link under the 2.5 mm rule; closed in pass 6, the DC+ runs to R136 / R141 are new there |
| AUX_LOVP | R143-2 (80.6, -5.3) to the track at (78.8, -24.2) | two layers, needs a via; as before |
| 5V_ISOL (1) | J4-45 to the track at U10 (96.1, -3.3) | the supply step left the feed from U10 to J4-45 open; not analysed (closed in pass 6) |
| GND: C112-2 | to C68-1, 0.8 mm (bottom / top), and to the In1 track at (71.9, -52.4), 1.4 mm | each needs a via; no legal via site (both pads sit beside DC+ / AUX_VIN pads); the pour starts at x 72 |
| GND: C68-1 | as above | outside the pour, HV pads around |
| GND: C145-2 | track at (78.3, -20.2) to the track at (81.0, -23.0), 3.9 mm | no legal link on B.Cu; why the two do not meet in the In2 pour was not looked at |
| GND: U9 side | (81.6, -41.8) bottom to (105.4, -44.0) top, 23.9 mm | the GND of the caps at U9 (C57 / C58 / C67, x 105.4) is an island east of the ISO aux area; it needs a track south of y -53 or a via into copper there |
| GND: U9 side | In1 track (107.9, -52.5) to F.Cu track (105.0, -49.4), 4.2 mm | two old GND pieces at U9 on different layers; needs a via |

## Verified how

- By tool on the final refilled board: the table; `check_layout.py --board` OK; `domain_gaps.py --board` 0;
  kicad-cli DRC with parity; pour islands (which found the cut); the open-item rows; the layer use of
  DAB_PWM_PRI_HI_ISO in pass 6; every scripted piece DRC-gated.
- Seen in a render: nothing of the final board (the renders are made, none was looked at; time).
- Impression: the cause of the sigma-delta pair staying open; which via cut the pour.
- About 2 h 25 min. `tools/check_all.sh` was not run on the routed board.

## Files

- `tools/v5/route_pass1/` (aux links now driven by a DRC run; HV step split; `left_iso2`), `routing.json`.
- `reports/v5_layout/routing_pass7/`: renders (aux, j11bot, busn2, passage), `check_board.txt`, `check_pass.txt`,
  `check_layout.txt`, `domain_gaps.txt`, `chain_run.log`, `chain_try1.log`, `chain_try2.log`, `chain_runs_to_sdm.log`.
