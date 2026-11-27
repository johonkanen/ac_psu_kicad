#!/usr/bin/env bash
# Block F chain (V6_PLAN.md section 16): drawn design -> block_F_copper.csv -> replay on a fresh 3227a58 board ->
# checks. Block F needs no router step (block_F.md): its eight crossing nets are drawn by block_F_make.py.
#   tools/v6/route/block_F_chain.sh
# Boards in build/blockF/. Heavy jobs (refill + DRC) wait for 6 GB of free memory and take
# ~/.cache/ac_psu_heavy.lock (V6_PLAN 10a); kicad/ac_psu.kicad_pcb is never written.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
W="$R/build/blockF"; mkdir -p "$W"
BASE_REV="${BASE_REV:-3227a58}"
KIPY="$R/tools/p2k/bin/kipy"
kp() { "$KIPY" "$@" 2>&1 | grep -v -e "^Debug" -e "memory leak" || true; }

echo "== 00 base board $BASE_REV, refilled (reference numbers)"
git -C "$R" show "$BASE_REV:kicad/ac_psu.kicad_pcb" > "$W/base.kicad_pcb"
cp "$W/base.kicad_pcb" "$W/base_filled.kicad_pcb"
LIST=1 "$H/block_F_drc.sh" "$W/base_filled.kicad_pcb" "$W/base.drc.json" | sed 's/^/   /'
kp "$H/islands.py" "$W/base_filled.kicad_pcb" "$W/base.islands.json" | tail -1 | sed 's/^/   /'

echo "== 10 design -> CSV"
kp "$H/block_F_make.py" "$W/base.kicad_pcb" | sed 's/^/   /'

echo "== 20 replay on a fresh $BASE_REV board"
git -C "$R" show "$BASE_REV:kicad/ac_psu.kicad_pcb" > "$W/fresh.kicad_pcb"
kp "$H/block_F.py" --board "$W/fresh.kicad_pcb" --out "$W/replay.kicad_pcb" | sed 's/^/   /'

echo "== 30 checks on the replayed board (refilled)"
LIST=1 "$H/block_F_drc.sh" "$W/replay.kicad_pcb" "$W/replay.drc.json" | sed 's/^/   /'
kp "$H/islands.py" "$W/replay.kicad_pcb" "$W/replay.islands.json" "$W/base.islands.json" | tail -3 | sed 's/^/   /'
kp "$R/tools/v4/domain_gaps.py" --board "$W/replay.kicad_pcb" | tail -1 | sed 's/^/   /'
kp "$R/tools/v5/check_layout.py" --board "$W/replay.kicad_pcb" | tail -2 | sed 's/^/   /'
cp "$R/reports/assign_nets.txt" "$W/assign_nets.save"
AC_PSU_BOARD="$W/replay.kicad_pcb" "$KIPY" "$R/tools/assign_nets.py" --check 2>&1 | grep -v Debug | tail -3 | sed 's/^/   /' || true
cp "$W/assign_nets.save" "$R/reports/assign_nets.txt"

echo "== 40 renders of F (x -40 .. 42, y -48 .. 48)"
"$H/block_F_render.sh" "$W/replay.kicad_pcb" "$R/reports/v6/blocks/block_F" | sed 's/^/   /'
