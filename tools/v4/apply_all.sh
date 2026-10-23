#!/usr/bin/env bash
# The v4 board edits in order (documentation of how kicad/ac_psu.kicad_pcb was made from the
# frozen Proteus board at tag proteus-conversion-complete). Each script refuses to run twice.
#   git show proteus-conversion-complete:kicad/ac_psu.kicad_pcb > kicad/ac_psu.kicad_pcb
#   tools/v4/apply_all.sh
set -eu
cd "$(dirname "$0")/../.."
for f in fix_1_ret_iso fix_2_u11_inh fix_3_ada_caps fix_4_sdm_rc fix_5_r48_kelvin fix_6_u8u9_body; do
    tools/p2k/bin/kipy "tools/v4/$f.py"
done
