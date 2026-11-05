#!/usr/bin/env bash
# The v4 board edits in order (documentation of how kicad/ac_psu.kicad_pcb was made from the
# frozen Proteus board at tag proteus-conversion-complete). Each script refuses to run twice.
#   git show proteus-conversion-complete:kicad/ac_psu.kicad_pcb > kicad/ac_psu.kicad_pcb
#   tools/v4/apply_all.sh
# Fixes 1-15 ran before the domain net classes and DRC rules existed (tools/v4/domain_rules.py,
# fix 16); their zone fills depend on them, so they run with the project file of that time.
set -eu
cd "$(dirname "$0")/../.."
PRE16=8c4b5ac  # last commit before fix 16
cp kicad/ac_psu.kicad_pro kicad/ac_psu.kicad_pro.keep
[ -f kicad/ac_psu.kicad_dru ] && mv kicad/ac_psu.kicad_dru kicad/ac_psu.kicad_dru.keep
restore() {
    mv kicad/ac_psu.kicad_pro.keep kicad/ac_psu.kicad_pro
    [ -f kicad/ac_psu.kicad_dru.keep ] && mv kicad/ac_psu.kicad_dru.keep kicad/ac_psu.kicad_dru || true
}
trap restore EXIT
git show "$PRE16:kicad/ac_psu.kicad_pro" > kicad/ac_psu.kicad_pro
for f in fix_1_ret_iso fix_2_u11_inh fix_3_ada_caps fix_4_sdm_rc fix_5_r48_kelvin fix_6_u8u9_body fix_7_c67_ceramic fix_8_silk_refdes fix_9_ref_divider fix_10_u8_k7805 fix_11_meas_filters fix_12_silk_new_refs fix_13_m4_terminals fix_14_insulation_gaps fix_15_cable_ties; do
    tools/p2k/bin/kipy "tools/v4/$f.py"
done
restore
trap - EXIT
for f in fix_16_pour_holes; do
    tools/p2k/bin/kipy "tools/v4/$f.py"
done
