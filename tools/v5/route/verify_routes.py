#!/usr/bin/env python3
"""Rule check of the route files themselves (stdlib only), independent of the router's grid:

  python3 tools/v5/route/verify_routes.py ROUTES.json [ROUTES.json ...]

  * every new track (full width) and via lies inside the `unrouted` rectangles of lib/v5_copper.csv;
  * no track on In1.Cu / In4.Cu, none on In2.Cu;
  * no via and no F.Cu / B.Cu track in the DC bus band, nothing on F.Cu / B.Cu / In4.Cu and no via in the corridor
    north of J11 (x 40..56, y 51.1..55).
Prints the counts per layer and the vias; exit 1 on a violation.
"""
import collections
import json
import sys

RECTS = [(22.0, -22.0, 118.65, 54.0), (85.0, -40.0, 118.65, -22.0), (0.0, 36.0, 22.0, 54.0)]
BAND = (52.3, 43.2, 118.1, 48.8)
NORTH = (40.0, 51.1, 56.0, 55.0)


def inside(x, y, m=0.0):
    return any(x0 + m <= x <= x1 - m and y0 + m <= y <= y1 - m for x0, y0, x1, y1 in RECTS) or \
        (22.0 - 1e-6 <= x + m and x - m <= 22.0 + 1e-6 and 36.0 + m <= y <= 54.0 - m)      # the seam of two rectangles


def seg_hits(a, b, rect, m):
    x0, y0, x1, y1 = rect[0] - m, rect[1] - m, rect[2] + m, rect[3] + m
    n = max(2, int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 0.02))
    return any(x0 < a[0] + (b[0] - a[0]) * k / n < x1 and y0 < a[1] + (b[1] - a[1]) * k / n < y1 for k in range(n + 1))


def main():
    bad, per, length, nv = [], collections.Counter(), collections.Counter(), 0
    for path in sys.argv[1:]:
        with open(path) as f:
            r = json.load(f)
        for t in r["tracks"]:
            per[t["layer"]] += 1
            length[t["layer"]] += ((t["a"][0] - t["b"][0]) ** 2 + (t["a"][1] - t["b"][1]) ** 2) ** 0.5
            h = t["w"] / 2
            for p in (t["a"], t["b"]):
                if not inside(p[0], p[1], h - 1e-6):
                    bad.append(f"{path}: track {t['net']} {t['layer']} w {t['w']} at {p}: outside the unrouted rectangles")
            if t["layer"] in ("In1.Cu", "In2.Cu", "In4.Cu"):
                bad.append(f"{path}: track {t['net']} on {t['layer']}")
            if t["layer"] in ("F.Cu", "B.Cu") and seg_hits(t["a"], t["b"], BAND, h):
                bad.append(f"{path}: track {t['net']} {t['layer']} {t['a']} - {t['b']} in the DC bus band")
            if t["layer"] in ("F.Cu", "B.Cu", "In4.Cu") and seg_hits(t["a"], t["b"], NORTH, h):
                bad.append(f"{path}: track {t['net']} {t['layer']} in the corridor north of J11")
        for v in r["vias"]:
            nv += 1
            rr = v["d"] / 2
            if not inside(v["x"], v["y"], rr - 1e-6):
                bad.append(f"{path}: via {v['net']} at ({v['x']}, {v['y']}): outside the unrouted rectangles")
            for rect, what in ((BAND, "DC bus band"), (NORTH, "corridor north of J11")):
                if rect[0] - rr < v["x"] < rect[2] + rr and rect[1] - rr < v["y"] < rect[3] + rr:
                    bad.append(f"{path}: via {v['net']} at ({v['x']}, {v['y']}) in the {what}")
    print("verify_routes: " + ", ".join(f"{k} {per[k]} segments / {length[k]:.0f} mm" for k in sorted(per)) + f"; {nv} vias")
    for b in bad[:40]:
        print("verify_routes: ERROR " + b)
    print(f"verify_routes: {len(bad)} violations: " + ("FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
