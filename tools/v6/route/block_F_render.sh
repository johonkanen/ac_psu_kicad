#!/usr/bin/env bash
# Renders of block F (x -40 .. 42, y -48 .. 48): one PNG per copper layer, plus F_inner.png (In1 / In2 / In3 stacked).
#   tools/v6/route/block_F_render.sh BOARD OUTDIR        (render the refilled board)
set -euo pipefail
R="$(cd "$(dirname "$0")/../../.." && pwd)"
B="$1"; O="$2"; mkdir -p "$O"
RA() { python3 "$R/tools/v4/render_area.py" -40 42 -48 48 "$@" --board "$B" --ppm 14 > /dev/null; }
for L in F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu; do
    RA "$O/F_$L.png" --layers "$L,Edge.Cuts,F.Fab,B.Fab" &
done
wait
RA "$O/F_inner.png" --layers "In1.Cu,In2.Cu,In3.Cu,Edge.Cuts,F.Fab,B.Fab"
ls "$O"/F_*.png
