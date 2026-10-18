# Status

Updated: 2026-10-18 (Phase 1 done – schematic redrawn and verified against the IPC netlist)

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

## Next

Phase 2 – footprints and geometric check (Opus 5.5), PLAN.md section 4. Then Phase 3.

## Next prompt

See `next_prompt.md`.
