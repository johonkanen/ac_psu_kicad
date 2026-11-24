#!/usr/bin/env python3
"""Island count of every pour (kipy), for the island comparison after each chain step (planning rule 4).

  kipy islands.py BOARD OUT.json [BASE.json]

BOARD must be refilled with kicad-cli first. Writes {zone name|layer: islands} to OUT.json; with BASE.json prints
every pour whose count changed and exits 1 when one has more islands than in BASE (a pour split; for a "v6 bus"
lane that is a failed step) or vanished.
"""
import json
import sys

import pcbnew


def counts(b):
    out = {}
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().Seq():
            k = f"{z.GetZoneName() or z.GetNetname()}|{b.GetLayerName(l)}"
            out[k] = out.get(k, 0) + z.GetFilledPolysList(l).OutlineCount()
    return out


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    c = counts(b)
    json.dump(c, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    if len(sys.argv) < 4:
        print(f"islands: {len(c)} pour layers, {sum(c.values())} islands")
        return
    base = json.load(open(sys.argv[3]))
    worse = []
    for k in sorted(set(base) | set(c)):
        a, n = base.get(k), c.get(k)
        if a != n:
            tag = "WORSE" if (n is None or a is None or n > a) else "better"
            if tag == "WORSE" and a is not None and n is not None and n == 0 and a == 0:
                continue
            print(f"islands: {tag:6} {k}: {a} -> {n}")
            if tag == "WORSE":
                worse.append(k)
    print(f"islands: {len(c)} pour layers, {sum(c.values())} islands; " +
          (f"{len(worse)} WORSE than the base" if worse else "none worse than the base"))
    sys.exit(1 if worse else 0)


if __name__ == "__main__":
    main()
