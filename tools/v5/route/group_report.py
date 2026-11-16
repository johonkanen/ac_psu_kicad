#!/usr/bin/env python3
"""Open connections per group of reports/v5_layout/routing_list.md, before and after routing (stdlib only).

  python3 tools/v5/route/group_report.py BEFORE.drc.json AFTER.drc.json

Both files are kicad-cli DRC reports (JSON). Counts the unconnected items per net and sums them per group;
lists the nets that still have open connections.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def opens(path):
    with open(path) as f:
        d = json.load(f)
    c = collections.Counter()
    for u in d.get("unconnected_items", []):
        m = re.search(r"\[([^\]]*)\]", u["items"][0]["description"])
        c[m.group(1).split("/")[-1] if m else "?"] += 1
    return c


def main():
    before, after = opens(sys.argv[1]), opens(sys.argv[2])
    groups, cur = collections.OrderedDict(), None
    with open(os.path.join(ROOT, "reports", "v5_layout", "routing_list.md")) as f:
        for line in f:
            m = re.match(r"## (\d+)\. (.*)", line)
            if m:
                cur = f"{m.group(1)}. {m.group(2).strip()}"
                groups[cur] = []
            elif cur and line.startswith("| ") and not line.startswith("| Net |") and not line.startswith("|---"):
                groups[cur].append(line.split("|")[1].strip())
    seen = set()
    print(f"{'group':62s} before  after")
    for g, nets in groups.items():
        seen.update(nets)
        left = [f"{n} {after[n]}" for n in nets if after[n]]
        print(f"{g[:62]:62s} {sum(before[n] for n in nets):5d}  {sum(after[n] for n in nets):5d}   {', '.join(left)}")
    rest_b = sum(v for n, v in before.items() if n not in seen)
    rest_a = sum(v for n, v in after.items() if n not in seen)
    print(f"{'not in the list (aux flyback, DC bus)':62s} {rest_b:5d}  {rest_a:5d}")
    print(f"{'total':62s} {sum(before.values()):5d}  {sum(after.values()):5d}")


if __name__ == "__main__":
    main()
