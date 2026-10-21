#!/usr/bin/env bash
# ERC of the project schematic; fails on ERC errors (warnings are listed only).
# Full report: reports/erc.rpt
set -u
cd "$(dirname "$0")/.."
mkdir -p reports
tools/p2k/bin/kicad-cli sch erc --severity-all -o reports/erc.rpt kicad/ac_psu.kicad_sch >/dev/null || exit 1
errs=$(grep -c '; error' reports/erc.rpt)
warns=$(grep -c '; warning' reports/erc.rpt)
echo "erc: $errs errors, $warns warnings (reports/erc.rpt)"
[ "$errs" -eq 0 ]
