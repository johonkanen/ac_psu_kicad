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
PLANES = [(44.4, 10.8, 95.1, 33.0), (58.9, -9.4, 118.1, 48.8), (102.5, -34.5, 118.1, 3.0), (42.5, -20.7, 85.5, 5.8),
          (67.0, -54.6, 82.9, -4.2)]


def keepout(b, name, r, layers, vias=True, tracks=True):
    x0, y0, x1, y1 = r
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(TMP + name)
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
        clear(b, TMP + "domain")
        clear(b, TMP + "planes")
        for i, r in enumerate(DOMAIN_FENCES[d]):
            keepout(b, f"domain {d} {i}", r, AL)
        for i, r in enumerate(PLANES):
            keepout(b, f"planes {i}", r, ["In1.Cu", "In2.Cu", "In4.Cu"], vias=False)
    elif mode == "clear":
        print(f"clear: {clear(b)} temporary keep-outs removed")
    b.Save(dst)


if __name__ == "__main__":
    main()
