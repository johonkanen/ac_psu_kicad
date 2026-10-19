# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase
(or session that stops mid-phase), see PLAN.md section 9 "Handoff prompt".

```
Read PLAN.md and STATUS.md in /home/jari/dev/ac_psu_kicad. Use Fable 5.1.
Phases 0-3 are done. The 11-sheet KiCad schematic matches the Proteus IPC-D-356A netlist, and
kicad/ac_psu.kicad_pcb is rebuilt from the Proteus gerbers by tools/make_pcb.sh (reproducible
byte for byte): 271 footprints at the Proteus positions (pads within 0.038 mm of the IPC pads,
on the IPC nets), 4052 tracks, 173 vias, 79 filled zones; copper connectivity 0 shorts / 0
opens; DRC 0 shorts, 0 unconnected, 0 schematic parity issues. Start Phase 4 (PLAN.md section
6): independent verification and final review.

Read first: STATUS.md (all of "Phase 3 PCB", including the footprint changes, the remaining DRC
items and the findings), PLAN.md section 6, reports/assign_nets.txt, tools/make_pcb.sh and the
docstrings of tools/build_pcb.py, gerber_to_tracks.py, assign_nets.py, pours_to_zones.py,
check_board.py, drc.py. Tools: tools/bin/kipy = AppImage python3.11 with pcbnew (no numpy);
tools/bin/kicad-cli (10.0.7, has `pcb export gerbers`, `pcb export ipcd356`, `pcb export svg`).
System python3 has numpy, scipy and PIL (use it for raster work). Never run the AppImage with
--version (hangs). Do not hand-edit the board: change the generating scripts and re-run
tools/make_pcb.sh (it removes and recreates tracks, vias and zones).

Verify state first: tools/check_all.sh. At handoff it printed
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
       (50 courtyards_overlap + 6 pth_inside_courtyard errors accepted, 413 silk/dangling warnings)
  ALL CHECKS PASSED
(the 8 ERC warnings and the accepted DRC items are explained in STATUS.md).

Steps (PLAN.md 6.3, 6.4 and a review):
1. Gerber round trip (tools/gerber_roundtrip.py, system python3): export KiCad gerbers
   (kicad-cli pcb export gerbers) and rasterise each copper layer of both sets on the same grid
   (Proteus side: tools/gerber.py parses the Proteus files; regions dark/clear in file order,
   strokes, flashes incl. PPAD macros; for the KiCad gerbers extend the parser as needed, e.g.
   arcs G02/G03 and aperture macros KiCad uses for round-rect pads, or rasterise kicad-cli SVG
   instead). XOR per layer: report the differing area per layer and the larger difference
   clusters with position and the nearest refdes/net; write overlay PNGs to reports/roundtrip/.
   Expected differences: pads where the KiCad pad size was kept (0402/0603/1206 passives, J12,
   TPS73033, ...), KiCad's 0.15 mm clearance where a KiCad pad is larger than Proteus', pad-1
   square TO-247 pads, zone fill rounding. Anything else (missing track, missing pour piece,
   extra copper) is a finding. Also compare the drill files (positions and diameters).
2. Pad list: kicad-cli pcb export ipcd356, parse it (tools/ipc356.py may help) and diff against
   the Proteus IPC file: every pad and via within 0.05 mm, same net (via the IPC <-> KiCad net
   mapping, names differ for #00xxx and sheet-local nets), N/C the same.
3. Independent review: read the generating scripts and spot-check the board in places that are
   easy to get wrong (thermal-relief spoke tracks + kept zone holes, the two floating
   NonConductor lines beside J6, the mounting holes, bottom-side parts, multi-pad pins ACIN/
   ACOUT, R87 pads 4/5, Kelvin shunts R48/R64/R91, single-pin nets ADA0/4/5/6 and DGND).
   Confirm or refute each Phase 3 finding.
4. Add the new checks to tools/check_all.sh where they give a pass/fail.

Open points to tell the user (do not change without asking):
- U8/U9 (VXO7805): Proteus silk draws the body on the opposite side of the pin row from the
  KiCad R-78E footprint (STATUS.md, Phase 3 findings); check the datasheet before mirroring the
  body graphics of ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus.
- C67: symbol C_Polarized on sheet 7 vs ac_psu:C in part_map, non-polar 1206 land pattern.
- KiCad silk/refdes positions are the footprint defaults (199 silk_overlap warnings);
  reference positions could be taken from the Proteus assembly layers if wanted (PLAN 3e).

Done when: the round-trip report exists with per-layer numbers and every difference cluster
explained (or listed as a finding); the KiCad IPC-D-356 diff shows 0 position/net mismatches;
tools/check_all.sh passes with the new checks; STATUS.md has a Phase 4 section (results,
findings, final state of the migration); next_prompt.md is replaced (either a prompt for the
remaining work, or a note that the migration is complete); committed; the session ends with
that prompt.
```
