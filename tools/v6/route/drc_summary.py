#!/usr/bin/env python3
"""One-line DRC summary of a kicad-cli JSON report (stdlib): errors that matter for routing, unconnected, parity.

  python3 drc_summary.py DRC.json [--list]
"""
import collections
import json
import sys

COPPER = {"clearance", "shorting_items", "tracks_crossing", "hole_clearance", "copper_edge_clearance",
          "hole_to_hole", "via_diameter", "track_width", "annular_width", "drill_out_of_range", "items_not_allowed",
          "zones_intersect", "starved_thermal", "padstack", "isolated_copper"}
d = json.load(open(sys.argv[1]))
c = collections.Counter(v["type"] for v in d["violations"] if v.get("severity") == "error")
cop = {k: n for k, n in c.items() if k in COPPER}
dang = sum(1 for v in d["violations"] if v["type"] in ("track_dangling", "via_dangling"))
print(f"drc: {sum(c.values())} errors ({', '.join(f'{k} {n}' for k, n in sorted(c.items())) or '-'}); copper errors "
      f"{sum(cop.values())}; dangling {dang}; unconnected {len(d['unconnected_items'])}; parity {len(d.get('schematic_parity', []))}")
if "--list" in sys.argv:
    for v in d["violations"]:
        if v["type"] in COPPER and v.get("severity") == "error":
            print("  ", v["type"], v["description"][:70], " | ".join(
                f"{i['description'][:50]} @({i['pos']['x']:.2f},{-i['pos']['y']:.2f})" for i in v["items"]))
