#!/usr/bin/env python3
"""Routing chain step 07 (kipy): a via with a short stub next to every SMD pad of a plane net that lies inside its
plane and has no track yet (as the v5 pass-7 helper scripted.py planes); a same-net via within 1.2 mm is shared.

  kipy 07_planes.py IN OUT

Plane nets: the card-area planes on In1 / In2 / In4 (CTRLGND_A, 3V3_CTRL, CTRLGND, 5V_CTRL, ISOGND, 3V3_ISO, GND,
VCC) and the v6 In4 strips (GND primary, ISOGND ISO). Vias may perforate the other planes (the refill makes the
antipads); every via and stub is tested by geo.Ctx. Prints per net: vias made, pads on a shared via, pads left.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import F, T, P, xy  # noqa: E402
from drawlib import ring  # noqa: E402

PLANE_NETS = ["CTRLGND_A", "3V3_CTRL", "CTRLGND", "5V_CTRL", "ISOGND", "3V3_ISO", "GND", "VCC"]
PLANE_LAYERS = (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In4_Cu)


def main():
    src, dst = sys.argv[1:3]
    b = pcbnew.LoadBoard(src)
    cx = geo.Ctx(b)
    cx.via_pierce = set(PLANE_NETS)
    fills = {}
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() not in PLANE_NETS:
            continue
        for l in PLANE_LAYERS:
            if z.IsOnLayer(l) and z.GetFilledPolysList(l).OutlineCount():
                fills.setdefault(z.GetNetname(), []).append(z.GetFilledPolysList(l))
    tracks = {}
    for t in b.GetTracks():
        tracks.setdefault(t.GetNetname(), []).append(t)
    total = 0
    for net in PLANE_NETS:
        fs = fills.get(net, [])

        def inplane(x, y, fs=fs):      # a via there lands in the fill with margin (not on its edge)
            return any(all(f.Contains(P(x + dx, y + dy)) for dx, dy in ((0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45))) for f in fs)
        done = shared = 0
        left = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() != net or p.HasHole():
                    continue
                x, y = xy(p.GetPosition())
                if not any(f.Contains(P(x, y)) for f in fs):
                    continue
                layer = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
                ps = p.GetEffectiveShape(layer)
                if any((t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == layer) and ps.Collide(t.GetEffectiveShape(layer), 0)
                       for t in tracks.get(net, [])):
                    continue
                s = p.GetSize(layer)
                smin = min(T(s.x), T(s.y))
                w = min(0.4, max(0.2, smin))
                hit = None
                for o in tracks.get(net, []):
                    if o.Type() == pcbnew.PCB_VIA_T:
                        vx, vy = xy(o.GetPosition())
                        d = math.hypot(vx - x, vy - y)
                        if d <= 1.2 and inplane(vx, vy):
                            t = cx.mktrack(net, layer, (x, y), (vx, vy), w)
                            if cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
                                hit = t
                                break
                if hit:
                    cx.commit(hit)
                    tracks[net].append(hit)
                    shared += 1
                    continue
                r0 = smin / 2 + geo.VIA / 2 + 0.06
                ok = False
                for vx, vy, r in ring(x, y, r0, 2.0, n=24):
                    if not inplane(vx, vy):
                        continue
                    v = cx.via_ok(net, vx, vy)
                    if v is None or ps.Collide(v.GetEffectiveShape(layer), F(0.03)):
                        continue
                    t = cx.mktrack(net, layer, (x, y), (vx, vy), w)
                    if not cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
                        continue
                    cx.commit(t, v)
                    tracks.setdefault(net, []).extend([t, v])
                    ok = True
                    break
                if ok:
                    done += 1
                else:
                    left.append(f"{fp.GetReference()}-{p.GetNumber()}")
        total += done
        print(f"planes: {net}: {done} vias, {shared} pads on a shared via, {len(left)} left" +
              (": " + ", ".join(left[:20]) if left else ""))
    print(f"planes: {total} vias in all")
    b.Save(dst)


if __name__ == "__main__":
    main()
