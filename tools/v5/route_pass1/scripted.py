"""Scripted copper of the routing pass that the router is bad at (run under tools/p2k/bin/kipy; IPC frame, y up).

  kipy scripted.py taps IN OUT      one via with a short F.Cu / B.Cu stub at each of the six divider-tap nets of the
                                    U7 / U2 block (the In3 run from the west ends there)
  kipy scripted.py hvstubs IN OUT   escape stubs at pads of the high-voltage aux nets that have low-voltage copper
                                    closer than 2.5 mm (the router keeps a flat 2.5 mm around low-voltage copper
                                    and could not leave such a pad). Reading of "2.5 mm, pads as listed": the
                                    stub never comes closer to that copper than the pad itself is (the pad gap is
                                    the placement's, kept by the pad clearances of card_layout.HV_PADS), keeps
                                    2.5 mm to everything else, and ends where 2.5 mm holds all round
  kipy scripted.py bus IN OUT       the passage north of J11 as drawn lanes on In3 / In4 (see bus() below)
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
STRICT_POUR = False     # True (via_scan.py): keep the zone's own clearance to another net's pour, so that a refill
#                         does not move the pour edge at all. False: 0.25 mm; the pour then gives way by its own
#                         clearance, and check_pass.py compares the islands of every pour before and after.


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

    def clear(self, net, shape, bbox, layer, is_via=False, override=None, same_net_too=False, extra=0.0, keep=True):
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
                if STRICT_POUR:
                    c = max(c, T(_.GetLocalClearance() or 0) + 0.23)
                if fill.Collide(shape, F(c)):
                    return False
        for outline, kb, notr, novia in self.keep[layer] if keep else ():
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



# ---- the passage north of J11 as a drawn bus (pass 3) --------------------------------------------------------
# Lanes: horizontal 0.152 mm tracks at 0.305 mm pitch between the J8 north-row pads (top edge y 52.605) and the
# north fence y 55.3 (INU_OUT2 pads at 55.46): 8 per layer, y 52.84 .. 54.975, on In3 and In4.
# In3 lanes are entered without a via from the gap between J6 and J4 (x 77.2 .. 86.2): a vertical from y 49.3 (just
# north of the DC bus band) up to the lane; west to east in the gap = south to north in the lanes.
# In4 lanes are entered through the missing pin column of J6 at x 68.98: vias at y 49.95 below the south row
# (0.61 mm via pitch: three tracks fit the 1.73 mm column), In4 north through the column, then west.
# Exits: through the missing pin columns of J8 (x 33.78 and x 24.89; lowest lane = eastmost slot) down to y 50.0
# south of the J8 pads. The router does the ends (pin -> lane start, lane end -> U4 / R50 / J8 pins / old In2 ends).
LANE_Y0, LANE_PITCH, BUS_W = 52.84, 0.305, 0.152
COL_E, COL_W, COL_J6 = 33.78, 24.89, 68.98
#          net                   lane  entry x   exit column, slot (0 = eastmost)
BUS_IN3 = [("Net-(U7B--)",          0, 79.000, COL_E, 0),
           ("Net-(U7B-+)",          1, 79.305, COL_E, 1),
           ("Net-(U2--)",           2, 79.610, COL_E, 2),
           ("Net-(U2-+)",           3, 79.915, COL_E, 3),
           ("Net-(U7A-+)",          4, 80.220, COL_E, 4),
           ("PWM_TRANS6",           5, 82.380, COL_W, 0),
           ("PWM_Q7",               6, 83.640, COL_W, 1),
           ("PWM_Q5",               7, 84.920, COL_W, 2)]
BUS_IN4 = [("GPIO_BYPASS_RLY_ISO",  2, COL_J6 - 0.61, COL_E, 3),
           ("MDATA_INU",            3, COL_J6,        COL_W, 0),
           ("INU_ADCLK",            4, COL_J6 + 0.61, COL_W, 1)]
# ISOGND needs no via: its In4 plane ends at y 48.8, so a 0.4 mm In4 track starts on the plane edge, passes the
# other missing column of J6 (x 60.09) and takes the two lowest In4 lanes; it leaves through the J8 column at 33.78.
ISOGND_BUS = [(60.09, 48.82), (60.09, LANE_Y0 + 0.124), (COL_E + 0.42, LANE_Y0 + 0.124), (COL_E + 0.42, 50.0)]


def bus(b, cx):
    def draw(net, layer, pts, via_at=None):
        segs = []
        for a, c in zip(pts, pts[1:]):
            t = cx.mktrack(net, layer, a, c, BUS_W)
            if not cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer):
                return f"blocked at ({a[0]:.2f}, {a[1]:.2f}) - ({c[0]:.2f}, {c[1]:.2f})"
            segs.append(t)
        v = None
        if via_at:
            v = cx.via_ok(net, *via_at)
            if v is None:
                return f"no via at ({via_at[0]:.2f}, {via_at[1]:.2f})"
        cx.commit(*segs, *([v] if v else []))
        return None

    global MARGIN
    MARGIN = 0.002          # the lanes stand at exactly 0.153 mm from each other; the DRC gate follows
    n = 0
    for net, k, xe, col, slot in BUS_IN3:
        y = LANE_Y0 + k * LANE_PITCH
        xs = col + 0.61 - slot * LANE_PITCH
        err = draw(net, pcbnew.In3_Cu, [(xe, 49.3), (xe, y), (xs, y), (xs, 50.0)])
        print(f"bus: In3 lane {k} y {y:.3f} {net}: " + (err or f"x {xe:.2f} -> column x {xs:.3f}, down to y 50.0"))
        n += not err
    for net, k, xe, col, slot in BUS_IN4:
        y = LANE_Y0 + k * LANE_PITCH
        xs = col + 0.61 - slot * LANE_PITCH
        err = draw(net, pcbnew.In4_Cu, [(xe, 49.95), (xe, y), (xs, y), (xs, 50.0)], via_at=(xe, 49.95))
        print(f"bus: In4 lane {k} y {y:.3f} {net}: " + (err or f"via ({xe:.2f}, 49.95) -> column x {xs:.3f}, down to y 50.0"))
        n += not err
    segs = []
    for a, c in zip(ISOGND_BUS, ISOGND_BUS[1:]):
        t = cx.mktrack("ISOGND", pcbnew.In4_Cu, a, c, 0.4)
        # keep=False: the first 0.2 mm end cap lies on the plane edge, inside the In4 plane fence
        if not cx.clear("ISOGND", t.GetEffectiveShape(pcbnew.In4_Cu), t.GetBoundingBox(), pcbnew.In4_Cu, keep=False):
            segs = None
            break
        segs.append(t)
    if segs:
        cx.commit(*segs)
    print("bus: In4 lanes 0+1 ISOGND 0.4 mm from the plane edge at (60.09, 48.82): " + ("drawn" if segs else "BLOCKED"))
    # Net-(U7A--): In4 lane 5, entered through the one via patch in the J6 / J4 gap (x 77.75), leaves through the
    # J8 column at x 24.89
    y5 = LANE_Y0 + 5 * LANE_PITCH
    err = draw("Net-(U7A--)", pcbnew.In3_Cu, [(77.75, 49.3), (77.75, 50.6)], via_at=(77.75, 50.6))
    err = err or draw("Net-(U7A--)", pcbnew.In4_Cu, [(77.75, 50.6), (77.75, y5), (24.89, y5), (24.89, 50.0)])
    print(f"bus: In4 lane 5 y {y5:.3f} Net-(U7A--): " + (err or "via (77.75, 50.60) -> column x 24.89, down to y 50.0"))
    n += not err
    # 15V_ISO: 0.4 mm on In4 lanes 6+7, no via: from the through-hole pin J4-48 west along y 49.5, up at x 81.0,
    # west over J8, around its west end to the through-hole pin J8-48
    yr = LANE_Y0 + 6.5 * LANE_PITCH
    pts = [(86.88, 49.5), (81.0, 49.5), (81.0, yr), (20.3, yr), (20.3, 50.93), (21.08, 50.93)]
    segs = []
    for a, c in zip(pts, pts[1:]):
        t = cx.mktrack("15V_ISO", pcbnew.In4_Cu, a, c, 0.4)
        if not cx.clear("15V_ISO", t.GetEffectiveShape(pcbnew.In4_Cu), t.GetBoundingBox(), pcbnew.In4_Cu):
            print(f"bus: 15V_ISO blocked at ({a[0]:.2f}, {a[1]:.2f}) - ({c[0]:.2f}, {c[1]:.2f})")
            segs = None
            break
        segs.append(t)
    if segs:
        cx.commit(*segs)
    print("bus: In4 lanes 6+7 15V_ISO 0.4 mm J4-48 -> J8-48: " + ("drawn" if segs else "NOT drawn"))
    print(f"bus: {n} of {len(BUS_IN3) + len(BUS_IN4) + 1} signal lanes drawn")


# ---- hooks: source pin -> lane start, for bus nets the router left open at the source end (pass 3) ------------
# NET: (source ref, pad, lane start x, y on In3). A via at the pad (an existing one of the net within 2.5 mm, else
# a new one beside the pad), then In3: vertical, 45 degrees, vertical to the lane start. Every piece gated.
HOOKS = {"PWM_Q7": ("U20", "11", 83.64, 49.3), "PWM_Q5": ("U20", "12", 84.92, 49.3), "PWM_TRANS6": ("U20", "10", 82.38, 49.3),
         "INU_ADCLK": ("U21", "14", 77.705, 49.3), "MDATA_INU": ("U21", "12", 77.4, 49.3)}


def hooks(b, cx, nets):
    global MARGIN
    MARGIN = 0.002
    for net in nets:
        ref, num, sx, sy = HOOKS[net]
        if ref is None:
            print(f"hooks: {net}: no source pin in reach (comes from the U7 / U2 block), left to the router")
            continue
        pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
        _, px, py, layer, smin, smax = pad_info(pad)
        vias = [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks()
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net and math.hypot(T(t.GetPosition().x) - px, -T(t.GetPosition().y) - py) < 2.5]
        how = "existing via"
        if not vias:
            before = {(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T}
            if via_at_pad(cx, pad, net, 2.5, 0.2) is None:
                print(f"hooks: {net}: NO PLACE for a via within 2.5 mm of {ref}-{num}")
                continue
            vias = [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T
                    and (t.GetPosition().x, t.GetPosition().y) not in before and t.GetNetname() == net]
            how = "new via"
        done = None
        for vx, vy in vias:
            dx = sx - vx
            ym = vy
            while ym <= sy - abs(dx) + 1e-6 and not done:
                pts = [(vx, vy), (vx, ym), (sx, ym + abs(dx)), (sx, sy)]
                pts = [q for i, q in enumerate(pts) if i == 0 or math.hypot(q[0] - pts[i - 1][0], q[1] - pts[i - 1][1]) > 1e-4]
                segs = [cx.mktrack(net, pcbnew.In3_Cu, a, c, BUS_W) for a, c in zip(pts, pts[1:])]
                if all(cx.clear(net, t.GetEffectiveShape(pcbnew.In3_Cu), t.GetBoundingBox(), pcbnew.In3_Cu) for t in segs):
                    cx.commit(*segs)
                    done = (vx, vy, ym)
                ym += 0.25
            if done:
                break
        print(f"hooks: {net}: " + (f"{how} ({done[0]:.2f}, {done[1]:.2f}) -> In3 -> ({sx:.2f}, {sy:.2f})" if done
                                   else f"{how} at {vias}, but NO clear In3 path to ({sx:.2f}, {sy:.2f})"))



# ---- pass 4: the passage as a fanned bus -----------------------------------------------------------------------
# INU_OUT2's two south pads (r 1.6 at (44.06, 57.06) and (49.94, 57.06)) pinch the corridor only at x 42.5 .. 51.5.
# The narrowest place is the neck between the west pad and the corner pin of J8 at (41.4, 52.2): 5.54 mm between
# centres, 3.08 mm free for track centre lines = 11 lanes of 0.152 mm at 0.305 mm pitch per layer. The lanes pass
# the pinch packed at y 52.165 .. 55.215, cross the neck at right angles to the line of centres (28.7 degrees) and
# spread over J8 (y 52.84 .. 55.89); east of the pinch they step up 0.675 mm over J6.
FAN_BASE = [(90.0, 52.84), (54.0, 52.84), (53.325, 52.165), (42.81, 52.165), (41.58, 52.84), (15.0, 52.84)]
#          net              lane  entry x (In3 vertical from y 49.3)
FAN_IN3 = [("MDATA_INU",       0, 77.400), ("INU_ADCLK",     1, 77.705),
           ("Net-(U7A-+)",     2, 78.600), ("Net-(U7A--)",   3, 78.905), ("Net-(U7B--)", 4, 79.210),
           ("Net-(U7B-+)",     5, 79.515), ("Net-(U2--)",    6, 79.820), ("Net-(U2-+)",  7, 80.125),
           ("PWM_TRANS6",      8, 82.380), ("PWM_Q7",        9, 83.640), ("PWM_Q5",     10, 84.920)]


def offset_poly(pts, d):
    """Parallel polyline d to the right of the direction of travel (north, for a path that runs west)."""
    lines = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 + nx * d, y1 + ny * d)))
    out = [lines[0][0]]
    for (a0, a1), (b0, b1) in zip(lines, lines[1:]):
        dax, day, dbx, dby = a1[0] - a0[0], a1[1] - a0[1], b1[0] - b0[0], b1[1] - b0[1]
        den = dax * dby - day * dbx
        t = ((b0[0] - a0[0]) * dby - (b0[1] - a0[1]) * dbx) / den
        out.append((a0[0] + t * dax, a0[1] + t * day))
    out.append(lines[-1][1])
    return out


def _poly(cx, net, layer, pts, w, keep=True):
    segs = []
    for a, c in zip(pts, pts[1:]):
        if math.hypot(a[0] - c[0], a[1] - c[1]) < 1e-4:
            continue
        t = cx.mktrack(net, layer, a, c, w)
        if not cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer, keep=keep):
            return f"blocked at ({a[0]:.2f}, {a[1]:.2f}) - ({c[0]:.2f}, {c[1]:.2f})"
        segs.append(t)
    cx.commit(*segs)
    return None


def fan(b, cx):
    global MARGIN
    MARGIN = 0.002
    n = 0
    for net, i, xe in FAN_IN3:
        mid = offset_poly(FAN_BASE, i * LANE_PITCH)[1:-1]
        ye, yw = 52.84 + i * LANE_PITCH, 52.84 + i * LANE_PITCH
        if i <= 4:
            xs = COL_E + 0.61 - i * LANE_PITCH
            tail = [(xs, yw), (xs, 50.0)]
            how = f"J8 column, x {xs:.3f}, down to y 50.0"
        elif i <= 7:
            xs = COL_W + 0.61 - (i - 5) * LANE_PITCH
            tail = [(xs, yw), (xs, 50.0)]
            how = f"J8 column, x {xs:.3f}, down to y 50.0"
        elif i == 8:        # PWM_TRANS6 -> J8-47 (north row) from the south through the 0.46 mm gap at x 21.715
            tail = [(24.585, yw), (24.585, 50.0), (21.715, 50.0), (21.715, 51.565), (21.08, 52.2)]
            how = "column x 24.585, under J8, gap x 21.715, pin J8-47"
        elif i == 9:        # PWM_Q7 -> J8-43 (north row) from the north-east
            tail = [(24.255, yw), (24.255, 52.835), (23.62, 52.2)]
            how = "column x 24.255, pin J8-43"
        else:               # PWM_Q5 -> J8-44 (south row) from the north through the gap at x 22.985
            tail = [(22.985, yw), (22.985, 51.565), (23.62, 50.93)]
            how = "gap x 22.985 of the north row, pin J8-44"
        err = _poly(cx, net, pcbnew.In3_Cu, [(xe, 49.3), (xe, ye)] + mid + tail, BUS_W)
        print(f"fan: In3 lane {i:2d} {net}: " + (err or f"entry x {xe:.3f}; {how}"))
        n += not err
    # In4: 5V_ISOL 0.8 mm, southmost (it has to drop onto the north-row pins J6-45 and J8-45), from pin J4-45
    d = 0.33
    mid = offset_poly(FAN_BASE, d)[1:-1]
    err = _poly(cx, "5V_ISOL", pcbnew.In4_Cu, [(88.15, 50.77), (88.15, 52.84 + d)] + mid + [(22.35, 52.84 + d), (22.35, 52.2)], 0.8)
    err = err or _poly(cx, "5V_ISOL", pcbnew.In4_Cu, [(57.55, 52.84 + d), (57.55, 52.0)], 0.8)
    print("fan: In4 5V_ISOL 0.8 mm J4-45 -> J6-45 -> J8-45 (lanes 0..3): " + (err or "drawn"))
    # In4: ISOGND 0.4 mm from the plane edge through the missing pin column of J4 at x 90.69 (east of J4-45, so it
    # does not cross the 5V_ISOL lane), around the west end of J8 to pin J8-46
    d = 1.09
    mid = offset_poly(FAN_BASE, d)[1:-1]
    err = _poly(cx, "ISOGND", pcbnew.In4_Cu, [(90.69, 48.82), (90.69, 52.84 + d)] + mid
                + [(20.25, 52.84 + d), (20.25, 49.9), (22.35, 49.9), (22.35, 50.93)], 0.4, keep=False)
    print("fan: In4 ISOGND 0.4 mm plane edge (90.69, 48.82) -> J8-46 (lanes 3..4): " + (err or "drawn"))
    print(f"fan: {n} of {len(FAN_IN3)} In3 signal lanes drawn")


def link(cx, net, a, c, layer=pcbnew.In3_Cu, w=BUS_W, dry=False):
    """A short octilinear connection a -> c on one layer, first pattern that is clear. Returns the tracks (drawn
    unless dry) or None."""
    (ax, ay), (bx, by) = a, c
    dx, dy = bx - ax, by - ay
    sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
    m = min(abs(dx), abs(dy))
    pats = [[a, (ax, by), c], [a, (bx, ay), c],
            [a, (ax, by - sy * abs(dx)), c] if abs(dy) >= abs(dx) else [a, (bx - sx * abs(dy), ay), c],
            [a, (ax + sx * m, ay + sy * m), c]]
    k = 0.5
    while k < 14:           # vertical, horizontal at another height (also beyond the target), vertical
        pats.append([a, (ax, ay + sy * k), (bx, ay + sy * k), c])
        if abs(dx) > k:
            pats.append([a, (ax + sx * k, ay), (ax + sx * k, by), c])
        k += 0.25
    for pts in pats:
        segs = [cx.mktrack(net, layer, p, q, w) for p, q in zip(pts, pts[1:]) if math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-4]
        if all(cx.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer) for t in segs):
            if not dry:
                cx.commit(*segs)
            return segs
    return None


def westends(b, cx):
    """West ends of the lanes that the router did not make in pass 3 (run after fan and hooks)."""
    global MARGIN
    MARGIN = 0.002          # the column tracks stand 0.153 mm apart; a link continues one of them
    drop = {net: ((COL_E if i <= 4 else COL_W) + 0.61 - (i if i <= 4 else i - 5) * LANE_PITCH, 50.0) for net, i, _ in FAN_IN3 if i <= 7}
    # sigma-delta pair: a via beside the pad at U4 / R50, then In3 from the column
    for net, ref, num in (("MDATA_INU", "R50", "2"), ("INU_ADCLK", "U4", "7")):
        pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
        before = {(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T}
        r = via_at_pad(cx, pad, net, 3.0, 0.2)
        if r is None:
            print(f"westends: {net}: NO PLACE for a via within 3 mm of {ref}-{num}")
            continue
        v = [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T
             and (t.GetPosition().x, t.GetPosition().y) not in before][0]
        ok = link(cx, net, drop[net], v)
        print(f"westends: {net}: via ({v[0]:.2f}, {v[1]:.2f}) at {ref}-{num}; In3 from the column: " + ("drawn" if ok else "NO clear path, left to the router"))
    # divider taps: the old copper is on In2 and ends under pours; a via on the old track where one fits and where
    # an In3 link from the column reaches it. The near ones first, the two that go on to x 5 last (they pass below).
    order = ["Net-(U7B-+)", "Net-(U2--)", "Net-(U2-+)", "Net-(U7B--)", "Net-(U7A-+)", "Net-(U7A--)"]
    for net in order:
        cand = []
        for t in b.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() != net or t.GetLayer() != pcbnew.In2_Cu:
                continue
            (x0, y0), (x1, y1) = (T(t.GetStart().x), -T(t.GetStart().y)), (T(t.GetEnd().x), -T(t.GetEnd().y))
            L = math.hypot(x1 - x0, y1 - y0)
            for k in range(int(L / 0.25) + 1):
                f = k * 0.25 / L if L else 0
                x, y = x0 + f * (x1 - x0), y0 + f * (y1 - y0)
                if 0.5 <= x <= 45 and 36.5 <= y <= 53.5:
                    cand.append((math.hypot(x - drop[net][0], y - drop[net][1]), x, y))
        done, legal, first = None, 0, None
        for _, x, y in sorted(cand):
            v = cx.via_ok(net, x, y)
            if v is None:
                continue
            legal += 1
            first = first or (x, y)
            segs = link(cx, net, drop[net], (x, y), dry=True)
            if segs:
                cx.commit(v, *segs)
                done = (x, y)
                break
        if not done and first:
            cx.commit(cx.via_ok(net, *first))
        print(f"westends: {net}: {len(cand)} points on the old In2 track in reach, {legal} legal for a via; "
              + (f"via at ({done[0]:.2f}, {done[1]:.2f}) and In3 from the column drawn" if done
                 else (f"via at ({first[0]:.2f}, {first[1]:.2f}), no simple In3 link: left to the router" if first
                       else "NO legal via point on the old track")))


def main():
    mode, src, dst = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    cx = Ctx(b)
    if mode == "hooks":
        hooks(b, cx, sys.argv[4].split(","))
    else:
        {"taps": taps, "planes": planes, "hvstubs": hvstubs, "bus": bus, "fan": fan, "westends": westends}[mode](b, cx)
    b.Save(dst)


if __name__ == "__main__":
    main()
