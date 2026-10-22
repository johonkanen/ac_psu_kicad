#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
set -u
cd "$(dirname "$0")/.."
[ -x tools/p2k/bin/p2k ] || { echo "tools/p2k missing: git submodule update --init"; exit 1; }
fail=0
step() { echo "== $1"; shift; "$@" || { echo "!! FAILED: $*"; fail=1; }; }

step "KiCad environment" tools/p2k/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" tools/p2k/bin/p2k ipc356 --check
step "Gerber X2 export vs IPC (pads, vias, drills, outline)" tools/p2k/bin/p2k check_sources
step "Symbol library up to date" python3 tools/gen_symbols.py --check
step "Symbol pin sets vs IPC" tools/p2k/bin/p2k check_symbols
step "ERC" tools/erc.sh
step "Netlist comparison vs IPC" tools/p2k/bin/p2k compare_netlists
step "Footprint library and map up to date" python3 tools/gen_footprints.py --check
step "Footprints vs IPC pad geometry" tools/p2k/bin/kipy tools/check_footprints.py --pcbnew
step "Board pads, holes, vias vs IPC" tools/p2k/bin/kipy tools/check_board.py
step "Board copper connectivity after zone fill" tools/p2k/bin/kipy tools/assign_nets.py --check
step "DRC with schematic parity" python3 tools/drc.py
step "IPC-D-356 from the board vs Proteus" python3 tools/ipc356_diff.py
step "Gerber round trip vs Proteus (copper, drills)" python3 tools/gerber_roundtrip.py --check

echo
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
