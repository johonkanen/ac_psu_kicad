# Routing pass 6 (v5 step 17: GND pour on In2 in the aux area)

Branch `routing-pass6`, from d5654c3. A gauge, not a layout. Coordinates: IPC frame, mm, y up. Chain
`tools/v5/route_pass1/chain.sh`; final board `build/route_p6/routed.kicad_pcb` (not committed), refilled copy
`build/pass6/check/ac_psu.kicad_pcb`. One chain run.

## Verdict

- **Legal.** 0 shorts, 0 clearance errors, parity 0, domain gaps 0, `check_layout.py` OK, no pour lost an island
  (85 compared, the new aux pour is one island), no signal on In2, HV check 0, existing copper unchanged.
- **16 unconnected items on 10 nets** (pass 5 follow-up: 22). Closed now: **15V (all 6), CLK1,
  DAB_PWM_PRI_HI_ISO**, two GND pads.
- **New opens: three J11 nets to the bottom isolators** (DAB_PWM_LO_SEC_CTRL, INU_ADCLK_CTRL, PWM_Q5_CTRL). They
  were closed in pass 5; routing DAB_PWM_PRI_HI_ISO first, before that group, is the only change there.
- Still open: AUX_VIN (2), AUX_LOVP (1), GND (5), 3V3_ISO at U20-16, ISOGND at C120-2, and the three wire-link items.

## Pass 5 follow-up against pass 6

| | Pass 5 follow-up | Pass 6 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 22 on 10 nets | 16 on 10 nets |
| Signal connections open (of 174) | 4 | 6: three J11 bottom nets, AUX_VIN 2, AUX_LOVP 1 |
| West-bound ISO signals open (12 nets) | 0 | 0 |
| Supply open, CTRL | 0 | 0 |
| Supply open, ISO | 2 | 2: 3V3_ISO 1, ISOGND 1 |
| Supply open, primary | 13 (GND 7, 15V 6) | 5 (GND 5, 15V 0) |
| Items on the wire-link nets | 3 | 3 |
| Vias on signals, all / new | 220 / 162 | 226 / 168 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps (`domain_gaps.py --board`) | 0 | 0 |
| `check_layout.py --board` | OK | OK |
| Pours whose island count changed | none cut (84) | none cut (85; In2 3V3_CTRL 8 -> 1 as before) |
| Signal tracks on In2 in the planes (card and aux pour) | 0 | 0 |
| HV spacing (`check_pass.py`, my reading) | 0 | 0 |
| Existing tracks / vias changed | 0 | 0 |

Copper outside the `unrouted` rectangle is the fan as in pass 5 (80 track ends at y 54..55.3, 24 above) and 3 ends
of GPIO_BYPASS_RLY at y -22.05. The router laid the 15V track on In2 at y -74 again; the prune step deleted it.

## Did the pour do what it was meant to?

Yes for what it covers. Before any signal of the area, the script set a via into the In2 pour at 10 GND pads of the
aux parts (one of them farther than 1.0 mm from its pad); only C68-1 found no place. 15V, routed next, closed in
48 s (pass 5: skipped twice at 300 s and 420 s). GND open went from 7 to 5; what is left lies mostly outside the pour.

## The other points

- **CLK1 escape**: drawn exactly as specified (0.127 mm, pad 3 -> (59.593, 4.489) -> (60.75, 4.489)), accepted by
  the DRC gate with no violation; the router continued from there and CLK1 is closed (render `r87_B.png`).
- **DAB_PWM_PRI_HI_ISO**: closed by the step that routes it alone, placed right after the planar fan.
- **Supply steps**: all finished inside their budgets (600 s; 15V in an early step of its own).
- **U20-16 and C120-2** (with the 2.5 mm keep-out of BUSN2 in force, `near_via.txt`): the nearest legal via sites
  are (95.07, 38.30), 5.4 mm from U20-16, and (86.81, 41.48), 3.9 mm from C120-2. Neither has a clear straight stub:
  for U20-16 tracks of DAB_PWM_HI_SEC and Net-(U7A--) are in the way; for C120-2 the BUSN2 keep-out, its own
  part's 3V3_ISO pad and track, and the DAB_PWM_LO_SEC via at (87.5, 41.1). No short track to a neighbour pad either
  (the router tried: both stay open).

## Nets still open

| Net | Open item (DRC) | Why |
|---|---|---|
| DAB_PWM_LO_SEC_CTRL, INU_ADCLK_CTRL, PWM_Q5_CTRL | J11 stub ends at (45.5..46.6, 40.5..42.3) to U20-4 / U21-3 / U20-5 | open since DAB_PWM_PRI_HI_ISO is routed before this group; not analysed which track blocks |
| AUX_VIN (2) | via (77.0, -12.3) to the C112-1 stub (68.0, -11.0), and to the track at T1-11 (76.8, -48.9) | grid router found no legal F.Cu path under the 2.5 mm rule; the HV router step left the trunk in two pieces this time |
| AUX_LOVP (1) | R143-2 (80.6, -5.3) to the track at (78.8, -24.2) | no legal F.Cu path under the 2.5 mm rule from the pad beside the HV pad of its own part |
| GND: C68-1 | to GND copper at (71.65, -48.20), 3.5 mm | outside the pour; HV rule: its own part's DC+ pad (1.92 mm), a DC+ track and the DC+ pour |
| GND: C112-2 | to C28-2 (69.95, -16.50), 5.6 mm | outside the pour and, by the tool, not inside a GND plane outline; AUX_VIN track at 2.45 mm, PWM_G3 tracks cross |
| GND: C145-2 | to the GND via at (81.0, -23.0) | a straight link to the track end at (77.00, -20.20), 1.3 mm, is free by the tool; the script skipped the pad because it already has copper. Why the two GND vias do not meet in the pour was not looked at |
| GND: two more | (81.6, -41.8) to (103.9, -44.0); (107.9, -52.5) to (105.0, -49.4) | east of the pour, at U9; as in pass 5 |
| 3V3_ISO (1), ISOGND (1) | U20-16, C120-2 | beside BUSN2, see above |

## Verified how

- By tool on the final refilled board: the table; `check_layout.py --board` OK; `domain_gaps.py --board` 0;
  kicad-cli DRC with parity; pour islands; the GND and via-site rows above; every scripted piece DRC-gated.
- Seen in a render of the final board: B.Cu at R87 (the escape and its continuation), In2 of the aux area (the pour
  with its antipads, one piece).
- Rendered but not looked at: aux F / In3 / B, J11-22, the passage.
- Impression: that routing DAB_PWM_PRI_HI_ISO first is what opened the three J11 nets.
- About 2 hours. `tools/check_all.sh` was not run on the routed board.

## Files

- `tools/v5/route_pass1/` (new: `scripted.py auxgnd` and `clk1`, `near_via.py`; In2 fenced in the aux pour), `routing.json`.
- `reports/v5_layout/routing_pass6/`: renders (aux, r87, j11_22, passage), `check_board.txt`, `check_pass.txt`,
  `check_layout.txt`, `domain_gaps.txt`, `near_via.txt`, `aux_gnd_report.txt`, `chain_run.log`.
