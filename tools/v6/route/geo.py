"""Geometry helpers for the scripted copper of the v6 routing chain (run under tools/p2k/bin/kipy; IPC frame, y up).
Taken from the v5 pass-7 helpers (routing-pass7: tools/v5/route_pass1/scripted.py Ctx, maze.py Grid) and adapted:

- the high-voltage rule (hv.py) holds on every layer: 2.5 mm between an HV net and any other net, 1.0 mm between
  two HV nets, a pad's own local clearance always;
- the domain gaps (tools/v4/domains.py: P-I / P-C / I-C 5.0 mm, P/I-E 2.5 mm) are checked for every new piece;
- pours of other nets are obstacles on every layer (inner layers too: a drawn track may not cut a bus lane or a
  plane), with the pour's own clearance, at least 0.25 mm;
- keep-out rule areas forbid what they say (tracks / vias), the temporary router fences ("tmp route") excepted.

Every piece is tested before it is added; nothing is added when a test fails (the caller reports it).
"""
import heapq
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path[:0] = [HERE, os.path.join(R, "tools"), os.path.join(R, "tools", "v4")]
import board_common as bc  # noqa: E402
import domains  # noqa: E402
from hv import is_hv  # noqa: E402

F, T = pcbnew.FromMM, pcbnew.ToMM
CLR, VIA, DRILL = 0.15, 0.4572, 0.3
MARGIN = 0.02
LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu,
          "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}
_DOM = None


def dom_of(net):
    global _DOM
    if _DOM is None:
        _, nets = bc.export_netlist()
        _DOM = {domains.short(k): v for k, v in domains.classify(nets).items()}
    return _DOM.get(domains.short(net)) if net else None


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def xy(v):
    return T(v.x), -T(v.y)


class Ctx:
    def __init__(self, b):
        self.b = b
        self.pierce = set()     # nets whose pours a new piece may enter: hv_holes() then cuts the pour back
        self.layers = list(b.GetEnabledLayers().CuStack())
        self.items = {l: [] for l in self.layers}      # (net, shape, bbox, kind, local clearance mm)
        self.zones = {l: [] for l in self.layers}      # (net, fill, bbox, clearance mm)
        self.keep = {l: [] for l in self.layers}       # (outline, bbox, no tracks, no vias)
        for fp in b.GetFootprints():
            for p in fp.Pads():
                lc = T(p.GetLocalClearance() or 0)
                for l in self.layers:
                    if p.IsOnLayer(l):
                        self.items[l].append((p.GetNetname(), p.GetEffectiveShape(l), p.GetBoundingBox(), "pad", lc))
        for t in b.GetTracks():
            self.add_track(t)
        for z in b.Zones():
            for l in self.layers:
                if not z.IsOnLayer(l):
                    continue
                if z.GetIsRuleArea():
                    if not z.GetZoneName().startswith("tmp route"):
                        self.keep[l].append((z.Outline(), z.GetBoundingBox(), z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))
                else:
                    self.zones[l].append((z.GetNetname(), z.GetFilledPolysList(l), z.GetBoundingBox(),
                                          T(z.GetLocalClearance() or 0)))

    def add_track(self, t):
        if t.Type() == pcbnew.PCB_VIA_T:
            for l in self.layers:
                self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "via", 0.0))
        else:
            l = t.GetLayer()
            self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "track", 0.0))

    @staticmethod
    def rule(net, onet, lc=0.0):
        """Clearance between a new piece of `net` and an object of `onet` with local clearance lc."""
        if not onet:
            return 0.25
        c = max(CLR, lc)
        hn, ho = is_hv(net), is_hv(onet)
        if hn != ho:
            c = max(c, 2.5)
        elif hn and ho:
            c = max(c, 1.0)
        g = domains.gap(dom_of(net), dom_of(onet))
        if g:
            c = max(c, g)
        return c

    def clear(self, net, shape, bbox, layer, is_via=False, keep=True, zones=True, why=None):
        box = pcbnew.BOX2I(bbox.GetPosition(), bbox.GetSize())
        box.Inflate(F(5.2))
        for o in self.items[layer]:
            if not box.Intersects(o[2]):
                continue
            if o[0] == net and o[0]:
                if is_via and o[3] != "track" and shape.Collide(o[1], F(CLR)):
                    return self._why(why, "same-net pad / via", o)
                continue
            if shape.Collide(o[1], F(self.rule(net, o[0], o[4]) + MARGIN)):
                return self._why(why, f"{o[3]} {o[0]}", o)
        if zones:
            for znet, fill, zb, zc in self.zones[layer]:
                if znet != net and znet not in self.pierce and box.Intersects(zb) and fill.OutlineCount():
                    if fill.Collide(shape, F(max(self.rule(net, znet), zc, 0.25) + MARGIN)):
                        return self._why(why, f"pour {znet}", None)
        if keep:
            for outline, kb, notr, novia in self.keep[layer]:
                if (novia if is_via else notr) and box.Intersects(kb) and outline.Collide(shape, F(0.05)):
                    return self._why(why, "keep-out", None)
        return True

    @staticmethod
    def _why(why, s, o):
        if why is not None:
            why.append(s)
        return False

    def via_ok(self, net, x, y, why=None):
        v = self.mkvia(net, x, y)
        for l in self.layers:
            if not self.clear(net, v.GetEffectiveShape(l), v.GetBoundingBox(), l, is_via=True, why=why):
                if why is not None:
                    why[-1] = f"{self.b.GetLayerName(l)}: {why[-1]}"
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

    def poly(self, net, layer, pts, w, dry=False):
        """Draw a polyline; returns None or the reason it is blocked (nothing is drawn then)."""
        segs = []
        for a, c in zip(pts, pts[1:]):
            if math.hypot(a[0] - c[0], a[1] - c[1]) < 1e-4:
                continue
            t = self.mktrack(net, layer, a, c, w)
            why = []
            if not self.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer, why=why):
                return f"blocked at ({a[0]:.2f}, {a[1]:.2f}) - ({c[0]:.2f}, {c[1]:.2f}) by {why[-1] if why else '?'}"
            segs.append(t)
        self.last = segs
        if not dry:
            self.commit(*segs)
        return None


def plen(pts):
    return sum(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def offset_poly(pts, d):
    """Parallel polyline at distance d to the left of the direction of travel (d < 0: right)."""
    lines = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 + nx * d, y1 + ny * d)))
    out = [lines[0][0]]
    for (a0, a1), (b0, b1) in zip(lines, lines[1:]):
        dax, day, dbx, dby = a1[0] - a0[0], a1[1] - a0[1], b1[0] - b0[0], b1[1] - b0[1]
        den = dax * dby - day * dbx
        if abs(den) < 1e-12:
            out.append(a1)
            continue
        t = ((b0[0] - a0[0]) * dby - (b0[1] - a0[1]) * dbx) / den
        out.append((a0[0] + t * dax, a0[1] + t * day))
    out.append(lines[-1][1])
    return out


def pad(b, ref, num):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == str(num)][0]


def pad_xy(b, ref, num):
    return xy(pad(b, ref, num).GetPosition())


# ---- grid router on one layer (A*, 0.1 mm, 45 degree moves); obstacles rasterised with the Ctx rules ----------
G = 0.1


class Grid:
    def __init__(self, cx, layer, box, w, net, planview_hv=True):
        self.cx, self.layer, self.net, self.w = cx, layer, net, w
        self.planview_hv = planview_hv
        self.x0, self.y0, x1, y1 = box
        self.nx, self.ny = int(round((x1 - self.x0) / G)) + 1, int(round((y1 - self.y0) / G)) + 1
        self.blk = bytearray(self.nx * self.ny)
        self.cost = None
        self._build()

    def ij(self, x, y):
        return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def xy(self, i, j):
        return self.x0 + i * G, self.y0 + j * G

    def _build(self):
        """A cell is blocked when a track centre there would break a rule: tested with a short probe segment
        through the cell centre against each object near the box (exact shapes, slow but exact)."""
        cx, l, net, hw = self.cx, self.layer, self.net, self.w / 2
        box = pcbnew.BOX2I(P(self.x0, self.y0 + self.ny * G), pcbnew.VECTOR2L(F(self.nx * G), F(self.ny * G)))
        box.Inflate(F(5.5))
        obs = []
        for o in cx.items[l]:
            if box.Intersects(o[2]) and not (o[0] == net and o[0]):
                obs.append((o[1], o[2], cx.rule(net, o[0], o[4])))
        soft = []
        if self.planview_hv:
            # high-voltage SMD pads on the outer layers: a drawn inner-layer run pays extra within 2.5 mm of them in
            # plan view (prefers not to run under the side-1 pads of U4 / U5); not a rule, a cost (self.soft)
            for ol in (pcbnew.F_Cu, pcbnew.B_Cu):
                if ol == l:
                    continue
                for o in cx.items[ol]:
                    if o[3] == "pad" and o[0] and is_hv(o[0]) and box.Intersects(o[2]) and not is_hv(net):
                        soft.append((o[1], o[2], 2.5))
        self.soft = bytearray(self.nx * self.ny)
        for shp, bb, r in soft:
            rr = r + hw
            xa, xb = T(bb.GetLeft()) - rr, T(bb.GetRight()) + rr
            ya, yb = -T(bb.GetBottom()) - rr, -T(bb.GetTop()) + rr
            ia, ja = self.ij(xa, ya)
            ib, jb = self.ij(xb, yb)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    k = j * self.nx + i
                    if not self.soft[k] and shp.Collide(P(*self.xy(i, j)), F(rr)):
                        self.soft[k] = 1
        zs = [(fill, zb, max(cx.rule(net, zn), zc, 0.25)) for zn, fill, zb, zc in cx.zones[l]
              if zn != net and zn not in cx.pierce and box.Intersects(zb) and fill.OutlineCount()]
        ks = [(o, kb) for o, kb, notr, _ in cx.keep[l] if notr and box.Intersects(kb)]
        for shp, bb, r in obs:
            rr = r + hw + MARGIN
            xa, xb = T(bb.GetLeft()) - rr, T(bb.GetRight()) + rr
            ya, yb = -T(bb.GetBottom()) - rr, -T(bb.GetTop()) + rr
            ia, ja = self.ij(xa, ya)
            ib, jb = self.ij(xb, yb)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    k = j * self.nx + i
                    if self.blk[k]:
                        continue
                    x, y = self.xy(i, j)
                    if shp.Collide(P(x, y), F(rr)):
                        self.blk[k] = 1
        for fill, zb, r in zs:
            rr = r + hw + MARGIN
            xa, xb = T(zb.GetLeft()) - rr, T(zb.GetRight()) + rr
            ya, yb = -T(zb.GetBottom()) - rr, -T(zb.GetTop()) + rr
            ia, ja = self.ij(xa, ya)
            ib, jb = self.ij(xb, yb)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    k = j * self.nx + i
                    if not self.blk[k] and fill.Collide(P(*self.xy(i, j)), F(rr)):
                        self.blk[k] = 1
        for o, kb in ks:
            rr = hw + 0.05
            xa, xb = T(kb.GetLeft()) - rr, T(kb.GetRight()) + rr
            ya, yb = -T(kb.GetBottom()) - rr, -T(kb.GetTop()) + rr
            ia, ja = self.ij(xa, ya)
            ib, jb = self.ij(xb, yb)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    k = j * self.nx + i
                    if not self.blk[k]:
                        v = P(*self.xy(i, j))
                        if o.Contains(v) or o.Collide(v, F(rr)):
                            self.blk[k] = 1

    def wall(self, xa, ya, xb, yb):
        ia, ja = self.ij(xa, ya)
        ib, jb = self.ij(xb, yb)
        for j in range(max(0, ja), min(self.ny, jb + 1)):
            for i in range(max(0, ia), min(self.nx, ib + 1)):
                self.blk[j * self.nx + i] = 1

    def block_poly(self, pts, r):
        """Block the cells within r of a polyline (e.g. a track drawn in the same step on this grid)."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(L / (G * 0.5)))
            for k in range(n + 1):
                x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
                i0, j0 = self.ij(x, y)
                m = int(r / G) + 1
                for j in range(max(0, j0 - m), min(self.ny, j0 + m + 1)):
                    for i in range(max(0, i0 - m), min(self.nx, i0 + m + 1)):
                        xx, yy = self.xy(i, j)
                        if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                            self.blk[j * self.nx + i] = 1

    def route(self, a, c, turn=0.4):
        nx, ny, blk = self.nx, self.ny, bytearray(self.blk)
        ia, ja = self.ij(*a)
        ic, jc = self.ij(*c)
        for (i, j) in ((ia, ja), (ic, jc)):
            if not (0 <= i < nx and 0 <= j < ny):
                return None
            blk[j * nx + i] = 0
        start, goal = ja * nx + ia, jc * nx + ic
        moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142),
                 (-1, 1, 1.4142), (-1, -1, 1.4142)]
        best = {(start, -1): 0.0}
        came = {}
        heap = [(0.0, 0.0, start, -1)]
        end = None
        cost = self.cost
        while heap:
            f, g, n, d = heapq.heappop(heap)
            if n == goal:
                end = (n, d)
                break
            if best.get((n, d), 1e18) < g:
                continue
            i, j = n % nx, n // nx
            for k, (di, dj, cst) in enumerate(moves):
                i2, j2 = i + di, j + dj
                if not (0 <= i2 < nx and 0 <= j2 < ny):
                    continue
                n2 = j2 * nx + i2
                if blk[n2] and n2 != goal:
                    continue
                if di and dj and (blk[j * nx + i2] or blk[j2 * nx + i]):
                    continue
                g2 = g + cst * (1.0 + (cost[n2] if cost else 0.0)) + (0.0 if k == d or d < 0 else turn)
                if g2 < best.get((n2, k), 1e18):
                    best[(n2, k)] = g2
                    came[(n2, k)] = (n, d)
                    dx, dy = abs(i2 - ic), abs(j2 - jc)
                    heapq.heappush(heap, (g2 + max(dx, dy) + 0.4142 * min(dx, dy), g2, n2, k))
        if end is None:
            return None
        cells = []
        cur = end
        while cur[0] != start or cur[1] != -1:
            cells.append(cur)
            cur = came[cur]
        cells.append(cur)
        cells.reverse()
        pts = [a]
        for q, (n, d) in enumerate(cells):
            if 0 < q and q + 1 < len(cells) and cells[q + 1][1] == d:
                continue
            pts.append(self.xy(n % nx, n // nx))
        pts.append(c)
        # drop the grid points next to the exact ends when they make a kink
        return pts


def hv_holes(cx, objs, tag):
    """Cut the pours of the nets in cx.pierce back from the new pieces objs: one keep-out (no zone fill) per piece
    and layer, an octagon around a via / a capsule around a track, radius = the rule between the two nets (2.5 mm
    for an HV pour) + the piece's half width + 0.05 mm. Returns the number of keep-outs added."""
    b, n = cx.b, 0
    for o in objs:
        via = o.Type() == pcbnew.PCB_VIA_T
        for l in (cx.layers if via else [o.GetLayer()]):
            shape = o.GetEffectiveShape(l)
            for znet, fill, zb, zc in cx.zones[l]:
                if znet not in cx.pierce or not is_hv(znet) or znet == o.GetNetname() or not fill.OutlineCount():
                    continue
                r = max(cx.rule(o.GetNetname(), znet), zc) + T(o.GetWidth(pcbnew.F_Cu) if via else o.GetWidth()) / 2 + 0.05
                if not fill.Collide(shape, F(r + 0.3)):
                    continue
                if via:
                    c = xy(o.GetPosition())
                    a, e = c, c
                else:
                    a, e = xy(o.GetStart()), xy(o.GetEnd())
                ro = r / math.cos(math.pi / 8)
                L = math.hypot(e[0] - a[0], e[1] - a[1])
                ang = math.atan2(e[1] - a[1], e[0] - a[0]) if L > 1e-6 else 0.0
                pts = [(e[0] + ro * math.cos(ang - math.pi / 2 + k * math.pi / 4), e[1] + ro * math.sin(ang - math.pi / 2 + k * math.pi / 4)) for k in range(5)]
                pts += [(a[0] + ro * math.cos(ang + math.pi / 2 + k * math.pi / 4), a[1] + ro * math.sin(ang + math.pi / 2 + k * math.pi / 4)) for k in range(5)]
                z = pcbnew.ZONE(b)
                z.SetIsRuleArea(True)
                z.SetZoneName(f"v6 route HV keep-out {tag} {znet}")
                z.SetDoNotAllowTracks(False)
                z.SetDoNotAllowVias(False)
                z.SetDoNotAllowZoneFills(True)
                z.SetDoNotAllowPads(False)
                z.SetDoNotAllowFootprints(False)
                ls = pcbnew.LSET()
                ls.AddLayer(l)
                z.SetLayerSet(ls)
                ol = z.Outline()
                ol.NewOutline()
                for x, y in pts:
                    ol.Append(F(x), F(-y))
                b.Add(z)
                n += 1
                break
    return n
