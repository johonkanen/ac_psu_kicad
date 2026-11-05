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
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deviations  # noqa: E402  (v5 pending-layout areas)

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
    # v5: unrouted items of the v5 change wait for the GUI layout (lib/v5_copper.csv pending areas)
    v5refs = deviations.v5_parts()
    moved = {(r["ref"], r["pin"]) for r in deviations.rows() if r["kind"] == "pin" and r.get("fix") == "v5"}
    cut = deviations.v5_cut_nets()

    def v5_item(i):
        m = re.search(r"Pad (\S+) \[([^\]]*)\] of (\S+)", i["description"])
        if m and (m.group(3) in v5refs or (m.group(3), m.group(1)) in moved or m.group(2) in cut):
            return True
        m = re.search(r"\[([^\]]*)\]", i["description"])
        if m and m.group(1) in cut:
            return True
        m = re.match(r"Zone '([^']*)' \[([^\]]*)\]", i["description"])
        if m and zone_touches_pending(m.group(1), m.group(2)):
            return True   # a pour split by the v5 domain rules where it reaches into a pending area
        return deviations.in_pending(i["pos"]["x"], -i["pos"]["y"])
    zones = None

    def zone_touches_pending(name, net):
        nonlocal zones
        if zones is None:
            sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
            from p2k import sexpr
            zones = []
            for z in sexpr.walk(sexpr.load(BOARD), "zone"):
                nm, zn = sexpr.find(z, "name"), sexpr.find(z, "net")
                for poly in sexpr.find_all(z, "polygon"):
                    pts = [(float(q[1]), -float(q[2])) for q in sexpr.find(poly, "pts")[1:] if q[0] == "xy"]
                    if pts:
                        zones.append((str(nm[1]) if nm else "", str(zn[1]) if zn else "",
                                      min(x for x, _ in pts), min(y for _, y in pts),
                                      max(x for x, _ in pts), max(y for _, y in pts)))
        return any(zn == name and znet == net and x0 <= a[2] and a[0] <= x1 and y0 <= a[3] and a[1] <= y1
                   for zn, znet, x0, y0, x1, y1 in zones for a in deviations.pending_areas())
    pending = [u for u in unconnected if any(v5_item(i) for i in u["items"])]
    unconnected = [u for u in unconnected if not any(v5_item(i) for i in u["items"])]
    parity = d.get("schematic_parity", [])
    # v5: clearance violations of the v5 change (CTRL domain rules on the v4 layout, staged parts)
    pend_viol = [v for v in viol if v["type"] == "clearance" and any(v5_item(i) for i in v["items"])]
    viol = [v for v in viol if v not in pend_viol]
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
          f"{len(parity)} parity issues (reports/drc.json)"
          + (f"; {len(pending)} unconnected v5 items and {len(pend_viol)} v5 clearance violations pending GUI layout"
             if pending or pend_viol else ""))
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
