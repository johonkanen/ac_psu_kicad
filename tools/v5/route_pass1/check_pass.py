"""Checks of a routing-pass board that DRC does not make (run under tools/p2k/bin/kipy; IPC frame, y up).

  kipy check_pass.py PLACED.kicad_pcb ROUTED_REFILLED.kicad_pcb [DRC.json]

New copper = tracks and vias of ROUTED that are not in PLACED (by geometry). Reports:
  1. existing copper that is missing or changed in ROUTED (must be 0: nothing outside the scope may change)
  2. new copper outside the `unrouted` rectangles of lib/v5_copper.csv (and outside the brief's passage y <= 55.3)
  3. new tracks on the plane layers In1 / In2 / In4 inside the card planes, new F.Cu / B.Cu copper in the DC bus
     band, in the passage north of J11, or within 2.5 mm of the bus wire pads (rules 2, 3, 3a)
  4. high-voltage spacing: copper of AUX_DRAIN / AUX_CLAMP / AUX_VIN / DC+ / AUX_ST1/2 / AUX_LV1/2 closer than
     2.5 mm to another net on F.Cu / B.Cu, for every pair with at least one new item (a pad's own clearance
     replaces 2.5 mm where the placement set one: HV_PADS of card_layout.py)
  5. new vias (all / signal), new track length per layer, open connections per group (from DRC.json)
"""
import collections
import csv
import json
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
T, F = pcbnew.ToMM, pcbnew.FromMM
HV = set(json.load(open(os.path.join(HERE, "hv_clearances.json"))))
GROUPS = json.load(open(os.path.join(HERE, "groups.json")))
BUS_BAND = (58.9, 43.2, 118.1, 48.8)
PASSAGE = (40.0, 51.1, 59.0, 55.0)
CARD_PLANES = [(44.4, 10.8, 95.1, 33.0), (58.9, -9.4, 118.1, 48.8), (102.5, -34.5, 118.1, 3.0), (42.5, -20.7, 85.5, 5.8)]


def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return ("via", t.GetPosition().x, t.GetPosition().y, t.GetNetname())
    a, b = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    return ("trk", t.GetLayer(), min(a, b), max(a, b), t.GetWidth(), t.GetNetname())


def rects():
    out = []
    for r in csv.reader(open(os.path.join(ROOT, "lib", "v5_copper.csv"))):
        if r and r[0] == "unrouted":
            out.append(tuple(float(v) for v in r[2:6]))
    return out


def inside(rs, x, y, m=0.0):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, y0, x1, y1 in rs)


def pts(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return [(T(t.GetPosition().x), -T(t.GetPosition().y))]
    return [(T(t.GetStart().x), -T(t.GetStart().y)), (T(t.GetEnd().x), -T(t.GetEnd().y))]


def gap(sa, sb, lo=0.0, hi=2.5):
    for _ in range(12):
        mid = (lo + hi) / 2
        if sa.Collide(sb, F(mid)):
            hi = mid
        else:
            lo = mid
    return hi


def main():
    placed, routed = pcbnew.LoadBoard(sys.argv[1]), pcbnew.LoadBoard(sys.argv[2])
    old = collections.Counter(key(t) for t in placed.GetTracks())
    seen = collections.Counter()
    new = []
    for t in routed.GetTracks():
        k = key(t)
        seen[k] += 1
        if seen[k] > old.get(k, 0):
            new.append(t)
    missing = sum((old - seen).values())
    print(f"1. existing tracks/vias missing or changed: {missing}")
    for k in list((old - seen))[:10]:
        print("     ", k[0], k[-1], [round(T(v), 2) if isinstance(v, int) else v for v in k[1:-1]][:4])
    ur = rects()
    out54, out553 = [], []
    for t in new:
        for x, y in pts(t):
            if not inside(ur, x, y, 0.01):
                (out553 if not (y <= 55.3 and inside([(r[0], r[1], r[2], 55.3) for r in ur if r[3] == 54.0], x, y)) else out54).append((t, x, y))
    for name, lst in (("outside the unrouted rectangles but inside the brief's passage (y 54..55.3)", out54),
                      ("outside the unrouted rectangles", out553)):
        nets = collections.Counter(t.GetNetname() for t, _, _ in lst)
        print(f"2. new copper {name}: {len(lst)} ends on {len(nets)} nets {dict(nets) if nets else ''}")
        for t, x, y in lst[:6] if "passage" not in name else []:
            print(f"      {t.GetNetname()} {routed.GetLayerName(t.GetLayer())} ({x:.2f}, {y:.2f})")
    bad = collections.Counter()
    busp = []
    for ref in ("BUSP1", "BUSN1", "BUSP2", "BUSN2"):
        pad = list(routed.FindFootprintByReference(ref).Pads())[0]
        busp.append((pad, pad.GetNetname()))
    for t in new:
        ln = routed.GetLayerName(t.GetLayer())
        via = t.Type() == pcbnew.PCB_VIA_T
        for x, y in pts(t):
            if not via and ln in ("In1.Cu", "In2.Cu", "In4.Cu") and inside(CARD_PLANES, x, y):
                bad[f"track on plane layer {ln} in the card area: {t.GetNetname()}"] += 1
            if (via or ln in ("F.Cu", "B.Cu")) and inside([BUS_BAND], x, y):
                bad[f"F/B copper or via in the DC bus band: {t.GetNetname()}"] += 1
            if (via or ln in ("F.Cu", "B.Cu")) and inside([PASSAGE], x, y):
                bad[f"F/B copper or via in the passage north of J11: {t.GetNetname()}"] += 1
        if via or ln in ("F.Cu", "B.Cu"):
            for pad, net in busp:
                lay = pcbnew.F_Cu if via else t.GetLayer()
                if t.GetNetname() != net and t.GetEffectiveShape(lay).Collide(pad.GetEffectiveShape(lay), F(2.5)):
                    bad[f"within 2.5 mm of bus wire pad {pad.GetParentFootprint().GetReference()}: {t.GetNetname()}"] += 1
    print(f"3. rule 2 / 3 / 3a / plane-layer findings: {sum(bad.values())}")
    for k, v in bad.items():
        print(f"      {v} x {k}")
    # 4. HV spacing on the outer layers
    newset = {id(t) for t in new}
    viol, hvhv = [], []
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        items = []      # (net, shape, bbox, is_new, required or None, label)
        for t in routed.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == lay:
                items.append((t.GetNetname(), t.GetEffectiveShape(lay), t.GetBoundingBox(), id(t) in newset, None,
                              "via" if t.Type() == pcbnew.PCB_VIA_T else "track"))
        for fp in routed.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(lay) and p.GetNetname():
                    lc = p.GetLocalClearance()
                    items.append((p.GetNetname(), p.GetEffectiveShape(lay), p.GetBoundingBox(), False,
                                  T(lc) if lc else None, f"pad {fp.GetReference()}-{p.GetNumber()}"))
        zones = [(z.GetNetname(), z.GetFilledPolysList(lay), z.GetBoundingBox(), z.GetZoneName())
                 for z in routed.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(lay)]
        hv = [i for i in items if i[0] in HV]
        for a in hv:
            box = a[2].GetInflated(F(2.6)) if hasattr(a[2], "GetInflated") else a[2]
            if not hasattr(a[2], "GetInflated"):
                box.Inflate(F(2.6))
            for b in items:
                if b[0] == a[0] or not (a[3] or b[3]) or not box.Intersects(b[2]):
                    continue
                if b[0] in HV and b[0] < a[0]:
                    continue        # each HV-HV pair once
                req = min(v for v in (a[4], b[4], 2.5) if v)
                if a[1].Collide(b[1], F(req - 0.005)):
                    c = a[2].Centre()
                    (hvhv if b[0] in HV else viol).append((routed.GetLayerName(lay), a[0], a[5], b[0], b[5], req,
                                                           gap(a[1], b[1], 0, req), T(c.x), -T(c.y)))
            if a[3]:
                for net, fill, zb, zname in zones:
                    if net != a[0] and box.Intersects(zb) and fill.OutlineCount() and fill.Collide(a[1], F(2.495)):
                        c = a[2].Centre()
                        viol.append((routed.GetLayerName(lay), a[0], a[5], net, "zone " + zname, 2.5, -1, T(c.x), -T(c.y)))
    for title, lst in (("4. high-voltage spacing violations, HV net to a non-HV net (2.5 mm on F.Cu / B.Cu, pairs with new copper)", viol),
                       ("4b. two different HV nets closer than 2.5 mm (pairs with new copper; the placement puts their pads"
                        " 1.0 .. 2.0 mm apart, the router kept 1.0 mm between HV nets)", hvhv)):
        print(f"{title}: {len(lst)}")
        agg = collections.defaultdict(list)
        for v in lst:
            agg[(v[0], v[1], v[3])].append(v)
        for (ln, na, nb), vs in sorted(agg.items()):
            w = min(vs, key=lambda v: v[6])
            print(f"      {ln} {na} <-> {nb}: {len(vs)} items, worst {w[6]:.2f} mm (need {w[5]}) {w[2]} / {w[4]} at ({w[7]:.1f}, {w[8]:.1f})")
    # 5. numbers
    power = set(GROUPS["supply"]) | {"DC+", "PGND", "ISODC+", "ISOPGND"}
    vias = [t for t in new if t.Type() == pcbnew.PCB_VIA_T]
    length = collections.Counter()
    for t in new:
        if t.Type() != pcbnew.PCB_VIA_T:
            length[routed.GetLayerName(t.GetLayer())] += T(t.GetLength())
    print(f"5. new vias: {len(vias)} ({sum(1 for v in vias if v.GetNetname() not in power)} signal); new track mm per layer: "
          + ", ".join(f"{k} {v:.0f}" for k, v in sorted(length.items())))
    if len(sys.argv) > 3:
        d = json.load(open(sys.argv[3]))
        opens = collections.Counter()
        for u in d.get("unconnected_items", []):
            m = re.search(r"\[([^\]]+)\]", u["items"][0]["description"])
            opens[m.group(1) if m else "?"] += 1
        order = ["passage", "sdm_rest", "pwm_rest", "taps_rest", "other", "j11_top", "j11_bot", "ctrl_analog", "buck", "primary",
                 "aux_hv", "aux_lv", "aux_iso", "supply_C", "supply_I", "supply_P"]
        done = set()
        print(f"   open connections: {sum(opens.values())} on {len(opens)} nets")
        for g in order:
            ns = {n: opens[n] for n in GROUPS[g] if opens.get(n)}
            done |= set(GROUPS[g])
            print(f"      {g:12s} {sum(ns.values()):3d} open on {len(ns):2d}/{len(GROUPS[g])} nets  " + " ".join(f"{n}:{c}" for n, c in ns.items()))
        rest = {n: c for n, c in opens.items() if n not in done}
        print(f"      {'(not in scope)':12s} {sum(rest.values()):3d}  " + " ".join(f"{n}:{c}" for n, c in rest.items()))


main()
