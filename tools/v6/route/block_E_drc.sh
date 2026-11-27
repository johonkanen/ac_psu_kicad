#!/usr/bin/env bash
# Refill + DRC of a block-E board with the project's rules (the board is checked as kicad/ac_psu.kicad_pcb, beside
# ac_psu.kicad_pro / .kicad_dru; that file is restored afterwards).
#   tools/v6/route/block_E_drc.sh BOARD [OUT_JSON]       BOARD is replaced by its refilled copy
# Waits for 6 GB of free memory and takes ~/.cache/ac_psu_heavy.lock (V6_PLAN section 10a).
set -euo pipefail
R="$(cd "$(dirname "$0")/../../.." && pwd)"
B="$(readlink -f "$1")"; J="${2:-${B%.kicad_pcb}.drc.json}"
K="$R/kicad/ac_psu.kicad_pcb"
while [ "$(free -g | awk '/^Mem:/{print $7}')" -lt 6 ]; do echo "(waiting for memory)"; sleep 20; done
cp "$K" "$K.blockE-save"
cp "$B" "$K"
flock "$HOME/.cache/ac_psu_heavy.lock" timeout 1200 "$R/tools/p2k/bin/kicad-cli" pcb drc --refill-zones --save-board \
    --schematic-parity --format json -o "$J" "$K" > /dev/null 2>&1 || true
cp "$K" "$B"
mv "$K.blockE-save" "$K"
python3 "$R/tools/v6/route/drc_summary.py" "$J"
python3 "$R/tools/v6/route/block_E_check.py" "$J" ${LIST:+--list}
