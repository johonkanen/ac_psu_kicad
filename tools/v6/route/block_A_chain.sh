#!/usr/bin/env bash
# Block A chain (V6_PLAN.md section 16): drawn design -> block_A_copper.csv -> replay on a fresh d639e0e board ->
# checks. Block A needs no router run: every piece is drawn by block_A_make.py (geo.Ctx tests, grid runs on one
# layer), see block_A.md.
#   tools/v6/route/block_A_chain.sh
# Boards in build/blockA/. Heavy jobs (refill + DRC, domain_gaps) wait for 6 GB of free memory and take
# ~/.cache/ac_psu_heavy.lock (V6_PLAN 10a); kicad/ac_psu.kicad_pcb is never written.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
W="$R/build/blockA"; mkdir -p "$W"
BASE_REV="${BASE_REV:-d639e0e}"
KIPY="$R/tools/p2k/bin/kipy"
LOCK="$HOME/.cache/ac_psu_heavy.lock"
kp() { "$KIPY" "$@" 2>&1 | grep -v -e "Debug:" -e "memory leak" || true; }
memwait() { while [ "$(free -g | awk '/^Mem:/{print $7}')" -lt 6 ]; do echo "   (waiting for memory)"; sleep 20; done; }
checks() {   # checks NAME BOARD(refilled)
    kp "$H/islands.py" "$2" "$W/$1.islands.json" ${3:+"$3"} | tail -8 | sed 's/^/   /'
    memwait
    flock "$LOCK" "$KIPY" "$R/tools/v4/domain_gaps.py" --board "$2" 2>&1 | grep -v Debug | tail -1 | sed 's/^/   /' || true
    kp "$R/tools/v5/check_layout.py" --board "$2" | tail -1 | sed 's/^/   /'
    cp "$R/reports/assign_nets.txt" "$W/assign_nets.save"
    AC_PSU_BOARD="$2" "$KIPY" "$R/tools/assign_nets.py" --check 2>&1 | grep -v Debug | tail -3 | sed 's/^/   /' || true
    cp "$W/assign_nets.save" "$R/reports/assign_nets.txt"
}

echo "== 00 base board $BASE_REV, refilled (reference numbers)"
git -C "$R" show "$BASE_REV:kicad/ac_psu.kicad_pcb" > "$W/base.kicad_pcb"
cp "$W/base.kicad_pcb" "$W/base_filled.kicad_pcb"
LIST=1 "$H/block_A_drc.sh" "$W/base_filled.kicad_pcb" "$W/base.drc.json" | sed 's/^/   /'
checks base "$W/base_filled.kicad_pcb"
kp "$H/block_A_hv.py" "$W/base_filled.kicad_pcb" | tail -1 | sed 's/^/   /'

echo "== 10 design -> CSV (drawn on the refilled base: geo.Ctx reads the pour fills)"
kp "$H/block_A_make.py" "$W/base_filled.kicad_pcb" "$W/make.kicad_pcb" | grep -v "^    (" | sed 's/^/   /'

echo "== 20 replay on a fresh $BASE_REV board"
git -C "$R" show "$BASE_REV:kicad/ac_psu.kicad_pcb" > "$W/fresh.kicad_pcb"
kp "$H/block_A.py" --board "$W/fresh.kicad_pcb" --out "$W/replay.kicad_pcb" | sed 's/^/   /'
kp "$H/block_A_same.py" "$W/replay.kicad_pcb" "$W/make.kicad_pcb" | sed 's/^/   /'
kp "$H/block_A.py" --board "$W/replay.kicad_pcb" --dry | tail -1 | sed 's/^/   (second run refuses: /; s/$/)/'

echo "== 30 checks on the replayed board (refilled)"
LIST=1 "$H/block_A_drc.sh" "$W/replay.kicad_pcb" "$W/replay.drc.json" | sed 's/^/   /'
checks replay "$W/replay.kicad_pcb" "$W/base.islands.json"
kp "$H/block_A_hv.py" "$W/replay.kicad_pcb" --new "$H/block_A_copper.csv" | tail -1 | sed 's/^/   /'

echo "== 40 renders of A"
"$H/block_A_render.sh" "$W/replay.kicad_pcb" "$R/reports/v6/blocks/block_A" | sed 's/^/   /'

echo "== 50 rows for lib/v6_copper.csv"
python3 "$H/block_A_rows.py" | sed 's/^/   /'
