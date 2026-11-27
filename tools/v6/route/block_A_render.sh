#!/usr/bin/env bash
# Renders of block A: one PNG per copper layer of the whole block (x -130 .. 0, y -85 .. -10), and a zoom of the AFE
# sense / choke landing area (x -45 .. 0, y -85 .. -38) per layer.
#   tools/v6/route/block_A_render.sh BOARD OUTDIR        (render the refilled board)
set -euo pipefail
R="$(cd "$(dirname "$0")/../../.." && pwd)"
B="$1"; O="$2"; mkdir -p "$O"
RA() { python3 "$R/tools/v4/render_area.py" "$@" --board "$B" > /dev/null; }
for L in F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu; do
    RA -130 0 -85 -10 "$O/A_$L.png" --layers "$L,Edge.Cuts,F.Fab,B.Fab" --ppm 10 &
    RA -45 0 -85 -38 "$O/A_sense_$L.png" --layers "$L,Edge.Cuts,F.Fab,B.Fab" --ppm 25 &
    wait
done
ls "$O"/A_*.png
