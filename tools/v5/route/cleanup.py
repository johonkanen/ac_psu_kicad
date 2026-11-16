#!/usr/bin/env python3
"""Dangling stubs of the routing out, with DRC as the judge (stdlib only).

  python3 tools/v5/route/cleanup.py BOARD.kicad_pcb DROP.json

Reads BOARD.kicad_pcb.drc.json (quick_drc.py) and BOARD.kicad_pcb.ids.json (apply.py): every track segment or
via that this routing added and that DRC reports as track_dangling / via_dangling goes on the drop list (the
scripted escape of a J11 pin that the router did not use in the end, a spare via). apply.py leaves the listed
items out; run.sh repeats apply -> DRC -> cleanup until nothing new is found. Copper that was on the board
before is never touched. Exit status 10 if the list grew.
"""
import json
import os
import sys


def main():
    board, droppath = sys.argv[1], sys.argv[2]
    with open(board + ".drc.json") as f:
        d = json.load(f)
    with open(board + ".ids.json") as f:
        ids = json.load(f)
    drop = []
    if os.path.exists(droppath):
        with open(droppath) as f:
            drop = [tuple(x) for x in json.load(f)]
    rdir = os.path.dirname(droppath)
    routes = {}

    def route(name):
        if name not in routes:
            with open(os.path.join(rdir, name)) as f:
                routes[name] = json.load(f)
        return routes[name]

    def tee(k):
        """True if another routed track or via of the net sits on the inside of this segment: the segment is
        in use and only its tail dangles."""
        t = route(k[0])["tracks"][k[2]]
        (ax, ay), (bx, by) = t["a"], t["b"]
        ll = (bx - ax) ** 2 + (by - ay) ** 2
        pts = []
        for name in sorted(n for n in os.listdir(rdir) if n[0] == "r" and n[1:-5].isdigit() and n.endswith(".json")):
            r = route(name)
            for i, o in enumerate(r["tracks"]):
                if o["net"] == t["net"] and o["layer"] == t["layer"] and (name, "t", i) != k and (name, "t", i) not in drop:
                    pts += [o["a"], o["b"]]
            pts += [[o["x"], o["y"]] for i, o in enumerate(r["vias"]) if o["net"] == t["net"] and (name, "v", i) not in drop]
        for x, y in pts:
            if ll < 1e-9:
                continue
            u = ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ll
            d2 = (ax + u * (bx - ax) - x) ** 2 + (ay + u * (by - ay) - y) ** 2
            if d2 < 0.03 ** 2 and 0.02 < u * ll ** 0.5 < ll ** 0.5 - 0.02:
                return True
        return False

    new = []
    for v in d["violations"]:
        if v["type"] in ("track_dangling", "via_dangling"):
            for it in v["items"]:
                k = ids.get(it.get("uuid", ""))
                if k and tuple(k) not in drop and tuple(k) not in new:
                    if k[1] == "t" and tee(tuple(k)):
                        print(f"cleanup: keep {it['description']} at ({it['pos']['x']:.2f}, {-it['pos']['y']:.2f}): a junction inside, only the tail dangles")
                        continue
                    new.append(tuple(k))
                    print(f"cleanup: drop {it['description']} at ({it['pos']['x']:.2f}, {-it['pos']['y']:.2f})")
    with open(droppath, "w") as f:
        json.dump(drop + new, f)
    print(f"cleanup: {len(new)} new, {len(drop) + len(new)} dropped in all")
    return 10 if new else 0


if __name__ == "__main__":
    sys.exit(main())
