"""For a pad of a plane net that got no via: the nearest place where a via into its plane is legal, and whether a
straight stub from the pad reaches it (run under kipy; draws nothing).

  kipy near_via.py BOARD REF-PAD [REF-PAD ...]
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
    outs = [z.Outline() for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == net
            and any(z.IsOnLayer(l) for l in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In4_Cu))]
    first = with_stub = None
    for vx, vy, r in S.ring(x, y, 0.5, 8.0, 0.1, 36):
        if not any(o.Contains(S.P(vx, vy)) for o in outs):
            continue
        v = cx.via_ok(net, vx, vy)
        if v is None:
            continue
        first = first or (vx, vy, r)
        t = cx.mktrack(net, layer, (x, y), (vx, vy), min(0.4, max(0.2, smin)))
        if cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
            with_stub = (vx, vy, r)
            break
    print(f"{ref}-{num} {net} at ({x:.2f}, {y:.2f}) on {b.GetLayerName(layer)}: "
          + (f"nearest legal via site ({first[0]:.2f}, {first[1]:.2f}), {first[2]:.2f} mm from the pad" if first else "no legal via site within 8 mm")
          + ("" if not first else (f"; nearest with a clear straight stub ({with_stub[0]:.2f}, {with_stub[1]:.2f}), {with_stub[2]:.2f} mm"
                                   if with_stub else "; no site within 8 mm has a clear straight stub from the pad")))
    if first and not with_stub:
        t = cx.mktrack(net, layer, (x, y), (first[0], first[1]), min(0.4, max(0.2, smin)))
        sh = t.GetEffectiveShape(layer)
        blk = []
        for o in cx.items[layer]:
            if o[0] != net and sh.Collide(o[1], pcbnew.FromMM(cx.need(net, layer, o))):
                c = o[2].Centre()
                blk.append(f"{o[3]} {o[5]} [{o[0]}] at ({T(c.x):.1f}, {-T(c.y):.1f})")
        for outline, kb, notr, novia in cx.keep[layer]:
            if notr and outline.Collide(sh, pcbnew.FromMM(0.05)):
                blk.append("a keep-out rule area")
        for znet, fill, zb, z in cx.zones[layer]:
            if znet != net and fill.OutlineCount() and fill.Collide(sh, pcbnew.FromMM(0.25)):
                blk.append(f"pour [{znet}]")
        print("   the stub to the nearest site is blocked by: " + "; ".join(sorted(set(blk))[:6]))
