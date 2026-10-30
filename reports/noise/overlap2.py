"""Copper of 'victim' nets vs 'aggressor' nets: overlap area on adjacent layers (parallel-plate
coupling) and same-layer proximity. Output: TSV lines."""
import pcbnew, re, sys, json
b = pcbnew.LoadBoard("/home/jari/dev/ac_psu_kicad/kicad/ac_psu.kicad_pcb")
F, T = pcbnew.FromMM, pcbnew.ToMM
LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LN = {pcbnew.F_Cu: "F", pcbnew.In1_Cu: "In1", pcbnew.In2_Cu: "In2", pcbnew.B_Cu: "B"}
ERR = F(0.005)

def copper(netpred):
    out = {}
    def add(net, L, setter):
        ps = out.setdefault(net, {}).setdefault(L, pcbnew.SHAPE_POLY_SET())
        setter(ps)
    for t in b.GetTracks():
        n = t.GetNetname()
        if not netpred(n): continue
        for L in LAYERS:
            if t.IsOnLayer(L):
                add(n, L, lambda ps: t.TransformShapeToPolygon(ps, L, 0, ERR, pcbnew.ERROR_INSIDE))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            n = p.GetNetname()
            if not netpred(n): continue
            for L in LAYERS:
                if p.IsOnLayer(L) and p.FlashLayer(L):
                    add(n, L, lambda ps: p.TransformShapeToPolygon(ps, L, 0, ERR, pcbnew.ERROR_INSIDE))
    for z in b.Zones():
        if z.GetIsRuleArea(): continue
        n = z.GetNetname()
        if not netpred(n): continue
        for L in LAYERS:
            if z.IsOnLayer(L):
                fp_ = z.GetFilledPolysList(L)
                add(n, L, lambda ps: ps.Append(fp_))
    for n in out:
        for L in out[n]:
            out[n][L].Simplify()
    return out

victims_re = re.compile(sys.argv[1])
aggr_re = re.compile(sys.argv[2])
V = copper(lambda n: bool(victims_re.search(n)))
A = copper(lambda n: bool(aggr_re.search(n)))
res = []
for vn, vl in V.items():
    for L, vps in vl.items():
        va = vps.Area() / 1e12
        bb = vps.BBox()
        res.append(("AREA", vn, LN[L], round(va, 2), round(T(bb.Centre().x), 1), round(-T(bb.Centre().y), 1)))
        idx = LAYERS.index(L)
        for an, al in A.items():
            if an == vn: continue
            for L2 in [LAYERS[i] for i in (idx - 1, idx + 1) if 0 <= i < 4]:
                if L2 not in al: continue
                x = pcbnew.SHAPE_POLY_SET(vps); x.BooleanIntersection(al[L2])
                ar = x.Area() / 1e12
                if ar > 0.05:
                    c = x.BBox().Centre()
                    res.append(("OVL", vn, LN[L], an, LN[L2], round(ar, 2), round(T(c.x), 1), round(-T(c.y), 1)))
            for L3 in [L] + [LAYERS[i] for i in (LAYERS.index(L)-1, LAYERS.index(L)+1) if 0 <= i < 4]:
              if L3 not in al: continue
              for d in (0.3, 0.6, 1.0, 2.0, 3.0, 5.0, 8.0):
                    g = pcbnew.SHAPE_POLY_SET(vps); g.Inflate(F(d), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, ERR)
                    g.BooleanIntersection(al[L3])
                    if g.Area() > 0:
                        c = g.BBox().Centre()
                        res.append(("NEAR", vn, LN[L], an, LN[L3], d, round(g.Area()/1e12, 3), round(T(c.x), 1), round(-T(c.y), 1)))
                        break
for r in res:
    print("\t".join(str(x) for x in r))
