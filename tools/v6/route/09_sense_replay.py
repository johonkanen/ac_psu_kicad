#!/usr/bin/env python3
"""Routing chain step 09 (kipy): the copper of the two current-sense groups replayed from their Proteus layout.

  kipy 09_sense_replay.py IN OUT

v6 step 3 (tools/v6/v6_3_placement.py) turned the groups R48 + U5 + 9 parts and R91 + U4 + 11 parts by 180 degrees
as rigid blocks about their shunts and deleted the 67 tracks / vias of their private nets (SHUNT2, INU_SHUNT1,
Net-(D8-K), Net-(D9-K), Net-(U4-MDAT), Net-(U4-VIN+/-), Net-(U5-VIN+/-)). The layout of each block is unchanged, so
that copper fits again after the same turn: it is read from the board before step 3 (v6 step 2, 26d47e2), turned
about the old shunt pad centroid and moved to the new one, and each piece is tested by geo.Ctx at the new place
(2.5 mm to everything outside its own side-1 net group; two side-1 nets keep their Proteus spacing, 0.15 mm).
"""
import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import F, T, P, xy  # noqa: E402

R = geo.R
OLD_REV = "26d47e2"
GROUPS = {   # as v6_3_placement.GROUPS
    "AFE sense": (("R48", "U5", "D8", "R59", "R57", "R58", "C52", "C53", "C91", "C71", "C73"), "R48", (-36.0, -62.4)),
    "INV sense": (("R91", "U4", "D9", "R94", "R92", "R93", "C51", "C54", "C90", "C55", "C78", "C37", "R50"), "R91", (-83.5, 48.3)),
}
PRIVATE = {"SHUNT2", "INU_SHUNT1", "Net-(D8-K)", "Net-(D9-K)", "Net-(U4-MDAT)", "Net-(U4-VIN+)", "Net-(U4-VIN-)",
           "Net-(U5-VIN+)", "Net-(U5-VIN-)"}


def centroid(fp):
    ps = [xy(p.GetPosition()) for p in fp.Pads()]
    return sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)


def main():
    src, dst = sys.argv[1:3]
    old_path = os.path.join(R, "build", "v6route", "old_step2.kicad_pcb")
    if not os.path.exists(old_path):
        with open(old_path, "w") as fh:
            fh.write(subprocess.run(["git", "-C", R, "show", f"{OLD_REV}:kicad/ac_psu.kicad_pcb"], capture_output=True,
                                    text=True, check=True).stdout)
    old = pcbnew.LoadBoard(old_path)
    b = pcbnew.LoadBoard(src)
    cx = geo.Ctx(b)
    base_rule = cx.rule

    def rule(net, onet, lc=0.0):      # side-1 nets among themselves: their Proteus spacing
        if net and onet and geo.is_hv(net) and geo.is_hv(onet) and net != onet:
            return max(0.15, lc)
        return base_rule(net, onet, lc)
    cx.rule = rule
    cx.pierce = {"/05 VSI/INDUCTOR_OUTPUT", "/01 afe/LEMOUT"}   # HV pours round the blocks: they give way by their own clearance
    total = kept = 0
    for name, (refs, anchor, (nx, ny)) in GROUPS.items():
        ox, oy = centroid(old.FindFootprintByReference(anchor))
        xs, ys = [], []
        for r in refs:
            for p in old.FindFootprintByReference(r).Pads():
                x, y = xy(p.GetPosition())
                xs.append(x)
                ys.append(y)
        box = (min(xs) - 1.5, min(ys) - 1.5, max(xs) + 1.5, max(ys) + 1.5)

        def tr(x, y):
            return nx - (x - ox), ny - (y - oy)

        def inside(x, y):
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]
        objs = []
        for t in old.GetTracks():
            if t.GetNetname().split("/")[-1] not in PRIVATE:
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                x, y = xy(t.GetPosition())
                if inside(x, y):
                    objs.append(("via", t.GetNetname(), tr(x, y), None, 0, None))
            else:
                a, c = xy(t.GetStart()), xy(t.GetEnd())
                if inside(*a) and inside(*c):
                    objs.append(("trk", t.GetNetname(), tr(*a), tr(*c), T(t.GetWidth()), t.GetLayer()))
        n_ok = 0
        bad = []
        for kind, net, a, c, w, lay in objs:
            total += 1
            if kind == "via":
                v = cx.via_ok(net, *a)
                if v is None:
                    bad.append(f"via {net} ({a[0]:.1f}, {a[1]:.1f})")
                    continue
                cx.commit(v)
            else:
                err = cx.poly(net, lay, [a, c], w)
                if err:
                    bad.append(f"{net} {b.GetLayerName(lay)} {err}")
                    continue
            n_ok += 1
        kept += n_ok
        print(f"sense: {name}: {n_ok} of {len(objs)} pieces of the Proteus copper replayed" +
              (f"; left out: {'; '.join(bad[:8])}" if bad else ""))
    print(f"sense: {kept} of {total} pieces in all")
    b.Save(dst)


if __name__ == "__main__":
    main()
