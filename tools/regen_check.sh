#!/usr/bin/env bash
# Regression check for the shared proteus2kicad tools: clone this repo (with submodules) into a
# temporary directory, regenerate every generated file there, and fail if anything differs
# from the commit. Run after bumping tools/p2k (commit the bump first, or pass a ref).
#   tools/regen_check.sh [REF]      (default: HEAD)
# make_skeleton is one-shot with random UUIDs: it is only run, not compared.
set -u
src="$(cd "$(dirname "$0")/.." && pwd)"
ref="${1:-HEAD}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git clone -q "$src" "$tmp/c" && cd "$tmp/c" && git checkout -q "$(git -C "$src" rev-parse "$ref")" \
    && git submodule -q update --init || { echo "regen_check: clone failed"; exit 1; }
# a local submodule commit not yet pushed: take it from the source checkout
git -C tools/p2k cat-file -e "$(git -C "$src" rev-parse "$ref:tools/p2k")" 2>/dev/null \
    || git -C tools/p2k fetch -q "$src/tools/p2k" && git submodule -q update
fail=0
run() { "$@" >/dev/null 2>&1 || { echo "regen_check: FAILED: $*"; fail=1; }; }
(cp -r . "$tmp/skel" && cd "$tmp/skel" && tools/p2k/bin/p2k make_skeleton --force >/dev/null) \
    || { echo "regen_check: FAILED: make_skeleton"; fail=1; }
run tools/p2k/bin/p2k ipc356
run python3 tools/gen_symbols.py
for s in tools/sheets/sheet[0-9]*.py; do run python3 "$s"; done
run python3 tools/gen_footprints.py
run tools/make_pcb.sh
run tools/p2k/bin/kipy tools/assign_nets.py --check
changed="$(git status --short)"
if [ -n "$changed" ]; then echo "regen_check: regenerated files differ:"; echo "$changed"; fail=1; fi
[ $fail -eq 0 ] && echo "regen_check: OK (every generated file byte-identical)"
exit $fail
