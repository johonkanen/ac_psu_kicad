#!/usr/bin/env bash
# Refill + DRC (+ schematic parity) of a block-A board with the project's rules. The board is checked as
# build/blockA/drc/ac_psu.kicad_pcb beside copies of kicad/ac_psu.kicad_pro / .kicad_dru / the schematic sheets, so
# kicad/ac_psu.kicad_pcb is never touched (a bare copy without the project files gives false errors).
#   tools/v6/route/block_F_drc.sh BOARD [OUT_JSON]       BOARD is replaced by its refilled copy
# Waits for 6 GB of free memory and takes ~/.cache/ac_psu_heavy.lock (V6_PLAN section 10a).
set -euo pipefail
R="$(cd "$(dirname "$0")/../../.." && pwd)"
B="$(readlink -f "$1")"; J="${2:-${B%.kicad_pcb}.drc.json}"
D="$R/build/blockA/drc"; mkdir -p "$D"
cp "$R"/kicad/*.kicad_sch "$R"/kicad/ac_psu.kicad_pro "$R"/kicad/ac_psu.kicad_dru "$R"/kicad/*-lib-table "$D/"
cp "$B" "$D/ac_psu.kicad_pcb"
while [ "$(free -g | awk '/^Mem:/{print $7}')" -lt 6 ]; do echo "(waiting for memory)"; sleep 20; done
flock "$HOME/.cache/ac_psu_heavy.lock" timeout 1200 "$R/tools/p2k/bin/kicad-cli" pcb drc --refill-zones --save-board \
    --schematic-parity --format json -o "$J" "$D/ac_psu.kicad_pcb" > /dev/null 2>&1 || true
cp "$D/ac_psu.kicad_pcb" "$B"
python3 "$R/tools/v6/route/drc_summary.py" "$J"
python3 "$R/tools/v6/route/block_A_check.py" "$J" ${LIST:+--list}
