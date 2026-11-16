#!/usr/bin/env bash
# Card-area routing chain (reports/v5_layout/routing_brief.md). Rerunnable: every stage reads the placed board
# of commit $BASE and the routes of the earlier stages, and writes its own routes; nothing is patched by hand.
#
#   tools/v5/route/run.sh            all stages, routed board in build/route/out/ac_psu.kicad_pcb, quick checks
#   tools/v5/route/run.sh 3          from stage 3 on (earlier route files are kept)
#   tools/v5/route/run.sh install    copy build/route/out/ac_psu.kicad_pcb to kicad/ (then: tools/check_all.sh)
#
# A board copy is always build/route/<dir>/ac_psu.kicad_pcb with ac_psu.kicad_pro and ac_psu.kicad_dru next to
# it: without them pcbnew fills the zones without the domain rules, and SaveBoard writes a default project file
# (so the two files are copied again after every save).
set -eu
cd "$(dirname "$0")/../../.."
BASE=7c4dfc0
B=build/route
KIPY=tools/p2k/bin/kipy
R=tools/v5/route
FROM=${1:-0}
STAGES="s1_iso_signals s2_iso_analog s3_ctrl_j11 s4_ctrl_analog s5_buck s6_primary s7_planes s8_iso_supplies"

prep() { mkdir -p "$B/$1"; cp kicad/ac_psu.kicad_pro kicad/ac_psu.kicad_dru "$B/$1/"; }

if [ "$FROM" = install ]; then
    cp "$B/out/ac_psu.kicad_pcb" kicad/ac_psu.kicad_pcb
    echo "run.sh: installed build/route/out/ac_psu.kicad_pcb as kicad/ac_psu.kicad_pcb"
    exit 0
fi

if [ "$FROM" -le 0 ] || [ ! -f "$B/s0.json" ]; then
    prep base; prep s0
    git show "$BASE:kicad/ac_psu.kicad_pcb" > "$B/base/ac_psu.kicad_pcb"
    $KIPY $R/s0_swap.py "$B/base/ac_psu.kicad_pcb" "$B/s0/ac_psu.kicad_pcb"
    prep s0
    $KIPY $R/extract.py "$B/s0/ac_psu.kicad_pcb" "$B/s0.json"
    python3 $R/quick_drc.py "$B/base/ac_psu.kicad_pcb" > /dev/null      # the open connections before routing
    cp "$B/base/ac_psu.kicad_pcb.drc.json" "$B/base.drc.json"
fi

n=0
prev=""
for s in $STAGES; do
    n=$((n + 1))
    [ -f "$R/$s.py" ] || continue
    if [ "$n" -ge "$FROM" ] || [ ! -f "$B/r$n.json" ]; then
        echo "== stage $n: $s"
        # shellcheck disable=SC2086
        python3 "$R/$s.py" "$B/s0.json" "$B/r$n.json" $prev | grep -E '^==|!!|^router|^stage' || true
    fi
    prev="$prev $B/r$n.json"
done

# apply, DRC, drop the stubs that DRC calls dangling, until none is left (the drop list starts empty)
python3 $R/verify_routes.py $prev
rm -f "$B/drop.json"
for pass in 1 2 3 4 5; do
    prep out
    # shellcheck disable=SC2086
    $KIPY $R/apply.py "$B/s0/ac_psu.kicad_pcb" "$B/out/ac_psu.kicad_pcb" $prev "--drop=$B/drop.json"
    prep out
    python3 $R/quick_drc.py "$B/out/ac_psu.kicad_pcb" > "$B/quick_drc.txt"
    python3 $R/cleanup.py "$B/out/ac_psu.kicad_pcb" "$B/drop.json" && break
done
cat "$B/quick_drc.txt"
python3 $R/group_report.py "$B/base.drc.json" "$B/out/ac_psu.kicad_pcb.drc.json" || true
$KIPY tools/v5/check_layout.py --board "$B/out/ac_psu.kicad_pcb" | tail -4
$KIPY tools/v4/domain_gaps.py --board "$B/out/ac_psu.kicad_pcb" | tail -3
