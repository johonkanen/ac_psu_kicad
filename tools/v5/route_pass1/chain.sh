#!/usr/bin/env bash
# Routing pass of the card area and the aux flyback area (to judge the placement, not to ship). Pass 2 form.
#   tools/v5/route_pass1/chain.sh [LAST_STEP] [FROM_STEP]
# Placed board kicad/ac_psu.kicad_pcb -> $ROUTE_DIR/routed.kicad_pcb (default build/route); every step's board is
# kept as NN_step.kicad_pcb (+ .log / .json). Net groups: groups.json (make_groups.py), rules: routing.json.
# The design board is not written. Every router step has a time budget (TMO seconds, default below); a step that
# runs out is skipped as a whole (its nets stay open) and says so.
#   WEST_FENCE=0   drop the two fences west of x 22 (see prep.py) before routing
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
SK="${ROUTING_SKILL:-$HOME/.claude/skills/kicad-agentic-routing/scripts}"
export KICAD_ENV="${KICAD_ENV:-$R/tools/p2k/bin/kicad_env.sh}"
source "$SK/kenv.sh"
export ROUTING_CONFIG="$R/routing.json"
W="${ROUTE_DIR:-$R/build/route}"; mkdir -p "$W"
LAST="${1:-}"; FROM="${2:-}"
OUT="$W/routed.kicad_pcb"
N=0; SKIP=0; [ -n "$FROM" ] && SKIP=1
DEF_TMO=600

python3 "$H/make_groups.py" > /dev/null

gate() {    # DRC gate for scripted copper
    cp "$R/kicad/ac_psu.kicad_pro" "${1%.kicad_pcb}.kicad_pro"; cp "$R/kicad/ac_psu.kicad_dru" "${1%.kicad_pcb}.kicad_dru"
    kcli pcb drc --severity-all --format json -o "${1%.kicad_pcb}.drc.json" "$1" > /dev/null || true
    python3 -I "$SK/prep_check.py" "${1%.kicad_pcb}.drc.json"
}

script() {  # script NAME MODE: a scripted-copper step (prep.py / scripted.py), gated, numbered like a router step
    N=$((N + 1)); local out="$W/$(printf %02d "$N")_$1.kicad_pcb"
    if [ "$SKIP" = 1 ] && [ "$FROM" != "$1" ]; then CUR="$out"; return; fi
    SKIP=0; echo "== $1"
    if [ "${4:-}" = fill ] || [ -z "${4:-}" ]; then kpy "$H/$2" "$3" "$CUR" "$out" | grep -v "Debug: Adding"
    else kpy "$H/$2" "$3" "$CUR" "$out" "$4" | grep -v "Debug: Adding"; fi
    if [ "${4:-}" = fill ]; then kpy "$SK/fill_zones.py" "$out" "$out" | tail -1; fi
    gate "$out"; CUR="$out"
    kpy "$SK/lock_tracks.py" "$CUR" lock-all | tail -1
    if [ "$LAST" = "$1" ]; then cp "$CUR" "$OUT"; echo "stopped after $1: wrote $OUT"; exit 0; fi
}

step() {    # step NAME GROUPS [route.py options]
    N=$((N + 1)); local out="$W/$(printf %02d "$N")_$1.kicad_pcb"
    if [ "$SKIP" = 1 ] && [ "$FROM" != "$1" ]; then CUR="$out"; return; fi
    SKIP=0; echo "== $1 (domain ${D:?step without a domain})"; local t0=$SECONDS tmo="${TMO:-$DEF_TMO}"
    # the fence of this step's domain (prep.py DOMAIN_FENCES): the router does not know the 5 mm class rules
    local in="$W/_in_$1.kicad_pcb"
    kpy "$H/prep.py" domain "$CUR" "$in" "$D" > /dev/null
    cp "${CUR%.kicad_pcb}.kicad_pro" "${in%.kicad_pcb}.kicad_pro"; cp "${CUR%.kicad_pcb}.kicad_dru" "${in%.kicad_pcb}.kicad_dru"
    CUR="$in"
    set +e
    timeout "$tmo" python3 -I "$SK/route_step.py" "$CUR" "$out" "${@:2}" \
        --net-clearances "${NC:-$H/hv_clearances.json}" 2>&1 | cut -c1-600
    local rc=$?; set -e
    if [ "$rc" = 124 ]; then      # time budget used up: the step is skipped, its nets stay open
        pkill -f "route.py $CUR" || true
        echo "   TIMED OUT after $tmo s: step skipped"; cp "$CUR" "$out"
        cp "${CUR%.kicad_pcb}.kicad_pro" "${out%.kicad_pcb}.kicad_pro"; cp "${CUR%.kicad_pcb}.kicad_dru" "${out%.kicad_pcb}.kicad_dru"
    elif [ "$rc" != 0 ]; then exit "$rc"; fi
    CUR="$out"
    kpy "$SK/lock_tracks.py" "$CUR" lock-all | tail -1
    echo "   $((SECONDS - t0)) s"
    if [ "$LAST" = "$1" ]; then cp "$CUR" "$OUT"; echo "stopped after $1: wrote $OUT"; exit 0; fi
}

# --- prep: lock the existing copper, temporary keep-outs and fences (In1 / In4 fenced inside the card planes from
#     the start), header stubs; then a via at each of the six divider-tap inputs of the U7 / U2 block --------------
CUR="$R/kicad/ac_psu.kicad_pcb"
script prep prep.py prep fill
if [ "${WEST_FENCE:-1}" = 0 ] && { [ "$SKIP" = 0 ] || [ "$FROM" = taps_vias ]; }; then
    kpy "$H/prep.py" unfence "$CUR" "$CUR"
fi
script taps_vias scripted.py taps
# --- (run before the bus: this router step deleted the drawn lanes of nets that were still open, pass 3 try 1)
# --- aux flyback, high voltage, before any other primary net (most constrained; low-voltage tracks laid first
#     took the room around R98 / C112 in the first try): escape stubs at the HV pads that have low-voltage copper closer than 2.5 mm (scripted.py), then
#     the HV nets (2.5 mm to every other net, 1.0 mm between two HV nets: hv_step_clearances.json), then the
#     controller's small signals (2.5 mm to the HV nets: hv_clearances.json, the default of every step)
script hv_stubs scripted.py hvstubs
D=P NC="$H/hv_step_clearances.json" step aux_hv    aux_hv    --layers F.Cu B.Cu --power-nets AUX_DRAIN AUX_CLAMP AUX_VIN 'DC+' --power-nets-widths 1.0 0.6 0.6 0.6
# --- the passage north of J11 as a fanned bus (scripted.py fan, pass 4): 11 signal lanes on In3 entered from the
#     J6 / J4 gap, on In4 5V_ISOL (0.8 mm, from pin J4-45, drops onto J6-45 and J8-45) and ISOGND (0.4 mm, from the
#     plane edge through the J4 column at x 90.69). Then hooks: a via beside the source pin and In3 up to the lane
#     start for the five lane nets that start at U20 / U21. Then westends: vias at U4-7 / R50-2 and on the old In2
#     tracks of the six taps. The router does what is left of the ends.
script bus scripted.py fan
script hooks scripted.py hooks PWM_TRANS6,PWM_Q7,PWM_Q5,MDATA_INU,INU_ADCLK
script westends scripted.py westends
# --- ISO side. The PWM lines to J6 / J4 first: they cross the DC bus band on In3 only (pin -> via south of the
#     band -> In3 -> through-hole pin), so everything that runs east-west there has to go around them. Then the
#     nets that pass north of J11 (In3 / In4; F.Cu / B.Cu fenced there), then the rest of the ISO signals.
D=I step pwm_rest  pwm_rest  --layers In3.Cu B.Cu F.Cu --layer-costs 1 2 3
#     North of the bus band a via fits only in a few patches (via_scan.py: x 59.5..72 beside the J6 pins, x 77.5..79,
#     above J8 at x 26..40, west of J8), so In4 is hard to enter there and In3 carries most of the passage: these
#     nets get the board's narrowest track (0.152 mm).
D=I step passage_a PWM_TRANS6,PWM_Q7,PWM_Q5,INU_ADCLK,MDATA_INU,GPIO_BYPASS_RLY_ISO  --layers In3.Cu In4.Cu B.Cu F.Cu In2.Cu --layer-costs 1 1.2 3 2 8 --track-width 0.152
D=I step passage_b passage  --layers In3.Cu In4.Cu B.Cu F.Cu In2.Cu --layer-costs 1 1.2 3 2 8 --track-width 0.152
D=I step sdm_rest  sdm_rest  --layers In3.Cu B.Cu F.Cu --layer-costs 1 2 2
D=I step taps_rest taps_rest,other --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 2 1 8
D=I TMO=420 step left_iso  passage,pwm_rest --layers In3.Cu In4.Cu F.Cu B.Cu In2.Cu --layer-costs 1 1.2 1.5 1.5 8 --track-width 0.152
# --- CTRL piece at J11: the fan to the top-side isolators is planar on F.Cu in pin order (make_groups.py J11_TOP);
#     then the bottom-side isolators (all three layers), then the analog chain
D=C step j11_top   j11_top   --layers F.Cu --ordering original
D=C step j11_bot   j11_bot   --layers B.Cu In3.Cu F.Cu --layer-costs 1 1.2 1.5
D=C step ctrl_analog ctrl_analog --layers F.Cu In3.Cu B.Cu --layer-costs 2 2 1
# --- CTRL piece at J12: buck ------------------------------------------------------------------------------------
D=C step buck      buck      --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1 \
               --power-nets CTRL_SW CTRL_RAW CTRL_W --power-nets-widths 1.0 1.0 1.0
# --- primary side of U13/U15/U16, ADC and reference -------------------------------------------------------------
#     (In2 only to reach the old In2 track ends south of the VCC plane, y -21.6 .. -24.8)
D=P step primary   primary   --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 1.5 1 8
D=P step aux_lv    aux_lv --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1
D=I step aux_iso   aux_iso --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1
# --- leftovers of the signals, split by area (one step over everything ran out of time in pass 1) ----------------
D=C TMO=420 step left_ctrl j11_top,j11_bot --layers F.Cu In3.Cu B.Cu --layer-costs 1 1 1
D=P TMO=420 step left_pri  primary --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 1 1 8
# --- supplies. First a via next to every SMD pad of a plane net inside its plane (scripted.py planes, brief rule
#     7), zones refilled so the router sees the planes; then the router for what is left, one net per step, each
#     with its own time budget: pads outside the planes (U4 / C37 / J8 west of J11, the aux area) and the rails
#     without a plane (15V_ISO, 5V_ISOL, 15V, 5V_CTRL_A).
script plane_vias scripted.py planes fill
STMO="${SUPPLY_TMO:-420}"; ITMO="${ISOGND_TMO:-900}"      # time budget of each supply step, seconds
Q="--quick"                    # main pass only for the rails that timed out in pass 2: no rescue / reconciliation laps
PW=(--power-nets 3V3_CTRL CTRLGND_A CTRLGND 5V_CTRL 5V_CTRL_A 3V3_ISO ISOGND 15V_ISO 5V_ISOL GND VCC 15V
    --power-nets-widths 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.5 0.8 0.4 0.4 0.5)
for n in 5V_ISOL 15V_ISO 3V3_ISO ISOGND; do
    [ "$n" = ISOGND ] && STMO=$ITMO
    D=I TMO=$STMO step "supply_$n" "$n" --layers F.Cu In3.Cu In4.Cu B.Cu In2.Cu --layer-costs 1 2 2 1 8 "${PW[@]}" $Q
done
STMO="${SUPPLY_TMO:-420}"
D=C TMO=$STMO step supply_C  supply_C  --layers F.Cu In3.Cu B.Cu --layer-costs 1 4 1 "${PW[@]}"
for n in VCC 15V; do
    D=P TMO=$STMO step "supply_$n" "$n" --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 3 1 8 "${PW[@]}"
done
D=P TMO=$STMO step supply_GND GND --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 3 1 8 "${PW[@]}" $Q
# --- the router's power-net passes do not honour the fences (15V track at y -74 in pass 2): delete what lies in one
kpy "$H/prep.py" prune "$CUR" "$CUR" "$R/kicad/ac_psu.kicad_pcb" | grep -v "Debug: Adding"

cp "$CUR" "$W/final_locked.kicad_pcb"
kpy "$H/prep.py" finish "$CUR" "$OUT"
cp "$R/kicad/ac_psu.kicad_pro" "$W/routed.kicad_pro"; cp "$R/kicad/ac_psu.kicad_dru" "$W/routed.kicad_dru"
echo "wrote $OUT"
