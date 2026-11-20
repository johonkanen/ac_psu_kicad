"""Pass 5: the fanned bus of pass 4 with every run that the router failed drawn by script (run under kipy).

  kipy maze.py fan IN OUT     lanes of the passage north of J11 (In3: relay, sigma-delta pair, five taps, PWM trio;
                              In4: 5V_ISOL, ISOGND, one tap, 15V_ISO, 3V3_ISO), entries and fanned-out exits
  kipy maze.py runs IN OUT    the runs to and from the lanes with a small grid router of its own (A* on a 0.1 mm
                              grid, one layer, 45 degree moves): source pin / via -> lane entry, lane exit -> a via
                              on the old track or beside the pad. Every piece is gated by scripted.Ctx.clear.
  kipy maze.py aux IN OUT     short links in the aux area for pads beside an HV pad (after the router steps)

Lanes (0.152 mm at 0.305 mm; index from the south): In3 0 relay, 1 MDATA_INU, 2 INU_ADCLK, 3 Net-(U7A-+),
4 Net-(U7A--), 5 Net-(U7B--), 6 Net-(U7B-+), 7 Net-(U2--), 8 PWM_TRANS6, 9 PWM_Q7, 10 PWM_Q5.
In4: 5V_ISOL 0.8 mm (0..3), ISOGND 0.4 mm (3..4), Net-(U2-+) (5), 15V_ISO 0.4 mm (6..7), 3V3_ISO 0.4 mm (8..9).
The relay line moved to In3 and one tap to In4: with the taps drawn, a net that starts west of the tap risers
(x 79..81.5) cannot reach an In4 entry east of J4, and an In4 entry west of J4-45 would cross the 5V_ISOL lane.
"""
import heapq
import math
import sys

import pcbnew

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import scripted as S  # noqa: E402

T, F = pcbnew.ToMM, pcbnew.FromMM
G = 0.1
W = S.BUS_W
P = S.LANE_PITCH
IN3, IN4 = pcbnew.In3_Cu, pcbnew.In4_Cu
#           net                 lane entry x
FAN_IN3 = [("GPIO_BYPASS_RLY_ISO", 0, 77.25), ("MDATA_INU", 1, 77.85), ("INU_ADCLK", 2, 78.45),
           ("Net-(U7A-+)", 3, 79.05), ("Net-(U7A--)", 4, 79.65), ("Net-(U7B--)", 5, 80.25),
           ("Net-(U7B-+)", 6, 80.85), ("Net-(U2--)", 7, 81.45),
           ("PWM_TRANS6", 8, 82.38), ("PWM_Q7", 9, 83.64), ("PWM_Q5", 10, 84.92)]
EXIT3 = {i: 34.95 - 0.6 * i for i in range(5)}                 # fanned-out end below the J8 column at x 33.78
EXIT3.update({i: 26.75 - 0.6 * (i - 5) for i in (5, 6, 7)})     # ... and below the column at x 24.89
#           net            lane   width  col x (In3, y 48.9)  via x (y 51.9)  west end x (y 49.4)
FAN_IN4 = [("Net-(U2-+)",  5.0,   W,     98.95,              98.65,          19.65),
           ("15V_ISO",     6.4,   0.4,   99.45,              99.45,          19.05),
           ("3V3_ISO",     8.2,   0.4,   100.05,             100.25,         18.35)]
TAPS = ["Net-(U7A-+)", "Net-(U7A--)", "Net-(U7B--)", "Net-(U7B-+)", "Net-(U2--)", "Net-(U2-+)"]


def fan(b, cx):
    S.MARGIN = 0.002
    for net, i, xe in FAN_IN3:
        mid = S.offset_poly(S.FAN_BASE, i * P)[1:-1]
        y = 52.84 + i * P
        if i <= 7:
            xs = (S.COL_E if i <= 4 else S.COL_W) + 0.61 - (i if i <= 4 else i - 5) * P
            xt = EXIT3[i]
            tail = [(xs, y), (xs, 50.3), (xt, 50.3 - abs(xt - xs)), (xt, 49.4 if i <= 4 else 48.6)]
        elif i == 8:
            tail = [(24.585, y), (24.585, 50.0), (21.715, 50.0), (21.715, 51.565), (21.08, 52.2)]
        elif i == 9:
            tail = [(24.255, y), (24.255, 52.835), (23.62, 52.2)]
        else:
            tail = [(22.985, y), (22.985, 51.565), (23.62, 50.93)]
        err = S._poly(cx, net, IN3, [(xe, 49.3), (xe, y)] + mid + tail, W)
        print(f"fan: In3 lane {i:2d} {net}: " + (err or f"entry ({xe:.2f}, 49.3)" + (f", exit ({EXIT3[i]:.2f}, {49.4 if i <= 4 else 48.6})" if i <= 7 else ", to its J8 pin")))
    d = 0.33
    mid = S.offset_poly(S.FAN_BASE, d)[1:-1]
    err = S._poly(cx, "5V_ISOL", IN4, [(88.15, 50.77), (88.15, 52.84 + d)] + mid + [(22.35, 52.84 + d), (22.35, 52.2)], 0.8)
    err = err or S._poly(cx, "5V_ISOL", IN4, [(57.55, 52.84 + d), (57.55, 52.0)], 0.8)
    print("fan: In4 5V_ISOL 0.8 mm J4-45 -> J6-45 -> J8-45: " + (err or "drawn"))
    d = 1.09
    mid = S.offset_poly(S.FAN_BASE, d)[1:-1]
    err = S._poly(cx, "ISOGND", IN4, [(90.69, 48.82), (90.69, 52.84 + d)] + mid
                  + [(20.25, 52.84 + d), (20.25, 49.9), (22.35, 49.9), (22.35, 50.93)], 0.4, keep=False)
    err = err or S._poly(cx, "ISOGND", IN4, [(88.15, 49.5), (88.15, 48.82)], 0.4, keep=False)     # J4-46 onto the plane edge
    print("fan: In4 ISOGND 0.4 mm plane edge -> J8-46, and J4-46 to the plane edge: " + (err or "drawn"))
    for net, idx, w, xc, xv, xw in FAN_IN4:
        d = idx * P
        mid = S.offset_poly(S.FAN_BASE, d)[1:-1]
        v = cx.via_ok(net, xv, 51.9)
        err = None if v is not None else f"no via at ({xv}, 51.9)"
        if not err:
            cx.commit(v)
            pts3 = [(xc, 48.9), (xc, 51.9 - 0.25 - abs(xv - xc)), (xv, 51.9 - 0.25), (xv, 51.9)]
            err = S._poly(cx, net, IN3, pts3, w)
            err = err or S._poly(cx, net, IN4, [(xv, 51.9), (xv, 52.84 + d)] + mid + [(xw, 52.84 + d), (xw, 49.4)], w)
        print(f"fan: In4 lane {idx} {net} {w} mm: " + (err or f"In3 from ({xc}, 48.9) through the J4 column, via ({xv}, 51.9), west end ({xw}, 49.4)"))


# ---- grid router -------------------------------------------------------------------------------------------------
class Grid:
    def __init__(self, b, layer, box):
        self.b, self.layer = b, layer
        self.x0, self.y0, x1, y1 = box
        self.nx, self.ny = int(round((x1 - self.x0) / G)) + 1, int(round((y1 - self.y0) / G)) + 1
        self.keep = None

    def ij(self, x, y):
        return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def xy(self, i, j):
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

    def keepouts(self):
        """Rule areas that forbid tracks on this layer, grown by 0.27 mm (widest track here 0.4 mm): once per grid."""
        if self.keep is not None:
            return self.keep
        blk = bytearray(self.nx * self.ny)
        m = 0.27
        for z in self.b.Zones():
            if not (z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(self.layer)):
                continue
            if z.GetZoneName().startswith("tmp route domain"):
                continue
            bb = z.GetBoundingBox()
            xa, xb, ya, yb = T(bb.GetLeft()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetTop())
            o = z.Outline()
            if o.OutlineCount() == 1 and o.Outline(0).PointCount() == 4 and o.HoleCount(0) == 0:
                self.rect(blk, xa - m, ya - m, xb + m, yb + m)
                continue
            ia, ja = self.ij(xa - m, ya - m)
            ib, jb = self.ij(xb + m, yb + m)
            for j in range(max(0, ja), min(self.ny, jb + 1)):
                row = j * self.nx
                for i in range(max(0, ia), min(self.nx, ib + 1)):
                    x, y = self.xy(i, j)
                    if any(o.Contains(pcbnew.VECTOR2I(F(x + dx), F(-(y + dy)))) for dx, dy in ((0, 0), (m, 0), (-m, 0), (0, m), (0, -m))):
                        blk[row + i] = 1
        self.keep = blk
        return blk

    def build(self, net, w, walls=()):
        blk = bytearray(self.keepouts())
        hw = w / 2
        xa, ya = self.x0 - 3, self.y0 - 3
        xb, yb = self.x0 + self.nx * G + 3, self.y0 + self.ny * G + 3
        for t in self.b.GetTracks():
            if t.GetNetname() == net:
                continue
            via = t.Type() == pcbnew.PCB_VIA_T
            if not via and t.GetLayer() != self.layer:
                continue
            x, y = T(t.GetStart().x), -T(t.GetStart().y)
            if via:
                if xa < x < xb and ya < y < yb:
                    self.disc(blk, x, y, 0.2286 + 0.15 + hw + 0.06)
                continue
            x1, y1 = T(t.GetEnd().x), -T(t.GetEnd().y)
            if max(x, x1) < xa or min(x, x1) > xb or max(y, y1) < ya or min(y, y1) > yb:
                continue
            r = T(t.GetWidth()) / 2 + 0.15 + hw + 0.06
            L = math.hypot(x1 - x, y1 - y)
            n = max(1, int(L / (G * 0.7)))
            for k in range(n + 1):
                f = k / n
                self.disc(blk, x + f * (x1 - x), y + f * (y1 - y), r)
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                if not p.IsOnLayer(self.layer) or (p.GetNetname() == net and net):
                    continue
                x, y = T(p.GetPosition().x), -T(p.GetPosition().y)
                if not (xa < x < xb and ya < y < yb):
                    continue
                s = p.GetSize(self.layer)
                lc = p.GetLocalClearance()
                c = max(0.15, T(lc) if lc else 0) + hw + 0.06
                bb = p.GetBoundingBox()
                self.rect(blk, T(bb.GetLeft()) - c, -T(bb.GetBottom()) - c, T(bb.GetRight()) + c, -T(bb.GetTop()) + c)
        for r in walls:
            self.rect(blk, *r)
        return blk

    def route(self, blk, a, c):
        """A* from point a to point c; returns the polyline (a, grid points ..., c) or None."""
        nx, ny = self.nx, self.ny
        ia, ja = self.ij(*a)
        ic, jc = self.ij(*c)
        for (i, j) in ((ia, ja), (ic, jc)):                 # the end points are own copper
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    if 0 <= i + di < nx and 0 <= j + dj < ny and abs(di) + abs(dj) < 2:
                        blk[(j + dj) * nx + i + di] = 0
        start, goal = ja * nx + ia, jc * nx + ic
        moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        best = {(start, -1): 0.0}
        came = {}
        heap = [(0.0, 0.0, start, -1)]
        end = None
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
                if blk[n2]:
                    continue
                if di and dj and (blk[j * nx + i2] or blk[j2 * nx + i]):
                    continue
                g2 = g + cst + (0.0 if k == d or d < 0 else 0.4)
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
            if q + 1 < len(cells) and cells[q + 1][1] == d and q > 0:
                continue
            pts.append(self.xy(n % nx, n // nx))
        pts.append(c)
        return pts


def run(cx, grid, net, layer, a, c, w, walls=(), what=""):
    blk = grid.build(net, w, walls)
    pts = grid.route(blk, a, c)
    if pts is None:
        print(f"runs: {net} {what}: NO PATH on the grid from ({a[0]:.2f}, {a[1]:.2f}) to ({c[0]:.2f}, {c[1]:.2f})")
        return False
    S.MARGIN = 0.002
    err = S._poly(cx, net, layer, pts, w)
    L = sum(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(pts, pts[1:]))
    print(f"runs: {net} {what}: " + (f"path found but {err}" if err else f"drawn, {L:.1f} mm, {len(pts) - 1} segments"))
    return not err


def old_track_points(b, net, layer, box, near):
    out = []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() != net or t.GetLayer() != layer:
            continue
        (x0, y0), (x1, y1) = (T(t.GetStart().x), -T(t.GetStart().y)), (T(t.GetEnd().x), -T(t.GetEnd().y))
        L = math.hypot(x1 - x0, y1 - y0)
        for k in range(int(L / 0.25) + 1):
            f = k * 0.25 / L if L else 0
            x, y = x0 + f * (x1 - x0), y0 + f * (y1 - y0)
            if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                out.append((math.hypot(x - near[0], y - near[1]), x, y))
    return [(x, y) for _, x, y in sorted(out)]


def to_old_track(b, cx, grid, net, layer, a, w, box=(0.5, 36.5, 40.0, 52.5)):
    """A via on the net's old In2 track where one is legal and the grid router reaches it from a."""
    legal = 0
    for x, y in old_track_points(b, net, pcbnew.In2_Cu, box, a):
        v = cx.via_ok(net, x, y)
        if v is None:
            continue
        legal += 1
        if legal > 8:
            break
        blk = grid.build(net, w)
        pts = grid.route(blk, a, (x, y))
        if pts is None:
            continue
        S.MARGIN = 0.002
        cx.commit(v)
        err = S._poly(cx, net, layer, pts, w)
        print(f"runs: {net} west end: via on the old In2 track at ({x:.2f}, {y:.2f}); " + (f"path found but {err}" if err else "drawn"))
        return not err
    print(f"runs: {net} west end: {legal} legal via points on the old In2 track tried, NOT reached")
    return False


def pad_of(b, ref, num):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]


def new_via_at(b, cx, ref, num, rmax=3.0):
    pad = pad_of(b, ref, num)
    before = {(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T}
    S.MARGIN = 0.02
    if S.via_at_pad(cx, pad, pad.GetNetname(), rmax, 0.2) is None:
        return None
    return [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T
            and (t.GetPosition().x, t.GetPosition().y) not in before][0]


def runs(b, cx):
    east3 = Grid(b, IN3, (59.95, -22.05, 112.05, 50.55))
    west3 = Grid(b, IN3, (0.55, 36.45, 40.05, 52.55))
    west4 = Grid(b, IN4, (0.55, 36.45, 40.05, 52.55))
    entry = {net: (xe, 49.3) for net, i, xe in FAN_IN3}
    exit3 = {net: (EXIT3[i], 49.4 if i <= 4 else 48.6) for net, i, xe in FAN_IN3 if i <= 7}
    # --- sources at the isolators: via beside the pin, In3 to the lane entry. Relay first (westmost entry).
    for net, ref, num in (("GPIO_BYPASS_RLY_ISO", "U19", "15"), ("MDATA_INU", "U21", "12"), ("INU_ADCLK", "U21", "14"),
                          ("PWM_TRANS6", "U20", "10"), ("PWM_Q7", "U20", "11"), ("PWM_Q5", "U20", "12")):
        v = new_via_at(b, cx, ref, num, 2.5)
        if v is None:
            print(f"runs: {net}: NO PLACE for a via within 2.5 mm of {ref}-{num}")
            continue
        run(cx, east3, net, IN3, v, entry[net], W, what=f"{ref}-{num} via ({v[0]:.2f}, {v[1]:.2f}) -> lane entry")
    # --- the divider taps from the vias at the U7 / U2 inputs: north along x >= 100.1, west under the U20 pins
    #     (south of their vias: wall above y 40.75 east of x 81.9), up to the lane entries. Lane order.
    wall = [(81.9, 40.75, 112.0, 50.5)]
    for net in ["Net-(U2--)", "Net-(U7B-+)", "Net-(U7B--)", "Net-(U7A--)", "Net-(U7A-+)", "Net-(U2-+)"]:   # eastmost entry first
        vs = [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T
              and t.GetNetname() == net and T(t.GetPosition().x) > 90]
        if not vs:
            print(f"runs: {net}: no via at the U7 / U2 block")
            continue
        if net in entry:
            run(cx, east3, net, IN3, vs[0], entry[net], W, wall, what=f"block via ({vs[0][0]:.2f}, {vs[0][1]:.2f}) -> lane entry")
        else:               # the In4 tap: on to the J4 column at x 99.58
            run(cx, east3, net, IN3, vs[0], (98.95, 48.9), W, what=f"block via ({vs[0][0]:.2f}, {vs[0][1]:.2f}) -> J4 column (In4 lane)")
    # --- 15V_ISO from the through-hole pin U8-1, 3V3_ISO from a new via into its In2 plane, to the J4 column
    p = pad_of(b, "U8", "1")
    run(cx, east3, "15V_ISO", IN3, (T(p.GetPosition().x), -T(p.GetPosition().y)), (99.45, 48.9), 0.4, what="U8-1 -> J4 column (In4 lane)")
    v = None
    for x, y in ((104.05, 40.35), (105.05, 40.35), (106.05, 40.35), (108.55, 40.35), (108.55, 42.05), (110.05, 44.05), (104.05, 38.55)):
        v = cx.via_ok("3V3_ISO", x, y)
        if v is not None:
            cx.commit(v)
            run(cx, east3, "3V3_ISO", IN3, (x, y), (100.05, 48.9), 0.4, what=f"plane via ({x}, {y}) -> J4 column (In4 lane)")
            break
    if v is None:
        print("runs: 3V3_ISO: no place for a plane via among the points tried")
    # --- west ends on In3: relay and taps onto their old In2 tracks, the sigma-delta pair to vias at R50-2 / U4-7
    for net, ref, num in (("MDATA_INU", "R50", "2"), ("INU_ADCLK", "U4", "7")):
        v = new_via_at(b, cx, ref, num)
        if v is None:
            print(f"runs: {net} west end: NO PLACE for a via within 3 mm of {ref}-{num}")
        else:
            run(cx, west3, net, IN3, exit3[net], v, W, what=f"west end -> via ({v[0]:.2f}, {v[1]:.2f}) at {ref}-{num}")
    for net in ["Net-(U2--)", "Net-(U7B-+)", "Net-(U7B--)", "Net-(U7A--)", "Net-(U7A-+)", "GPIO_BYPASS_RLY_ISO"]:
        to_old_track(b, cx, west3, net, IN3, exit3[net], W)
    # --- west ends on In4, around the west end of J8
    xw = {net: (x, 49.4) for net, _, _, _, _, x in FAN_IN4}
    to_old_track(b, cx, west4, "Net-(U2-+)", IN4, xw["Net-(U2-+)"], W)
    to_old_track(b, cx, west4, "15V_ISO", IN4, xw["15V_ISO"], 0.4)
    for ref, num in (("U4", "8"), ("C37", "2")):
        v = new_via_at(b, cx, ref, num)
        if v is not None:
            run(cx, west4, "3V3_ISO", IN4, xw["3V3_ISO"], v, 0.4, what=f"west end -> via ({v[0]:.2f}, {v[1]:.2f}) at {ref}-{num}")
            break
    else:
        print("runs: 3V3_ISO west end: NO PLACE for a via at U4-8 or C37-2")


def aux(b, cx):
    """Short links in the aux area: a pad that is still alone on its net gets a link to the nearest copper of the net
    on its own layer (HV rule per pad as in scripted.Ctx.need)."""
    S.MARGIN = 0.02
    todo = [("C68", "1"), ("C112", "2"), ("C114", "2"), ("R102", "2"), ("C145", "2"), ("R105", "2"), ("R101", "1"),
            ("C112", "1"), ("R143", "2")]
    for ref, num in todo:
        pad = pad_of(b, ref, num)
        net = pad.GetNetname()
        _, x, y, layer, smin, smax = S.pad_info(pad)
        ps = pad.GetEffectiveShape(layer)
        if any(t.GetNetname() == net and (t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == layer)
               and ps.Collide(t.GetEffectiveShape(layer), 0) for t in b.GetTracks()):
            print(f"aux: {ref}-{num} {net}: has copper already")
            continue
        cand = []
        for t in b.GetTracks():
            if t.GetNetname() != net:
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                cand.append((T(t.GetPosition().x), -T(t.GetPosition().y)))
            elif t.GetLayer() == layer:
                cand += [(T(t.GetStart().x), -T(t.GetStart().y)), (T(t.GetEnd().x), -T(t.GetEnd().y))]
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net and p is not pad and p.IsOnLayer(layer) and (fp.GetReference(), p.GetNumber()) != (ref, num):
                    cand.append((T(p.GetPosition().x), -T(p.GetPosition().y)))
        cand = sorted((math.hypot(cx_ - x, cy_ - y), cx_, cy_) for cx_, cy_ in cand if 0.2 < math.hypot(cx_ - x, cy_ - y) < 8.0)
        done = None
        for d, tx, ty in cand[:12]:
            if S.link(cx, net, (x, y), (tx, ty), layer=layer, w=min(0.3, smin)):
                done = (tx, ty, d)
                break
        print(f"aux: {ref}-{num} {net} ({x:.1f}, {y:.1f}): " + (f"linked to ({done[0]:.2f}, {done[1]:.2f}), {done[2]:.1f} mm away" if done
                                                             else f"NO legal link to any of {min(len(cand), 12)} nearest points of the net"))


def main():
    mode, src, dst = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    cx = S.Ctx(b)
    {"fan": fan, "runs": runs, "aux": aux}[mode](b, cx)
    b.Save(dst)


main()
