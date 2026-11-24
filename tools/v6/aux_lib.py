"""Shared pieces of the aux flyback routes (V6_PLAN.md section 10; run under tools/p2k/bin/kipy).

Used by tools/v6/aux_design.py (draws, gates, writes tools/v6/aux_routes_copper.csv) and tools/v6/aux_routes.py (replays
that table onto the current board) and tools/v6/aux_check.py (HV / area / island checks of a filled board).

Frame: mm, IPC (y up); KiCad y = -y.

Clearance rule used to gate every piece (the HV rule lives only in pad clearances on the board, so it is explicit here):
  - outer layers: HV net <-> low-voltage net 2.5 mm; to an HV pad that carries its own (smaller) clearance from
    card_layout.HV_PADS that clearance (the placement's pad gaps, 1.5 / 2.0 mm); HV <-> HV of another net 1.0 mm
    (or the pad's own clearance if larger)
  - inner layers: HV <-> low voltage 0.5 mm (IPC-2221 B1 internal 301-500 V: 0.25 mm), AUX_DRAIN / AUX_CLAMP <-> any
    other net 2.0 mm (B1 internal > 500 V), others 0.15 mm
  - everything >= 2.5 mm from the mounting hole H4 (a metal screw: P <-> PE basic)
  - a pad's own clearance always holds; +0.02 mm margin
"""
import heapq
import math

import pcbnew

F, T = pcbnew.FromMM, pcbnew.ToMM
HV = {"AUX_DRAIN", "AUX_CLAMP", "AUX_VIN", "DC+", "AUX_ST1", "AUX_ST2", "AUX_LV1", "AUX_LV2"}
CLR, MARGIN, VIA, DRILL = 0.15, 0.02, 0.4572, 0.3
HV_OUT, HV_HV, HV_IN, HOLE = 2.5, 1.0, 0.5, 2.5
# the switching nodes on inner layers: IPC-2221 B1 internal conductors > 500 V 0.0025 mm/V, ~750 V peak -> 2.0 mm
SWING, HV_SWING_IN = {"AUX_DRAIN", "AUX_CLAMP"}, 2.0
AREAS = {"PX": (67.0, -54.6, 82.9, -4.0), "IA": (88.0, -48.0, 97.5, -25.5)}
OUTER = (pcbnew.F_Cu, pcbnew.B_Cu)
H4 = (81.0, -14.5)


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def xy(v):
    return T(v.x), -T(v.y)


def in_area(x, y, m=0.0):
    for k, (x0, y0, x1, y1) in AREAS.items():
        if x0 + m <= x <= x1 - m and y0 + m <= y <= y1 - m:
            return k
    return None


def box_in_area(bb, m=0.0):
    """True if the KiCad bounding box lies inside one area (shrunk by m)."""
    x0, x1, y0, y1 = T(bb.GetLeft()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetTop())
    return any(a0 + m <= x0 and x1 <= a1 - m and b0 + m <= y0 and y1 <= b1 - m for a0, b0, a1, b1 in AREAS.values())


def is_hv(net):
    return net in HV


class Ctx:
    """Copper of the board by layer, and the gate for new pieces (after tools/v5/route_pass1/scripted.py, pass 7)."""

    def __init__(self, b):
        self.b = b
        self.layers = list(b.GetEnabledLayers().CuStack())
        self.items = {l: [] for l in self.layers}       # (net, shape, bbox, kind, local clearance mm, ref)
        self.zones = {l: [] for l in self.layers}
        self.keep = {l: [] for l in self.layers}
        self.added = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                lc = p.GetLocalClearance()
                for l in self.layers:
                    if p.IsOnLayer(l):
                        self.items[l].append((p.GetNetname(), p.GetEffectiveShape(l), p.GetBoundingBox(), "pad",
                                              T(lc) if lc else 0.0, fp.GetReference()))
        for t in b.GetTracks():
            self.add_track(t)
        for z in b.Zones():
            for l in self.layers:
                if not z.IsOnLayer(l):
                    continue
                if z.GetIsRuleArea():
                    self.keep[l].append((z.Outline(), z.GetBoundingBox(), z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))
                else:
                    self.zones[l].append((z.GetNetname(), z.GetFilledPolysList(l), z.GetBoundingBox(), z))

    def add_track(self, t):
        if t.Type() == pcbnew.PCB_VIA_T:
            for l in self.layers:
                self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "via", 0.0, ""))
        else:
            l = t.GetLayer()
            (x1, y1), (x2, y2) = xy(t.GetStart()), xy(t.GetEnd())
            self.items[l].append((t.GetNetname(), t.GetEffectiveShape(l), t.GetBoundingBox(), "track", 0.0,
                                  (x1, y1, x2, y2, T(t.GetWidth()))))

    @staticmethod
    def need(net, layer, onet, kind, lc):
        if not onet:
            return (HOLE if kind == "pad" else 0.25) + MARGIN
        c = max(CLR, lc)
        if layer in OUTER:
            if is_hv(net) != is_hv(onet):
                c = lc if (kind == "pad" and lc and is_hv(onet)) else max(HV_OUT, lc)
            elif is_hv(net) and is_hv(onet):
                c = max(HV_HV, lc)
        else:
            if net in SWING or onet in SWING:
                c = max(c, HV_SWING_IN)
            elif is_hv(net) != is_hv(onet):
                c = max(c, HV_IN)
        return c + MARGIN

    def clear(self, net, shape, bbox, layer, is_via=False, same_net_too=False, keep=True, why=None, area_tol=0.0,
              override=None):
        override = override or {}
        box = pcbnew.BOX2I(bbox.GetPosition(), bbox.GetSize())
        box.Inflate(F(2.8))
        for o in self.items[layer]:
            if not box.Intersects(o[2]):
                continue
            if o[0] == net and o[0]:
                if same_net_too and o[3] == "via" and shape.Collide(o[1], F(CLR)):
                    if why is not None:
                        why.append(f"same-net via at {xy(o[2].GetCenter())}")
                    return False
                continue
            c = self.need(net, layer, o[0], o[3], o[4])
            c = min(c, override.get(id(o), c))
            if shape.Collide(o[1], F(c)):
                if why is not None:
                    why.append(f"{o[3]} {o[5]} [{o[0]}] near {tuple(round(v, 2) for v in xy(o[2].GetCenter()))}")
                return False
        if layer in OUTER:      # outer pours: they give way only by their own clearance on a refill
            for znet, fill, zb, z in self.zones[layer]:
                # same class: the pour gives way by its own clearance on a refill (enough); HV <-> LV: 2.5 mm
                if znet != net and box.Intersects(zb) and fill.OutlineCount() and is_hv(net) != is_hv(znet):
                    if fill.Collide(shape, F(min(HV_OUT, override.get(id(fill), HV_OUT)))):
                        if why is not None:
                            why.append(f"pour {z.GetZoneName()} [{znet}]")
                        return False
        for outline, kb, notr, novia in self.keep[layer] if keep else ():
            if (novia if is_via else notr) and box.Intersects(kb) and outline.Collide(shape, F(0.05)):
                if why is not None:
                    why.append("rule area")
                return False
        if not box_in_area(bbox, -area_tol):
            if why is not None:
                why.append("outside the areas")
            return False
        return True

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

    def via_ok(self, net, x, y, why=None, override=None):
        v = self.mkvia(net, x, y)
        for l in self.layers:
            if not self.clear(net, v.GetEffectiveShape(l), v.GetBoundingBox(), l, is_via=True, same_net_too=True, why=why,
                              override=(override or {}).get(l)):
                return None
        return v

    def track_ok(self, net, layer, a, c, w, why=None, area_tol=0.0, override=None):
        t = self.mktrack(net, layer, a, c, w)
        return t if self.clear(net, t.GetEffectiveShape(layer), t.GetBoundingBox(), layer, why=why, area_tol=area_tol,
                               override=override) else None

    def pads_at(self, net, layer, pts):
        """(shape, net) of the pads of `net` on `layer` that contain one of the points."""
        out = []
        for o in self.items[layer]:
            if o[3] == "pad" and o[0] == net:
                for x, y in pts:
                    if o[1].Collide(P(x, y), 0):
                        out.append((o[1], net))
                        break
        return out

    def padgap(self, pads, layer):
        """Pad-gap exception (as tools/v5/route_pass1/scripted.py hvstubs): copper that leaves one of these pads may come
        as close to an obstacle as the pad itself is (the placement's gap, kept by the pad clearances of HV_PADS)."""
        ov = {}
        for ps in pads:
            for o in self.items[layer]:
                if o[0] and o[0] != ps[1] and o[1].Collide(ps[0], F(HV_OUT + 0.3)):
                    g = gap(ps[0], o[1])
                    ov[id(o)] = min(ov.get(id(o), 9), max(CLR + MARGIN, g - 0.005))
            if layer in OUTER:
                for znet, fill, zb, z in self.zones[layer]:
                    if znet != ps[1] and fill.OutlineCount() and fill.Collide(ps[0], F(HV_OUT + 0.3)):
                        g = gap(fill, ps[0])
                        ov[id(fill)] = min(ov.get(id(fill), 9), max(CLR + MARGIN, g - 0.005))
        return ov

    def commit(self, *objs):
        for o in objs:
            o.SetLocked(True)
            self.b.Add(o)
            self.add_track(o)
            self.added.append(o)


# ---- grid router (after tools/v5/route_pass1/maze.py): A* on a 0.1 mm grid, one layer, 45 degree moves ----------
G = 0.1


class Grid:
    def __init__(self, cx, layer, box):
        self.cx, self.layer = cx, layer
        self.x0, self.y0, x1, y1 = box
        self.nx, self.ny = int(round((x1 - self.x0) / G)) + 1, int(round((y1 - self.y0) / G)) + 1

    def ij(self, x, y):
        return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def gxy(self, i, j):
        return self.x0 + i * G, self.y0 + j * G

    def disc(self, blk, x, y, r):
        i0, j0 = self.ij(x, y)
        n = int(r / G) + 1
        r2 = r * r
        for j in range(max(0, j0 - n), min(self.ny, j0 + n + 1)):
            yy = self.y0 + j * G - y
            row = j * self.nx
            for i in range(max(0, i0 - n), min(self.nx, i0 + n + 1)):
                xx = self.x0 + i * G - x
                if xx * xx + yy * yy <= r2:
                    blk[row + i] = 1

    def rect(self, blk, xa, ya, xb, yb):
        ia, ja = self.ij(xa, ya)
        ib, jb = self.ij(xb, yb)
        for j in range(max(0, ja), min(self.ny, jb + 1)):
            row = j * self.nx
            for i in range(max(0, ia), min(self.nx, ib + 1)):
                blk[row + i] = 1

    def build(self, net, w):
        """Blocked cells for a track of width w of `net`: centre-line keep-out of every obstacle (approximate: pad
        boxes, track discs); the exact gate is Ctx.clear afterwards."""
        blk = bytearray(self.nx * self.ny)
        hw = w / 2 + 0.03
        cx, L = self.cx, self.layer
        xa, ya = self.x0 - 3.5, self.y0 - 3.5
        xb, yb = self.x0 + self.nx * G + 3.5, self.y0 + self.ny * G + 3.5
        for o in cx.items[L]:
            onet, shape, bb, kind, lc, ref = o
            if onet == net and onet:
                continue
            c = Ctx.need(net, L, onet, kind, lc) + hw
            bx0, bx1, by0, by1 = T(bb.GetLeft()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetTop())
            if bx1 < xa or bx0 > xb or by1 < ya or by0 > yb:
                continue
            if kind == "via":
                x, y = (bx0 + bx1) / 2, (by0 + by1) / 2
                self.disc(blk, x, y, (bx1 - bx0) / 2 + c)
            elif kind == "track":
                x, y, x1, y1, tw = ref
                r = tw / 2 + c
                n = max(1, int(math.hypot(x1 - x, y1 - y) / (G * 0.7)))
                for k in range(n + 1):
                    f = k / n
                    self.disc(blk, x + f * (x1 - x), y + f * (y1 - y), r)
            else:
                if abs((bx1 - bx0) - (by1 - by0)) < 0.05 and kind == "pad" and shape.Type() == pcbnew.SH_CIRCLE:
                    self.disc(blk, (bx0 + bx1) / 2, (by0 + by1) / 2, (bx1 - bx0) / 2 + c)
                else:
                    # rounded box: corners as discs, edges as rects
                    self.rect(blk, bx0 - c, by0, bx1 + c, by1)
                    self.rect(blk, bx0, by0 - c, bx1, by1 + c)
                    for qx in (bx0, bx1):
                        for qy in (by0, by1):
                            self.disc(blk, qx, qy, c)
        if L in OUTER:
            for znet, fill, zb, z in cx.zones[L]:
                if znet == net or not fill.OutlineCount() or is_hv(net) == is_hv(znet):
                    continue
                c = HV_OUT + hw
                ia, ja = self.ij(T(zb.GetLeft()) - c, -T(zb.GetBottom()) - c)
                ib, jb = self.ij(T(zb.GetRight()) + c, -T(zb.GetTop()) + c)
                for j in range(max(0, ja), min(self.ny, jb + 1)):
                    for i in range(max(0, ia), min(self.nx, ib + 1)):
                        k = j * self.nx + i
                        if blk[k]:
                            continue
                        x, y = self.gxy(i, j)
                        if fill.Collide(P(x, y), F(c)):
                            blk[k] = 1
        for outline, kb, notr, novia in cx.keep[L]:
            if not notr:
                continue
            ia, ja = self.ij(T(kb.GetLeft()) - 0.5, -T(kb.GetBottom()) - 0.5)
            ib, jb = self.ij(T(kb.GetRight()) + 0.5, -T(kb.GetTop()) + 0.5)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    k = j * self.nx + i
                    if not blk[k]:
                        x, y = self.gxy(i, j)
                        if outline.Collide(P(x, y), F(hw + 0.05)):
                            blk[k] = 1
        # outside the areas
        for j in range(self.ny):
            for i in range(self.nx):
                x, y = self.gxy(i, j)
                if not in_area(x, y, hw):
                    blk[j * self.nx + i] = 1
        return blk

    def route(self, blk, a, c, free=0.35):
        nx, ny = self.nx, self.ny
        ia, ja = self.ij(*a)
        ic, jc = self.ij(*c)
        n = int(free / G)
        for (i, j) in ((ia, ja), (ic, jc)):                 # the end points are own copper
            for dj in range(-n, n + 1):
                for di in range(-n, n + 1):
                    if 0 <= i + di < nx and 0 <= j + dj < ny and di * di + dj * dj <= n * n:
                        blk[(j + dj) * nx + i + di] = 0
        start, goal = ja * nx + ia, jc * nx + ic
        moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        best = {(start, -1): 0.0}
        came = {}
        heap = [(0.0, 0.0, start, -1)]
        end = None
        while heap:
            f, g, nd, d = heapq.heappop(heap)
            if nd == goal:
                end = (nd, d)
                break
            if best.get((nd, d), 1e18) < g:
                continue
            i, j = nd % nx, nd // nx
            for k, (di, dj, cst) in enumerate(moves):
                i2, j2 = i + di, j + dj
                if not (0 <= i2 < nx and 0 <= j2 < ny):
                    continue
                n2 = j2 * nx + i2
                if blk[n2]:
                    continue
                if di and dj and (blk[j * nx + i2] or blk[j2 * nx + i]):
                    continue
                g2 = g + cst + (0.0 if k == d or d < 0 else 0.6)
                if g2 < best.get((n2, k), 1e18):
                    best[(n2, k)] = g2
                    came[(n2, k)] = (nd, d)
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
        for q, (nd, d) in enumerate(cells):
            if 0 < q and q + 1 < len(cells) and cells[q + 1][1] == d:
                continue
            if q == 0:
                continue
            pts.append(self.gxy(nd % nx, nd // nx))
        pts[-1] = c
        return pts


def gap(sa, sb, lo=0.0, hi=3.0):
    for _ in range(16):
        mid = (lo + hi) / 2
        if sa.Collide(sb, F(mid)):
            hi = mid
        else:
            lo = mid
    return lo


def pad_of(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        raise KeyError(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return p
    raise KeyError(f"{ref}-{num}")


def pad_xy(b, ref, num):
    return xy(pad_of(b, ref, num).GetPosition())
