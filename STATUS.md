# Status

Updated: 2026-10-21 (tools moved to the shared proteus2kicad submodule; design files unchanged)

## Shared tools – proteus2kicad (2026-10-21, branch `p2k-submodule`)

- The generic tools moved to https://github.com/johonkanen/proteus2kicad, a submodule at
  `tools/p2k` (pinned commit): `sexpr`, `geom2d`, `gerber`, `fpgeom`, `sch_builder`,
  `render_sheet`, `ipc356`, and the `kipy` / `kicad-cli` / `kicad_env.sh` wrappers (mount
  state now `/tmp/p2k_kicad_mount.<uid>`). Board values are in `p2k_config.py`. The other
  scripts in `tools/` stay here for now and import the shared modules from `p2k`; they move
  to proteus2kicad when tube_psu_kicad needs them, with this board as the regression test.
  Paths in the phase sections below (`tools/bin/kipy`, `tools/ipc356.py`, …) are historical.
- New check in `check_all.sh`: `p2k check_sources` (Gerber X2 pad/via/drill flashes vs IPC,
  outline 246.8 × 154.7 mm) – passes.
- Regression proof: `tools/check_all.sh` output identical to before apart from the new step
  and the extra IPC counts (records 1075, smd_top 341, smd_bottom 172, free_pads 0).
  Regenerating everything from a fresh `--recurse-submodules` clone (`p2k ipc356`,
  `gen_symbols`, the 11 sheet scripts, `gen_footprints`, `make_pcb.sh`, `assign_nets --check`)
  reproduces every committed file byte for byte; `kicad/`, `lib/`, `reports/` are unchanged
  against `main`. `make_skeleton` (one-shot, random UUIDs) runs. `reference/` changed only in
  format: new column `refdes_proteus` (= `refdes` on this board) and header lines; pad, net
  and alias data identical.
- `tools/regen_check.sh [REF]`: the regression check above as a script (clean clone,
  regenerate everything, fail on any difference; negative-tested with a changed sheet value).
  Run it, plus `tools/check_all.sh`, after every `tools/p2k` bump.

Previous update: 2026-10-19 (Phase 4 done – gerber round trip and IPC-D-356 diff against Proteus pass; the migration is complete apart from the open points listed under Phase 4)

## Phase 0 – done

- `tools/kicad_env.sh`: mounts `~/kicad/kicad-10.0.7-x86_64.AppImage` with
  `--appimage-mount` (background, mount path cached in `/tmp/ac_psu_kicad_mount.<uid>`,
  reused while alive) and puts `tools/bin` on PATH. `tools/bin/kipy` = AppImage
  python3.11 with the pcbnew dist-packages on PYTHONPATH; `tools/bin/kicad-cli`.
  Both wrappers mount on demand, so they work without sourcing anything.
- `tools/ipc356.py`: parses the IPC-D-356A file (stdlib only, plain `python3`).
  Writes `reference/ipc356_pads.{json,csv}`, `reference/pin_nets_by_component.md`
  (redraw cheat sheet) and `reference/pins_by_net.md`. `--check` verifies counts,
  fix-ups and that the reference files are up to date.
- `tools/check_all.sh`: runs the pcbnew import check and the parser self-check.

### Last verification (`tools/check_all.sh`)

```
== KiCad environment
pcbnew 10.0.7
== IPC-D-356A parser self-check
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
ipc356: OK
ALL CHECKS PASSED
```

`refdes_raw=265` counts the blank refdes of vias/holes; 264 real (truncated) refdes,
267 after the fix-up. The 562 THT records = component THT pads + 173 vias + 4
unnetted mounting holes (3.0 mm).

### Findings that matter for Phase 1

- Truncated refdes resolved from the PDF (by coordinate, nets cross-checked):
  `AFE_OUT`→G3_SOURCE_HI, `FILTER_IN`→FILTER_INPUT, `FILTER_OUT`→LEMOUT,
  `INU_OUT2`→Q5_S, `DAB_PRI_1`→DAB_SOURCE_HI_PRI, `DAB_PRI_2`→DAB_CAP_PRI,
  `DAB_SEC_1`→DAB_SOURCE_HI_SEC, `DAB_SEC_2`→DAB_CAP_SEC.
- **TR1** (ETD34 DAB transformer, sheet 6) is **not on the PCB**; it connects through the
  DAB_PRI/DAB_SEC terminals. The IPC's only transformer is **TR2** (EF20, aux supply).
  In KiCad give TR1 "Exclude from board" and have the comparison ignore it.
- 74 nets have Proteus auto names `#00xxx` (PLAN.md assumed none). Comparison must be by
  pad-set equivalence; names are irrelevant for them.
- ACIN1/2, ACOUT1/2 have two holes both numbered pin 1 (same net) – the footprint needs
  two pads numbered 1.
- R87 (resistor array) pins 4 and 5 have no net record at all (not N/C).
- Single-pin nets: ADA0, ADA4, ADA5, ADA6 (U11 inputs), DGND (U11-6 only).
- PDF net labels are sometimes lowercase (`lemout`, `filter_input`); IPC names are
  uppercase. Use the IPC spelling in KiCad.

## Phase 1 preparation – done (Opus 5.5)

New files:

- `tools/sexpr.py` – KiCad s-expression reader/writer (stdlib).
- `tools/gen_symbols.py` → `lib/ac_psu.kicad_sym` (47 symbols, generated; `--check` verifies
  it is up to date). Simple parts are flattened copies of KiCad 10 std symbols with pins
  renumbered (diodes `A`/`C`; C3M0065090D 1=G 2=D 3=S; 2N7000 1=D 2=G 3=S as in Proteus;
  FKK5R0020FE 1/3 one end, 2/4 other end; WE-CMBNC windings 1-4 and 2-3). ICs, relay,
  EF20, IW1830, connectors are boxes with the **Proteus** pin names. 15 power symbols with
  IPC net names + `PWR_FLAG`. `ETD34_TRAN_1P1S` (TR1) has `on_board no`.
- `lib/part_map.csv` – refdes → PDF sheet, `ac_psu:` symbol, value (268 rows = 267 IPC parts
  + TR1). Values are only filled for non-passives; R/C values come from the PDF.
- `tools/check_symbols.py` – pin set of every mapped symbol (all units) == IPC pin ids of
  that refdes; every IPC refdes mapped; power symbol names are IPC nets.
- `tools/compare_netlists.py` – exports the kicadxml netlist and compares by pad-set
  equivalence. Only refdes present in KiCad are pin-compared, so it works sheet by sheet.
  Reports missing/extra parts, missing/extra pins, merged nets (KiCad net with pins of
  several IPC nets), split nets, N/C mismatches (incl. KiCad-unconnected pin of a multi-pin
  IPC net), name hints, and a per-sheet drawn/total summary. `--sheet N` limits the
  missing-part list to PDF page N; `--allow-missing` makes missing parts warnings.
  Parts with "exclude from board" (TR1) and `#` refs are ignored. Tested on a throw-away
  fixture with deliberate errors (merge, split, extra part, unplaced units, N/C flags).
- `tools/make_skeleton.py` (one-shot, refuses to overwrite) → `kicad/ac_psu.kicad_pro`,
  `kicad/sym-lib-table` (`ac_psu` → `${KIPRJMOD}/../lib/ac_psu.kicad_sym`), root sheet
  `kicad/ac_psu.kicad_sch` with 11 hierarchical sheets `01 afe` … `11 signal isolators`
  (files `kicad/01_afe.kicad_sch` …; sheet 10 is untitled in the PDF → `INU SDM and relay
  drive`). All sub-sheets are empty, A3.
- `tools/sch_builder.py` – helper to write sub-sheets from Python: `Sheet(path).place(sym,
  ref, x, y, rot, unit, value)` returns pin connection points; `power`, `pwr_flag`, `label`,
  `glabel`, `no_connect`, `wire`, `junction`, `text`, `save`. Rotation verified via netlist.
- `tools/erc.sh` – ERC via kicad-cli, fails on ERC errors, report in `reports/erc.rpt`.
- `tools/check_all.sh` now also runs: symbol library up to date, symbol pin sets, ERC,
  netlist comparison (`--allow-missing` until all sheets are drawn – remove it then).

### Last verification (`tools/check_all.sh`)

```
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: 31 part types, 268 refdes, 15 power symbols
symbols: OK
erc: 0 errors, 0 warnings (reports/erc.rpt)
compare: parts 0/267 present, 267 missing, 0 extra; pins compared 0, wrong-net pins 0; IPC nets touched 0, complete 0
compare: per sheet (drawn/total) 1:0/48 2:0/8 3:0/18 4:0/37 5:0/43 6:0/16 7:0/31 8:0/22 9:0/10 10:0/23 11:0/11
compare: OK
ALL CHECKS PASSED
```

### Findings

- **REF3025 pinout**: Proteus/IPC have REF1/REF2 pin 1 = GND, 2 = VIN, 3 = VOUT. The TI
  SOT-23 pinout (and KiCad's `REF3025`) is 1 = IN, 2 = OUT, 3 = GND. The project symbol
  follows Proteus (pin ids must match the IPC). Either the Proteus footprint numbers pads
  differently from their physical position, or the board has REF1/REF2 wired wrong –
  check in Phase 2 (pad geometry vs footprint) and tell the user.
- There is **no `3V3` net**: every `3V3`/`3v3` terminal in the PDF is net `VCC`
  (`VCC/VDD=POWER`). `DC-` and `AGND` (sheet 9) are net `GND`. Sheet 7's `ISO_GND`
  terminal is wired to `RET_iso` → net `RET_ISO` (it is *not* `ISOGND`).
- The relays have refdes **R20/R79** and pins 1,2,3,5,6 (no 4). PWM1 (IW1830) has no pin 6.
- J7 is a single-pin PIN terminal (like J5, J9, J10), not a gate-driver connector.
- Gate-driver connectors J1–J4, J6, J8 have pins 15–26, 29–40, 43–48 only.

### Transcription rules (for the sheet sessions)

- Use only `ac_psu:` symbols, exactly the `lib_id` in `lib/part_map.csv` for each refdes.
  Refdes exactly as there (R256, PE1…, DAB_PRI_1, FILTER_IN, INU_OUT2, …).
- Power nets → power symbols: GND, PGND, ISOGND, ISOPGND, DGND, DAB_GROUND, RET_ISO, VCC,
  3V3_ISO, 5V, 5V_ISOL, 20V, 20V_ISO_SEC, DC+, ISODC+ (mapping above for 3V3/DC-/AGND/ISO_GND).
  Add PWR_FLAGs where ERC reports undriven power pins (each power net once, on the sheet
  where it is generated or enters).
- Other named nets → labels with the IPC spelling (uppercase, e.g. `lemout` → `LEMOUT`,
  `filter_input` → `FILTER_INPUT`, `Mdata` → `MDATA`). Proteus terminals are global, so use
  **global labels** for every net that appears on more than one sheet; local labels are fine
  for nets that stay on one sheet. Auto-named `#00xxx` nets need no label (plain wires).
- N/C pins in the IPC (place a no-connect flag): J1-25 J1-39 J2-25 J3-25 J3-39 J4-39
  J6-25 J6-39 J8-25 J11-38 TR2-5 TR2-8 TR2-9 TR2-10 U3-4 U10-4 R20-5 R79-5 U17-1…16.
  R87 pins 4/5 have no net: place R87 unit D (4-5) with no-connect flags, or leave it
  unplaced (compare reports it as info only).
- Single-pin nets ADA0, ADA4, ADA5, ADA6 (U11 inputs) and DGND (U11-6): label/power
  symbol on one pin; ERC "isolated label" warnings for them are expected.
- TR1 (sheet 6) is drawn with `ETD34_TRAN_1P1S` (excluded from board); its pins connect to
  DAB_SOURCE_HI_PRI / DAB_CAP_PRI / DAB_SOURCE_HI_SEC / DAB_CAP_SEC as in the PDF.
- Keep symbols, wires and labels on the 1.27 mm grid (ERC flags off-grid ends).
- After each sheet: `tools/check_all.sh` (or `tools/compare_netlists.py --sheet N` and
  `tools/erc.sh`). Target per sheet: 0 missing on that sheet, 0 compare errors, 0 ERC errors.

## Phase 1 transcription – done (Fable 5.1, 2026-10-18)

Each sub-sheet is generated by a re-runnable script `tools/sheets/sheetNN.py` (uses
`tools/sheets/_common.py` helpers and `tools/sch_builder.py`; `Sheet.clear()` rebuilds the
sheet from scratch). Visual check: `tools/render_sheet.py kicad/NN_*.kicad_sch` →
`reports/render/NN_*.png` (kicad-cli SVG + librsvg/cairo via ctypes).
`compare_netlists.py` reports a *split* IPC net only as a warning while the net still has
pins on undrawn parts ("pending sheets ..."); it becomes an error once all its parts are drawn.
`tools/check_all.sh` now runs the comparison without `--allow-missing`.

| Sheet | Parts | Status |
|---|---|---|
| 2 fpga connector | 8/8 | done 2026-10-18; compare 0 errors, ERC 0 errors (source groups use PGND/ISOPGND/DAB_GROUND power symbols, see notes) |
| 3 regulators | 18/18 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 11 signal isolators | 11/11 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 10 INU SDM and relay drive | 23/23 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 9 primary side ADC | 10/10 | done 2026-10-18; compare 0 errors, ERC 0 errors (R87:D placed with N/C flags) |
| 8 SDM current measurements | 22/22 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 1 afe | 48/48 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 5 VSI | 43/43 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 6 Dual Active Bridge | 16/16 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 4 DC links | 37/37 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 7 Auxiliary supply | 31/31 | done 2026-10-18; compare 0 errors, ERC 0 errors |

Notes:

- PWR_FLAGs for GND, 20V, ISOGND, 20V_ISO_SEC are temporarily on sheet 2 (they enter
  through the connectors). Move them to sheet 7 (aux supply) when it is drawn – one flag per
  net. 5V/5V_ISOL/VCC/3V3_ISO are driven by power-output pins on sheet 3 (no flag needed).
- Two-pin parts get centred Reference/Value text from `sch_builder.place()` (KiCad mirrors
  or swaps field justification for rotated symbols); `vert2`/`horiz2` in `_common.py` place a
  two-pin part with a chosen pin at the top/left – check the IPC pin order (on sheet 3 every
  capacitor has pin 1 on the ground side).
- **PDF alias labels of power nets**: the PDF labels J1 15-20 / 29-34 and J3 29-34 as
  `G2_SOURCE_LO` / `G4_SOURCE_LO` / `DAB_SOURCE_LO_PRI`, J6 15-20 / 29-34 as `Q8_S` / `Q6_S`,
  J4 15-20 as `DAB_SOURCE_LO_SEC`; in the layout these are the power nets PGND, ISOPGND and
  DAB_GROUND. KiCad ERC reports *multiple_net_names* (error) when such a label shares a net
  with a power symbol, so sheet 2 uses the power symbols and shows the PDF names in brackets
  (rule: power nets → power symbols). Signal aliases that differ only in case are spelled
  like the IPC (`LEMOUT`, `FILTER_INPUT`, `SHUNT1`, ...).
- PWR_FLAG placement (final, one flag per net): 20V, GND, 20V_ISO_SEC, RET_ISO and the
  IW1830 Vcc node on sheet 7 (aux supply); ISOGND on sheet 2 (it is not generated on the
  board, it enters through J12 / J4 / J6 / J8); DC+ and PGND on sheet 1; ISODC+ on sheet 5;
  ISOPGND and DAB_GROUND on sheet 8 (R64); DGND and the L1-filtered ADC supply on sheet 9;
  the floating VDD1/GND1 rails of U4/U5/U6 on sheets 10/8. 5V, 5V_ISOL, VCC, 3V3_ISO are
  driven by power-output pins on sheet 3.
- Kelvin shunts: R48 pins 1 and 3 are the same net (SHUNT1) in the IPC, so they are wired
  together on sheet 1 (the symbol has no internal connection); R91 (sheet 5) has 4 distinct
  nets, R64 (sheet 8) too.
- Sheet 8 lower half: the PDF shows an unlabelled zener next to R75; it has no refdes and no
  pads in the IPC, so it is not drawn (text note on the sheet).
- R87 unit D (pins 4/5, no net in the IPC) is placed on sheet 9 with no-connect flags so the
  footprint's pads exist; compare treats the no-net pins as info.
- Two-pin parts get centred Reference/Value text from `sch_builder.place()` (KiCad mirrors
  or swaps field justification for rotated symbols); `vert2`/`horiz2` in `_common.py` place a
  two-pin part with a chosen pin at the top/left (rotation derived from the library pin
  geometry) – check the IPC pin order (most capacitors have pin 1 on the ground side).
  `terminal()` draws the Proteus PIN terminals, `adum_block()` the ADuM7701 blocks.

### Last verification (`tools/check_all.sh`, Phase 1 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
compare: per sheet (drawn/total) 1:48/48 2:8/8 3:18/18 4:37/37 5:43/43 6:16/16 7:31/31 8:22/22 9:10/10 10:23/23 11:11/11
compare: OK
ALL CHECKS PASSED
```

The 8 ERC warnings are expected: `isolated_pin_label` for the single-pin nets ADA0, ADA4,
ADA5, ADA6 (U11 inputs, as in Proteus); `ground_pin_not_ground` for the GND1 pins of
U4/U5/U6 (they float on the shunt nets INU_SHUNT2 / SHUNT1 / DAB_SHUNT2 by design) and for
U9 pin 3, whose Proteus name "+VOUT/GND" contains GND but carries 5V.

### Findings from the transcription (for Phase 2 and the user)

- **C67** (100 µF, 5 V rail, sheet 7): in the IPC its pin 1 is on GND and pin 2 on 5V, while
  the other polarized caps (C28, C15, C8, C11, C12, C61, C72, C79) have pin 1 on the positive
  rail. Either the footprint's pad 1 is the negative pad or the part is reversed – check the
  Proteus footprint / silkscreen polarity mark in Phase 2 and tell the user.
- **REF3025** pin ids follow Proteus (1 = GND, 2 = VIN, 3 = VOUT; TI: 1 = IN, 2 = OUT, 3 = GND),
  see above – resolve against the pad geometry in Phase 2.
- Sheet 8 shows an unlabelled zener next to R75 (U6 supply) that has no refdes and no pads
  in the IPC; it is not drawn. Sheet 7: R26 is "NA" (not fitted) in the PDF; drawn with value NA.
- The PDF's `ISO_GND` terminal on sheet 7 is wired to `RET_iso`: the isolated 20 V return
  (RET_ISO: TR2-6, C15, C36, R49) has no connection to ISOGND on this board.
- R96 / R97 (0 R) are the only links PGND–GND and ISOPGND–ISOGND (sheet 4).
- TR1 (sheet 6) is excluded from the board; the PDF's TR1 winding note is printed on page 7.
- Component values were read from the PDF renders (`source/schematic_pdf/hi-NN.png`); the
  PDF shows no footprints, so Phase 2 takes packages from `ROOT.LYT` strings and the IPC pad
  geometry (see PLAN.md section 4).

Visual check of every sheet: `reports/render/NN_*.png` (regenerate with
`tools/render_sheet.py kicad/NN_*.kicad_sch`). Layout follows the PDF pages; the per-sheet
scripts in `tools/sheets/` are the editable source of the sub-sheets (rerun a script, then
`tools/check_all.sh`).

## Phase 2 footprints – done (Opus 5.5, 2026-10-18)

New / changed files:

- `tools/fpgeom.py` – footprint pad loader (.kicad_mod → pads, Y up) and the rigid fit
  (pads matched by number, least-squares rotation snapped to 45°, mirror for bottom side,
  pads sharing a number paired by permutation) + pad-size comparison. Its docstring has the
  **KiCad placement recipe** (see below).
- `tools/gen_footprints.py` → `lib/footprint_map.csv` (refdes → footprint, generated) and
  `lib/ac_psu.pretty/` (20 project footprints, generated). `--check` verifies both are up to
  date (needs the AppImage mount for the KiCad base footprints). Assignment = `RULES` keyed by
  symbol + IPC pad pattern (pad count, span, pad size, drill); project footprints = `PROJECT`
  (derived from a KiCad footprint: renumber / drop pads / move pad centres onto the Proteus
  positions, or built from the IPC pads).
- `kicad/fp-lib-table` registers `ac_psu` → `${KIPRJMOD}/../lib/ac_psu.pretty` (KiCad std
  libraries come from the global table).
- `tools/sch_builder.py`: `place()` fills the Footprint field from `lib/footprint_map.csv`;
  **UUIDs are now deterministic** (uuid5 per sheet file; symbol/pin UUIDs keyed by refdes, unit
  and pin number, the rest by drawing order). Re-running a sheet script now reproduces the
  file byte for byte, so the symbol UUIDs the PCB will link to stay stable. All 11 sheets were
  regenerated (no layout change).
- `tools/check_footprints.py` – reads the Footprint field of every symbol in `kicad/*.kicad_sch`,
  checks it equals `lib/footprint_map.csv`, fits each footprint onto the IPC pads and fails on a
  missing footprint, pad-number mismatch, or residual > 0.05 mm. `--pcbnew` (under `kipy`) also
  places every footprint on a pcbnew BOARD with the KiCad recipe and re-measures the pads.
  Writes `reports/footprint_fit.csv` (per part: side, angle, origin in IPC and KiCad
  coordinates, worst residual, size/drill deltas – the input for Phase 3 placement) and
  `reports/footprint_pads.csv` (per pad: residual, IPC vs footprint size and drill).
  Negative-tested (plain SOT-23 for REF1 → 0.151 mm, plain SOT-23-5 for U2 → 0.068 mm,
  empty field → error).
- `tools/check_all.sh`: new steps "Footprint library and map up to date" and
  "Footprints vs IPC pad geometry".

KiCad placement recipe (verified with pcbnew 10.0.7 on all 267 parts, worst 0.038 mm):
position = (x, −y) of the IPC origin; top part → `SetOrientationDegrees(angle)`; bottom part →
`Flip(pos, FLIP_DIRECTION_LEFT_RIGHT)` then `SetOrientationDegrees((180 + angle) % 360)`.
`reports/footprint_fit.csv` already has `kicad_x, kicad_y, kicad_orientation`. 190 parts top,
77 bottom (all bottom parts are SMD). THT parts are taken as top side; every THT pattern fits
unmirrored (the chiral ones – PWM1 DIP-8 – confirm top), so no THT part is on the bottom.

### Footprint decisions

| Parts | Footprint | Worst residual |
|---|---|---|
| R 0402 (33) | `Resistor_SMD:R_0402_1005Metric` | 0.010 |
| R 0603 (4) + R25/R26/R29/R31/R44 (Proteus pads 1.73 mm apart) | `Resistor_SMD:R_0603_1608Metric` | 0.038 |
| R59/R75/R94 0805 | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` | 0.000 |
| R23/R24/R45/R47/R49 1206 | `Resistor_SMD:R_1206_3216Metric` | 0.013 |
| R 1206 with pads 3.15 mm apart (41) | `Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | 0.025 |
| R10 TWW10J15RE | `Resistor_THT:R_Radial_Power_L13.0mm_W9.0mm_P5.00mm` | 0.000 |
| C 0402 (28) / 0603 (15) | `Capacitor_SMD:C_0402_1005Metric` / `C_0603_1608Metric` | 0.030 / 0.025 |
| C 1206 (9, incl. C67) | `Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` | 0.013 |
| C 2220 2.2u (8) | `Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder` | 0.038 |
| C 2n2 THT P7.5 (14) | `Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P7.50mm` (Proteus silk ~13 × 6 mm) | 0.000 |
| C21/C25/C33/C34 7u P27.5 (Proteus drill 1.27) / C24 (Proteus drill 1.016) | `ac_psu:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus` (Phase 3: Proteus pads/drills) / `Capacitor_THT:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4` | 0.000 |
| SNAP_IN_35MM (6) | `ac_psu:CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus` (Phase 3: Proteus 5.08 pads, 2.032 drills) | 0.000 |
| C15/C28 EEEFTE221XAP | `ac_psu:CP_Elec_6.3x7.7_EEEFTE221XAP` (KiCad graphics, Proteus pads) | 0.000 |
| D1/D2/D6 SMA | `ac_psu:D_SMA_AC` (KiCad D_SMA, pads C/A, Proteus centres) | 0.000 |
| D3–D5/D7/D10, D8/D9 SOD-323 | `ac_psu:D_SOD-323_AC` (KiCad HandSoldering, pads C/A, Proteus centres) | 0.001 |
| L1 | `Inductor_SMD:L_0805_2012Metric` | 0.025 |
| Q13/Q14 2N7000, REF1/REF2 | `ac_psu:SOT-23_Proteus` (KiCad SOT-23 renumbered 3→1, 1→2, 2→3; Phase 3: Proteus pad sizes and centres) | 0.020 |
| U2/U12/U14 TLV316, U3/U10 TPS73033 | `ac_psu:SOT-23-5_TLV316` (Phase 3: Proteus pad sizes) / `SOT-23-5_TPS73033` (Proteus rows 2.39 / 2.50 mm) | 0.001 |
| U1/U7 OPA2353UA | `ac_psu:TSSOP-8_3x3mm_P0.65mm_Proteus` (the pads are MSOP/TSSOP-8, not SO-8; Phase 3: Proteus pads, no 0.2 mm footprint clearance) | 0.000 |
| U11 | `ac_psu:TSSOP-16_4.4x5mm_P0.65mm_Proteus` (Phase 3: Proteus pads) | 0.013 |
| U13/U15/U16/U17 | `ac_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus` (U16 at 225°; Phase 3: Proteus pads) | 0.030 |
| U4/U5/U6 ADuM7701 | `ac_psu:SOIC-8W_7.5x5.85mm_P1.27mm_ADuM7701` (rows 9.70 mm) | 0.001 |
| AD1 ADS7056 | `ac_psu:X2QFN-8_1.5x1.5mm_P0.5mm_ADS7056` (Proteus pads and sizes) | 0.000 |
| R87 | `ac_psu:R_Array_Convex_4x0402_Proteus` (pads 4/5 kept, no net) | 0.000 |
| PWM1 IW1830 | `Package_DIP:DIP-8-N6_W7.62mm` | 0.000 |
| Q1–Q12 | `ac_psu:TO-247-3_Vertical_Proteus` (1=G 2=D 3=S; Phase 3: Proteus 3.048 pads, 1.651 drills) | 0.011 |
| J1–J4, J6, J8 | `ac_psu:PinHeader_2x24_P1.27mm_Vertical_Pins15-48` (pads 1–14, 27, 28, 41, 42 removed; Phase 3: Proteus 0.812 pads) | 0.000 |
| J11 / J12 | `ac_psu:PinHeader_2x19_P1.27mm_Vertical_Proteus` (Phase 3: Proteus 0.812 pads) / `ac_psu:PinHeader_2x03_P1.27mm_Vertical_Pins43-48` | 0.000 |
| U8/U9 VXO7805 | `ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus` (Phase 3: Proteus 1.8 pads, 1.2 drills) | 0.000 |
| TR2, CM1–CM3, R48/R64/R91, R20/R79 | `ac_psu:Transformer_EF20_2x5_P3.81mm`, `L_CommonMode_WE-CMBNC`, `R_Shunt_FKK5R0020FE`, `Relay_SLA-12VDC-SL-A` (built from the IPC pads; simple rectangle outlines) | 0.000 |
| PIN terminals | `ac_psu:Terminal_D4.0mm_Drill{2.0,2.55,3.0}mm`, `Terminal_D3.05mm_Drill1.52mm`; ACIN1/2, ACOUT1/2 `Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm` (two pads "1") | 0.000 |
| TR1 | none (excluded from board) | – |

41 distinct footprints (21 KiCad library, 20 project) at the end of Phase 2; 42 (14 KiCad
library, 28 project) after the Phase 3 pad/drill decisions. Footprints built purely from the IPC
pads have generic outlines (TR2 22 × 14 mm body from the Proteus silk, others the pad box);
Phase 3 tightened their courtyards to 0.25 mm around body and pads (circles for single PIN
terminals).

### Residual report

`tools/check_footprints.py`: 267/267 parts, 898 pads (894 pins + the 4 duplicate "1" holes
of ACIN/ACOUT), worst residual **0.038 mm** (R 0603 group with Proteus pads 1.73 mm apart,
C 2220). Per footprint: `tools/check_footprints.py -v`; per pad: `reports/footprint_pads.csv`.

Pad sizes: KiCad sizes accepted (PLAN.md 4.3). Largest differences: TO-247 (KiCad 2.5 × 4.5
oval vs Proteus 3.05 round), snap-in caps (4.0 vs 5.08), C_Rect P27.5 / R10 / C_Disc
(2.0–2.4 vs 1.52–2.29). **Drills where KiCad is smaller than Proteus**: TO-247 1.5 vs 1.651,
VXO7805 1.0 vs 1.2, C21/C25/C33/C34 1.2 vs 1.27, snap-in 2.0 vs 2.032 – the user may want the
Proteus drills (then derive a project footprint with `ipc_sizes=True` in `gen_footprints.py`).
**Resolved in Phase 3** (user decision 2026-10-19): these parts now use the Proteus drills and
pads, and 8 SMD/header packages use the Proteus pad sizes, see "Phase 3 – footprint changes".

### Polarity / pinout findings (for the user)

- **REF1/REF2 (REF3025) – board is wired correctly.** In the IPC the pad Proteus calls 1 (GND)
  sits alone on one side of the SOT-23 and pads 2 (VIN) and 3 (VOUT) on the other. A top-side
  (unmirrored) fit of KiCad's JEDEC SOT-23 matches only with Proteus 1 = JEDEC pin 3,
  Proteus 2 = pin 1, Proteus 3 = pin 2 (0.020 mm; the plain numbering gives 0.151 mm). TI's
  REF3025 pinout is 1 = IN, 2 = OUT, 3 = GND, so physically IN = VCC, OUT = VOUT net,
  GND = GND. Proteus simply numbers the SOT-23 pads differently. Same for Q13/Q14 (2N7000 in
  SOT-23, Proteus 1 = D, 2 = G, 3 = S): JEDEC pin 3 = D, 1 = G, 2 = S – also correct.
- **C67 (100 µF, 5 V)** sits on a plain 1206 land pattern identical to C57/C58 (22 µF ceramics);
  the Proteus top silk and assembly layers show a plain 1206 box with no polarity mark (C28/C15,
  the SMD electrolytics, have a bar at their negative pad 2). So the Proteus footprint is
  non-polar and "pin 1 on GND" is only pad numbering: fine for a 100 µF ceramic, but if a
  polarized part (tantalum/polymer) is fitted, the board does not show its polarity. KiCad
  footprint: the same non-polar 1206 as C57/C58. Note: sheet 7 draws C67 with `C_Polarized`
  (pin 1 at GND) while `lib/part_map.csv` says `ac_psu:C` – left as drawn; switch the symbol to
  `C` in `tools/sheets/sheet07.py` if the part is ceramic.

### Last verification (`tools/check_all.sh`, Phase 2 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 41 footprints (20 project), up to date
check_footprints: pcbnew placement of 267 parts, worst pad offset 0.038 mm
check_footprints: 267/267 parts fitted, 898 pads, 41 footprints, worst residual 0.038 mm (limit 0.05)
ALL CHECKS PASSED
```

## Phase 3 PCB – done (Opus 5.5, 2026-10-19)

`kicad/ac_psu.kicad_pcb` is generated by re-runnable scripts; `tools/make_pcb.sh` runs them in
order (≈10 s) and two runs give a byte-identical board (UUIDs seeded per script with
`KIID.SeedGenerator`). Do not hand-edit the board while it is still generated – change the
scripts (or stop regenerating it and say so here).

| Step | Script | What it does |
|---|---|---|
| 3a | `tools/build_pcb.py` | Exports the kicadxml netlist, creates the board (4 Cu layers, Proteus origin, KiCad y = −IPC y), one footprint per symbol (TR1 skipped) with reference, value, Datasheet/Description, symbol link (path = sheet path + symbol UUID, sheet name/file → DRC schematic parity 0) and pad nets; placement from `reports/footprint_fit.csv` with the Phase 2 recipe; outline on Edge.Cuts from Mechanical 1 (246.8 × 154.7 mm); mounting holes H1–H4 = `ac_psu:Terminal_D4.0mm_Drill3.0mm`, board-only, no net, at the IPC 'hole' records; design rules (below); User.1–4 renamed `Proteus.{F,In1,In2,B}.Pours`; board thickness 2.267 mm (Proteus stack). |
| 3b | `tools/gerber_to_tracks.py` | Parses the copper and drill gerbers (`tools/gerber.py`). Conductor D01 draws → 4052 tracks; **pour edge strokes are not tracks** (Proteus strokes every G36 region and every clear hole with the pour's edge width, 0.1016/0.1524/0.254 mm; a draw whose ends are consecutive region vertices is a stroke – stroke count equals region edge count on every layer); ViaPad flashes on all 4 layers + ViaDrill → 173 through vias 0.4572/0.3 (= the 173 IPC vias); every pad flash lands on a footprint pad, every drill on a pad hole or via; positive G36 outlines → User.1–4 (79 pours); the 3 NonConductor draws (two floating 0.15 mm lines beside J6 pins 29–34, top) → F.Cu graphic lines, no net. `load_copper()` is the shared reader (tracks, vias, pad flashes, pours with their holes and stroke width). |
| 3c | `tools/assign_nets.py` | Union-find over copper shapes (`tools/geom2d.py`: segment/polygon cores grown by a radius, pours with holes). Stage A (Proteus pad flashes + tracks + vias): 447 groups, 0 shorts, 16 orphans (vias that only touch pours), 45 opens (connections through pours) – expected. Stage B (+ Proteus pours): **248 groups = 244 KiCad nets + 4 mounting holes, 0 shorts, 0 orphans, 0 opens**; every track/via gets its group's net (4225), every pour its net → `reports/pour_nets.json`. Via nets cross-checked against the IPC via records (IPC → KiCad net map built from the pads, 208 nets 1:1). `--check`: same analysis on the saved board with KiCad pads, tracks, vias and the filled zones; every item must carry its group's net. Report `reports/assign_nets.txt`. |
| 3d | `tools/pours_to_zones.py` | One ZONE per pour: outline = Proteus copper = region grown by half the stroke minus its clear holes shrunk by half the stroke (62 stroke-closed holes vanish, 405 kept), net from `pour_nets.json`, solid pad connection, min width 0.1 mm, islands removed, priority = Proteus draw order; filled with ZONE_FILLER. |
| 5 | `tools/drc.py` | `kicad-cli pcb drc --schematic-parity --severity-all` → `reports/drc.json` (not committed); fails on shorts, unconnected items, parity issues and error types not in its `ACCEPTED` list. |
| – | `tools/check_board.py` | Saved board vs IPC: 898 pads within 0.05 mm (worst 0.038) and on the IPC net (IPC ↔ KiCad nets 1:1 via the pads, N/C pins on no/`unconnected-` nets), 4 mounting holes (plated 3.0/4.0, no net), 173 vias at the IPC via positions on the IPC net, every track/via/zone has a net. |

How Proteus pours work (and why the zones look like this): the pour copper is the G36 region
plus its edge stroke; clear (`%LPC%`) regions after it are its holes: clearance cut-outs around
other-net copper, **thermal reliefs** (a hole around a same-net pad bridged by short spoke
*tracks*, which are imported as ordinary tracks), and deliberate isolation of a same-net via or
pad from the pour on that layer. Pads inside the pour without a hole are connected solid. The
zones keep every hole, so the KiCad fill reproduces the Proteus copper; KiCad's 0.15 mm
clearance applies on top (it only bites where a KiCad pad is larger than the Proteus pad).
Exported F.Cu (kicad-cli svg) was compared by eye with a render of the Proteus top copper:
same pours, holes, spokes and tracks.

Design rules (board setup, stored in `kicad/ac_psu.kicad_pro`): clearance 0.15 mm (Proteus
uses 6 mil: the smallest gap between different nets in the gerbers is 0.1514 mm, arc
rounding), min track 0.1 mm (thinnest Proteus track 0.1016), via 0.45 min / annular 0.075 /
drill 0.3 (Proteus vias 0.4572/0.3), hole clearance 0.15, hole-to-hole 0.25, copper-edge 0.25;
Default netclass 0.254 track, 0.4572/0.3 via.

### Phase 3 – footprint changes (user decision 2026-10-19)

The first DRC with KiCad library pads gave 2 shorts (U11 pins 9–11 touched the ADA3 track
routed past their ends; U2 pin 3 touched an ISOGND track), 54 clearance errors and 4 mask
bridges – all where KiCad pads are larger than the Proteus pads and reach Proteus tracks. The
user chose (1) Proteus pad sizes for exactly those packages and (2) Proteus pads + drills
where the KiCad drill was smaller than Proteus. `tools/gen_footprints.py` now derives
(`ipc_sizes=True`, pad centres and sizes/drills from one IPC part, KiCad graphics kept):

| Footprint | From | Change |
|---|---|---|
| `PinHeader_2x24_P1.27mm_Vertical_Pins15-48` (J1–J4, J6, J8), `PinHeader_2x19_P1.27mm_Vertical_Proteus` (J11) | J1 / J11 | pads 1.0 → 0.812 mm |
| `TSSOP-16_4.4x5mm_P0.65mm_Proteus` (U11), `TSSOP-8_3x3mm_P0.65mm_Proteus` (U1, U7) | U11 / U1 | pads 1.475×0.4 → 1.1×0.4; TSSOP-8's 0.2 mm footprint clearance dropped (Proteus land patterns use the board rule) |
| `SOT-23-5_TLV316` (U2, U12, U14), `SOT-23_Proteus` (Q13, Q14, REF1, REF2) | U2 / REF1 | pads 1.325×0.6 → 0.635×0.508; 1.475×0.6 → 1.016×0.889 |
| `SOIC-16W_7.5x10.3mm_P1.27mm_Proteus` (U13, U15–U17) | U13 | pads 2.05×0.6 → 1.85×0.65 |
| `TO-247-3_Vertical_Proteus` (Q1–Q12) | Q1 | pads 3.048 round (pin 1 square), drill 1.5 → 1.651 |
| `Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus` (U8, U9) | U8 | pads 1.8, drill 1.0 → 1.2 |
| `C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus` (C21, C25, C33, C34) | C21 | pads 2.286, drill 1.2 → 1.27 (C24 keeps the KiCad footprint: its Proteus drill is 1.016) |
| `CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus` (C8, C11, C12, C61, C72, C79) | C11 | pads 4.0 → 5.08, drill 2.0 → 2.032 |

Courtyards of the footprints built from the IPC pads (TR2, CM1–3, R48/R64/R91, R20/R79, PIN
terminals, ACIN/ACOUT, mounting holes) were tightened from pad box + 1.0 mm to 0.25 mm around
body and pads (circles for single round PIN terminals): 60 → 50 courtyard overlaps.
The schematic sheets were re-run so their Footprint fields follow `lib/footprint_map.csv`
(only Footprint fields changed).

### Remaining DRC items (all justified, `tools/drc.py` passes)

| Type | Count | Why it stays |
|---|---|---|
| shorting_items / unconnected / schematic parity | 0 / 0 / 0 | – |
| courtyards_overlap (error) | 50 | Proteus placed parts closer than KiCad's IPC-7351 courtyards (mostly 0402/1206 passives beside ICs, film/disc caps, terminals). Parts sit exactly at the Proteus positions; accepted in `tools/drc.py`. |
| pth_inside_courtyard (error) | 6 | J4 pins 47/48 inside J6's courtyard (the 2×24 outline still covers J6's unfitted pins 1–14; physical 2×24 housings would clear by ≈0.1 mm), J12 pins inside U8's courtyard (see U8/U9 finding). Accepted. |
| silk_overlap / silk_over_copper / silk_edge_clearance (warning) | 199 / 199 / 12 | KiCad footprint silk and default reference positions on a dense Proteus placement (PLAN 3e: silk comes from the KiCad footprints; refdes positions could be taken from the Proteus assembly layers later). |
| via_dangling (warning) | 2 | Proteus copper as drawn: GND via at (91.80, −49.09) and VCC via at (43.69, −20.29) (IPC coordinates, Y up) connect on one layer only. |
| track_dangling (warning) | 1 | 0.14 mm PWM_TRANS5 stub on In2.Cu at (47.7, 43.6) (IPC coordinates) in the Proteus copper. |

### Findings (for the user / Phase 4)

- **U8/U9 (VXO7805) body side**: the Proteus top silk draws the converter body (11.5 × 7.3 mm)
  entirely on the −y side of the pin row (away from J12), the KiCad R-78E footprint puts most
  of the body on the +y side, over J12's pins (hence the J12/U8 courtyard errors). Pads and pin
  order match, so only the body/courtyard graphics differ. Check the VXO7805 datasheet: if
  Proteus is right, mirror the body graphics in the project footprint
  (`Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus`). **Note:** the orientation of the mirrored
  graphics needs to be checked (body side relative to the pin row and J12, pin-1 marking,
  courtyard) against the datasheet and the Proteus silk.
- C67 symbol (`C_Polarized` on sheet 7 vs `ac_psu:C` in part_map, non-polar 1206 land pattern)
  is still open (Phase 2 finding).
- KiCad pads are still larger than Proteus on footprints that have no DRC conflict (e.g.
  0402/0603/1206 passives, J12, TPS73033). The gerber round trip (Phase 4) will show them.

### pcbnew 10.0.7 quirks found in Phase 3

- `board.Remove(item)` + garbage collection of the item's Python proxy breaks SWIG's type
  table: later calls return untyped `SwigPyObject`s (`GetNetInfo()`, `ZONE.Outline()`) and
  "memory leak … no destructor found" floods stderr. Use `board.Delete(item)`; set
  `thisown = False` on items created in Python after `board.Add()`.
- `LoadBoard` re-derives track nets from the connected pads (a wrong net written into the file
  is silently corrected on load), and `SaveBoard` writes the board design settings into the
  `.kicad_pro`.
- `KIID.SeedGenerator(n)` makes new UUIDs reproducible.

### Last verification (`tools/check_all.sh`, Phase 3 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 42 footprints (28 project), up to date
check_footprints: pcbnew placement of 267 parts, worst pad offset 0.038 mm
check_footprints: 267/267 parts fitted, 898 pads, 42 footprints, worst residual 0.038 mm (limit 0.05)
check_board: 271 footprints, 898 pads, worst pad offset 0.038 mm (limit 0.05), 208 IPC nets mapped 1:1, 4 mounting holes
check_board: 4052 tracks, 173 vias, 79 zones
assign_nets: after zone fill: 248 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
drc: 469 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
drc:     50 error    courtyards_overlap  accepted: KiCad courtyards vs the Proteus placement
drc:      6 error    pth_inside_courtyard  accepted: KiCad courtyards vs the Proteus placement
drc:    199 warning  silk_overlap
drc:    199 warning  silk_over_copper
drc:     12 warning  silk_edge_clearance
drc:      2 warning  via_dangling
drc:      1 warning  track_dangling
ALL CHECKS PASSED
```

Negative tests: footprint moved 0.1 mm → check_board fails; via deleted → check_board and
assign_nets --check (open VCC) fail; track net changed in memory → assign_nets --check reports
the foreign net.

## Phase 4 verification and review – done (Fable 5.1, 2026-10-19)

Independent checks of the end result against the Proteus CADCAM files, plus a review of the
Phase 3 findings. Both new checks are part of `tools/check_all.sh` (pass/fail).

New / changed files:

- `tools/gerber.py` now also reads KiCad's plots: 4.6 format, obround apertures, aperture
  macros with several primitives and `$n` expressions (KiCad's `RoundRect`: outline + circles
  + vector lines), and the `%TO.P/.N/.C` object attributes (attached to every object as
  `.attrs`). The Proteus side is unchanged (`tools/make_pcb.sh` still reproduces the board
  byte for byte).
- `tools/gerber_roundtrip.py` (system python3: numpy, scipy, PIL) – PLAN 6.3. Exports the 4
  copper layers and the plated drill of the board with kicad-cli (gerbers + drill as gerber,
  to a temp dir), rasterises both gerber sets on one 0.025 mm grid (objects in file order with
  their polarity, so Proteus' clear regions cut the pours like a plotter; the Proteus board
  outline that Proteus draws into every copper gerber with a `Profile` aperture is skipped) and
  per layer: raw XOR area, differing area after a 0.05 mm tolerance, 8-connected difference
  clusters with side, area, position, nearest IPC pad/net and via, and a category (**pad shape**
  = inside the XOR of the two sets' pad flashes; **clearance** = Proteus copper within 0.15 +
  0.05 mm of a KiCad pad that is larger than the Proteus pad; **zone fill** = Proteus copper
  thinner than the 0.1 mm zone minimum width; **other** = finding). Because a 0.05 mm
  tolerance cannot see features thinner than 0.1 mm (thinnest Proteus track 0.1016 mm), it
  also checks **coverage**: the centre line of every draw and the centre of every flash of each
  set must lie on copper of the other set (1 px slack; samples inside the clearance / pad
  shape masks are explained). Drills: every Proteus drill has a KiCad drill within 0.05 mm
  and vice versa; KiCad may be larger (footprints kept with the KiCad drill, Phase 3 decision)
  but never smaller. Report `reports/roundtrip/roundtrip.txt` (every cluster ≥ 0.01 mm², pad
  shape clusters per footprint, drill table), overlays `reports/roundtrip/{F_Cu,In1_Cu,In2_Cu,
  B_Cu}.png` (0.1 mm/px: common copper grey, only Proteus red, only KiCad cyan, differences
  absorbed by the tolerance dim yellow). `--check` fails on an `other` cluster, an uncovered
  draw/flash or a drill mismatch. ≈ 40 s.
- `tools/ipc356_diff.py` (stdlib) – PLAN 6.4. Exports the board's IPC-D-356 with kicad-cli and
  matches every Proteus record (same truncated refdes + pin, nearest position; vias; mounting
  holes) to a KiCad record within 0.05 mm, then checks THT/SMD, side, drill (KiCad never
  smaller) and net by pad-set equivalence (Proteus nets ↔ KiCad nets 1:1; Proteus N/C and
  net-less pads ↔ KiCad `unconnected-(…)` / N/C). KiCad's file: units `CUST 0` = 0.0001 inch,
  net names > 14 characters as `NNAME` aliases, `Y0000` for round pads, refdes `VIA`, mounting
  holes `H1..H4` as N/C, bottom side = access code 04 (copper layer count).
- `tools/check_all.sh`: steps "IPC-D-356 from the board vs Proteus" and "Gerber round trip vs
  Proteus (copper, drills)".

### Gerber round trip (`tools/gerber_roundtrip.py`)

| Layer | Proteus copper | KiCad copper | raw XOR | only Proteus (> 0.05 mm) | only KiCad (> 0.05 mm) | clusters ≥ 0.01 mm² | uncovered draws/flashes |
|---|---|---|---|---|---|---|---|
| F.Cu | 19439.7 mm² | 19501.2 mm² | 94.38 mm² | 2.62 mm² | 58.34 mm² | 188 pad shape | 0 / 0 |
| In1.Cu | 6395.0 | 6489.9 | 99.09 | 0.00 | 81.57 | 91 pad shape | 0 / 0 |
| In2.Cu | 6519.7 | 6627.9 | 112.07 | 0.04 | 92.08 | 117 pad shape, 3 clearance | 0 / 0 (3 Proteus strokes explained) |
| B.Cu | 15580.9 | 15707.4 | 144.19 | 1.42 | 99.01 | 316 pad shape | 0 / 0 |

No `other` cluster on any layer: outside the pads the KiCad copper (tracks, vias, zone fills
with their holes and thermal spokes, the NonConductor lines) is the Proteus copper to within
0.05 mm, and every Proteus draw/flash is on KiCad copper and vice versa. Every cluster is
explained (the full list is in the report):

- **pad shape, only KiCad** (the bulk, 58–99 mm² per layer): the square pad 1 of the TO-247s
  (Proteus round 3.048; ≈ 20 mm² on F/B.Cu), the 2.0 mm pads of the 14 disc capacitors
  (`C_Disc_D12.5mm` vs Proteus 1.524; ≈ 31 mm² on the inner layers), the rounded-square pad 1
  of the 6 snap-in caps (Proteus round 5.08), the 1206 hand-solder pads (`R_1206 …
  Pad1.30x1.75mm`, 41 parts, vs Proteus 1.016 × 1.524; 26.6 mm² on B.Cu), R10 and C24 (KiCad
  2.4 mm pads vs Proteus 1.52 / 2.29), PWM1 (DIP-8 1.6 oval vs 1.524), J12 (1.0 vs 0.812),
  D_SMA/D_SOD-323 hand-solder pads, U4–U6 (ADuM7701 pads), U8/U9 (square pad 1), R59/R75/R94
  (0805), `C_1206 … Pad1.33x1.80mm`, and the round-rect corners of KiCad pads in general.
- **pad shape, only Proteus** (0–2.6 mm² per layer): Proteus pads are *larger* than KiCad's on
  the 0402 and 0603 passives (e.g. C 0402 0.609² vs KiCad 0.56 × 0.62, R 0603 group with 1.73 mm
  spacing 0.939 × 0.99 vs 0.9 × 0.95), the plain `R_1206_3216Metric` (R23/R24/R45/R47) and L1
  (0805, Proteus 1.6 × 1.0 pads). So the Phase 3 note "KiCad pads larger than Proteus on
  0402/0603" is the wrong way round; it is right for the 1206 hand-solder pads and J12.
  TPS73033 (U3/U10): 0.03 mm² in total.
- **clearance** (In2.Cu, 0.04 mm² in 3 clusters) and the 3 explained coverage misses: the
  ISOGND pour's edge strokes at the corners of J12-43, where KiCad's 0.15 mm clearance around
  the 1.0 mm square KiCad pad bites into Proteus copper that was 0.15 mm from the round 0.812 pad.
- Drills: 562 = 562 matched within 0.05 mm. Equal diameters everywhere (0.5588 vs 0.558 is
  rounding) except where the KiCad footprint drill is larger: 28 × 0.8128 → 1.0 (C_Disc), 7 ×
  0.762 → 0.8 (PWM1), 6 × 0.5588 → 0.65 (J12), 2 × 1.01 → 1.2 (R10), 2 × 1.016 → 1.2 (C24).

Blind spots of the round trip: a 0.05 mm tolerance hides differences in features narrower
than 0.1 mm – covered for tracks and flashes by the coverage check, not for pour slivers
under 0.1 mm (KiCad's zone minimum width removes those anyway); and copper that is redundant
with a same-net zone (a track inside its own pour) is, correctly, no copper difference.
Negative tests: a 53 mm F.Cu track (y = 44.6, mostly inside its pour) turned into a move → the
parts of it outside the pour appear as 3 `other` clusters (0.87 mm²), FAILED; a 0.33 mm In1.Cu
spoke inside its zone removed → no difference (as it should be); the board outline left in the
raster → 200 mm² `other` ring on every layer (how the Profile skip was found).

### IPC-D-356 diff (`tools/ipc356_diff.py`)

1075 Proteus records = 1075 KiCad records, all matched: 898 pads (incl. the 36 N/C / net-less
pads and the duplicate pin-1 holes of ACIN/ACOUT), 173 vias, 4 mounting holes; worst position
offset 0.039 mm; THT/SMD and side equal everywhere; 208 Proteus nets ↔ 208 KiCad nets 1:1;
**0 mismatches**. KiCad drills larger as above; pad sizes differ on 406 pads (info, the pad
shape list above). Negative test: one record moved to another net and one shifted 0.1 mm →
FAILED (the moved record breaks the 1:1 net mapping, the shifted one has no record within 0.05 mm).

### Review of the Phase 3 findings and the spot checks

- **Thermal reliefs / zone holes**: 79 zones with 409 holes, solid pad connection, 0.1 mm
  minimum width; the round trip shows the filled copper equals the Proteus pours with their
  holes and spoke tracks. Confirmed.
- **NonConductor lines beside J6**: 3 F.Cu graphic lines without net (0.1524 mm): (64.5, 52.7)–
  (69.05, 52.7), (65.39, 50.0)–(68.2, 50.0) and a 0.026 mm stub at (69.05, 52.7) – Phase 3 said
  "two lines", the third draw is the stub. Present in both gerber sets (coverage 0 misses).
- **Mounting holes** H1–H4: at the IPC positions, 3.0 mm plated, 4.0 mm pad, no net; the drill
  files agree. Confirmed.
- **Bottom-side parts**: 77, all SMD, pads only on B.Cu, silk on B.SilkS; the IPC diff confirms
  the side of every pad (KiCad access 04 ↔ Proteus 16). Confirmed.
- **ACIN1/2, ACOUT1/2**: two pads "1" per part, both on the net, matched by position. Confirmed.
- **R87 pads 4/5**: on `unconnected-(R87D-R4.1-Pad4)` / `…Pad5`, no net in Proteus; no copper
  touches them (DRC 0 shorts). Confirmed.
- **Kelvin shunts**: R48 1/3 = SHUNT1, 2 = SHUNT2, 4 = G1_SOURCE_HI; R64 DAB_SHUNT2 /
  DAB_SHUNT1 / ISOPGND / DAB_GROUND; R91 INU_SHUNT2 / INU_SHUNT1 / Q7_S / Net-(J7-Pad1) – as in
  the IPC. Confirmed.
- **Single-pin nets** ADA0/ADA4/ADA5/ADA6 (U11-15/1/2/4) and DGND (U11-6): one pad each, no
  track, no zone. Confirmed.
- **Dangling via/track warnings**: the copper is Proteus' to 0.05 mm, so the two vias
  connected on one layer only and the 0.14 mm PWM_TRANS5 stub are Proteus artefacts. Confirmed.
- **U8/U9 (VXO7805) body side** – still open, now with the datasheet facts (CUI VXO78-500,
  rev. 05/2023, mechanical drawing p. 3): body 10.0 × 7.2 × 11.0 mm, pins Ø 1.2 on 2.54 mm, pin
  row 1.80 mm from the module-PCB face and 5.40 mm from the component face; the front view
  (component side, toroid visible) numbers the pins 1-2-3 left to right. With pin 1 at −x
  (U8/U9 at 0°) that puts the body bulk on the **−y side of the pin row – the Proteus silk**
  (body entirely on −y, away from J12); the KiCad R-78E graphics put 6.56 mm on +y and 2.06 mm
  on −y (KiCad frame: body −6.56 … +2.06, pin 1 at x = 0). **But** the same page's
  "Recommended PCB Layout Top View" draws the outline on the other side of the pin row (pins
  at the bottom edge, pin 1 left), so the datasheet is internally inconsistent. If Proteus is
  right the footprint body should span y = −5.4 … +1.8 (IPC frame; plus 0.25 mm courtyard),
  which would also remove the 4 J12/U8 `pth_inside_courtyard` errors (J12's pads are 3.1 mm
  on the +y side). Not changed – decide with a physical part in hand; after mirroring, check
  pin-1 marking, body side vs J12 and the courtyard again.
- **C67** (`C_Polarized` on sheet 7 vs `ac_psu:C` in part_map, non-polar 1206 land pattern):
  unchanged, open.
- **KiCad pads larger than Proteus** where there is no DRC conflict: quantified above
  (per footprint in `reports/roundtrip/roundtrip.txt`); largest only-KiCad copper on the TO-247
  square pad 1, the disc caps, the snap-in pad 1 and the 1206 hand-solder pads; 0402/0603 are
  the other way round. All within DRC (0 clearance errors).
- Scripts read for the review (`build_pcb.py` rules, `pours_to_zones.py`, `assign_nets.py`,
  `check_board.py`, `drc.py`): nothing found that the two independent checks did not already
  cover; design rules in the board are the Proteus values (clearance 0.15, track 0.1, via
  0.45/0.3, 4 layers, 2.267 mm).

### Final state of the migration

- Schematic: 11 sheets generated by `tools/sheets/sheetNN.py`, pin-for-pin identical to the
  Proteus IPC-D-356A netlist (`compare_netlists.py`: 267/267 parts, 894 pins, 0 wrong-net pins,
  244/244 nets complete), ERC 0 errors (8 expected warnings).
- Footprints: 42 (14 KiCad library, 28 project), every pad within 0.038 mm of the Proteus pad.
- Board: generated by `tools/make_pcb.sh` from the schematic and the Proteus gerbers,
  reproducible byte for byte; 271 footprints, 4052 tracks, 173 vias, 79 zones; copper
  connectivity 0 shorts / 0 opens; DRC 0 shorts, 0 unconnected, 0 parity issues (50 + 6
  courtyard errors and 413 silk/dangling warnings accepted, see Phase 3); KiCad copper = Proteus
  copper to 0.05 mm except pad shapes (listed above); KiCad IPC-D-356 = Proteus IPC-D-356
  (positions, sides, nets).
- Open points (user decisions): U8/U9 body graphics, C67 symbol, silk/refdes positions
  (KiCad footprint defaults, PLAN 3e), KiCad vs Proteus pad sizes where DRC does not force a
  choice, KiCad drills larger than Proteus on C_Disc/J12/PWM1/R10/C24.

### Last verification (`tools/check_all.sh`, Phase 4 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 42 footprints (28 project), up to date
check_footprints: 267/267 parts fitted, 898 pads, 42 footprints, worst residual 0.038 mm (limit 0.05)
check_board: 271 footprints, 898 pads, worst pad offset 0.038 mm (limit 0.05), 208 IPC nets mapped 1:1, 4 mounting holes
check_board: 4052 tracks, 173 vias, 79 zones
assign_nets: after zone fill: 248 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
drc: 469 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
ipc356_diff: Proteus 1075 records, KiCad 1075; matched 1075 (898 pads incl. 36 N/C, 173 vias, 4 holes), worst position offset 0.039 mm (limit 0.05)
ipc356_diff: 208 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
roundtrip: F.Cu   XOR   94.38 mm^2, beyond 0.05 mm: only Proteus   2.62, only KiCad  58.34 mm^2; clusters >= 0.01 mm^2: 188 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In1.Cu XOR   99.09 mm^2, beyond 0.05 mm: only Proteus   0.00, only KiCad  81.57 mm^2; clusters >= 0.01 mm^2: 91 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In2.Cu XOR  112.07 mm^2, beyond 0.05 mm: only Proteus   0.04, only KiCad  92.08 mm^2; clusters >= 0.01 mm^2: 117 pad shape, 3 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: B.Cu   XOR  144.19 mm^2, beyond 0.05 mm: only Proteus   1.42, only KiCad  99.01 mm^2; clusters >= 0.01 mm^2: 316 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: drills 0 mismatches; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png
ALL CHECKS PASSED
```

## Next

The migration is complete. What remains are the user decisions listed under "Final state of
the migration" (U8/U9 body graphics, C67 symbol, silk/refdes positions, pad sizes/drills kept
from KiCad). `next_prompt.md` has a prompt for that optional clean-up session.

## Next prompt

See `next_prompt.md`.
