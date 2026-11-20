"""For pads in the aux area that are still alone: the nearest copper of the net and what stands in the way of a
straight link under the per-pad HV rule of scripted.Ctx.need (run under kipy; draws nothing).

  kipy aux_report.py BOARD REF-PAD [REF-PAD ...]
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scripted as S  # noqa: E402

T = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
cx = S.Ctx(b)
S.MARGIN = 0.02
for arg in sys.argv[2:]:
    ref, num = arg.split("-")
    pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
    net = pad.GetNetname()
    _, x, y, layer, smin, smax = S.pad_info(pad)
    ln = b.GetLayerName(layer)
    cand = []
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            cand.append((T(t.GetPosition().x), -T(t.GetPosition().y), "via"))
        else:
            for q in (t.GetStart(), t.GetEnd()):
                cand.append((T(q.x), -T(q.y), "track end on " + b.GetLayerName(t.GetLayer())))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and (fp.GetReference(), p.GetNumber()) != (ref, num):
                lay = "through" if p.HasHole() else ("B.Cu" if fp.IsFlipped() else "F.Cu")
                cand.append((T(p.GetPosition().x), -T(p.GetPosition().y), f"pad {fp.GetReference()}-{p.GetNumber()} {lay}"))
    cand = sorted((math.hypot(cx_ - x, cy_ - y), cx_, cy_, what) for cx_, cy_, what in cand if math.hypot(cx_ - x, cy_ - y) > 0.2)
    same = [c for c in cand if c[3] == "via" or ln in c[3] or "through" in c[3]]
    print(f"{ref}-{num} {net} at ({x:.2f}, {y:.2f}) on {ln}:")
    for d, tx, ty, what in (same[:2] if same else cand[:2]):
        t = cx.mktrack(net, layer, (x, y), (tx, ty), min(0.3, smin))
        sh = t.GetEffectiveShape(layer)
        blk = []
        for o in cx.items[layer]:
            if o[0] != net and sh.Collide(o[1], pcbnew.FromMM(cx.need(net, layer, o))):
                c = o[2].Centre()
                blk.append(f"{o[3]} {o[5]} [{o[0]}] at ({T(c.x):.1f}, {-T(c.y):.1f}) needs {cx.need(net, layer, o) - 0.02:.2f} mm, has {S.gap(sh, o[1]):.2f}")
        for znet, fill, zb, z in cx.zones[layer]:
            if znet != net and fill.OutlineCount() and fill.Collide(sh, pcbnew.FromMM(2.5 if ((net in S.HV) != (znet in S.HV)) else 0.25)):
                blk.append(f"pour [{znet}]")
        print(f"   nearest reachable on its layer: {what} at ({tx:.2f}, {ty:.2f}), {d:.2f} mm; straight link "
              + ("is free" if not blk else "blocked by: " + "; ".join(blk[:5])))
