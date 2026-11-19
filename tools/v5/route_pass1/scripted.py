"""Scripted copper of the routing pass that the router is bad at (run under tools/p2k/bin/kipy; IPC frame, y up).

  kipy scripted.py taps IN OUT      one via with a short F.Cu / B.Cu stub at each of the six divider-tap nets of the
                                    U7 / U2 block (the In3 run from the west ends there)
  kipy scripted.py hvstubs IN OUT   escape stubs at pads of the high-voltage aux nets that have low-voltage copper
                                    closer than 2.5 mm (the router keeps a flat 2.5 mm around low-voltage copper
                                    and could not leave such a pad). Reading of "2.5 mm, pads as listed": the
                                    stub never comes closer to that copper than the pad itself is (the pad gap is
                                    the placement's, kept by the pad clearances of card_layout.HV_PADS), keeps
                                    2.5 mm to everything else, and ends where 2.5 mm holds all round
  kipy scripted.py planes IN OUT    a via with a stub next to every SMD pad of a plane net that lies inside its
                                    plane and has no track yet (brief rule 7); a same-net via in reach is shared

Every piece is tested against the copper of the board (pads with their own clearance, tracks, vias, pours of other
nets, keep-out rule areas) before it is added; a pad for which nothing fits is reported and left alone.
Clearances: 0.15 mm (+0.02 margin); HV net to another net on F.Cu / B.Cu 2.5 mm, pads as listed; two HV nets 1.0 mm.
"""
import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
F, T = pcbnew.FromMM, pcbnew.ToMM
HV = set(json.load(open(os.path.join(HERE, "hv_clearances.json"))))
CLR, MARGIN, VIA, DRILL = 0.15, 0.02, 0.4572, 0.3
TAPS = ["Net-(U2-+)", "Net-(U2--)", "Net-(U7A-+)", "Net-(U7A--)", "Net-(U7B-+)", "Net-(U7B--)"]
PLANE_NETS = ["CTRLGND_A", "3V3_CTRL", "CTRLGND", "5V_CTRL", "ISOGND", "3V3_ISO", "GND", "VCC"]
SCOPE = (38.0, -36.0, 119.0, 50.0)      # the card area: plane vias only here
OUTER = (pcbnew.F_Cu, pcbnew.B_Cu)


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


class Ctx:
    def __init__(self, b):
        self.b = b
        self.layers = [l for l in b.GetEnabledLayers().CuStack()]
        self.items = {l: [] for l in self.layers}       # (net, shape, bbox, kind, local clearance mm or 0, ref)
        self.zones = {l: [] for l in self.layers}
        self.keep = {l: [] for l in self.layers}        # (outline, bbox, no tracks, no vias)
        self.keepobj = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                for l in self.layers:
                    if p.IsOnLayer(l):
                        lc = p.GetLocalClearance()
                        self.items[l].append((p.GetNetname(), p.GetEffectiveShape(l), p.GetBoundingBox(), "pad",
                                              T(lc) if lc else 0.0, fp.GetReference()))
        for t in b.GetTracks():
            self.add_track(t)
        for z in b.Zones():
            for l in self.layers:
                if not z.IsOnLayer(l):
                    continue
                if z.GetIsRuleArea():
                    if z.GetZoneName().startswith("tmp route domain"):
                        continue                            # the fence of the last router step's domain
                    self.keep[l].append((z.Outline(), z.GetBoundingBox(), z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))
                    self.keepobj.append(z)
                else:
                    self.zones[l].append((z.GetNetname(), z.GetFilledPolysList(l), z.GetBoundingBox(), z))

    def add_track(self, t):
        if t.Type() == pcbnew.PCB_VIA_T:
            for l in self.layers:
                self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "via", 0.0, ""))
        else:
            l = t.GetLayer()
            self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "track", 0.0, ""))

    def need(self, net, layer, o, override=None):
        """Clearance a new piece of `net` needs to the obstacle o on this layer."""
        onet, _, _, kind, lc, ref = o
        if override and id(o) in override:
            return override[id(o)]
        if not onet:
            return 0.25 + MARGIN                           # hole or pad without a net
        c = max(CLR, lc)                                   # a pad's own clearance always holds (DRC)
        if layer in OUTER and ((net in HV) != (onet in HV)):
            c = lc if (kind == "pad" and lc and onet in HV) else 2.5      # HV pad: as listed in HV_PADS
        elif layer in OUTER and net in HV and onet in HV:
            c = max(1.0, lc)
        return c + MARGIN

    def clear(self, net, shape, bbox, layer, is_via=False, override=None, same_net_too=False, extra=0.0):
        box = pcbnew.BOX2I(bbox.GetPosition(), bbox.GetSize())
        box.Inflate(F(2.6 + extra))
        for o in self.items[layer]:
            if not box.Intersects(o[2]):
                continue
            if o[0] == net and o[0]:
                if same_net_too and o[3] != "track" and shape.Collide(o[1], F(CLR)):
                    return False
                continue
            ex = extra if (o[0] and (net in HV) != (o[0] in HV)) else 0.0
            if shape.Collide(o[1], F(max(self.need(net, layer, o, override), ex))):
                return False
        for znet, fill, zb, _ in self.zones[layer] if layer in OUTER else ():     # inner planes: the refill makes the antipad
            if znet != net and box.Intersects(zb) and fill.OutlineCount():
                c = max(2.5 if (layer in OUTER and ((net in HV) != (znet in HV))) else 0.25, extra)
                if fill.Collide(shape, F(c)):
                    return False
        for outline, kb, notr, novia in self.keep[layer]:
            if (novia if is_via else notr) and box.Intersects(kb) and outline.Collide(shape, F(0.05)):
                return False
        return True

    def via_ok(self, net, x, y, extra_outer=0.0):
        v = self.mkvia(net, x, y)
        for l in self.layers:
            if not self.clear(net, v.GetEffectiveShape(l), v.GetBoundingBox(), l, is_via=True, same_net_too=True,
                              extra=extra_outer if l in OUTER else 0.0):
                return None
        return v

    def mkvia(self, net, x, y):
        v = pcbnew.PCB_VIA(self.b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(P(x, y))
        v.SetWidth(pcbnew.F_Cu, F(VIA))
        v.SetDrill(F(DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNetCode(self.b.GetNetcodeFromNetname(net))
        return v

    def mktrack(self, net, layer, a, c, w):
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(P(*a))
        t.SetEnd(P(*c))
        t.SetWidth(F(w))
        t.SetLayer(layer)
        t.SetNetCode(self.b.GetNetcodeFromNetname(net))
        return t

    def commit(self, *objs):
        for o in objs:
            o.SetLocked(True)
            self.b.Add(o)
            self.add_track(o)


def pad_info(p):
    fp = p.GetParentFootprint()
    c = p.GetPosition()
    layer = pcbnew.B_Cu if (fp.IsFlipped() and not p.HasHole()) else pcbnew.F_Cu
    s = p.GetSize(layer)
    return fp.GetReference(), T(c.x), -T(c.y), layer, min(T(s.x), T(s.y)), max(T(s.x), T(s.y))


def ring(x, y, r0, r1, step=0.1, n=24):
    r = r0
    while r <= r1 + 1e-9:
        for k in range(n):
            a = 2 * math.pi * k / n
            yield x + r * math.cos(a), y + r * math.sin(a), r
        r += step


def via_at_pad(cx, p, net, rmax, width, in_zone=None):
    """Nearest legal via + straight stub for pad p. Returns distance or None."""
    ref, x, y, layer, smin, smax = pad_info(p)
    w = min(width, max(0.152, smin))
    for vx, vy, r in ring(x, y, smin / 2 + VIA / 2 + 0.06, rmax):
        if in_zone and not in_zone(vx, vy):
            continue
        v = cx.via_ok(net, vx, vy)
        if v is None:
            continue
        if p.GetEffectiveShape(layer).Collide(v.GetEffectiveShape(layer), F(0.03)):
            continue                                        # no via in the pad
        t = cx.mktrack(net, layer, (x, y), (vx, vy), w)
        if not cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
            continue
        cx.commit(t, v)
        return r
    return None


def taps(b, cx):
    for net in TAPS:
        best = None
        pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == net and not p.HasHole()
                and T(p.GetPosition().x) > 90]
        # the op-amp pin first, then its R / C
        pads.sort(key=lambda p: (not p.GetParentFootprint().GetReference().startswith("U"),))
        for p in pads:
            r = via_at_pad(cx, p, net, 2.5, 0.2)
            if r is not None:
                ref, x, y = pad_info(p)[:3]
                best = f"{ref}-{p.GetNumber()} ({x:.1f}, {y:.1f}), via {r:.2f} mm from the pad centre"
                break
        print(f"taps: {net}: {best or 'NO PLACE for a via within 2.5 mm of any pad of the block'}")


def planes(b, cx):
    x0, y0, x1, y1 = SCOPE
    zones = {}
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() not in PLANE_NETS:
            continue
        if any(z.IsOnLayer(l) for l in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In4_Cu)):
            bb = z.GetBoundingBox()
            if T(bb.GetRight()) > x0 and T(bb.GetLeft()) < x1 and -T(bb.GetTop()) > y0 and -T(bb.GetBottom()) < y1:
                zones.setdefault(z.GetNetname(), []).append(z.Outline())
    ends = {}
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T:
            ends.setdefault(t.GetNetname(), []).append(t)
    stat = {}
    for net in PLANE_NETS:
        outs = zones.get(net, [])

        def inz(x, y, outs=outs):
            return any(all(o.Contains(P(x + dx, y + dy)) for dx, dy in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))) for o in outs)
        done = shared = 0
        failed, dist = [], []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() != net or p.HasHole():
                    continue
                ref, x, y, layer, smin, smax = pad_info(p)
                if not (x0 <= x <= x1 and y0 <= y <= y1) or not any(o.Contains(P(x, y)) for o in outs):
                    continue
                ps = p.GetEffectiveShape(layer)
                if any(t.GetLayer() == layer and ps.Collide(t.GetEffectiveShape(layer), 0) for t in ends.get(net, [])):
                    continue                                # has a track already
                w = min(0.4, max(0.2, smin))
                # a same-net via in reach (decoupling capacitor next to the pin): share it
                hit = None
                for o in b.GetTracks():
                    if o.Type() == pcbnew.PCB_VIA_T and o.GetNetname() == net:
                        vx, vy = T(o.GetPosition().x), -T(o.GetPosition().y)
                        d = math.hypot(vx - x, vy - y)
                        if d <= 1.2 and inz(vx, vy):
                            t = cx.mktrack(net, layer, (x, y), (vx, vy), w)
                            if cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
                                hit = (d, t)
                                break
                if hit:
                    cx.commit(hit[1])
                    ends.setdefault(net, []).append(hit[1])
                    shared += 1
                    dist.append(hit[0])
                    continue
                r = via_at_pad(cx, p, net, 2.0, w, inz)
                if r is None:
                    failed.append(f"{ref}-{p.GetNumber()} ({x:.1f}, {y:.1f})")
                else:
                    done += 1
                    dist.append(r)
        stat[net] = (done, shared, failed)
        far = sum(1 for d in dist if d > 1.0)
        print(f"planes: {net}: {done} vias, {shared} pads on a shared via, {far} farther than 1.0 mm, "
              f"{len(failed)} without a place" + (": " + ", ".join(failed) if failed else ""))


def gap(sa, sb, lo=0.0, hi=3.0):
    for _ in range(14):
        mid = (lo + hi) / 2
        if sa.Collide(sb, F(mid)):
            hi = mid
        else:
            lo = mid
    return lo


HVSTUB = ("AUX_VIN", "AUX_CLAMP", "AUX_DRAIN", "DC+")     # the chain nodes AUX_ST / AUX_LV route without


def hvstubs(b, cx):
    for fp in b.GetFootprints():
        for p in fp.Pads():
            net = p.GetNetname()
            if net not in HVSTUB:
                continue
            ref, x, y, layer, smin, smax = pad_info(p)
            if not (60 <= x <= 86 and -60 <= y <= 0):
                continue
            lc = p.GetLocalClearance()
            own_lc = T(lc) if lc else 0.0
            for lay in ((layer,) if not p.HasHole() else OUTER):
                ps = p.GetEffectiveShape(lay)
                off = [o for o in cx.items[lay] if o[0] and o[0] != net and o[0] not in HV and o[1].Collide(ps, F(2.5 + 0.45))]
                if not off:
                    continue
                foreign = [o for o in off if not (o[3] == "pad" and o[5] == ref)]
                # low-voltage copper that the placement already has closer than 2.5 mm to this pad: the stub may
                # not come closer to it than the pad itself is
                override = {id(o): max(CLR + MARGIN, min(2.5 + MARGIN, gap(ps, o[1]) - 0.01)) for o in off}
                w = min(0.6, smin)
                found = None
                for ex, ey, r in ring(x, y, smax / 2 + 0.3, 7.0, 0.25, 32):
                    t = cx.mktrack(net, lay, (x, y), (ex, ey), w)
                    if not cx.clear(net, t.GetEffectiveShape(lay), t.GetBoundingBox(), lay, override=override):
                        continue
                    tip = cx.mktrack(net, lay, (ex, ey), (ex + 0.001, ey), w)
                    # the router continues from the tip: 2.5 mm + its own margin must hold there without exceptions
                    if not cx.clear(net, tip.GetEffectiveShape(lay), tip.GetBoundingBox(), lay, extra=2.95):
                        continue
                    found = (t, r, ex, ey)
                    break
                names = sorted({f"{o[5]}[{o[0]}]" if o[3] == "pad" else f"{o[3]}[{o[0]}]" for o in off})
                if found:
                    cx.commit(found[0])
                    print(f"hvstubs: {ref}-{p.GetNumber()} {net} {b.GetLayerName(lay)}: stub {found[1]:.2f} mm to "
                          f"({found[2]:.2f}, {found[3]:.2f}); within 2.95 mm: {', '.join(names)[:120]}")
                    break
                print(f"hvstubs: {ref}-{p.GetNumber()} {net} {b.GetLayerName(lay)} ({x:.1f}, {y:.1f}): NO legal stub; "
                      f"within 2.95 mm: {', '.join(names)[:160]}"
                      + (f"; {len(foreign)} of them are not pads of {ref}" if foreign else ""))


def main():
    mode, src, dst = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    cx = Ctx(b)
    {"taps": taps, "planes": planes, "hvstubs": hvstubs}[mode](b, cx)
    b.Save(dst)


if __name__ == "__main__":
    main()
