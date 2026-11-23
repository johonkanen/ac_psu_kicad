# v6 aux flyback routes (V6_PLAN.md section 10), helper report

Branch `aux-routes`, cut from `v6-baseboard` 4b2d4c2 (step 3 board). Nothing in the main worker's checkout touched.

## Deliverables

| File | What |
|---|---|
| `tools/v6/aux_routes.py` | the step: replays `aux_routes_copper.csv` onto the current board, seed 6100 (`--board`, `--out`, `--dry`). Checks first that every one of the 81 pads in PX / IA is where the table says (ref, pad, net, position within 0.01 mm) and exits 1 without saving if one is not. Zones are added unfilled; fill afterwards. The `BOUNDARY` table is in it |
| `tools/v6/aux_routes_copper.csv` | the copper as data: rows `pad` (checks), `foreign` (remnants cut at the area edge), `zoneclr`, `move`, `track`, `via`, `zone` |
| `tools/v6/aux_design.py` + `aux_design_steps.py` | how the table is made (rerun only if the routes change): every piece drawn on a copy of the board and gated by `aux_lib.Ctx` with the HV rule; writes the CSV |
| `tools/v6/aux_lib.py` | the gate (clearance rules below) and a small grid router (after `route_pass1/maze.py` of pass 7) |
| `tools/v6/aux_check.py` | HV clearance check, pour islands, drain copper area, opens inside the areas from a DRC report |

Replay on the main board: `tools/p2k/bin/kipy tools/v6/aux_routes.py`, then the zone fill, DRC, parity, domain_gaps.

## Clearance rule used (explicit, the board carries it only in pad clearances)

- F.Cu / B.Cu: HV net (DC+, AUX_VIN, AUX_DRAIN, AUX_CLAMP, AUX_ST1/ST2, AUX_LV1/LV2) to any other net 2.5 mm; to an HV pad
  with its own clearance from `card_layout.HV_PADS` that clearance; HV to HV of another net 1.0 mm.
- Inner layers: HV to low voltage 0.5 mm (IPC-2221 B1 internal, 301-500 V: 0.25 mm). AUX_DRAIN / AUX_CLAMP (switching,
  ~750 V peak) to anything 2.0 mm (B1 internal, > 500 V: 0.0025 mm/V). The drain zones carry 2.0 mm as zone clearance.
- Everything >= 2.5 mm from the mounting hole H4 (metal screw, P to PE basic).
- Pad-gap rule (as `route_pass1/scripted.py hvstubs`): copper that leaves a pad may come as close to other copper as that
  pad already is (the placement's gaps, e.g. 1.8 mm between the two pads of a 1206 / 1210, R138-1 / R138-2).
- Vias in pads: one, DC+ in R98-1 (2512 pad; JLC 6-layer boards have filled and capped vias in pads). The pad's 1.5 mm
  clearance keeps the PGND pour on B.Cu away from it.

## Result of the replay test

Clean `kicad/ac_psu.kicad_pcb` at 4b2d4c2 -> `aux_routes.py` -> zone fill -> kicad-cli DRC (schematic parity) ->
`domain_gaps.py` -> `aux_check.py` (logs in `reports/v6/aux_routes/`: `replay.log`, `aux_check.txt`, `domain_gaps.txt`).

- **Open connections inside the areas: 0.** DRC lists 9 unconnected items with one end in the areas; all 9 are
  boundary items whose other end is outside and not routed yet (15V to J22 / J23 / U9, GND to J22 / J23, 15V_ISO to
  C93, ISOGND to its B.Cu pour) or the cut 5V remnant (below).
- DRC: 0 shorts, 0 clearance errors, parity 0. Errors inside the areas: 0 (whole board: 34 courtyard overlaps, the
  accepted type, none in the areas). Warnings in the areas: track_dangling on the boundary stubs, on the cut remnants
  (5V, PWM_G1, GND In1, outside ends) and on a 0.04 mm GND stub at C111-2 that was there before.
- `domain_gaps.py`: OK, 0 violations. `check_layout.py` and `check_layout_v6.py`: OK (run on the design board).
- HV check (`aux_check.py`): 0 violations by aux copper; 42 close pairs pass by the pad clearance or pad-gap rule
  (listed with `-v`). 21 pairs not involving aux copper are reported as pre-existing: the chain rows R136..R138 /
  R141..R143 are 0.65 mm apart pad to pad (equal voltages side by side, v5 step 9) and their north pads are 2.0-2.4 mm
  from REF1 / VCC / REF_1V65 copper just north of PX; J33 / J34 / C12 against the PGND / DC+ pours outside PX (step 3).

### Islands of every pour touching the areas (base 4b2d4c2 -> after)

All 10 existing pours: 1 -> 1 (PGND B.Cu 0, DC+ F.Cu 5, 15V F.Cu 20, GND In1 1, VCC In2 1, v5 aux GND In2, card-I
ISOGND In1 / In4, card-I 3V3_ISO In2, card-P GND In4). New: 4 zones, 1 island each. (A first try with the new In2 GND
zone overlapping the v5 one left two zero-area slivers in the v5 zone; the zones now only abut at y -21.6.)

### AUX_DRAIN copper (V6_PLAN 10: inner layers under T1)

Zones "v6 aux P In1.Cu / In4.Cu AUX_DRAIN" over x 73.0..82.4, y -38.4..-51.2, fed by the T1-12 through-hole pin (no
drain vias: each would need a 2.0 mm hole in the In2 GND pour). Filled: **77.0 mm2 on In1 + 77.0 mm2 on In4**, plus
17.3 mm2 of B.Cu tracks (bar under U18 from pins 7/8 to 5/6, 1.5 mm to T1-12, 0.8 mm to D12-A); about 171 mm2 in all
against the 230 mm2 of the v5 loss estimate. Only x 79.5..82.4 of it lies under the T1 body (PX ends 2.5 mm before
the barrier); the rest lies between U18 and T1-11. Heat from the pins reaches the inner copper only through
T1-12 (1 mm from pins 5/6). Added drain capacitance to the In2 GND pour (0.55 mm / 0.66 mm away): about 5.7 + 4.7 pF,
~10 pF (adds roughly 0.5 x 10 pF x (450 V)^2 x f_sw to the switching loss, ~0.07 W at 65 kHz).

## What was routed

| Net(s) | How |
|---|---|
| GND | v5 In2 pour (clearance 1.0 -> 0.5 mm so it reaches the R102-2 via beside T1-1) + new In2 zone north (x 70..82.9, y -21.6..-4.2, notched round H4) + new In4 zone north overlapping the card-P In4 GND plane (the tie to the main GND); 12 vias at the GND pads; primary return C111-2 -> R105-2 on F.Cu (0.8 mm) |
| 15V | D14-C -> R108-1 / R101-1 on B.Cu, via to F.Cu at R100-1, trunk south on F.Cu at x 82.45 (0.4 mm, beside T1's primary row) to the south edge; north round H4 to C28-1 / C41-1 on B.Cu; west exit under C28 |
| AUX_DRAIN | as above |
| AUX_VIN, AUX_CLAMP | pad to pad on B.Cu / F.Cu (0.6..1.0 mm), all within the pads' own clearance halos |
| DC+ | R98-1 via in pad to the F.Cu pour; F.Cu feed x 68.85 from the chains R136 / R141 through C68-2 into the DC+ pour (2.5 mm from the PWM_G1 via at 65.87) |
| chains ST1 / ST2 / LV1 / LV2 | in-row F.Cu |
| AUX_GATE, AUX_LOVP | F.Cu stubs to vias at x 82.05 east of R138 / R143, then In3 (grid router) to vias at U18-10 (under the package) and at R144-1 |
| AUX_COMP | B.Cu at U18 / C146 / R139, In4 from a via at R139-1 to R140-1 (the B.Cu corridor east of the R column is taken by 15V) |
| AUX_VERR, AUX_CS, AUX_VDD, AUX_VDDR, AUX_COMPC, AUX_W1 | B.Cu (CS between the pads of C146); AUX_VDD via at C113-1 to F.Cu up to D11-C |
| IA: AUX_W2, 15V_ISO, ISOGND | B.Cu; 15V_ISO between R109-2 and T1-9, ISOGND round the east of C116 |

## Part moves

| Part | From | To | Why |
|---|---|---|---|
| C68 (DC+ 100n, v4) | F (72.0, -51.5) rot 0 | F (70.4, -13.0) rot 180 | its DC+ pad stood above C112's AUX_VIN pad (B.Cu) with its own GND pad between it and the DC+ pour: no legal DC+ link (F.Cu needs 2.5 mm past its GND pad, any via lands in or within 1.5 mm of C112-1). New place: on the DC+ feed of the chains, out of the 35 mm courtyard of C12 (to y -18.8) and 2 mm from the control card tails at y -16.4; GND via at (73.1, -12.5) |

## Foreign copper removed inside the areas

Dangling remnants of the v5 runs to the old gate-card headers, cut at the area edge (rows "foreign", generic: any
copper of these nets inside PX / IA): PWM_TRANS3 In2 (x 71 column and y -53.4 run: it lay under U18's pad row and
split the In2 GND pour), PWM_TRANS2 (In2 / B.Cu / via, wholly inside), PWM_G1 In2 (diagonal), 5V In2 (x 67.5 run),
GND In1 (dangling branch from the In1 plane to (72.0, -52.5)). The parts left outside still dangle (DRC warnings);
the main worker's chain deletes or reroutes them.

## Boundary list (also `BOUNDARY` in `tools/v6/aux_routes.py`)

| Net | Area | Point (IPC mm) | Layer | Continues to |
|---|---|---|---|---|
| 15V | PX south edge | (82.45, -54.6) | F.Cu, 0.4 mm | J23-6 / U9-1 (old 15V run at (89.73, -53.8)) |
| 15V | PX west edge | (67.0, -19.8) | B.Cu, 0.5 mm | J21-6 / J22-6 |
| GND | PX north-west | x 69.0..69.65, y -20.66..-4.2 | In4.Cu | zone overlap with the card-P In4 GND plane (already connected) |
| DC+ | inside PX | (68.85, -32.5) | F.Cu | ends in the F.Cu DC+ pour (no crossing) |
| 15V_ISO | IA north edge | (90.95, -25.5) | B.Cu, 0.8 mm | U8-1 / C93-1 / the 15V_ISO pours |
| ISOGND | IA north edge | (96.9, -25.5) | B.Cu, 0.6 mm | ISOGND B.Cu pour 15, 0.9 mm north (y -24.58) |

## Left for the main worker / to verify

- The boundary links above, outside the areas.
- The 15V F.Cu trunk is 0.4 mm (T1's pins leave no more beside them); fine for the ~0.5 A of the 15V loads.
- U18 drain copper is 171 mm2, not 230: measure the controller temperature on the first board (as v5 step 9 said).
- Pre-existing HV pairs outside the aux copper (listed above): chain pads vs REF1 / VCC / REF_1V65 north of PX.
- Brief notes: the HV rule lives in pad clearances only, as the brief said; I added the inner-layer 2.0 mm for the
  drain / clamp (IPC B1), which the v5 chain did not use. The PGND B.Cu pour reaches into PX (x 69..78.7, y -43..-55,
  round R98 / C112 / D13): HV copper there stays inside the HV pads' own clearance halos.
