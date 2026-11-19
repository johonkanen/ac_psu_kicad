#!/usr/bin/env bash
# First routing pass of the card area and the aux flyback area (to judge the placement, not to ship).
#   tools/v5/route_pass1/chain.sh [LAST_STEP] [FROM_STEP]
# Placed board kicad/ac_psu.kicad_pcb -> build/route/routed.kicad_pcb; every step's board is kept as
# build/route/NN_step.kicad_pcb (+ .log / .json). Net groups: groups.json (make_groups.py), rules: routing.json.
# The design board is not written.
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

python3 "$H/make_groups.py" > /dev/null

# --- prep: lock the existing copper, temporary keep-outs, J11 west-row stubs; gate with DRC ----------------------
CUR="$W/00_prep.kicad_pcb"
if [ "$SKIP" = 0 ]; then
    cp "$R/kicad/ac_psu.kicad_pro" "$W/00_prep.kicad_pro"; cp "$R/kicad/ac_psu.kicad_dru" "$W/00_prep.kicad_dru"
    kpy "$H/prep.py" prep "$R/kicad/ac_psu.kicad_pcb" "$CUR"
    kcli pcb drc --severity-all --format json -o "$W/prep.json" "$CUR" > /dev/null || true
    python3 -I "$SK/prep_check.py" "$W/prep.json"
fi

step() {    # step NAME GROUPS [route.py options]
    N=$((N + 1)); local out="$W/$(printf %02d "$N")_$1.kicad_pcb"
    if [ "$SKIP" = 1 ] && [ "$FROM" != "$1" ]; then CUR="$out"; return; fi
    SKIP=0; echo "== $1"; local t0=$SECONDS
    set +e
    timeout "${TMO:-1200}" python3 -I "$SK/route_step.py" "$CUR" "$out" "${@:2}" \
        --net-clearances "${NC:-$H/hv_clearances.json}" 2>&1 | cut -c1-600
    local rc=$?; set -e
    if [ "$rc" = 124 ]; then      # time limit (TMO seconds): the step is skipped, its nets stay open
        pkill -f "route.py $CUR" || true
        echo "   TIMED OUT after ${TMO:-1200} s: step skipped"; cp "$CUR" "$out"
        cp "${CUR%.kicad_pcb}.kicad_pro" "${out%.kicad_pcb}.kicad_pro"; cp "${CUR%.kicad_pcb}.kicad_dru" "${out%.kicad_pcb}.kicad_dru"
    elif [ "$rc" != 0 ]; then exit "$rc"; fi
    CUR="$out"
    kpy "$SK/lock_tracks.py" "$CUR" lock-all | tail -1
    echo "   $((SECONDS - t0)) s"
    if [ "$LAST" = "$1" ]; then cp "$CUR" "$OUT"; echo "stopped after $1: wrote $OUT"; exit 0; fi
}

# --- ISO side. The PWM lines to J6 / J4 first: they cross the DC bus band on In3 only (pin -> via south of the
#     band -> In3 -> through-hole pin), so everything that runs east-west there has to go around them. Then the
#     nets that pass north of J11 (In3 / In4; F.Cu / B.Cu fenced there), then the rest of the ISO signals.
step pwm_rest  pwm_rest  --layers In3.Cu B.Cu F.Cu --layer-costs 1 2 3
step passage   passage   --layers In3.Cu In4.Cu B.Cu F.Cu In2.Cu --layer-costs 1 1.2 3 2 8
step sdm_rest  sdm_rest  --layers In3.Cu B.Cu F.Cu --layer-costs 1 2 2
step taps_rest taps_rest,other --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 2 1 8
# --- CTRL piece at J11: the fan to the top-side isolators is planar on F.Cu in pin order (make_groups.py J11_TOP);
#     then the bottom-side isolators (all three layers), then the analog chain
step j11_top   j11_top   --layers F.Cu --ordering original
step j11_bot   j11_bot   --layers B.Cu In3.Cu F.Cu --layer-costs 1 1.2 1.5
step ctrl_analog ctrl_analog --layers F.Cu In3.Cu B.Cu --layer-costs 2 2 1
# --- CTRL piece at J12: buck ------------------------------------------------------------------------------------
step buck      buck      --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1 \
               --power-nets CTRL_SW CTRL_RAW CTRL_W --power-nets-widths 1.0 1.0 1.0
# --- primary side of U13/U15/U16, ADC and reference -------------------------------------------------------------
#     (In2 only to reach the old In2 track ends south of the VCC plane, y -21.6 .. -24.8)
step primary   primary   --layers F.Cu In3.Cu B.Cu In2.Cu --layer-costs 1 1.5 1 8
# --- aux flyback: high voltage first (2.5 mm to every other net, 1.0 mm between
#     two HV nets: hv_step_clearances.json), then the controller's small signals ----------
NC="$H/hv_step_clearances.json" step aux_hv    aux_hv    --layers F.Cu B.Cu --power-nets AUX_DRAIN AUX_CLAMP AUX_VIN 'DC+' --power-nets-widths 1.0 0.6 0.6 0.6
step aux_lv    aux_lv,aux_iso --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1
# --- supplies: stubs and vias to the planes ---------------------------------------------------------------------
step supply_C  supply_C  --layers F.Cu In3.Cu B.Cu --layer-costs 1 4 1 \
               --power-nets 3V3_CTRL CTRLGND_A CTRLGND 5V_CTRL 5V_CTRL_A --power-nets-widths 0.4 0.4 0.4 0.4 0.4
#     (supply_I joins the ISOGND / 3V3_ISO / 15V_ISO / 5V_ISOL copper west of J11 to the card planes through the
#     passage: it ran over 17 min in run 1 without ending, so it has a time limit)
TMO=480 step supply_I  supply_I  --layers F.Cu In3.Cu In4.Cu B.Cu --layer-costs 1 2 2 1 \
               --power-nets 3V3_ISO ISOGND 15V_ISO 5V_ISOL --power-nets-widths 0.4 0.4 0.5 0.8
step supply_P  supply_P  --layers F.Cu In3.Cu B.Cu --layer-costs 1 3 1 \
               --power-nets GND VCC 15V --power-nets-widths 0.4 0.4 0.5
# --- leftovers of the CTRL and primary signals, all three routing layers at equal cost ---------------------------
#     (one step over every open signal ran into the 8 min limit in run 2: the router spends its time on the
#     ISO nets that have no way; so the leftovers are split by area)
step leftovers j11_top,j11_bot,primary --layers F.Cu In3.Cu B.Cu --layer-costs 1 1 1
# --- second leftovers without the west fences (prep.py unfence), In4 / In2 allowed for the nets north of J11 ------
if [ "$SKIP" = 0 ] || [ "$FROM" = leftovers2 ]; then
    cp "$CUR" "$W/unfenced.kicad_pcb"; kpy "$H/prep.py" unfence "$W/unfenced.kicad_pcb" "$W/unfenced.kicad_pcb"
    cp "$R/kicad/ac_psu.kicad_pro" "$W/unfenced.kicad_pro"; cp "$R/kicad/ac_psu.kicad_dru" "$W/unfenced.kicad_dru"
    CUR="$W/unfenced.kicad_pcb"
fi
step leftovers2 passage,pwm_rest --layers In3.Cu In4.Cu F.Cu B.Cu In2.Cu --layer-costs 1 1.2 1.5 1.5 8

kpy "$H/prep.py" finish "$CUR" "$OUT"
cp "$R/kicad/ac_psu.kicad_pro" "$W/routed.kicad_pro"; cp "$R/kicad/ac_psu.kicad_dru" "$W/routed.kicad_dru"
echo "wrote $OUT"
