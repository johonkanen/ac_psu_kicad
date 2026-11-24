#!/usr/bin/env bash
# v6 routing chain (V6_PLAN.md section 6 step 5), rerunnable: the committed v6-baseboard board -> routed board.
#   tools/v6/route/chain.sh [BASE_REV]        (default: v6-baseboard)
# Every step's board is kept as build/v6route/NN_name.kicad_pcb; the result is written to kicad/ac_psu.kicad_pcb.
# Heavy jobs (zone fill, router) take the shared lock ~/.cache/ac_psu_heavy.lock (V6_PLAN section 10a).
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
W="$R/build/v6route"; mkdir -p "$W" "$R/reports/v6/pass1"
BASE="${1:-v6-baseboard}"
BOARD="$R/kicad/ac_psu.kicad_pcb"
LOCK="$HOME/.cache/ac_psu_heavy.lock"; mkdir -p "$HOME/.cache"
KIPY="$R/tools/p2k/bin/kipy"; CLI="$R/tools/p2k/bin/kicad-cli"
fill() { flock "$LOCK" "$CLI" pcb drc --refill-zones --save-board --format json -o "$W/fill.json" "$BOARD" > /dev/null 2>&1 || true; }
keep() { cp "$BOARD" "$W/$1.kicad_pcb"; echo "   -> build/v6route/$1.kicad_pcb"; }

git -C "$R" show "$BASE:kicad/ac_psu.kicad_pcb" > "$BOARD"; keep 00_base
echo "== 01 aux routes (helper script, V6_PLAN section 10)"
flock "$LOCK" "$KIPY" "$R/tools/v6/aux_routes.py" 2>&1 | grep -v Debug | tail -2; fill; keep 01_aux
echo "== 02 aux fixes"
flock "$LOCK" "$KIPY" "$H/02_aux_fixes.py" 2>&1 | grep -v Debug | sed -n 2p; fill; keep 02_aux_fixes
echo "== 03 prune dangling copper in the v6 areas"
flock "$LOCK" "$KIPY" "$H/03_prune.py" 2>&1 | grep -v Debug | tail -1; fill; keep 03_prune
