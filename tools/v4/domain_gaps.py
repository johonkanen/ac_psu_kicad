#!/usr/bin/env python3
"""Insulation spacing check of the board copper between the domains of tools/v4/domains.py (run
under tools/p2k/bin/kipy).

Per copper layer: the union of the copper of each domain (pads, tracks, vias, filled zones),
grown by the required gap (P <-> I 5.0 mm reinforced, P/I <-> E 2.5 mm basic; IEC 61010-1 /
IEC 60664-1 printed wiring, PD2, 500 V row, see STATUS.md) and intersected with the other
domain's copper. Any overlap is a violation (reported with its position, the nets involved and
the gap found by bisection). Also: P copper on one layer must not overlap I copper on an adjacent
layer (prepreg/core thinner than the 0.4 mm solid insulation).

Usage: tools/p2k/bin/kipy tools/v4/domain_gaps.py [--board FILE] [-v]
Exit 1 on any violation.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common as bc  # noqa: E402
import domains  # noqa: E402

LAYERS = [("F.Cu", pcbnew.F_Cu), ("In1.Cu", pcbnew.In1_Cu), ("In2.Cu", pcbnew.In2_Cu), ("B.Cu", pcbnew.B_Cu)]
F = pcbnew.FromMM
T = pcbnew.ToMM
ERR = F(0.005)


def item_polys(board, layer_id, dom):
    """{domain: [(net, SHAPE_POLY_SET)]} on one layer."""
    out = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(layer_id):
                d = dom.get(pad.GetNetname())
                if d:
                    ps = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(ps, layer_id, 0, ERR, pcbnew.ERROR_INSIDE)
                    out.setdefault(d, []).append((pad.GetNetname(), ps, f"{fp.GetReference()}-{pad.GetNumber()}"))
    for t in board.GetTracks():
        if t.IsOnLayer(layer_id):
            d = dom.get(t.GetNetname())
            if d:
                ps = pcbnew.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(ps, layer_id, 0, ERR, pcbnew.ERROR_INSIDE)
                out.setdefault(d, []).append((t.GetNetname(), ps, "via" if t.GetClass() == "PCB_VIA" else "track"))
    for z in board.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer_id):
            continue
        d = dom.get(z.GetNetname())
        if d:
            ps = z.GetFilledPolysList(layer_id)
            if ps.OutlineCount():
                out.setdefault(d, []).append((z.GetNetname(), ps.CloneDropTriangulation(), f"zone {z.GetZoneName()}"))
    return out


def union(parts):
    u = pcbnew.SHAPE_POLY_SET()
    for _, ps, _ in parts:
        u.Append(ps)
    u.Simplify()
    return u


def grown(ps, r):
    g = ps.CloneDropTriangulation()
    g.Inflate(F(r), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, ERR)
    return g


def overlap(a, b):
    c = a.CloneDropTriangulation()
    c.BooleanIntersection(b)
    return c


def clusters(ps):
    out = []
    for i in range(ps.OutlineCount()):
        bb = ps.Outline(i).BBox()
        out.append((T(bb.Centre().x), -T(bb.Centre().y), T(bb.GetWidth()), T(bb.GetHeight())))
    return out


def near(parts, x, y, r):
    names = set()
    pt = pcbnew.VECTOR2I(F(x), F(-y))
    for net, ps, what in parts:
        if ps.Collide(pt, F(r)):
            names.add(f"{what} {domains.short(net)}")
    return sorted(names)


def check(board, dom, verbose=False):
    viol = []
    per_layer = {}
    for lname, lid in LAYERS:
        parts = item_polys(board, lid, dom)
        uni = {d: union(p) for d, p in parts.items()}
        per_layer[lname] = uni
        for a, b in (("P", "I"), ("P", "E"), ("I", "E"), ("P", "C"), ("I", "C")):
            if a not in uni or b not in uni:
                continue
            req = domains.gap(a, b)
            ov = overlap(grown(uni[a], req - 0.001), uni[b])
            if ov.OutlineCount() == 0 or ov.Area() < 1e-6:
                continue
            for x, y, w, h in clusters(ov):
                # bisection on the local gap
                lo, hi = 0.0, req
                for _ in range(8):
                    mid = (lo + hi) / 2
                    o2 = overlap(grown(uni[a], mid), uni[b])
                    hit = any(abs(cx - x) < (w / 2 + mid + 0.5) and abs(cy - y) < (h / 2 + mid + 0.5)
                              for cx, cy, _, _ in clusters(o2)) if o2.OutlineCount() else False
                    lo, hi = (lo, mid) if hit else (mid, hi)
                viol.append((lname, a, b, req, hi, x, y,
                             near(parts[a], x, y, req + 0.5)[:3], near(parts[b], x, y, req + 0.5)[:3]))
    stack = [n for n, _ in LAYERS]
    for la, lb in zip(stack, stack[1:]):
        for a, b in (("P", "I"), ("I", "P"), ("P", "C"), ("C", "P"), ("I", "C"), ("C", "I")):
            A, B = per_layer[la].get(a), per_layer[lb].get(b)
            if A is None or B is None:
                continue
            ov = overlap(A, B)
            if ov.OutlineCount() and ov.Area() > F(0.01) * F(1):
                for x, y, w, h in clusters(ov):
                    viol.append((f"{la}/{lb}", a, b, 0.0, 0.0, x, y, ["layer overlap"], []))
    return viol


def main():
    path = bc.BOARD
    if "--board" in sys.argv:
        path = sys.argv[sys.argv.index("--board") + 1]
    board = pcbnew.LoadBoard(path)
    _, nets = bc.export_netlist()
    dom = domains.classify(nets)
    viol = check(board, dom, "-v" in sys.argv)
    import deviations   # v5: gaps inside the pending-layout areas wait for the GUI layout
    pend = [v for v in viol if deviations.in_pending(v[5], v[6])]
    viol = [v for v in viol if v not in pend]
    for lname, a, b, req, g, x, y, na, nb in (pend if "-v" in sys.argv else pend[:10]):
        print(f"domain_gaps: pending {lname:7} {a}<->{b} gap {g:4.2f} mm at ({x:8.2f}, {y:8.2f})  {', '.join(na)} | {', '.join(nb)}")
    for lname, a, b, req, g, x, y, na, nb in viol:
        print(f"domain_gaps: {lname:7} {a}<->{b} gap {g:4.2f} mm < {req} mm at ({x:8.2f}, {y:8.2f})  {', '.join(na)} | {', '.join(nb)}")
    print(f"domain_gaps: {len(viol)} violations (P<->I, P/I<->C >= 5.0 mm, P/I<->E >= 2.5 mm on every layer, no "
          f"P/I/C overlap between adjacent layers)" + (f"; {len(pend)} in v5 pending-layout areas" if pend else ""))
    print("domain_gaps: " + ("OK" if not viol else "FAILED"))
    sys.exit(1 if viol else 0)


if __name__ == "__main__":
    main()
