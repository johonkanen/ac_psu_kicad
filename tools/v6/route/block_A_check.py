#!/usr/bin/env python3
"""Block A numbers from a kicad-cli DRC JSON report (stdlib).

  python3 block_A_check.py DRC.json [--list]

Open connections with both ends inside A (blocks.block_of == "A": x -128.3 .. -2, y -83.1 .. -12)
and D2 along its north edge), open connections with one end in A, DRC errors and dangling items located inside A.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blocks import block_of  # noqa: E402


def inA(x, y):
    return block_of(x, y) == "A"


def pos(i):
    return i["pos"]["x"], -i["pos"]["y"]


def net(u):
    d = u["items"][0]["description"]
    return d.split("[")[-1].split("]")[0] if "[" in d else "?"


def main():
    d = json.load(open(sys.argv[1]))
    inner, half = [], []
    for u in d["unconnected_items"]:
        its = u["items"]
        k = sum(inA(*pos(i)) for i in its)
        if k == len(its):
            inner.append(u)
        elif k:
            half.append(u)
    err = collections.Counter()
    errs, dang = [], []
    for v in d["violations"]:
        if not any(inA(*pos(i)) for i in v["items"]):
            continue
        if v["type"] in ("track_dangling", "via_dangling"):
            dang.append(v)
        elif v.get("severity") == "error" and v["type"] != "courtyards_overlap":
            err[v["type"]] += 1
            errs.append(v)
    print(f"A: open inside {len(inner)}, open with one end in A {len(half)}, DRC errors {sum(err.values())} "
          f"({', '.join(f'{k} {n}' for k, n in err.items()) or '-'}), dangling {len(dang)}")
    if "--list" in sys.argv:
        c = collections.Counter(net(u) for u in inner)
        print("  open inside by net:", ", ".join(f"{n} {k}" for n, k in c.most_common()))
        for u in inner:
            print("    ", " | ".join(f"{i['description'][:70]} @({pos(i)[0]:.2f},{pos(i)[1]:.2f})" for i in u["items"]))
        c = collections.Counter(net(u) for u in half)
        print("  open one end in A:", ", ".join(f"{n} {k}" for n, k in c.most_common()))
        for u in half:
            print("    ", " | ".join(f"{i['description'][:70]} @({pos(i)[0]:.2f},{pos(i)[1]:.2f})" for i in u["items"]))
        for v in errs + dang:
            print("  ", v["type"], " | ".join(f"{i['description'][:60]} @({pos(i)[0]:.2f},{pos(i)[1]:.2f})"
                                               for i in v["items"]))


if __name__ == "__main__":
    main()
