#!/usr/bin/env python3
"""Lock / fence helpers of the v6 routing chain (kipy; IPC frame, y up).

  kipy fence.py lock IN OUT          lock every track and via (KRT never rips locked copper)
  kipy fence.py domain IN OUT D      replace the temporary domain fence by the one of domain D (P / I / C)
  kipy fence.py clear IN OUT         remove every temporary keep-out ("tmp route ...")

The router does not know the 5 mm class rules between the domains, and the barrier strips stop it only where they
are drawn. Each router step gets the fence of its domain: keep-outs (tracks and vias) over the other domains' land.
v6 land (tools/v4/domains.py on the board): west of the card area the inverter DC link and output filter are I
(pads y >= -6.5, pours down to y -10.1), the AFE is P (pads y <= -15.8, pours up to y -12.9); the card area as in
v5 (C|P line y 8.3, P|I line x 88, the ISO aux area IA x 88..97.5, y -48..-25.5).
Also: no tracks on In1 / In2 / In4 inside the card-area planes and the aux GND pours (vias allowed).
"""
import sys

import pcbnew

F = pcbnew.FromMM
TMP = "tmp route "
AL = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
DOMAIN_FENCES = {
    # an I step: keep out of the AFE (west, y < -7.9 = 5 mm above the highest P pour), the primary card area and
    # the aux primary side PX, and south of IA (U9 / 15V / J23 band)
    "I": [(-130, -90, 41.9, -7.9), (41.9, -90, 88.0, 8.3), (88.0, -90, 125, -48.0)],
    # a P step: keep out of the west ISO land (y > -15.1 = 5 mm below the lowest I pour), the card area north of the
    # C|P line, and the ISO / CTRL column east of x 88 down to y -53 (IA ends at -48)
    "P": [(-130, -15.1, 41.9, 80), (41.9, 8.3, 125, 80), (88.0, -53.0, 125, 8.3)],
    # a C step: the two CTRL pieces are ringed by barrier strips; fence everything outside them
    "C": [(-130, -90, 41.9, 80), (41.9, -90, 125, -37.0), (41.9, 48.6, 125, 80), (41.9, -37.0, 102.0, 8.3)],
}
# the two current-sense blocks with U29 / U30 (planning update 2026-11-24: routed last, in steps that can be dropped):
# fenced for every step before those
GROUPS = [(-46.0, -84.5, -17.0, -42.0), (-104.0, 38.0, -54.0, 71.8)]   # U30 at (-58.25, 56.9) since step 4d
PLANES = [(44.4, 10.8, 95.1, 33.0), (58.9, -9.4, 118.1, 48.8), (102.5, -34.5, 118.1, 3.0), (42.5, -20.7, 85.5, 5.8),
          (67.0, -54.6, 82.9, -4.2)]


def keepout(b, name, r, layers, vias=True, tracks=True, prefix=TMP):
    x0, y0, x1, y1 = r
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(prefix + name)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(b.GetLayerID(l))
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(F(x), F(-y))
    b.Add(z)


def pour_vias(b, nets):
    """The router lays vias inside other nets' pours on the other layers and splits them (v5 pass 3, v6 pass 1 try 1:
    the ISOGND step split the ISO lane on F.Cu, an HV pour on F.Cu and two more): every filled pour of a net that
    the step does not route becomes a keep-out for vias (its fill polygons with their holes, on its own layer).
    The planes of the card areas on In1 / In2 / In4 are left out: a via there only perforates them."""
    import sys as _s
    _s.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    n = 0
    zs = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() not in nets]
    for z in zs:
        for l in z.GetLayerSet().Seq():
            name = b.GetLayerName(l)
            if name in ("In1.Cu", "In2.Cu", "In4.Cu") and not z.GetZoneName().startswith("v6 bus"):
                continue
            fill = z.GetFilledPolysList(l)
            if not fill.OutlineCount():
                continue
            k = pcbnew.ZONE(b)
            k.SetIsRuleArea(True)
            k.SetZoneName(TMP + "pour " + (z.GetZoneName() or z.GetNetname()))
            k.SetDoNotAllowTracks(False)
            k.SetDoNotAllowVias(True)
            k.SetDoNotAllowZoneFills(False)
            k.SetDoNotAllowPads(False)
            k.SetDoNotAllowFootprints(False)
            ls = pcbnew.LSET()
            ls.AddLayer(l)
            k.SetLayerSet(ls)
            o = k.Outline()
            for i in range(fill.OutlineCount()):
                o.NewOutline()
                ch = fill.Outline(i)
                for j in range(ch.PointCount()):
                    p = ch.CPoint(j)
                    o.Append(p.x, p.y)
                for h in range(fill.HoleCount(i)):
                    o.NewHole()
                    hc = fill.Hole(i, h)
                    for j in range(hc.PointCount()):
                        p = hc.CPoint(j)
                        o.Append(p.x, p.y, -1, h)
            b.Add(k)
            n += 1
    return n


def clear(b, prefix=TMP):
    zs = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith(prefix)]
    for z in zs:
        b.Delete(z)
    return len(zs)


def main():
    mode, src, dst = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    if mode == "lock":
        n = 0
        for t in b.GetTracks():
            if not t.IsLocked():
                t.SetLocked(True)
                n += 1
        print(f"lock: {n} tracks / vias locked")
    elif mode == "domain":
        d = sys.argv[4]
        nets = set(sys.argv[5].split(",")) if len(sys.argv) > 5 else set()
        late = len(sys.argv) > 6 and sys.argv[6] == "late"
        clear(b)
        for i, r in enumerate(DOMAIN_FENCES[d]):
            keepout(b, f"domain {d} {i}", r, AL)
        for i, r in enumerate(PLANES):
            keepout(b, f"planes {i}", r, ["In1.Cu", "In2.Cu", "In4.Cu"], vias=False)
        if not late:
            for i, r in enumerate(GROUPS):
                keepout(b, f"sense group {i}", r, AL)
        print(f"domain: {pour_vias(b, nets)} via keep-outs over pours")
    elif mode == "clear":
        print(f"clear: {clear(b)} temporary keep-outs removed")
    b.Save(dst)


if __name__ == "__main__":
    main()
