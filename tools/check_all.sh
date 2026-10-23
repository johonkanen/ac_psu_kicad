#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
# Since v4 the Proteus comparisons apply exactly the deviations in lib/v4_deviations.csv and
# lib/v4_copper.csv (tools/deviations.py); anything else is still a failure.
set -u
cd "$(dirname "$0")/.."
[ -x tools/p2k/bin/p2k ] || { echo "tools/p2k missing: git submodule update --init"; exit 1; }
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }

step "KiCad environment" tools/p2k/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" tools/p2k/bin/p2k ipc356 --check
step "Gerber X2 export vs IPC (pads, vias, drills, outline)" tools/p2k/bin/p2k check_sources
step "Symbol library up to date" python3 tools/gen_symbols.py --check
step "Symbol pin sets vs IPC (+ v4 deviations)" python3 tools/check_symbols_v4.py
step "ERC" tools/erc.sh
step "Netlist comparison vs IPC (+ v4 deviations)" python3 tools/compare_netlists_v4.py
step "Footprint library and map up to date" python3 tools/gen_footprints.py --check
step "Footprints vs IPC pad geometry" tools/p2k/bin/kipy tools/check_footprints.py --pcbnew
step "Board pads, holes, vias vs IPC (+ v4 deviations)" tools/p2k/bin/kipy tools/check_board.py
step "Board copper connectivity after zone fill" tools/p2k/bin/kipy tools/assign_nets.py --check
step "DRC with schematic parity" python3 tools/drc.py
step "IPC-D-356 from the board vs Proteus (+ v4 deviations)" python3 tools/ipc356_diff.py
step "Gerber round trip vs Proteus (copper, drills; v4 areas)" python3 tools/gerber_roundtrip.py --check

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
