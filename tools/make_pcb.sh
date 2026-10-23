#!/usr/bin/env bash
# Rebuild the *Proteus* board (Phase 3) into build/proteus/src/kicad/ac_psu.kicad_pcb - reproducibility
# and regression check of the conversion tools, NOT the design board.
#
# Since v4 the design board kicad/ac_psu.kicad_pcb is frozen and edited directly (committed
# pcbnew scripts tools/v4/fix_*.py); this script never writes it. The Proteus board is built
# from the schematic, footprint fit and reports at tag proteus-conversion-complete (the design
# that is pin-for-pin identical to Proteus) with the raw Proteus reference (AC_PSU_PROTEUS=1):
#   1 build_pcb.py         footprints with nets at the Proteus positions, outline, holes
#   2 gerber_to_tracks.py  copper gerbers -> tracks and vias, pour outlines on User.1-4
#   3 assign_nets.py       nets of tracks/vias/pours by copper connectivity
#   4 pours_to_zones.py    pours -> filled zones
# tools/regen_check.sh compares the result byte for byte with the tag's kicad/ac_psu.kicad_pcb.
set -eu
cd "$(dirname "$0")/.."
TAG=proteus-conversion-complete
OUT=build/proteus
rm -rf "$OUT"; mkdir -p "$OUT/src"
git archive "$TAG" kicad lib reports | tar -x -C "$OUT/src"
export AC_PSU_PROTEUS=1
export AC_PSU_BOARD="$PWD/$OUT/src/kicad/ac_psu.kicad_pcb"   # next to the tag's .kicad_pro (as at the tag)
rm -f "$AC_PSU_BOARD"
export AC_PSU_SCHEMATIC="$PWD/$OUT/src/kicad/ac_psu.kicad_sch"
export AC_PSU_REPORTS="$PWD/$OUT/src/reports"
export AC_PSU_PRETTY="$PWD/$OUT/src/lib/ac_psu.pretty"            # the tag's project footprints
tools/p2k/bin/kipy tools/build_pcb.py
tools/p2k/bin/kipy tools/gerber_to_tracks.py
tools/p2k/bin/kipy tools/assign_nets.py
tools/p2k/bin/kipy tools/pours_to_zones.py
