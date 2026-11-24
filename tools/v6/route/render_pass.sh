#!/usr/bin/env bash
# Renders of a routed v6 board for the pass report: one PNG per copper layer of the whole board, and zooms (all
# copper layers stacked, plus fab) of the six card headers, the two current-sense blocks and the passage past J37.
#   tools/v6/route/render_pass.sh [BOARD] [OUTDIR]     (defaults: kicad/ac_psu.kicad_pcb, reports/v6/pass1/render)
set -euo pipefail
R="$(cd "$(dirname "$0")/../../.." && pwd)"
B="${1:-$R/kicad/ac_psu.kicad_pcb}"; O="${2:-$R/reports/v6/pass1/render}"; mkdir -p "$O"
RA() { python3 "$R/tools/v4/render_area.py" "$@" --board "$B" > /dev/null; }
for L in F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu; do
    RA -129 125 -85 72 "$O/board_$L.png" --layers "$L,Edge.Cuts,F.Fab" --ppm 7 &
done
wait
CU="F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,Edge.Cuts,F.Fab,B.Fab"
while read -r name x0 x1 y0 y1; do
    RA "$x0" "$x1" "$y0" "$y1" "$O/zoom_$name.png" --layers "$CU" --ppm 20 &
done <<'EOF'
J21 -6 14 -58 -42
J22 44 64 -64 -48
J23 80 100 -64 -48
J24 4 22 36 52
J25 54 72 42 56
J26 86 104 42 56
sense_AFE -46 -18 -84 -48
sense_INV -102 -66 38 72
passage_J37 18 60 40 60
EOF
wait
ls "$O"
