#!/usr/bin/env python3
"""High-voltage rule in block A (kipy): every pair of copper objects of two nets on one layer, one of them a
high-voltage net (hv.py, plus the switch node SW_AFE_1), closer than 2.5 mm (HV <-> HV of another net: 1.0 mm).
Objects: pads, tracks, vias and filled zones that touch block A (blocks.block_of == "A", +3 mm).

  kipy block_A_hv.py BOARD [--new NEW.csv] [-v]

Two pads of one footprint are not counted (the part's own pin pitch). A pair is reported once, with the gap.
--new: pairs with a track / via of the CSV rows (kind track / via, matched by net, layer and ends) are "new"; the
other pairs are "old" (present on the base board before block A; listed with -v).
Exit 1 if a "new" pair exists (or any pair without --new).
"""
import csv
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from blocks import BLOCKS  # noqa: E402
from hv import is_hv as _is_hv  # noqa: E402

F, T = pcbnew.FromMM, pcbnew.ToMM
A = BLOCKS["A"][1]
EXTRA_HV = {"SW_AFE_1"}
# side-1 nets of one floating modulator: one group, they keep their Proteus spacing (09_sense_replay.py)
GROUPS = [{"SHUNT1", "SHUNT2", "Net-(U5-VIN+)", "Net-(U5-VIN-)", "SDM_RAW_VOLTAGE", "Net-(D8-K)"},
          {"INU_SHUNT1", "INU_SHUNT2", "Net-(U4-VIN+)", "Net-(U4-VIN-)", "ISO_AFE_SDM_RAW_VOLTAGE", "Net-(D9-K)"}]


def same_group(a, b):
    a, b = a.split("/")[-1], b.split("/")[-1]
    return any(a in g and b in g for g in GROUPS)


def is_hv(n):
    return bool(n) and (_is_hv(n) or n.split("/")[-1] in EXTRA_HV)


def near_a(bb, m=3.0):
    return not (T(bb.GetRight()) < A[0] - m or T(bb.GetLeft()) > A[2] + m or -T(bb.GetTop()) < A[1] - m
                or -T(bb.GetBottom()) > A[3] + m)


def items(b, layer):
    out = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and p.GetNetname() and near_a(p.GetBoundingBox()):
                q = p.GetPosition()
                out.append((p.GetNetname(), p.GetEffectiveShape(layer), p.GetBoundingBox(), "pad",
                            fp.GetReference(), f"{fp.GetReference()}-{p.GetNumber()}", (T(q.x), -T(q.y))))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == layer:
            if near_a(t.GetBoundingBox()) and t.GetNetname():
                kind = "via" if t.Type() == pcbnew.PCB_VIA_T else "track"
                q = t.GetPosition() if kind == "via" else t.GetStart()
                out.append((t.GetNetname(), t.GetEffectiveShape(layer), t.GetBoundingBox(), kind, None,
                            kind, (T(q.x), -T(q.y)), t))
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer) or not z.GetNetname():
            continue
        fill = z.GetFilledPolysList(layer)
        if not fill.OutlineCount() or not near_a(z.GetBoundingBox()):
            continue
        for k in range(fill.OutlineCount()):
            ps = pcbnew.SHAPE_POLY_SET()
            ps.AddOutline(fill.Outline(k))
            for h in range(fill.HoleCount(k)):
                ps.AddHole(fill.Hole(k, h))
            bb = fill.Outline(k).BBox()
            out.append((z.GetNetname(), ps, pcbnew.BOX2I(bb.GetPosition(), bb.GetSize()), "zone", None,
                        f"zone '{z.GetZoneName()}'", None))
    return out


def collide(a, b_, c):
    sa, sb = a[1], b_[1]
    if isinstance(sa, pcbnew.SHAPE_POLY_SET) and isinstance(sb, pcbnew.SHAPE_POLY_SET):
        g = pcbnew.SHAPE_POLY_SET(sa)
        g.Inflate(F(c), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, F(0.01))
        g.BooleanIntersection(sb)
        return g.OutlineCount() > 0
    if isinstance(sa, pcbnew.SHAPE_POLY_SET):
        return sa.Collide(sb, F(c))
    if isinstance(sb, pcbnew.SHAPE_POLY_SET):
        return sb.Collide(sa, F(c))
    return sa.Collide(sb, F(c))


def check(b):
    bad = []
    for layer in b.GetEnabledLayers().CuStack():
        its = items(b, layer)
        for i, a in enumerate(its):
            if not is_hv(a[0]):
                continue
            for j, o in enumerate(its):
                if j == i or o[0] == a[0] or (is_hv(o[0]) and j < i) or same_group(a[0], o[0]):
                    continue
                if a[3] == "pad" and o[3] == "pad" and a[4] == o[4]:
                    continue
                req = 1.0 if is_hv(o[0]) else 2.5
                bb = pcbnew.BOX2I(a[2].GetPosition(), a[2].GetSize())
                bb.Inflate(F(req))
                if not bb.Intersects(o[2]):
                    continue
                if not collide(a, o, req - 0.005):
                    continue
                lo, hi = 0.0, req
                for _ in range(12):
                    m = (lo + hi) / 2
                    if collide(a, o, m):
                        hi = m
                    else:
                        lo = m
                bad.append((b.GetLayerName(layer), a, o, lo, req))
    return bad


def key(b, t):
    if t.Type() == pcbnew.PCB_VIA_T:
        q = t.GetPosition()
        return ("via", t.GetNetname(), round(T(q.x), 3), round(-T(q.y), 3))
    e = sorted([(round(T(t.GetStart().x), 3), round(-T(t.GetStart().y), 3)),
                (round(T(t.GetEnd().x), 3), round(-T(t.GetEnd().y), 3))])
    return ("track", t.GetNetname(), b.GetLayerName(t.GetLayer())) + tuple(e)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    new = None
    if "--new" in sys.argv:
        with open(sys.argv[sys.argv.index("--new") + 1]) as fh:
            new = [r for r in csv.DictReader(fh) if r["kind"] in ("track", "via")]
        newkeys = set()
        for r in new:
            if r["kind"] == "via":
                newkeys.add(("via", r["net"], round(float(r["x1"]), 3), round(float(r["y1"]), 3)))
            else:
                e = sorted([(round(float(r["x1"]), 3), round(float(r["y1"]), 3)),
                            (round(float(r["x2"]), 3), round(float(r["y2"]), 3))])
                newkeys.add(("track", r["net"], r["layer"]) + tuple(e))
    bad = check(b)
    nnew = 0
    for L, a, o, g, req in bad:
        tag = ""
        if new is not None:
            isnew = any(it[3] in ("track", "via") and key(b, it[7]) in newkeys for it in (a, o))
            tag = "new " if isnew else "old "
            nnew += isnew
        pos = a[6] or o[6]
        if "-v" in sys.argv or tag != "old ":
            print(f"  {tag}{L}: {a[5]} [{a[0].split('/')[-1]}] - {o[5]} [{o[0].split('/')[-1]}] gap {g:.2f} < {req}"
                  + (f" near ({pos[0]:.2f}, {pos[1]:.2f})" if pos else ""))
    if new is None:
        print(f"block_A_hv: {len(bad)} pairs closer than the HV rule in A")
        sys.exit(1 if bad else 0)
    print(f"block_A_hv: {len(bad)} pairs closer than the HV rule in A, {nnew} with block A copper, "
          f"{len(bad) - nnew} on the base board")
    sys.exit(1 if nnew else 0)


if __name__ == "__main__":
    main()
