#!/usr/bin/env python3
"""DRC of kicad/ac_psu.kicad_pcb via kicad-cli, with schematic parity (stdlib only).

Writes reports/drc.json (full kicad-cli report) and prints a count per violation type.
Fails on: any short (shorting_items), any unconnected item, any schematic parity issue, and
any other error-severity violation whose type is not in ACCEPTED below (each accepted type
is justified there and in STATUS.md). Warnings are only counted.

Usage: python3 tools/drc.py [-v]
"""
import json
import os
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
REPORT = os.path.join(ROOT, "reports", "drc.json")

# Error-severity DRC types that remain by design (the Proteus layout as it is):
ACCEPTED = {
    # KiCad library courtyards are larger than the Proteus placement spacing (parts sit
    # where Proteus put them; the Proteus silk outlines do not overlap).
    "courtyards_overlap": "KiCad courtyards vs the Proteus placement",
    "pth_inside_courtyard": "KiCad courtyards vs the Proteus placement",
}


def main():
    cli = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    r = subprocess.run([cli, "pcb", "drc", "--schematic-parity", "--severity-all", "--format", "json",
                        "-o", REPORT, BOARD], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(REPORT):
        sys.exit(f"drc: kicad-cli failed:\n{r.stdout}{r.stderr}")
    with open(REPORT) as f:
        d = json.load(f)
    viol = d["violations"]
    unconnected = d.get("unconnected_items", [])
    parity = d.get("schematic_parity", [])
    by_type = Counter((v["type"], v["severity"]) for v in viol)
    errors = []
    shorts = by_type.get(("shorting_items", "error"), 0)
    if shorts:
        errors.append(f"{shorts} shorts")
    if unconnected:
        errors.append(f"{len(unconnected)} unconnected items")
    if parity:
        errors.append(f"{len(parity)} schematic parity issues")
    for (t, sev), n in sorted(by_type.items()):
        if sev == "error" and t != "shorting_items" and t not in ACCEPTED:
            errors.append(f"{n} {t}")
    print(f"drc: {len(viol)} violations, {shorts} shorts, {len(unconnected)} unconnected, "
          f"{len(parity)} parity issues (reports/drc.json)")
    for (t, sev), n in sorted(by_type.items(), key=lambda kv: (kv[0][1], -kv[1])):
        note = f"  accepted: {ACCEPTED[t]}" if sev == "error" and t in ACCEPTED else ""
        print(f"drc:   {n:4d} {sev:8s} {t}{note}")
    if "-v" in sys.argv or errors:
        for v in viol:
            if v["severity"] == "error" and v["type"] not in ACCEPTED:
                items = " / ".join(i["description"] for i in v["items"])
                print(f"drc: {v['type']}: {v['description']}: {items}")
        for u in unconnected[:20]:
            print("drc: unconnected: " + " / ".join(i["description"] for i in u["items"]))
        for p in parity[:20]:
            print(f"drc: parity: {p['description']}: " + " / ".join(i["description"] for i in p["items"]))
    for e in errors:
        print("drc: ERROR " + e)
    print("drc: " + ("FAILED" if errors else "OK"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
