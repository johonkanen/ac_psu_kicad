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
B="${1:-$R/build/route/routed.kicad_pcb}"; O="${2:-$R/build/pass2}"
mkdir -p "$O"
cd "$R"
"$SK/check_board.sh" "$B" "$O/check" > "$O/check_board.txt" 2>&1
grep -v "^    \|^find:" "$O/check_board.txt" | grep -v "^  [0-9]* [A-Za-z0-9+_/()-]*$"
echo "--- DRC items that are not silk / courtyard / library:"
grep "^    " "$O/check_board.txt" | cut -d: -f1 | sort | uniq -c
C="$O/check/ac_psu.kicad_pcb"
echo "--- check_pass.py"
"$SK/check_board.sh" "$R/kicad/ac_psu.kicad_pcb" "$O/base" > "$O/base_check_board.txt" 2>&1     # refilled placed board
kpy "$H/check_pass.py" "$R/kicad/ac_psu.kicad_pcb" "$C" "$O/check/drc.json" "$O/base/ac_psu.kicad_pcb" | grep -v "Debug: Adding" | tee "$O/check_pass.txt"
echo "--- domain_gaps.py"
kpy "$R/tools/v4/domain_gaps.py" --board "$C" | grep -v "Debug: Adding" | tee "$O/domain_gaps.txt" | tail -15
echo "--- check_layout.py"
kpy "$R/tools/v5/check_layout.py" --board "$C" | grep -v "Debug: Adding" | tee "$O/check_layout.txt" | tail -15
echo "--- renders"
"$SK/render_layers.sh" "$C" "$O/aux" F.Cu,In2.Cu,In3.Cu,B.Cu 500 64,2,92,58             # aux flyback with the In2 GND pour
"$SK/render_layers.sh" "$C" "$O/r87" F.Cu,B.Cu 3000 56,-8,67,-1                        # CLK1 escape at R87
"$SK/render_layers.sh" "$C" "$O/j11_22" F.Cu,B.Cu 1200 42,-40,62,-28                   # J11-22 stub
"$SK/render_layers.sh" "$C" "$O/passage" In3.Cu,In4.Cu 900 15,-59,60,-49               # the passage
