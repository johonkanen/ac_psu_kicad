#!/usr/bin/env python3
"""DRC of a board copy while routing (stdlib only): kicad-cli with zones refilled, a count per type, every
error that is not a courtyard overlap, and the open connections per net.

  python3 tools/v5/route/quick_drc.py BOARD.kicad_pcb [-v] [--nets REGEX]

The board copy needs ac_psu.kicad_pro and ac_psu.kicad_dru next to it under the name of the copy (run.sh
copies them). The final verdict is tools/check_all.sh on kicad/ac_psu.kicad_pcb; this is the fast loop.
"""
import collections
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    board = sys.argv[1]
    rep = board + ".drc.json"
    cli = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
    r = subprocess.run([cli, "pcb", "drc", "--severity-all", "--format", "json", "-o", rep, board], capture_output=True, text=True)
    if not os.path.exists(rep):
        sys.exit(r.stdout + r.stderr)
    with open(rep) as f:
        d = json.load(f)
    by = collections.Counter((v["type"], v["severity"]) for v in d["violations"])
    for (t, s), n in sorted(by.items(), key=lambda kv: (kv[0][1], -kv[1])):
        print(f"quick_drc: {n:4d} {s:8s} {t}")
    skip = {"courtyards_overlap", "pth_inside_courtyard"}
    for v in d["violations"]:
        if v["severity"] == "error" and v["type"] not in skip or v["type"] in ("track_dangling", "via_dangling") and "-v" in sys.argv:
            p = v["items"][0]["pos"]
            if p["y"] > 84 and v["type"] == "clearance":
                continue        # staging area
            print(f"quick_drc: {v['type']} ({p['x']:.2f}, {-p['y']:.2f}) {v['description']}: " + " / ".join(i["description"] for i in v["items"]))
    un = collections.Counter()
    for u in d.get("unconnected_items", []):
        m = re.search(r"\[([^\]]*)\]", u["items"][0]["description"])
        un[m.group(1) if m else "?"] += 1
    pat = sys.argv[sys.argv.index("--nets") + 1] if "--nets" in sys.argv else None
    print(f"quick_drc: {sum(un.values())} unconnected on {len(un)} nets")
    if pat or "-v" in sys.argv:
        for n, c in sorted(un.items()):
            if not pat or re.search(pat, n):
                print(f"quick_drc:   {c} {n}")


if __name__ == "__main__":
    main()
