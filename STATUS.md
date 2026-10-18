# Status

Updated: 2026-10-18 (Phase 1 transcription in progress)

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

## Phase 1 transcription – in progress (Fable 5.1)

Each sub-sheet is generated by a re-runnable script `tools/sheets/sheetNN.py` (uses
`tools/sheets/_common.py` helpers and `tools/sch_builder.py`; `Sheet.clear()` rebuilds the
sheet from scratch). Visual check: `tools/render_sheet.py kicad/NN_*.kicad_sch` →
`reports/render/NN_*.png` (kicad-cli SVG + librsvg/cairo via ctypes).
`compare_netlists.py` reports a *split* IPC net only as a warning while the net still has
pins on undrawn parts ("pending sheets ..."); it becomes an error once all its parts are drawn.

| Sheet | Parts | Status |
|---|---|---|
| 2 fpga connector | 8/8 | done 2026-10-18; compare 0 errors (2 pending splits PGND/ISOPGND), ERC 0 errors / 38 isolated-label warnings |
| 3 regulators | 18/18 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 11 signal isolators | 0/11 | |
| 10 INU SDM and relay drive | 0/23 | |
| 9 primary side ADC | 0/10 | |
| 8 SDM current measurements | 0/22 | |
| 1 afe | 0/48 | |
| 5 VSI | 0/43 | |
| 6 Dual Active Bridge | 0/16 | |
| 4 DC links | 0/37 | |
| 7 Auxiliary supply | 0/31 | |

Notes:

- PWR_FLAGs for GND, 20V, ISOGND, 20V_ISO_SEC are temporarily on sheet 2 (they enter
  through the connectors). Move them to sheet 7 (aux supply) when it is drawn – one flag per
  net. 5V/5V_ISOL/VCC/3V3_ISO are driven by power-output pins on sheet 3 (no flag needed).
- Two-pin parts get centred Reference/Value text from `sch_builder.place()` (KiCad mirrors
  or swaps field justification for rotated symbols); `vert2`/`horiz2` in `_common.py` place a
  two-pin part with a chosen pin at the top/left – check the IPC pin order (on sheet 3 every
  capacitor has pin 1 on the ground side).
- Sheet 2 labels follow the PDF (`G2_SOURCE_LO`, `DAB_SOURCE_LO_SEC`, `Q6_S`, …); the IPC
  names of those nets are PGND/DAB_GROUND/ISOPGND because they are tied to the power net on
  sheets 1/4/5/6 – the comparison is by pad set, so the names are only hints.

## Next

Phase 1 transcription: Fable 5.1, one sheet per turn, order 2 → 3 → 11 → 10 → 9 → 8 → 1 →
5 → 6 → 4 → 7 (PLAN.md section 3).

## Next prompt

See `next_prompt.md`.
