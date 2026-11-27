#!/usr/bin/env python3
"""Block E numbers from a kicad-cli DRC JSON report (stdlib).

  python3 block_E_check.py DRC.json [--list]

Open connections with both ends inside E (E minus block G), open connections with one end in E, DRC errors and
dangling items located inside E (an item counts when its position lies in E).
"""
import collections
import json
import sys

E = (40.0, -46.0, 118.7, 46.0)
G = (67.0, -54.6, 97.5, -4.0)


def inE(x, y):
    return E[0] <= x <= E[2] and E[1] <= y <= E[3] and not (G[0] < x < G[2] and G[1] < y < G[3])


def pos(i):
    return i["pos"]["x"], -i["pos"]["y"]


d = json.load(open(sys.argv[1]))
inner, half = [], []
for u in d["unconnected_items"]:
    its = u["items"]
    k = sum(inE(*pos(i)) for i in its)
    if k == len(its):
        inner.append(u)
    elif k:
        half.append(u)
err = collections.Counter()
errs = []
dang = []
for v in d["violations"]:
    if not any(inE(*pos(i)) for i in v["items"]):
        continue
    if v["type"] in ("track_dangling", "via_dangling"):
        dang.append(v)
    elif v.get("severity") == "error" and v["type"] != "courtyards_overlap":
        err[v["type"]] += 1
        errs.append(v)
print(f"E: open inside {len(inner)}, open with one end in E {len(half)}, DRC errors {sum(err.values())} "
      f"({', '.join(f'{k} {n}' for k, n in err.items()) or '-'}), dangling {len(dang)}")
if "--list" in sys.argv:
    def net(u):
        return u["items"][0]["description"].split("[")[-1].split("]")[0] if "[" in u["items"][0]["description"] else "?"
    c = collections.Counter(net(u) for u in inner)
    print("  open inside by net:", ", ".join(f"{n} {k}" for n, k in c.most_common()))
    c = collections.Counter(net(u) for u in half)
    print("  open one end in E:", ", ".join(f"{n} {k}" for n, k in c.most_common()))
    for v in errs + dang:
        print("  ", v["type"], " | ".join(f"{i['description'][:60]} @({pos(i)[0]:.2f},{pos(i)[1]:.2f})" for i in v["items"]))
