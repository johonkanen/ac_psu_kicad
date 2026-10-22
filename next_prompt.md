# Next prompt

Ready-to-paste prompt for the next agent session.

```
Work in /home/jari/dev/ac_psu_kicad (KiCad 10.0.7 migration of a Proteus board, conversion
complete and tagged proteus-conversion-complete). Read README.md, PLAN.md, STATUS.md (first the
section "v4 design fixes – in progress", then the tools/p2k and "Regression procedure" parts) and
tools/check_all.sh. Never run the KiCad AppImage with --version.

Task: five design fixes for board revision v4 (user decisions already made):
- Freeze the generated board: kicad/ac_psu.kicad_pcb is edited directly with small committed pcbnew
  scripts (tools/v4/fix_*.py, run once). tools/make_pcb.sh must not overwrite it any more (build the
  Proteus board from the tagged schematic into build/proteus/, used by regen_check). Proteus
  comparisons stay strict, with an explicit reviewed deviation list (lib/v4_deviations.csv,
  lib/v4_copper.csv) consumed by project-local wrappers; prefer not to touch tools/p2k (if needed:
  STATUS regression procedure, commit there, do not push).
- Fix 1 RET_ISO -> ISOGND (sheet 7 power symbol; board: re-net and join to ISOGND, In1 zone plan in STATUS).
- Fix 2 U11-6 INH from DGND to GND (sheet 9; board track pad 6 -> pad 7). Remove DGND if unused.
- Fix 3 C88 (ADA2) and C89 (ADA3) 1 nF 0402 to GND like C42 (JLC C1523), near U11 (plan in STATUS).
- Fix 4 per ADuM7701 a 100 nF C0G 1206 (JLC C170182) between VIN+ and VIN- (C90 U4, C91 U5,
  C92 U6) close to the input pins, and R92/R93, R57/R58, R73/R74 10R -> 12.4R (0402, JLC C477607).
  Text note on the sheet and in STATUS: with 100 nF, R_leg ~= 2.5 Ohm per nH (4 nH 10R, 5 nH 12.4R,
  6 nH 15R). OPEN QUESTION (ask the user first): at U4/U5 the cap needs a via jump and the F.Cu
  above is an HV pour (ISODC+ / PGND) -> vias with ~1.8 mm F.Cu pour keep-outs, or a larger local
  re-route? U6 is low-voltage, vias are fine.
- Fix 5 split SHUNT1 at R48: pin 1 sense (keeps SHUNT1 with U5-4, R58-2, C52-2, C53-2, D8-A, C71-2,
  C73-2), pin 3 force (SHUNT1_FORCE with J5-1); pin roles are verified, the 6 B.Cu tracks to delete
  are listed in STATUS.
Schematic changes through tools/sheets/sheetNN.py (+ _common.adum_block), part_map,
gen_footprints, gen_symbols; "v4: ..." text note beside each fix. New footprints without
courtyard collisions where avoidable; existing parts not moved. DRC: 0 shorts / 0 unconnected / 0
parity, no new error types. Add the new parts and the 12.4R line to fab/jlc_bom.csv.

Verify first: tools/check_all.sh (~1 min) must end with ALL CHECKS PASSED (output as in STATUS
Phase 4: compare 267/267, check_board 208 IPC nets 1:1, drc 469 violations 0/0/0, ipc356_diff 0
mismatches, roundtrip pad shape clusters only).

Done when: all five fixes in schematic and board, tools/check_all.sh passes with the Proteus
comparisons reporting exactly the listed deviations, renders of the changed sheets
(p2k render_sheet) and board areas (tools/v4/render_area.py) checked by eye, STATUS.md section
"v4 design fixes" (what/why/changes/positions/deviation list/check output), next_prompt.md
replaced, committed (Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>), not pushed.
```
