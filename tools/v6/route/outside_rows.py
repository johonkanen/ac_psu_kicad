#!/usr/bin/env python3
"""New copper of the routing chain that lies outside the open-layout rows of lib/v5_copper.csv / lib/v6_copper.csv
(kipy). The Proteus comparisons of tools/check_all.sh (check_board, gerber_roundtrip) accept changed copper only
inside those rows: this lists, per 10 mm grid cell, the new tracks / vias outside them, so that rows can be added.

  kipy outside_rows.py ROUTED_BOARD BASE_BOARD
"""
import collections
import os
import sys

import pcbnew

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(R, "tools")]
import deviations  # noqa: E402

T = pcbnew.ToMM


def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return ("v", t.GetPosition().x, t.GetPosition().y, t.GetNetname())
    a, c = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    return ("t", t.GetLayer(), min(a, c), max(a, c), t.GetNetname())


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    old = {key(t) for t in pcbnew.LoadBoard(sys.argv[2]).GetTracks()}
    cells = collections.defaultdict(set)
    for t in b.GetTracks():
        if key(t) in old:
            continue
        via = t.Type() == pcbnew.PCB_VIA_T
        pts = [t.GetPosition()] if via else [t.GetStart(), t.GetEnd()]
        lay = "*" if via else b.GetLayerName(t.GetLayer())
        for p in pts:
            x, y = T(p.x), -T(p.y)
            if not deviations.in_area(lay, x, y):
                cells[(int(x // 10) * 10, int(y // 10) * 10)].add(t.GetNetname().split("/")[-1])
    for (x, y), nets in sorted(cells.items()):
        print(f"outside: cell x {x}..{x + 10}, y {y}..{y + 10}: {', '.join(sorted(nets))}")
    print(f"outside: {len(cells)} cells with new copper outside the open-layout rows")


if __name__ == "__main__":
    main()
