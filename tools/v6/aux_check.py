#!/usr/bin/env python3
"""Checks of the aux flyback routes on a FILLED board (run under tools/p2k/bin/kipy; V6_PLAN.md section 10).

  tools/p2k/bin/kipy tools/v6/aux_check.py BOARD [--base BASE_FILLED] [--drc DRC.json]

  1. HV clearance (the rule lives only in pad clearances on the board): every pair HV copper <-> other copper within
     the areas PX / IA (+3 mm) on F.Cu / B.Cu closer than 2.5 mm (HV <-> HV of another net 1.0 mm), on inner layers
     closer than 0.5 mm (AUX_DRAIN / AUX_CLAMP: 2.0 mm). A pair passes if
       - both are pads of one footprint (the part's own pad gap), or
       - one is an HV pad with its own clearance (card_layout.HV_PADS) and the gap holds that clearance, or
       - pad-gap rule: the piece is not closer to the other copper than the nearest pad of its own net is
     Anything else is a violation (exit 1).
  2. Islands of every pour that touches the areas (and the change against --base).
  3. Open connections inside the areas from a kicad-cli DRC report (--drc).
  4. Copper area of AUX_DRAIN per layer.
"""
import json
import math
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aux_lib as L  # noqa: E402

F, T = pcbnew.FromMM, pcbnew.ToMM
ERR = F(0.005)


def gapc(a, b, hi=3.0):
    return L.gap(a, b, 0.0, hi)


def scope_box(m=3.0):
    out = []
    for x0, y0, x1, y1 in L.AREAS.values():
        bb = pcbnew.BOX2I(L.P(x0 - m, y1 + m), pcbnew.VECTOR2L(F(x1 - x0 + 2 * m), F(y1 - y0 + 2 * m)))
        out.append(bb)
    return out


def items(b, layer, boxes):
    """(net, shape, kind, lc, ref, label)"""
    out = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and any(bx.Intersects(p.GetBoundingBox()) for bx in boxes):
                lc = p.GetLocalClearance()
                out.append((p.GetNetname(), p.GetEffectiveShape(layer), "pad", T(lc) if lc else 0.0, fp.GetReference(),
                            f"{fp.GetReference()}-{p.GetNumber()}"))
    for t in b.GetTracks():
        if t.IsOnLayer(layer) and any(bx.Intersects(t.GetBoundingBox()) for bx in boxes):
            v = t.Type() == pcbnew.PCB_VIA_T
            x, y = L.xy(t.GetPosition() if v else t.GetStart())
            lab = f"via ({x:.2f},{y:.2f})" if v else "track ({:.2f},{:.2f})-({:.2f},{:.2f})".format(x, y, *L.xy(t.GetEnd()))
            out.append((t.GetNetname(), t.GetEffectiveShape(layer), "via" if v else "track", 0.0, "", lab))
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer):
            continue
        fill = z.GetFilledPolysList(layer)
        if fill.OutlineCount() and any(bx.Intersects(z.GetBoundingBox()) for bx in boxes):
            out.append((z.GetNetname(), fill, "zone", T(z.GetLocalClearance() or 0), "", f"zone '{z.GetZoneName()}'"))
    return out


def required(layer, a, b_):
    na, nb = a[0], b_[0]
    outer = layer in L.OUTER
    if outer:
        if L.is_hv(na) != L.is_hv(nb):
            return L.HV_OUT
        if L.is_hv(na) and L.is_hv(nb):
            return L.HV_HV
        return None
    if na in L.SWING or nb in L.SWING:
        return L.HV_SWING_IN
    if L.is_hv(na) != L.is_hv(nb):
        return L.HV_IN
    return None


def hv_check(b, verbose=False):
    boxes = scope_box()
    bad, ok_n, pre = [], 0, []
    for layer in b.GetEnabledLayers().CuStack():
        its = items(b, layer, boxes)
        pads_by_net = {}
        for it in its:
            if it[2] == "pad":
                pads_by_net.setdefault(it[0], []).append(it)
        for i, a in enumerate(its):
            if not a[0] or not (L.is_hv(a[0]) or a[0] in L.SWING):
                continue
            for b_ in its:
                if b_ is a or not b_[0] or b_[0] == a[0]:
                    continue
                if L.is_hv(b_[0]) and id(b_) < id(a):
                    continue        # HV-HV pair: once
                req = required(layer, a, b_)
                if req is None or not a[1].Collide(b_[1], F(req - 0.005)):
                    continue
                g = gapc(a[1], b_[1])
                why = None
                if a[2] == "pad" and b_[2] == "pad" and a[4] == b_[4]:
                    why = "pads of one part"
                elif (a[2] == "pad" and a[3] and g >= a[3] - 0.01) or (b_[2] == "pad" and b_[3] and g >= b_[3] - 0.01):
                    why = "pad clearance (HV_PADS)"
                else:
                    # pad-gap rule: nearest pad of either net to the other item
                    best = 0.0
                    for own, other in ((a, b_), (b_, a)):
                        for p in pads_by_net.get(own[0], []):
                            if p is own or not p[1].Collide(own[1], F(0.01)):
                                continue        # only the pad the piece leaves (touches)
                            if p[1].Collide(other[1], F(req)):
                                best = max(best, 0.0)
                                gp = gapc(p[1], other[1])
                                if g >= gp - 0.02 and gp < req:
                                    why = f"pad-gap rule ({p[5]} is {gp:.2f} mm from it)"
                                    break
                        if why:
                            break
                if why:
                    ok_n += 1
                    if verbose:
                        print(f"  ok   {b.GetLayerName(layer)} {a[5]} [{a[0]}] - {b_[5]} [{b_[0]}]: {g:.3f} < {req}: {why}")
                    continue
                msg = f"{b.GetLayerName(layer)} {a[5]} [{a[0]}] - {b_[5]} [{b_[0]}]: {g:.3f} mm < {req}"
                (bad if (mine(a) or mine(b_)) else pre).append(msg)
    return bad, ok_n, pre


def mine(it):
    """Copper of the aux routes: tracks / vias inside the areas, the 'v6 aux' zones."""
    if it[2] == "zone":
        return "v6 aux" in it[5]
    if it[2] in ("track", "via"):
        bb = it[1].BBox()
        return L.box_in_area(pcbnew.BOX2I(bb.GetPosition(), bb.GetSize()), -0.6)
    return False


def islands(b, boxes):
    out = {}
    for z in b.Zones():
        if z.GetIsRuleArea() or not any(bx.Intersects(z.GetBoundingBox()) for bx in boxes):
            continue
        n = sum(z.GetFilledPolysList(l).OutlineCount() for l in z.GetLayerSet().CuStack())
        out[(z.GetZoneName(), z.GetNetname())] = n
    return out


def drain_area(b):
    res = {}
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == "AUX_DRAIN":
            for l in z.GetLayerSet().CuStack():
                res[b.GetLayerName(l)] = res.get(b.GetLayerName(l), 0.0) + z.GetFilledPolysList(l).Area() / 1e12
    for t in b.GetTracks():
        if t.GetNetname() == "AUX_DRAIN" and t.Type() != pcbnew.PCB_VIA_T:
            ps = pcbnew.SHAPE_POLY_SET()
            t.TransformShapeToPolygon(ps, t.GetLayer(), 0, ERR, pcbnew.ERROR_INSIDE)
            k = b.GetLayerName(t.GetLayer()) + " tracks"
            res[k] = res.get(k, 0.0) + ps.Area() / 1e12
    return res


def drc_open(path):
    d = json.load(open(path))
    out = []
    for u in d.get("unconnected_items", []):
        its = u["items"]
        if any(L.in_area(i["pos"]["x"], -i["pos"]["y"], -0.5) for i in its):
            out.append(" | ".join(f"{i['description']} ({i['pos']['x']:.2f}, {-i['pos']['y']:.2f})" for i in its))
    viol = []
    for v in d.get("violations", []):
        its = v["items"]
        if v.get("severity") == "error" and any(L.in_area(i["pos"]["x"], -i["pos"]["y"], -0.5) for i in its):
            viol.append(f"{v['type']}: " + " | ".join(f"{i['description']} ({i['pos']['x']:.2f}, {-i['pos']['y']:.2f})" for i in its))
    return out, viol, len(d.get("unconnected_items", [])), len(d.get("violations", []))


def main():
    args = sys.argv[1:]
    b = pcbnew.LoadBoard(args[0])
    verbose = "-v" in args
    rc = 0
    bad, ok_n, pre = hv_check(b, verbose)
    print(f"HV clearance: {len(bad)} violations by aux copper, {ok_n} close pairs accepted by the rules above, "
          f"{len(pre)} pre-existing pairs without aux copper (placement / outside the areas)")
    for m in bad:
        print("  VIOLATION", m)
    for m in pre:
        print("  pre-existing", m)
    rc |= bool(bad)
    boxes = scope_box(0.0)
    isl = islands(b, boxes)
    base = None
    if "--base" in args:
        base = islands(pcbnew.LoadBoard(args[args.index("--base") + 1]), boxes)
    print("pours touching the areas: islands" + (" (base -> now)" if base else ""))
    for k in sorted(isl):
        was = base.get(k, "new") if base else None
        print(f"  {k[0]!r} [{k[1]}]: " + (f"{was} -> {isl[k]}" if base else f"{isl[k]}"))
    print("AUX_DRAIN copper (mm2):", ", ".join(f"{k} {v:.1f}" for k, v in sorted(drain_area(b).items())))
    if "--drc" in args:
        op, viol, nu, nv = drc_open(args[args.index("--drc") + 1])
        print(f"DRC: {nu} unconnected items on the whole board, {len(op)} with an end inside the areas; "
              f"{nv} violations on the board, {len(viol)} errors inside the areas")
        for m in op:
            print("  OPEN", m)
        for m in viol:
            print("  DRC", m)
    sys.exit(rc)


if __name__ == "__main__":
    main()
