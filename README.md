# ac_psu_kicad

Migration of the **single_phase_inverter_psu_v3** board ("Inverter PSU") from Proteus 8.12
to KiCad 10. The KiCad schematic is redrawn from the Proteus PDF, and the PCB is rebuilt
from the Proteus gerbers, so that every pad, track, via and pour carries a net from the new
schematic. The goal is a KiCad design that is **electrically identical** to the Proteus
original.

The Proteus project file is binary and cannot be read, so the IPC-D-356A netlist in the
CADCAM export is the reference: 208 nets, 267 parts, 1075 pads, each with net, refdes, pin
and coordinates. Every check in this repo compares against that file.

- `PLAN.md`: the full plan, inventory of the source files, risks and model usage.
- `STATUS.md`: what is done, the last verification output, findings about the original
  design, and what comes next.
- `next_prompt.md`: the prompt for the next work session, replaced at the end of every
  phase.

## Layout

```
source/      Proteus exports (read-only): schematic PDF + page renders, CADCAM zip
             (gerbers, drill, IPC-D-356A netlist)
reference/   tables generated from the IPC netlist: pads (CSV/JSON), pin→net per part,
             pins per net
lib/         ac_psu.kicad_sym (project symbols, pin numbers = IPC pin ids),
             ac_psu.pretty (project footprints), part_map.csv (refdes → sheet, symbol,
             value), footprint_map.csv (refdes → footprint)
kicad/       KiCad project: root sheet + 11 hierarchical sheets, ac_psu.kicad_pcb
             (Proteus-generated up to tag proteus-conversion-complete, v4 edits by tools/v4/)
tools/       scripts and checks (see below)
reports/     generated reports: footprint fit, net assignment, pour nets (committed);
             ERC and DRC (not committed)
```

## Phases

| Phase | Content | State |
|---|---|---|
| 0 | Tooling: KiCad AppImage wrappers, IPC-D-356A parser, pin/net reference tables | done |
| 1 | Schematic: symbol library and part map, netlist comparison script, project skeleton, transcription of the 11 sheets from the PDF | done |
| 2 | Footprints for every symbol, pad numbers = IPC pin ids, checked by fitting footprint pads onto the IPC pad coordinates | done |
| 3 | PCB: place footprints at the Proteus positions, convert gerber tracks/vias/pours into KiCad tracks, vias and zones, assign nets by copper connectivity | done |
| 4 | Verification: schematic netlist ≡ IPC, DRC clean, gerber round-trip overlay, regenerated IPC-356 pad list diff | not started |

`STATUS.md` holds the current state; this table is only updated when a phase finishes.

## Requirements

- KiCad 10.0.7 AppImage at `~/kicad/kicad-10.0.7-x86_64.AppImage`. The scripts mount it
  on demand and use its `kicad-cli` and Python (with `pcbnew`). Do not run the AppImage
  with `--version`; it hangs.
- Python 3 for the plain scripts.

## Tools

The generic tools are the shared [proteus2kicad](https://github.com/johonkanen/proteus2kicad)
repository, a git submodule in `tools/p2k` (clone with `git clone --recurse-submodules`, or
run `git submodule update --init`). Board values (source files, refdes/net fix-ups, expected
counts, layers, outline) are in `p2k_config.py`. The scripts in `tools/` are the ones not
moved yet; they import the shared modules from `p2k`. Wrappers: `tools/p2k/bin/p2k <tool>`,
`tools/p2k/bin/kipy` (KiCad's Python with pcbnew), `tools/p2k/bin/kicad-cli`.
The generic migration method distilled from this board, the playbook, is in proteus2kicad
(`tools/p2k/CONVERSION_PLAYBOOK.md`).

## Checks

Run everything with one command:

```sh
tools/check_all.sh
```

It runs:

| Step | Script |
|---|---|
| KiCad environment (pcbnew 10.0.7 loads) | `tools/p2k/bin/kipy` |
| IPC parser self-check | `tools/p2k/bin/p2k ipc356 --check` |
| Gerber X2 flashes and drills vs IPC, outline | `tools/p2k/bin/p2k check_sources` |
| Symbol library is up to date with its generator | `tools/gen_symbols.py --check` |
| Symbol pin sets match the IPC pins for every refdes (+ v4 deviations) | `tools/check_symbols_v4.py` |
| ERC | `tools/erc.sh` (report in `reports/erc.rpt`) |
| Schematic netlist vs IPC netlist (+ v4 deviations, values) | `tools/compare_netlists_v4.py` |
| Footprint library and map are up to date | `tools/gen_footprints.py --check` |
| Footprint pads fit the IPC pads (≤ 0.05 mm) | `tools/check_footprints.py --pcbnew` |
| Board pads/holes/vias vs IPC (position and net) | `tools/check_board.py` |
| Copper connectivity after zone fill: 0 shorts, 0 opens, every item on its group's net | `tools/assign_nets.py --check` |
| DRC with schematic parity: 0 shorts, 0 unconnected | `tools/drc.py` (report in `reports/drc.json`) |

`p2k compare_netlists` exports the KiCad netlist and compares nets as sets of
(refdes, pin), so net names do not have to match. It reports pins on the wrong net, merged
or split nets, N/C mismatches, missing or extra parts and pins, and progress per sheet.
Use `--sheet N` to check one sheet while drawing.

Other tools: `gen_symbols.py` builds `lib/ac_psu.kicad_sym` from KiCad standard symbols
and box symbols (helpers in `p2k.symgen`); `p2k.sch_builder` is a small library for writing schematic sheets from
Python; `p2k.sexpr` reads and writes KiCad s-expression files; `p2k make_skeleton` created
the project skeleton once; `tools/sheets/sheetNN.py` generate the 11 sheets.

**Since v4 the design board `kicad/ac_psu.kicad_pcb` is frozen**: it is edited directly by small
committed pcbnew scripts (`tools/v4/fix_*.py`, see STATUS.md "v4 design fixes"), and the Proteus
comparisons apply exactly the deviations listed in `lib/v4_deviations.csv` / `lib/v4_copper.csv`
(`tools/deviations.py`; wrappers `tools/compare_netlists_v4.py`, `tools/check_symbols_v4.py`).
`tools/make_pcb.sh` now rebuilds the *Proteus* board from the schematic at tag
`proteus-conversion-complete` into `build/proteus/` (regression check of the conversion tools,
`tools/regen_check.sh`). The Proteus board was built with `tools/make_pcb.sh`: `build_pcb.py` (footprints, nets, outline,
mounting holes), `gerber_to_tracks.py` (Proteus copper gerbers → tracks and vias, using
`p2k.gerber`), `assign_nets.py` (nets by copper connectivity, `p2k.geom2d`) and
`pours_to_zones.py` (Proteus pours → filled zones). The output is reproducible byte for byte.
