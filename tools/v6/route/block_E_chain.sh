#!/usr/bin/env bash
# Block E routing chain (development; V6_PLAN.md section 16). Makes the copper that block_E.py replays:
#   tools/v6/route/block_E_chain.sh [FROM [LAST]]
# 00: the 6226a75 board cleaned by block_E.py --clean-only, refilled. Then router steps fenced to E and their domain
# (block_E_fence.py), scripted plane vias after the J11 / J12 fans, supplies, leftovers. Boards in build/blockE/NN_*.
# At the end: block_E_make.py copper (00 board -> last board) writes the CSV.
# Heavy jobs wait for 6 GB of free memory and take ~/.cache/ac_psu_heavy.lock (V6_PLAN 10a); every router call has a
# timeout.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$H/../../.." && pwd)"
W="$R/build/blockE"; L="$W/log"; mkdir -p "$W" "$L"
FROM="${1:-00}"; LAST="${2:-99}"
LOCK="$HOME/.cache/ac_psu_heavy.lock"
KIPY="$R/tools/p2k/bin/kipy"
SK="${ROUTING_SKILL:-$HOME/.claude/skills/kicad-agentic-routing/scripts}"
export KICAD_ENV="$R/tools/p2k/bin/kicad_env.sh" ROUTING_CONFIG="$H/routing.json"
B="$W/cur.kicad_pcb"
T0=$SECONDS
memwait() { while [ "$(free -g | awk '/^Mem:/{print $7}')" -lt 6 ]; do echo "   (waiting for memory)"; sleep 20; done; }
kp() { "$KIPY" "$@" 2>&1 | grep -v -e "^Debug" -e "memory leak" || true; }
run_it() { [ "$((10#$1))" -ge "$((10#$FROM))" ] && [ "$((10#$1))" -le "$((10#$LAST))" ]; }
keep() { cp "$B" "$W/$1.kicad_pcb"; }
check() { "$H/block_E_drc.sh" "$B" "$W/$1.drc.json" | tee "$L/$1.check" | sed 's/^/   /'; }
resume() {
    local f; f=$(ls "$W"/[0-9][0-9]_*.kicad_pcb 2>/dev/null | awk -F/ -v n="$((10#$FROM))" '{s=$NF; if (substr(s,1,2)+0 < n) print}' | sort | tail -1)
    [ -n "$f" ] || { echo "no kept board before step $FROM"; exit 1; }
    cp "$f" "$B"; echo "== resume from $(basename "$f")"
}
rstep() {   # rstep NN name DOMAIN TMO NETS [route.py options]
    local nn="$1" name="$2" d="$3" tmo="$4" nets="$5"; shift 5
    run_it "$nn" || return 0
    echo "== $nn $name (domain $d, $tmo s)"; local t=$SECONDS
    kp "$H/block_E_fence.py" prep "$B" "$W/_in.kicad_pcb" "$d" "$nets" | sed 's/^/   /'
    memwait
    set +e
    flock "$LOCK" timeout "$tmo" python3 -I "$SK/route_step.py" "$W/_in.kicad_pcb" "$W/_out.kicad_pcb" "$nets" "$@" \
        --net-clearances "$H/hv_clearances.json" > "$L/${nn}_$name.log" 2>&1
    local rc=$?; set -e
    grep -E "Routed|routed|FAILED|failed|open" "$L/${nn}_$name.log" | cut -c1-300 | tail -4 | sed 's/^/   /' || true
    if [ "$rc" = 0 ]; then
        kp "$H/block_E_fence.py" finish "$B" "$W/_in.kicad_pcb" "$W/_out.kicad_pcb" "$B" | sed 's/^/   /'
        kp "$H/fence.py" lock "$B" "$B" > /dev/null
    else
        echo "   router failed or timed out ($rc): step skipped (if it died without output, rerun it)"
    fi
    check "${nn}_$name"; keep "${nn}_$name"; echo "   $((SECONDS - t)) s"
}
script() {  # script NN name SCRIPT [args]
    local nn="$1" name="$2" s="$3"; shift 3
    run_it "$nn" || return 0
    echo "== $nn $name"; local t=$SECONDS
    kp "$H/$s" "$B" "$B" "$@" | tee "$L/${nn}_$name.log" | tail -12 | sed 's/^/   /'
    kp "$H/fence.py" lock "$B" "$B" > /dev/null
    check "${nn}_$name"; keep "${nn}_$name"; echo "   $((SECONDS - t)) s"
}

if [ "$FROM" = 00 ]; then
    echo "== 00 clean start"
    git -C "$R" show 6226a75:kicad/ac_psu.kicad_pcb > "$W/base.kicad_pcb"
    kp "$H/block_E.py" --board "$W/base.kicad_pcb" --out "$B" --clean-only | sed 's/^/   /'
    kp "$H/fence.py" lock "$B" "$B" > /dev/null
    check 00_clean; keep 00_clean
else
    resume
fi

S3=(--layers F.Cu In3.Cu B.Cu)
J11TOP="ADASEL0_ISO,ADASEL1_ISO,ADASEL2_ISO,ADCLK_ISO,CLK1_ISO,CS1_ISO,SDATA1_ISO,MDATA_ISO,GPIO_BYPASS_RLY_ISOLATED,PWM_G1_ISO,PWM_G2_ISO,PWM_G3_ISO,PWM_G4_ISO,PWM_TRANS1_ISO,PWM_TRANS2_ISO,PWM_TRANS3_ISO,DAB_PWM_PRI_HI_ISO,DAB_PWM_PRI_LO_ISO"
J11BOT="ADCLK_DAB_CTRL,MDATA_DAB_CTRL,DAB_PWM_HI_SEC_CTRL,DAB_PWM_LO_SEC_CTRL,GPIO_BYPASS_RLY_ISO_CTRL,INU_ADCLK_CTRL,MDATA_INU_CTRL,PWM_Q5_CTRL,PWM_Q6_CTRL,PWM_Q7_CTRL,PWM_Q8_CTRL,PWM_TRANS4_CTRL,PWM_TRANS5_CTRL,PWM_TRANS6_CTRL"
CANA="ISOADA1_CTRL,ISOADA2_CTRL,ISOADA3_CTRL,ISOADA1_OUT,ISOADA2_OUT,ISOADA3_OUT,ISOADA1_M,ISOADA2_M,ISOADA3_M,ISOADA1_PL,ISOADA2_PL,ISOADA3_PL,ISOADA1_N,ISOADA2_N,ISOADA3_N,ISOADA1_P,ISOADA2_P,ISOADA3_P,OPA_SPARE,CTRL_NR,5V_CTRL_A"
BUCK="CTRL_RAW,CTRL_FB,CTRL_EN,CTRL_SW,CTRL_BOOT,CTRL_W"
PLOG="ADA0,ADA1,ADA2,ADA3,ADA4,ADA5,ADA6,ADASEL0,ADASEL1,ADASEL2,CLK1,CS1,Net-(AD1-AINP),Net-(AD1-AVDD),Net-(AD1-SCLK),Net-(AD1-SDO),Net-(AD1-~{CS}),Net-(C100-Pad1),Net-(C96-Pad1),Net-(C98-Pad1),Net-(R27-Pad1),Net-(R27-Pad2),Net-(R28-Pad1),Net-(R28-Pad2),Net-(REF1-VOUT),Net-(U11-X),Net-(U12--),Net-(U14-+),Net-(U14--),Net-(U15-B5),Net-(U1B-+),Net-(U1B--),REF_1V65,SDATA1"
PPORT="PWM_G1,PWM_G2,PWM_TRANS1,PWM_G3,PWM_G4,PWM_TRANS2,DAB_PWM_PRI_HI,DAB_PWM_PRI_LO,PWM_TRANS3,MDATA,ADCLK,GPIO_BYPASS_RLY,Net-(R2-Pad1),Net-(R5-Pad1),Net-(U1A-+),Net-(U1A--)"
ILOG="ADCLK_DAB,DAB_SHUNT1,DAB_SHUNT2,INU_ADCLK_U21,ISOADA1,ISOADA1_AIN,ISOADA2,ISOADA2_AIN,ISOADA3,ISOADA3_AIN,ISO_DAB_SDM_RAW_VOLTAGE,MDATA_DAB,Net-(C102-Pad1),Net-(C104-Pad1),Net-(C106-Pad1),Net-(D17-K),Net-(REF2-VOUT),Net-(U6-MDAT),Net-(U6-VIN+),Net-(U6-VIN-),REF_1V65_ISO"
IPORT="PWM_Q5,PWM_Q6,PWM_TRANS5,GPIO_BYPASS_RLY_ISO,PWM_TRANS6,PWM_Q8,PWM_Q7,MDATA_INU,INU_ADCLK,Net-(U7B--),Net-(U7B-+),Net-(U7A--),Net-(U7A-+),Net-(U2--),Net-(U2-+),DAB_PWM_HI_SEC,DAB_PWM_LO_SEC,PWM_TRANS4"
ISUPP="15V_ISO,5V_ISOL"
CSUP="CTRLGND_A,3V3_CTRL,CTRLGND,5V_CTRL"
PSUP="GND,VCC,5V,15V"
ISUP="ISOGND,3V3_ISO,15V_ISO,5V_ISOL"
PW=(--power-nets $(echo "$CSUP,$PSUP,$ISUP" | tr , ' ') --power-nets-widths 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4)

# --- the J11 fans first (pass 1: plane vias placed before them took the bottom fan's lanes) ---------------------
# J11 west-row escape stubs (pass-1 step 08 script: 0.152 mm stubs between the east-row pads, F.Cu pins 4..22,
# B.Cu pins 24..36)
script 08 j11_stubs 08_j11.py
# J11 bottom fan first (most constrained: its pin order is scrambled against U19 / U21 / U20): all six layers; the
# card planes fence In1 / In2 / In4 except in the J11 column (x 44.4 .. 53.5, y 33 .. 46), where the fan untangles
rstep 09 j11_bot C 1200 "$J11BOT" --layers B.Cu In3.Cu F.Cu In1.Cu In2.Cu In4.Cu --layer-costs 1 1.2 1.5 1.6 1.6 1.6
# (its In1 / In4 pieces inside the card outline are rerouted by steps 44 / 45)
# the analog filters beside J11 pins 1..4 (R128-R130, C129-C131) and the C analog chain before the top fan, whose
# lanes otherwise box them in; then the CTRLGND_A / 3V3_CTRL vias of the parts west of x 56
rstep 10 c_analog C 600 "$CANA" "${S3[@]}" --layer-costs 2 2 1
script 11 planes_j11 block_E_planes.py CTRLGND_A,3V3_CTRL 44,10,56,34
# J11 top fan: the inner-column (even) pins first on In3 / B (vias at the isolator end), then the odd pins on F.Cu
J11TE="ADASEL1_ISO,CLK1_ISO,DAB_PWM_PRI_HI_ISO,GPIO_BYPASS_RLY_ISOLATED,MDATA_ISO,PWM_G1_ISO,PWM_G4_ISO,PWM_TRANS2_ISO,SDATA1_ISO"
rstep 12 j11_top_even C 900 "$J11TE" "${S3[@]}" --layer-costs 6 1 1.5
rstep 13 j11_top C 900 "$J11TOP" "${S3[@]}" --layer-costs 1 2 3 --ordering original
rstep 14 buck C 600 "$BUCK" "${S3[@]}" --layer-costs 1 3 1 --power-nets CTRL_SW CTRL_RAW CTRL_W --power-nets-widths 1.0 1.0 1.0
rstep 15 p_logic P 600 "$PLOG" "${S3[@]}" --layer-costs 1 1.5 1
rstep 16 p_ports P 900 "$PPORT" --layers F.Cu In3.Cu B.Cu In1.Cu In2.Cu In4.Cu --layer-costs 3 1 3 2 1.5 2
rstep 17 i_logic I 600 "$ILOG" "${S3[@]}" --layer-costs 1 1.5 1
# the ISO plane vias of the isolator I-side band (y 38 .. 46) before the ISO ports, which otherwise take its room
script 18 planes_i block_E_planes.py ISOGND,3V3_ISO
rstep 19 i_ports I 900 "$IPORT" "${S3[@]}" --layer-costs 2 1.5 1
# --- planes: a via beside every SMD pad of a plane net in its plane (after the fans) -------------------------------
script 20 planes block_E_planes.py all -200,-200,200,200 3.0
# --- supplies (pads outside the planes, rails), per domain --------------------------------------------------------
SUPC=(--layers F.Cu In3.Cu B.Cu --layer-costs 1 2 1 --quick --max-iterations 1500000)
rstep 21 sup_c C 600 "$CSUP,5V_CTRL_A" "${SUPC[@]}" "${PW[@]}"
rstep 22 sup_p P 300 "VCC,5V,15V" "${SUPC[@]}" "${PW[@]}"
rstep 23 sup_i I 600 "$ISUP" "${SUPC[@]}" "${PW[@]}"
# --- leftovers per domain ------------------------------------------------------------------------------------------
rstep 30 left_c C 900 "$J11TOP,$J11BOT,$CANA,$BUCK,$CSUP" "${S3[@]}" --layer-costs 1 1.5 1 "${PW[@]}"
rstep 31 left_p P 900 "$PLOG,$PPORT,VCC" --layers F.Cu In3.Cu B.Cu In1.Cu In2.Cu In4.Cu --layer-costs 1 1.5 1 2 2 2 "${PW[@]}"
rstep 32 left_i I 900 "$ILOG,$IPORT,$ISUP" "${S3[@]}" --layer-costs 1 1.5 1 "${PW[@]}"

# --- last tries: the In3 sdm reserve shrunk to its part north of E (frees vias in the isolator I-side band), then the
#     remaining nets with every layer the fences allow
script 33 reserve block_E_reserve.py
rstep 34 fix_i I 300 "GPIO_BYPASS_RLY_ISO,INU_ADCLK_U21,DAB_SHUNT2,ISO_DAB_SDM_RAW_VOLTAGE" --layers B.Cu In3.Cu F.Cu --layer-costs 1 1 2
rstep 35 fix_p P 300 "ADA3,CLK1,GPIO_BYPASS_RLY,ADCLK" --layers F.Cu In3.Cu B.Cu In1.Cu In2.Cu In4.Cu --layer-costs 1 1 1 1.5 1.5 1.5
rstep 36 fix_c C 300 "CTRLGND_A" --layers B.Cu In3.Cu F.Cu --layer-costs 1 1 1 "${PW[@]}"

# --- dead kept copper (signal-net pieces that end at no pad) ---------------------------------------------------------
script 40 dead block_E_dead.py "$R/build/v6route/03_prune.kicad_pcb"
# --- the 5V_ISOL F.Cu run that cut the band's ISOPGND pour goes to In3 -----------------------------------------------
script 41 fix block_E_fix.py
rstep 42 fix_5visol I 300 "5V_ISOL" --layers B.Cu In3.Cu --layer-costs 1 1 --power-nets 5V_ISOL --power-nets-widths 0.4
script 43 dead2 block_E_dead.py "$R/build/v6route/03_prune.kicad_pcb"
# --- no In1 / In4 tracks inside the card outline (check_layout rule 6): the two bottom-fan nets that used them again on
#     F / In2 / In3 / B, then vias left without a purpose
script 44 strip block_E_strip.py
rstep 45 fan_fix C 600 "INU_ADCLK_CTRL,PWM_Q6_CTRL" --layers B.Cu In3.Cu F.Cu In2.Cu --layer-costs 1 1.2 1.5 1.6 --ordering original
script 46 dead3 block_E_dead.py "$R/build/v6route/03_prune.kicad_pcb"

if [ "$((10#$LAST))" -ge 90 ]; then
    echo "== 90 copper -> CSV"
    kp "$H/block_E_make.py" copper "$W/00_clean.kicad_pcb" "$B"
    echo "== 91 replay on a fresh 6226a75 board, compared with the chain board"
    git -C "$R" show 6226a75:kicad/ac_psu.kicad_pcb > "$W/fresh.kicad_pcb"
    kp "$H/block_E.py" --board "$W/fresh.kicad_pcb" --out "$W/replay.kicad_pcb" | sed 's/^/   /'
    kp "$H/block_E_same.py" "$W/replay.kicad_pcb" "$B" | sed 's/^/   /'
fi
echo "chain: $((SECONDS - T0)) s"
