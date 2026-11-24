#!/usr/bin/env bash
# v6 routing chain (V6_PLAN.md section 6 step 5), rerunnable: the committed v6-baseboard board -> routed board.
#   tools/v6/route/chain.sh [FROM [LAST]]       FROM / LAST: step numbers (default 00 .. the end); BASE_REV env
#                                                (default v6-baseboard)
# Every step's board is kept as build/v6route/NN_name.kicad_pcb; the result is written to kicad/ac_psu.kicad_pcb.
# A run from FROM > 00 starts from the kept board of the step before it.
# Heavy jobs (zone fill, DRC, router) take the shared lock ~/.cache/ac_psu_heavy.lock and wait for 6 GB of free
# memory first (V6_PLAN section 10a). After every step from 04 on: refill + DRC (kicad-cli), the island count of
# every pour against step 03 (islands.py: a split pour fails the step), open connections per net group.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
W="$R/build/v6route"; L="$R/reports/v6/pass1"; mkdir -p "$W" "$L"
FROM="${1:-00}"; LAST="${2:-99}"
BASE="${BASE_REV:-v6-baseboard}"
BOARD="$R/kicad/ac_psu.kicad_pcb"
LOCK="$HOME/.cache/ac_psu_heavy.lock"; mkdir -p "$HOME/.cache"
KIPY="$R/tools/p2k/bin/kipy"; CLI="$R/tools/p2k/bin/kicad-cli"
SK="${ROUTING_SKILL:-$HOME/.claude/skills/kicad-agentic-routing/scripts}"
export KICAD_ENV="$R/tools/p2k/bin/kicad_env.sh" ROUTING_CONFIG="$H/routing.json"
T0=$SECONDS

memwait() { while [ "$(free -g | awk '/^Mem:/{print $7}')" -lt 6 ]; do echo "   (waiting for memory)"; sleep 20; done; }
heavy() { memwait; flock "$LOCK" "$@"; }
fill() { heavy "$CLI" pcb drc --refill-zones --save-board --format json -o "$W/fill.json" "$BOARD" > /dev/null 2>&1 || true; }
keep() { cp "$BOARD" "$W/$1.kicad_pcb"; echo "   -> build/v6route/$1.kicad_pcb"; }
kp() { "$KIPY" "$@" 2>&1 | grep -v -e "^Debug" -e "memory leak" || true; }
run_it() { [ "$((10#$1))" -ge "$((10#$FROM))" ] && [ "$((10#$1))" -le "$((10#$LAST))" ]; }
CURN=""
resume() {  # board of the step before FROM
    local f; f=$(ls "$W"/[0-9][0-9]_*.kicad_pcb 2>/dev/null | awk -F/ -v n="$((10#$FROM))" '{s=$NF; if (substr(s,1,2)+0 < n) print}' | sort | tail -1)
    [ -n "$f" ] || { echo "no kept board before step $FROM"; exit 1; }
    cp "$f" "$BOARD"; echo "== resume from $(basename "$f")"
}
check() {   # check NN_name: refill + DRC, islands against 03, opens per group; log in reports/v6/pass1/NN_name.check
    local n="$1"
    heavy "$CLI" pcb drc --refill-zones --save-board --schematic-parity --format json -o "$W/$n.drc.json" "$BOARD" > /dev/null 2>&1 || true
    {
        python3 "$H/drc_summary.py" "$W/$n.drc.json"
        python3 "$H/groups_v6.py" "$W/$n.drc.json" | head -1
        kp "$H/islands.py" "$BOARD" "$W/$n.islands.json" "$W/03_prune.islands.json" | tail -8
    } | tee "$L/$n.check" | sed 's/^/   /'
}
script() {  # script NN name SCRIPT [args]: scripted copper (kipy SCRIPT IN OUT args), then lock, check
    local nn="$1" name="$2" s="$3"; shift 3
    run_it "$nn" || return 0
    echo "== $nn $name"; local t=$SECONDS
    kp "$H/$s" "$BOARD" "$BOARD" "$@" | tee "$L/${nn}_$name.log" | tail -25
    kp "$H/fence.py" lock "$BOARD" "$BOARD" > /dev/null
    check "${nn}_$name"; keep "${nn}_$name"; echo "   $((SECONDS - t)) s"
}
rstep() {   # rstep NN name DOMAIN TMO NETCLR NETS [route.py options]: one KRT step fenced to its domain
    local nn="$1" name="$2" d="$3" tmo="$4" nc="$5" nets="$6"; shift 6
    run_it "$nn" || return 0
    echo "== $nn $name (domain $d, $tmo s)"; local t=$SECONDS
    kp "$H/fence.py" domain "$BOARD" "$W/_in.kicad_pcb" "$d" "$nets" "${LATE:-}" > /dev/null
    memwait
    set +e
    flock "$LOCK" timeout "$tmo" python3 -I "$SK/route_step.py" "$W/_in.kicad_pcb" "$W/_out.kicad_pcb" "$nets" "$@" \
        --net-clearances "$H/$nc" > "$L/${nn}_$name.log" 2>&1
    local rc=$?; set -e
    cut -c1-400 "$L/${nn}_$name.log" | tail -6 | sed 's/^/   /'
    if [ "$rc" = 124 ]; then
        pkill -f "route.py $W/_in.kicad_pcb" || true
        echo "   TIMED OUT after $tmo s: step skipped" | tee -a "$L/${nn}_$name.log"
    elif [ "$rc" != 0 ]; then echo "   router failed ($rc): step skipped" | tee -a "$L/${nn}_$name.log"
    else
        kp "$H/fence.py" clear "$W/_out.kicad_pcb" "$BOARD" > /dev/null
        kp "$H/fence.py" lock "$BOARD" "$BOARD" > /dev/null
    fi
    check "${nn}_$name"; keep "${nn}_$name"; echo "   $((SECONDS - t)) s"
}

if [ "$FROM" = 00 ]; then
    git -C "$R" show "$BASE:kicad/ac_psu.kicad_pcb" > "$BOARD"; keep 00_base
else
    resume
fi
if run_it 01; then
    echo "== 01 aux routes (helper script, V6_PLAN section 10)"
    heavy "$KIPY" "$R/tools/v6/aux_routes.py" 2>&1 | grep -v Debug | tail -2; fill; keep 01_aux
fi
if run_it 02; then
    echo "== 02 aux fixes"
    heavy "$KIPY" "$H/02_aux_fixes.py" 2>&1 | grep -v Debug | sed -n 2p; fill; keep 02_aux_fixes
fi
if run_it 03; then
    echo "== 03 prune dangling copper in the v6 areas"
    heavy "$KIPY" "$H/03_prune.py" 2>&1 | grep -v Debug | tail -1; fill; keep 03_prune
    check 03_prune
fi

# --- pass 1 (planning session rules 2026-11-24): lock, then the drawn structures, then router steps by group ------
if run_it 04; then
    echo "== 04 lock the existing copper; per-net clearance files from hv.py"
    kp "$H/fence.py" lock "$BOARD" "$BOARD"; kp "$H/gen_clearances.py" "$BOARD"; keep 04_lock
fi
#     the six divider taps (U7 / U2 -> west of J24), drawn through the via column between the J37 / J38 tongues;
#     keep-outs reserve the room of the late ISO sigma-delta link
script 05 taps 05_sdm.py taps
source "$H/steps.sh"

if [ "$((10#$LAST))" -ge 90 ]; then
    kp "$H/fence.py" clear "$BOARD" "$BOARD"
    check 99_final; keep 99_final
fi
echo "chain: $((SECONDS - T0)) s"
