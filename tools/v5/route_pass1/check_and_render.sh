#!/usr/bin/env bash
# Checks and renders of a routing-pass board.
#   tools/v5/route_pass1/check_and_render.sh [ROUTED.kicad_pcb] [OUTDIR]
# 1. skill check_board.sh (DRC with zones refilled + schematic parity, plane audit, stats) -> OUTDIR/check/
# 2. check_pass.py (scope, rules 2 / 3 / 3a, plane layers, high-voltage spacing, open connections per group)
# 3. tools/v4/domain_gaps.py (5.0 mm between the domains on every layer) and tools/v5/check_layout.py
# 4. PNG per copper layer of the card area, the passage north of J11, the J11 fan-out and the aux area
# Windows are KiCad coordinates (y = -y of the IPC frame used in the documents).
set -uo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
SK="${ROUTING_SKILL:-$HOME/.claude/skills/kicad-agentic-routing/scripts}"
export KICAD_ENV="${KICAD_ENV:-$R/tools/p2k/bin/kicad_env.sh}"
export ROUTING_CONFIG="$R/routing.json"
source "$SK/kenv.sh"
B="${1:-$R/build/route/routed.kicad_pcb}"; O="${2:-$R/build/pass1}"
mkdir -p "$O"
cd "$R"
"$SK/check_board.sh" "$B" "$O/check" > "$O/check_board.txt" 2>&1
grep -v "^    \|^find:" "$O/check_board.txt" | grep -v "^  [0-9]* [A-Za-z0-9+_/()-]*$"
echo "--- DRC items that are not silk / courtyard / library:"
grep "^    " "$O/check_board.txt" | cut -d: -f1 | sort | uniq -c
C="$O/check/ac_psu.kicad_pcb"
echo "--- check_pass.py"
kpy "$H/check_pass.py" "$R/kicad/ac_psu.kicad_pcb" "$C" "$O/check/drc.json" | grep -v "Debug: Adding" | tee "$O/check_pass.txt"
echo "--- domain_gaps.py"
kpy "$R/tools/v4/domain_gaps.py" --board "$C" | grep -v "Debug: Adding" | tee "$O/domain_gaps.txt" | tail -15
echo "--- check_layout.py"
kpy "$R/tools/v5/check_layout.py" --board "$C" | grep -v "Debug: Adding" | tee "$O/check_layout.txt" | tail -15
echo "--- renders"
"$SK/render_layers.sh" "$C" "$O/card" F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu 400 38,-57,120,24
"$SK/render_layers.sh" "$C" "$O/passage" In3.Cu,In4.Cu,F.Cu,B.Cu 500 15,-58,95,-34
"$SK/render_layers.sh" "$C" "$O/j11" F.Cu,In3.Cu,B.Cu 600 42,-48,96,-9
"$SK/render_layers.sh" "$C" "$O/aux" F.Cu,In3.Cu,B.Cu 500 62,2,100,58
