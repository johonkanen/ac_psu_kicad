#!/usr/bin/env python3
"""Lane count across a cut line (V6 pass 1 routing list): how many tracks of width W fit side by side across a
straight cut on each copper layer, given the copper already on the board, the keep-out rule areas, the board edge,
the 2.5 mm high-voltage rule and the 5 mm domain gaps.

  kipy tools/v6/route/lanes.py BOARD CUTS.json [--w 0.2] [--s 0.15] [--ignore NET,NET]

CUTS.json: [{"name": ..., "dom": "I", "a": [x, y], "b": [x, y], "layers": ["F.Cu", ...]}, ...] (IPC frame, mm).
For every sample point on the cut (0.02 mm) a track centre is free when it keeps, from every object of another
net, max(0.15, the object's local clearance, 2.5 if either side is a high-voltage net, the domain gap) + W/2, lies
outside every keep-out that forbids tracks on that layer and 0.25 mm + W/2 inside the board edge. Free centre
intervals of length L give floor(L / (W + S)) + 1 lanes. Pours count as obstacles (a lane may not cut a pour).
"""
import json
import math
import os
import sys

import pcbnew

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path[:0] = [os.path.join(R, "tools"), os.path.join(R, "tools", "v4"), os.path.dirname(os.path.abspath(__file__))]
import board_common as bc  # noqa: E402
import domains  # noqa: E402
from hv import is_hv  # noqa: E402

M = pcbnew.FromMM
T = pcbnew.ToMM


def P(x, y):
    return pcbnew.VECTOR2I(M(x), M(-y))


def main():
    a = sys.argv[1:]
    board = pcbnew.LoadBoard(a[0])
    cuts = json.load(open(a[1]))
    W = float(a[a.index("--w") + 1]) if "--w" in a else 0.2
    S = float(a[a.index("--s") + 1]) if "--s" in a else 0.15
    ignore = set(a[a.index("--ignore") + 1].split(",")) if "--ignore" in a else set()
    _, nets = bc.export_netlist()
    dom = domains.classify(nets)
    dom = {domains.short(k): v for k, v in dom.items()}
    edge = board.GetBoardEdgesBoundingBox()
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, True)
    for c in cuts:
        cdom = c.get("dom")
        (x0, y0), (x1, y1) = c["a"], c["b"]
        L = math.hypot(x1 - x0, y1 - y0)
        n = int(L / 0.02) + 1
        pts = [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1)) for i in range(n)]
        res = []
        for lname in c["layers"]:
            lid = board.GetLayerID(lname)
            obst = []    # (shape-like collide(point, clearance) callable, required clearance)

            def req(net, local):
                r = max(0.15, local)
                sn = domains.short(net) if net else ""
                if sn and is_hv(sn):
                    r = max(r, 2.5)
                d = dom.get(sn)
                g = domains.gap(cdom, d)
                if g:
                    r = max(r, g)
                return r
            bbx = pcbnew.BOX2I(P(min(x0, x1) - 6, max(y0, y1) + 6), pcbnew.VECTOR2L(M(abs(x1 - x0) + 12), M(abs(y1 - y0) + 12)))
            for fp in board.GetFootprints():
                if not fp.GetBoundingBox().Intersects(bbx):
                    continue
                for pad in fp.Pads():
                    if not pad.IsOnLayer(lid) or pad.GetNetname() in ignore:
                        continue
                    sh = pad.GetEffectiveShape(lid)
                    obst.append((sh, req(pad.GetNetname(), T(pad.GetLocalClearance() or 0))))
            for t in board.GetTracks():
                if t.GetNetname() in ignore or not t.IsOnLayer(lid) or not t.GetBoundingBox().Intersects(bbx):
                    continue
                obst.append((t.GetEffectiveShape(lid), req(t.GetNetname(), 0)))
            zfills, keeps = [], []
            for z in board.Zones():
                if not z.IsOnLayer(lid) or not z.GetBoundingBox().Intersects(bbx):
                    continue
                if z.GetIsRuleArea():
                    if z.GetDoNotAllowTracks():
                        keeps.append(z.Outline())
                    continue
                if z.GetNetname() in ignore:
                    continue
                zfills.append((z.GetFilledPolysList(lid), req(z.GetNetname(), T(z.GetLocalClearance() or 0))))
            free = []
            for (x, y) in pts:
                v = P(x, y)
                ok = outline.Contains(v) and not any(k.Contains(v) for k in keeps)
                if ok:
                    ok = not any(k.Collide(v, M(W / 2)) for k in keeps)
                if ok:
                    ok = outline.Outline(0).PointCount() == 0 or True
                    for sh, r in obst:
                        if sh.Collide(pcbnew.SEG(v, v), M(r + W / 2)):
                            ok = False
                            break
                if ok:
                    for zp, r in zfills:
                        if zp.Collide(v, M(r + W / 2)):
                            ok = False
                            break
                free.append(ok)
            ivs, start = [], None
            for i, ok in enumerate(free + [False]):
                if ok and start is None:
                    start = i
                if not ok and start is not None:
                    ivs.append((start, i - 1))
                    start = None
            lanes = sum(int(((e - s) * 0.02) / (W + S)) + 1 for s, e in ivs)
            desc = ", ".join(f"{(e - s) * 0.02 + W:.2f}@({pts[s][0]:.1f},{pts[s][1]:.1f})" for s, e in ivs)
            res.append((lname, lanes, desc))
        print(f"{c['name']}  ({x0},{y0})-({x1},{y1}) {L:.1f} mm, dom {cdom}")
        for lname, lanes, desc in res:
            print(f"   {lname:7} lanes {lanes:3}   free widths (track edge to edge): {desc}")


if __name__ == "__main__":
    main()
