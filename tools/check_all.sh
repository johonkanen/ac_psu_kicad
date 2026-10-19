#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
set -u
cd "$(dirname "$0")/.."
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }

step "KiCad environment" tools/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" python3 tools/ipc356.py --check
step "Symbol library up to date" python3 tools/gen_symbols.py --check
step "Symbol pin sets vs IPC" python3 tools/check_symbols.py
step "ERC" tools/erc.sh
step "Netlist comparison vs IPC" python3 tools/compare_netlists.py
step "Footprint library and map up to date" python3 tools/gen_footprints.py --check
step "Footprints vs IPC pad geometry" tools/bin/kipy tools/check_footprints.py --pcbnew
step "Board pads, holes, vias vs IPC" tools/bin/kipy tools/check_board.py
step "Board copper connectivity after zone fill" tools/bin/kipy tools/assign_nets.py --check
step "DRC with schematic parity" python3 tools/drc.py
step "IPC-D-356 from the board vs Proteus" python3 tools/ipc356_diff.py
step "Gerber round trip vs Proteus (copper, drills)" python3 tools/gerber_roundtrip.py --check

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
