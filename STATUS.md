# Status

Updated: 2026-10-17

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

## Next

Phase 1 (PLAN.md section 3), first session: Opus 5.5 – comparison script, project
skeleton, symbol library, power symbols. Sheet transcription afterwards with Fable 5.1.

## Next prompt

```
Read PLAN.md and STATUS.md in /home/jari/dev/ac_psu_kicad. Use Opus 5.5.
Phase 0 is done; start Phase 1 (PLAN.md section 3), the preparatory part only (the
11-sheet transcription is a later Fable 5.1 session).

Read first: PLAN.md sections 3, 6.1 and 9; STATUS.md "Findings that matter for Phase 1";
reference/pin_nets_by_component.md and reference/pins_by_net.md (generated from the IPC
file; reference/ipc356_pads.json has the same data machine-readable).
Tools: tools/bin/kipy (AppImage python with pcbnew), tools/bin/kicad-cli (10.0.7); both
mount the AppImage on demand. Never run the AppImage with --version (it hangs).

Verify state first: tools/check_all.sh. At handoff it printed
  ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34,
          vias=173, holes=4, parts=267
  ALL CHECKS PASSED

Tasks:
1. tools/compare_netlists.py (PLAN.md 6.1): export the KiCad netlist with
   `kicad-cli sch export netlist --format kicadxml`, compare against
   reference/ipc356_pads.json by pad-set equivalence per net (names only as hints;
   74 nets are auto-named #00xxx). Report wrong-net pins, missing/extra parts and pins,
   N/C mismatches. Support per-sheet progress (e.g. --sheet or a summary of which IPC
   refdes are already present) so it is useful while only some sheets are drawn.
   Ignore TR1 (off-board, "Exclude from board"). Add it to tools/check_all.sh.
2. KiCad project skeleton kicad/ac_psu.kicad_pro + root sheet with 11 hierarchical
   sheets named after the Proteus sheets (see PLAN.md section 1 / source/schematic_pdf).
3. lib/ac_psu.kicad_sym: project symbols whose pin numbers equal the IPC pin ids
   (diodes A/C, C3M0065090D 1/2/3, shunt FKK5R0020FE 1..4, relays 1..6, EF20 TR2 1..10,
   WE-CMBNC chokes, IW1830, VXO7805-500, terminals, ACIN/ACOUT with two pads numbered 1,
   connectors J1..J12 with only the used pins) and project power symbols with names
   exactly as in the IPC (GND, PGND, ISOGND, ISOPGND, DGND, 3V3, 3V3_ISO, 5V, 5V_ISOL,
   20V, 20V_ISO_SEC, DC+, ISODC+, RET_ISO, VCC – check the actual list in
   reference/pins_by_net.md). Check every symbol's pin set against the IPC table with a
   script, not by eye.
4. Run ERC on the skeleton via kicad-cli.

Open points: Proteus pin ids vs KiCad standard symbols (use project copies where
they differ); TR1 handling; R87 pins 4/5 have no net; single-pin nets ADA0/4/5/6, DGND.

Done when: tools/check_all.sh runs compare_netlists.py against the (still empty)
schematic and reports all 267 IPC parts as missing without crashing; the symbol pin-set
check passes for every part type; ERC runs; STATUS.md updated, committed, and the
session ends with the handoff prompt for the Fable 5.1 sheet-transcription session.
```
