#!/usr/bin/env python3
"""Rows for lib/v6_copper.csv from block A's replay data (stdlib): what the integration needs for check_board /
ipc356_diff / gerber_roundtrip.

  python3 block_A_rows.py [OUT.csv]      default reports/v6/blocks/block_A_copper_rows.csv

Format of lib/v6_copper.csv: kind,layer,x,y,x1,y1,net,note (IPC frame, mm; x,y / x1,y1 = the corners).
  - unrouted,*  one row per straight leg of new copper (collinear joined pieces merged, L shapes split into legs),
                tight to the copper (half the width + 0.1 mm); one per new via; one per new copper zone (its outline)
  - area,<layer> one row per deleted piece of kept copper (dead track, or the part a shortened track lost), and
                one per fill keep-out (the HV pours lose their copper inside it)
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(HERE, "block_A_copper.csv")
TAG = "block A replay (V6_PLAN section 16, tools/v6/route/block_A.py)"


def f2(v):
    return f"{v:.2f}"


def box(pts, m):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m


def legs(tracks):
    """join collinear pieces of one net / layer / width that meet end to end"""
    out = []
    pool = [((float(r["x1"]), float(r["y1"])), (float(r["x2"]), float(r["y2"])), r) for r in tracks]
    used = [False] * len(pool)

    def ang(a, c):
        return math.atan2(c[1] - a[1], c[0] - a[0]) % math.pi
    for i, (a, c, r) in enumerate(pool):
        if used[i]:
            continue
        used[i] = True
        seg = [a, c]
        grown = True
        while grown:
            grown = False
            for j, (a2, c2, r2) in enumerate(pool):
                if used[j] or (r2["net"], r2["layer"], r2["w"]) != (r["net"], r["layer"], r["w"]):
                    continue
                if abs(ang(a2, c2) - ang(seg[0], seg[-1])) > 1e-3 and abs(abs(ang(a2, c2) - ang(seg[0], seg[-1])) - math.pi) > 1e-3:
                    continue
                for p, q in ((a2, c2), (c2, a2)):
                    if math.dist(p, seg[-1]) < 1e-3:
                        seg[-1] = q
                    elif math.dist(q, seg[0]) < 1e-3:
                        seg[0] = p
                    else:
                        continue
                    used[j] = grown = True
                    break
        out.append((r, seg))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reports", "v6", "blocks",
                                                             "block_A_copper_rows.csv")
    rows = list(csv.DictReader(open(SRC)))
    res = []
    for r, seg in legs([r for r in rows if r["kind"] == "track"]):
        x0, y0, x1, y1 = box(seg, float(r["w"]) / 2 + 0.1)
        res.append(("unrouted", "*", x0, y0, x1, y1, "", f"{TAG}: new {r['net'].split('/')[-1]} copper on {r['layer']}"))
    for r in rows:
        k = r["kind"]
        if k == "via":
            p = (float(r["x1"]), float(r["y1"]))
            x0, y0, x1, y1 = box([p], float(r["w"]) / 2 + 0.1)
            res.append(("unrouted", "*", x0, y0, x1, y1, "", f"{TAG}: new {r['net'].split('/')[-1]} via"))
        elif k == "zone":
            pts = [tuple(float(v) for v in q.split()) for q in r["tag"].split("|")[1].split(";")]
            x0, y0, x1, y1 = box(pts, 0.0)
            res.append(("unrouted", "*", x0, y0, x1, y1, "", f"{TAG}: new copper zone {r['tag'].split('|')[0]}"))
        elif k == "deadtrack":
            pts = [(float(r["x1"]), float(r["y1"])), (float(r["x2"]), float(r["y2"]))]
            x0, y0, x1, y1 = box(pts, 0.5)
            res.append(("area", r["layer"], x0, y0, x1, y1, "",
                        f"{TAG}: kept {r['net'].split('/')[-1]} track deleted (dead or under the HV rule)"))
        elif k == "cuttrack":
            o = [float(v) for v in r["tag"].split()]
            old, new = [(o[0], o[1]), (o[2], o[3])], [(float(r["x1"]), float(r["y1"])), (float(r["x2"]), float(r["y2"]))]
            lost = [p for p in old if min(math.dist(p, q) for q in new) > 1e-3]
            kept = [q for q in new if min(math.dist(q, p) for p in old) > 1e-3]
            x0, y0, x1, y1 = box(lost + kept, 0.5)
            res.append(("area", r["layer"], x0, y0, x1, y1, "",
                        f"{TAG}: kept {r['net'].split('/')[-1]} run shortened, its west part drawn again"))
        elif k == "keepout":
            pts = [tuple(float(v) for v in q.split()) for q in r["tag"].split("|")[1].split(";")]
            x0, y0, x1, y1 = box(pts, 0.0)
            res.append(("area", r["layer"], x0, y0, x1, y1, "",
                        f"{TAG}: {r['tag'].split('|')[0]}: high-voltage pour cut back from other nets' copper"))
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "layer", "x", "y", "x1", "y1", "net", "note"])
        for k, L, x0, y0, x1, y1, n, note in res:
            w.writerow([k, L, f2(x0), f2(y0), f2(x1), f2(y1), n, note])
    print(f"block_A_rows: {sum(1 for r in res if r[0] == 'unrouted')} unrouted rows, "
          f"{sum(1 for r in res if r[0] == 'area')} area rows -> {out}")


if __name__ == "__main__":
    main()
