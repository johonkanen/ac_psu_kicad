#!/usr/bin/env python3
"""Block E hand fix as a chain step (kipy; block_E_chain.sh step 41).

  kipy block_E_fix.py IN OUT

5V_ISOL ran on F.Cu from its via at (81.875, 42.3) along y 45.5 to (67.15, 45.5) beside C157; together with the
PWM_Q5 run at y 41.7 it cut a strip out of the ISOPGND F.Cu pour of the band (island count 1 -> 2). The F.Cu piece
goes to In3 (free there since the sdm reserve was shrunk to its part north of E) with a via at its west end. Every
new piece is tested by geo.Ctx (clearances, HV rule, domain gaps, pours, keep-outs).
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import xy  # noqa: E402

NET = "5V_ISOL"
A, Z = (81.875, 42.3), (67.15, 45.5)       # the via at the east end, the west end of the F.Cu run
# the second run: F.Cu between its vias at (99.05, 42.65) and (93.125, 41.3) around R97 closed an ISOPGND island
# (R97-2) with the ISOGND run of C158 / C159; it goes to In3 or B.Cu between the same vias
A2, Z2 = (99.05, 42.65), (93.125, 41.3)


def f_chain(b, a, z):
    fc = [t for t in b.GetTracks() if t.GetNetname() == NET and t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.F_Cu]
    chain, cur, seen = [], a, set()
    while True:
        nxt = [t for t in fc if id(t) not in seen and (
            max(abs(xy(t.GetStart())[0] - cur[0]), abs(xy(t.GetStart())[1] - cur[1])) < 1e-3 or
            max(abs(xy(t.GetEnd())[0] - cur[0]), abs(xy(t.GetEnd())[1] - cur[1])) < 1e-3)]
        if len(nxt) != 1:
            break
        t = nxt[0]
        seen.add(id(t))
        chain.append(t)
        s, e = xy(t.GetStart()), xy(t.GetEnd())
        cur = e if max(abs(s[0] - cur[0]), abs(s[1] - cur[1])) < 1e-3 else s
        if max(abs(cur[0] - z[0]), abs(cur[1] - z[1])) < 1e-3:
            return chain
    return None


def second(dst):
    """The 5V_ISOL F.Cu run between its vias (99.05, 42.65) and (93.125, 41.3) and the ISOGND run of C158 / C159 above
    it closed an ISOPGND island around R97-2 (the ISOGND-ISOPGND link): the run is deleted here and routed again on
    In3 / B.Cu by the next chain step (42)."""
    b = pcbnew.LoadBoard(dst)
    ch = f_chain(b, A2, Z2)
    if not ch:
        sys.exit(f"fix: the F.Cu run {A2} -> {Z2} of {NET} not found; nothing done")
    for t in ch:
        b.Delete(t)
    b.Save(dst)
    print(f"fix: {NET} F.Cu run {A2} -> {Z2} ({len(ch)} pieces) deleted (rerouted off F.Cu by step 42)")


def main():
    src, dst = sys.argv[1:3]
    b = pcbnew.LoadBoard(src)
    # the F.Cu chain from A to Z
    fc = [t for t in b.GetTracks() if t.GetNetname() == NET and t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.F_Cu]
    chain, cur, seen = [], A, set()
    while True:
        nxt = [t for t in fc if id(t) not in seen and (
            max(abs(xy(t.GetStart())[0] - cur[0]), abs(xy(t.GetStart())[1] - cur[1])) < 1e-3 or
            max(abs(xy(t.GetEnd())[0] - cur[0]), abs(xy(t.GetEnd())[1] - cur[1])) < 1e-3)]
        if len(nxt) != 1:
            break
        t = nxt[0]
        seen.add(id(t))
        chain.append(t)
        s, e = xy(t.GetStart()), xy(t.GetEnd())
        cur = e if max(abs(s[0] - cur[0]), abs(s[1] - cur[1])) < 1e-3 else s
        if max(abs(cur[0] - Z[0]), abs(cur[1] - Z[1])) < 1e-3:
            break
    if not chain or max(abs(cur[0] - Z[0]), abs(cur[1] - Z[1])) > 1e-3:
        sys.exit(f"fix: the F.Cu run {A} -> {Z} of {NET} not found; nothing done")
    w = pcbnew.ToMM(chain[0].GetWidth())
    for t in chain:
        b.Delete(t)
    tmp = dst + ".fix.kicad_pcb"
    b.Save(tmp)
    b = pcbnew.LoadBoard(tmp)
    os.remove(tmp)
    cx = geo.Ctx(b)
    cx.via_pierce = {"ISOGND", "3V3_ISO"}
    for ymid in (45.5, 45.2, 44.9, 44.6, 44.3):
        pts = [A, (A[0] - (ymid - A[1]), ymid), (Z[0] + 0.45, ymid), (Z[0] + 0.45, Z[1])]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        v = cx.via_ok(NET, Z[0] + 0.45, Z[1])
        if v is None:
            continue
        segs = [cx.mktrack(NET, pcbnew.In3_Cu, pts[i], pts[i + 1], w) for i in range(len(pts) - 1)]
        if all(cx.clear(NET, s.GetEffectiveShape(pcbnew.In3_Cu), s.GetBoundingBox(), pcbnew.In3_Cu) for s in segs):
            link = cx.mktrack(NET, pcbnew.F_Cu, (Z[0] + 0.45, Z[1]), Z, w)
            cx.commit(*segs, v, link)
            b.Save(dst)
            print(f"fix: {NET} F.Cu run {A} -> {Z} ({len(chain)} pieces) now on In3 at y {ymid}, via at "
                  f"({Z[0] + 0.45:.2f}, {Z[1]:.2f})")
            second(dst)
            return
    sys.exit(f"fix: no clear In3 path for {NET}; nothing done")


if __name__ == "__main__":
    main()
