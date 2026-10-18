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
lib/         ac_psu.kicad_sym (project symbols, pin numbers = IPC pin ids) and
             part_map.csv (refdes → sheet, symbol, value)
kicad/       KiCad project: root sheet + 11 hierarchical sheets
tools/       scripts and checks (see below)
reports/     generated reports, e.g. ERC (not committed)
```

## Phases

| Phase | Content | State |
|---|---|---|
| 0 | Tooling: KiCad AppImage wrappers, IPC-D-356A parser, pin/net reference tables | done |
| 1 | Schematic: symbol library and part map, netlist comparison script, project skeleton (done); transcription of the 11 sheets from the PDF (next) | in progress |
| 2 | Footprints for every symbol, pad numbers = IPC pin ids, checked by fitting footprint pads onto the IPC pad coordinates | not started |
| 3 | PCB: place footprints at the Proteus positions, convert gerber tracks/vias/pours into KiCad tracks, vias and zones, assign nets from the IPC pads, silkscreen and mask | not started |
| 4 | Verification: schematic netlist ≡ IPC, DRC clean, gerber round-trip overlay, regenerated IPC-356 pad list diff | not started |

`STATUS.md` holds the current state; this table is only updated when a phase finishes.

## Requirements

- KiCad 10.0.7 AppImage at `~/kicad/kicad-10.0.7-x86_64.AppImage`. The scripts mount it
  on demand and use its `kicad-cli` and Python (with `pcbnew`). Do not run the AppImage
  with `--version`; it hangs.
- Python 3 for the plain scripts.

## Checks

Run everything with one command:

```sh
tools/check_all.sh
```

It runs:

| Step | Script |
|---|---|
| KiCad environment (pcbnew 10.0.7 loads) | `tools/bin/kipy` |
| IPC parser self-check | `tools/ipc356.py --check` |
| Symbol library is up to date with its generator | `tools/gen_symbols.py --check` |
| Symbol pin sets match the IPC pins for every refdes | `tools/check_symbols.py` |
| ERC | `tools/erc.sh` (report in `reports/erc.rpt`) |
| Schematic netlist vs IPC netlist | `tools/compare_netlists.py` |

`compare_netlists.py` exports the KiCad netlist and compares nets as sets of
(refdes, pin), so net names do not have to match. It reports pins on the wrong net, merged
or split nets, N/C mismatches, missing or extra parts and pins, and progress per sheet.
Use `--sheet N` to check one sheet while drawing. `--allow-missing` is used in
`check_all.sh` until all sheets are drawn.

Other tools: `gen_symbols.py` builds `lib/ac_psu.kicad_sym` from KiCad standard symbols
and box symbols; `sch_builder.py` is a small library for writing schematic sheets from
Python; `sexpr.py` reads and writes KiCad s-expression files; `make_skeleton.py` created
the project skeleton once.
