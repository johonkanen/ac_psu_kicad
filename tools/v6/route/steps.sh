# v6 pass 1 chain steps 06.. (sourced by chain.sh; the functions script / rstep are defined there)
#   rstep NN name DOMAIN TIMEOUT_S NET_CLEARANCES NETS [route.py options]
HV=hv_clearances.json; SENSE=sense_clearances.json
ALL=(--layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu)
SIG3=(--layers F.Cu In3.Cu B.Cu)

# --- drawn structures, continued -------------------------------------------------------------------------------
#     the ISO nets leaving westwards past J37 / J38 (path A: pinch beside J37; path B, the via column, is step 05)
script 06 west 06_west.py
#     a via next to every SMD pad of a plane net inside its plane; the J11 west-row escape stubs
script 07 planes 07_planes.py
script 08 j11 08_j11.py

# --- rule 3, part 1: the current-sense groups (side-1 HV nets among themselves at 0.15 mm, 2.5 mm to everything
#     else: sense_clearances.json gives every low-voltage net 2.5 mm), the shunt force paths 2 mm wide --------------
rstep 10 sense_p P 600 $SENSE "SHUNT1,Net-(U5-VIN+),Net-(U5-VIN-),SDM_RAW_VOLTAGE,Net-(D8-K),AFE_CHOKE1,/01 afe/LEMOUT" \
    --layers B.Cu F.Cu In3.Cu --layer-costs 1 1.5 3 --power-nets AFE_CHOKE1 "/01 afe/LEMOUT" --power-nets-widths 2.0 2.0
rstep 11 sense_i I 600 $SENSE "INU_SHUNT1,INU_SHUNT2,Net-(U4-VIN+),Net-(U4-VIN-),ISO_AFE_SDM_RAW_VOLTAGE,Net-(D9-K),INU_CHOKE,/05 VSI/INDUCTOR_OUTPUT" \
    --layers B.Cu F.Cu In3.Cu --layer-costs 1 1.5 3 --power-nets INU_CHOKE "/05 VSI/INDUCTOR_OUTPUT" --power-nets-widths 2.0 2.0
rstep 12 sense_lv_p P 300 $HV "Net-(U5-MDAT)" "${SIG3[@]}"
rstep 13 sense_lv_i I 300 $HV "Net-(U4-MDAT),Net-(D17-K),ISO_DAB_SDM_RAW_VOLTAGE" "${SIG3[@]}"

# --- rule 3, part 1: supplies and grounds (headers, header capacitors, U29 / U30, the sense groups), one net per
#     step with its own time budget; 15V / 5V rails 0.4 mm ---------------------------------------------------------
PW=(--power-nets ISOGND 3V3_ISO 15V_ISO 5V_ISOL GND VCC 5V 15V CTRLGND_A 3V3_CTRL CTRLGND 5V_CTRL 5V_CTRL_A
    --power-nets-widths 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4 0.4)
SUPC=(--layers F.Cu In3.Cu B.Cu In1.Cu In2.Cu In4.Cu --layer-costs 1 2 1 3 3 3)
n=14
for net in ISOGND 3V3_ISO 15V_ISO 5V_ISOL; do rstep $n "sup_$net" I 600 $HV "$net" "${SUPC[@]}" "${PW[@]}"; n=$((n + 1)); done
for net in GND VCC 5V 15V; do rstep $n "sup_$net" P 600 $HV "$net" "${SUPC[@]}" "${PW[@]}"; n=$((n + 1)); done
rstep 22 sup_ctrl C 600 $HV "CTRLGND_A,3V3_CTRL,CTRLGND,5V_CTRL,5V_CTRL_A" "${SUPC[@]}" "${PW[@]}"

# --- rule 3, part 3: card PWM per card group (rule 3: after the drawn sigma-delta pairs) ----------------------------
rstep 23 pwm_p P 600 $HV "PWM_G1,PWM_G2,PWM_TRANS1,PWM_G3,PWM_G4,PWM_TRANS2,DAB_PWM_PRI_HI,DAB_PWM_PRI_LO,PWM_TRANS3" \
    "${ALL[@]}" --layer-costs 2 1.5 1.5 1 1.5 2
rstep 24 pwm_i I 600 $HV "PWM_Q5,PWM_Q6,PWM_TRANS5,DAB_PWM_HI_SEC,DAB_PWM_LO_SEC,PWM_TRANS4,PWM_Q7,PWM_Q8,PWM_TRANS6,GPIO_BYPASS_RLY_ISO" \
    "${ALL[@]}" --layer-costs 2 2 2 1 2 1.5

# --- rule 3, part 4: the card area under the control card -----------------------------------------------------------
J11TOP="ADASEL0_ISO,ADASEL1_ISO,ADASEL2_ISO,ADCLK_ISO,CLK1_ISO,CS1_ISO,SDATA1_ISO,MDATA_ISO,GPIO_BYPASS_RLY_ISOLATED,PWM_G1_ISO,PWM_G2_ISO,PWM_G3_ISO,PWM_G4_ISO,PWM_TRANS1_ISO,PWM_TRANS2_ISO,PWM_TRANS3_ISO,DAB_PWM_PRI_HI_ISO,DAB_PWM_PRI_LO_ISO"
J11BOT="ADCLK_DAB_CTRL,MDATA_DAB_CTRL,DAB_PWM_HI_SEC_CTRL,DAB_PWM_LO_SEC_CTRL,GPIO_BYPASS_RLY_ISO_CTRL,INU_ADCLK_CTRL,MDATA_INU_CTRL,PWM_Q5_CTRL,PWM_Q6_CTRL,PWM_Q7_CTRL,PWM_Q8_CTRL,PWM_TRANS4_CTRL,PWM_TRANS5_CTRL,PWM_TRANS6_CTRL"
ANALOG="ISOADA1_CTRL,ISOADA2_CTRL,ISOADA3_CTRL,ISOADA1_OUT,ISOADA2_OUT,ISOADA3_OUT,ISOADA1_M,ISOADA2_M,ISOADA3_M,ISOADA1_PL,ISOADA2_PL,ISOADA3_PL,ISOADA1_N,ISOADA2_N,ISOADA3_N,ISOADA1_P,ISOADA2_P,ISOADA3_P,OPA_SPARE,CTRL_NR"
BUCK="CTRL_RAW,CTRL_FB,CTRL_EN,CTRL_SW,CTRL_BOOT,CTRL_W"
LOGP="REF_1V65,ADASEL0,ADASEL1,ADASEL2,CLK1,CS1,SDATA1,ADA3,Net-(U11-X),Net-(U15-B5),GPIO_BYPASS_RLY"
LOGI="REF_1V65_ISO,ISOADA1,ISOADA2,ISOADA3,ISOADA1_AIN,ISOADA2_AIN,ISOADA3_AIN,MDATA_DAB,ADCLK_DAB,DAB_SHUNT2,SHUNT2"
rstep 25 j11_top C 600 $HV "$J11TOP" --layers F.Cu In3.Cu B.Cu --layer-costs 1 2 3 --ordering original
rstep 26 j11_bot C 600 $HV "$J11BOT" --layers B.Cu In3.Cu F.Cu --layer-costs 1 1.2 1.5
rstep 27 ctrl_analog C 600 $HV "$ANALOG" "${SIG3[@]}" --layer-costs 2 2 1
rstep 28 buck C 600 $HV "$BUCK" "${SIG3[@]}" --layer-costs 1 3 1 --power-nets CTRL_SW CTRL_RAW CTRL_W --power-nets-widths 1.0 1.0 1.0
rstep 29 logic_p P 600 $HV "$LOGP" "${SIG3[@]}" --layer-costs 1 1.5 1
rstep 30 logic_i I 600 $HV "$LOGI" "${SIG3[@]}" --layer-costs 1 1.5 1

# --- leftovers, all layers allowed (planes fenced), per domain -------------------------------------------------------
rstep 31 left_c C 600 $HV "$J11TOP,$J11BOT,$ANALOG,$BUCK,CTRLGND_A,3V3_CTRL,CTRLGND,5V_CTRL,5V_CTRL_A" "${ALL[@]}" --layer-costs 1 2 2 1.2 2 1 "${PW[@]}"
rstep 32 left_p P 600 $HV "$LOGP,PWM_G1,PWM_G2,PWM_TRANS1,PWM_G3,PWM_G4,PWM_TRANS2,DAB_PWM_PRI_HI,DAB_PWM_PRI_LO,PWM_TRANS3,GND,VCC,5V,15V" "${ALL[@]}" --layer-costs 1 2 2 1.2 2 1 "${PW[@]}"
rstep 33 left_i I 600 $HV "$LOGI,PWM_Q5,PWM_Q6,PWM_TRANS5,DAB_PWM_HI_SEC,DAB_PWM_LO_SEC,PWM_TRANS4,ISOGND,3V3_ISO,15V_ISO,5V_ISOL" "${ALL[@]}" --layer-costs 1 2 2 1.2 2 1 "${PW[@]}"
