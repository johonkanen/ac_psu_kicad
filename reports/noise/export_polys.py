"""kipy: export copper polygons (IPC frame, mm) of nets matching a regex -> JSON {net: {layer: [[ring...]...]}}"""
import pcbnew, re, sys, json
b = pcbnew.LoadBoard("/home/jari/dev/ac_psu_kicad/kicad/ac_psu.kicad_pcb")
F, T = pcbnew.FromMM, pcbnew.ToMM
LAYERS = {pcbnew.F_Cu: "F", pcbnew.In1_Cu: "In1", pcbnew.In2_Cu: "In2", pcbnew.B_Cu: "B"}
ERR = F(0.01)
rx = re.compile(sys.argv[1])
out = {}
def ps_for(n, L):
    return out.setdefault(n, {}).setdefault(L, pcbnew.SHAPE_POLY_SET())
for t in b.GetTracks():
    n = t.GetNetname()
    if rx.search(n):
        for L in LAYERS:
            if t.IsOnLayer(L): t.TransformShapeToPolygon(ps_for(n, L), L, 0, ERR, pcbnew.ERROR_INSIDE)
for fp in b.GetFootprints():
    for p in fp.Pads():
        n = p.GetNetname()
        if rx.search(n):
            for L in LAYERS:
                if p.IsOnLayer(L) and p.FlashLayer(L): p.TransformShapeToPolygon(ps_for(n, L), L, 0, ERR, pcbnew.ERROR_INSIDE)
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    n = z.GetNetname()
    if rx.search(n):
        for L in LAYERS:
            if z.IsOnLayer(L): ps_for(n, L).Append(z.GetFilledPolysList(L))
res = {}
for n, d in out.items():
    for L, ps in d.items():
        ps.Simplify()
        rings = []
        for i in range(ps.OutlineCount()):
            for ch in [ps.Outline(i)] + [ps.Hole(i, j) for j in range(ps.HoleCount(i))]:
                rings.append([(round(T(ch.CPoint(k).x), 3), round(-T(ch.CPoint(k).y), 3)) for k in range(ch.PointCount())])
        res.setdefault(n, {})[LAYERS[L]] = rings
refs = {}
for fp in b.GetFootprints():
    p = fp.GetPosition(); refs[fp.GetReference()] = (round(T(p.x), 2), round(-T(p.y), 2))
json.dump({"nets": res, "refs": refs}, open(sys.argv[2], "w"))
print("exported", len(res), "nets")
