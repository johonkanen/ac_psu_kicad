#!/usr/bin/env bash
# Rebuild kicad/ac_psu.kicad_pcb from the schematic and the Proteus CADCAM files (Phase 3).
#   1 build_pcb.py         footprints with nets at the Proteus positions, outline, holes
#   2 gerber_to_tracks.py  copper gerbers -> tracks and vias, pour outlines on User.1-4
#   3 assign_nets.py       nets of tracks/vias/pours by copper connectivity
#   4 pours_to_zones.py    pours -> filled zones
# Verify with tools/check_all.sh (board checks: check_board.py, assign_nets.py --check, drc.py).
set -eu
cd "$(dirname "$0")/.."
tools/bin/kipy tools/build_pcb.py
tools/bin/kipy tools/gerber_to_tracks.py
tools/bin/kipy tools/assign_nets.py
tools/bin/kipy tools/pours_to_zones.py
