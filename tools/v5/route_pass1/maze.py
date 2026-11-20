"""Pass 5: the fanned bus of pass 4 with every run that the router failed drawn by script (run under kipy).

  kipy maze.py fan IN OUT     lanes of the passage north of J11 (In3: relay, sigma-delta pair, five taps, PWM trio;
                              In4: 5V_ISOL, ISOGND, one tap, 15V_ISO, 3V3_ISO), entries and fanned-out exits
  kipy maze.py runs IN OUT    the runs to and from the lanes with a small grid router of its own (A* on a 0.1 mm
                              grid, one layer, 45 degree moves): source pin / via -> lane entry, lane exit -> a via
                              on the old track or beside the pad. Every piece is gated by scripted.Ctx.clear.
  kipy maze.py aux IN OUT     short links in the aux area for pads beside an HV pad (after the router steps)

Lanes (0.152 mm at 0.305 mm; index from the south): In3 0 relay, 1 MDATA_INU, 2 INU_ADCLK, 3..7 five taps
(taps as TAP_ORDER below), 8 PWM_TRANS6, 9 PWM_Q7, 10 PWM_Q5.
In4: 5V_ISOL 0.8 mm (0..3), ISOGND 0.4 mm (3..4), the sixth tap (5), 15V_ISO 0.4 mm (6..7), 3V3_ISO 0.4 mm (8..9).
The relay line moved to In3 and one tap to In4: with the taps drawn, a net that starts west of the tap risers
(x 79..81.5) cannot reach an In4 entry east of J4, and an In4 entry west of J4-45 would cross the 5V_ISOL lane.
"""
import heapq
import math
import os
import sys

import pcbnew

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import scripted as S  # noqa: E402

T, F = pcbnew.ToMM, pcbnew.FromMM
G = 0.1
W = S.BUS_W
P = S.LANE_PITCH
IN3, IN4 = pcbnew.In3_Cu, pcbnew.In4_Cu
# The five In3 taps in lane order (south to north = west to east in the corridor x >= 100.1 = the order they are
# routed in), then the tap that takes the In4 lane. Nets from the U2 side come up west of U7 and so lie inside the
# U7A pair; the U7B via east of U7 is the outermost and takes the In4 lane. MAZE_TAPS overrides (testing).
TAP_ORDER = (os.environ.get("MAZE_TAPS") or "Net-(U2-+),Net-(U2--),Net-(U7A-+),Net-(U7A--),Net-(U7B-+),Net-(U7B--)").split(",")
FAN_IN3 = ([("GPIO_BYPASS_RLY_ISO", 0, 77.25), ("MDATA_INU", 1, 77.85), ("INU_ADCLK", 2, 78.45)]
           + [(n, 3 + k, 79.05 + 0.6 * k) for k, n in enumerate(TAP_ORDER[:5])]
           + [("PWM_TRANS6", 8, 82.38), ("PWM_Q7", 9, 83.64), ("PWM_Q5", 10, 84.92)])
EXIT3 = {i: (33.78 if i == 2 else 34.95 - 0.6 * i) for i in range(5)}                 # fanned-out end below the J8 column at x 33.78
EXIT3.update({i: 26.75 - 0.6 * (i - 5) for i in (5, 6, 7)})     # ... and below the column at x 24.89
#           net            lane   width  col x  via x (y 51.9)  west end x  In3 goal        In4: west at y, climb from x
FAN_IN4 = [(TAP_ORDER[5],  5.0,   W,     98.95, 98.65,          19.65,      (98.15, 47.5),  52.55, 92.90),
           ("15V_ISO",     6.45,  0.4,   99.45, 99.45,          19.05,      (99.45, 47.2),  53.05, 93.10),
           ("3V3_ISO",     8.3,   0.4,   100.05, 100.25,        18.35,      (100.85, 47.5), 53.65, 93.31)]


def fan(b, cx):
    S.MARGIN = 0.002
    for net, i, xe in FAN_IN3:
        mid = S.offset_poly(S.FAN_BASE, i * P)[1:-1]
        y = 52.84 + i * P
        if i <= 7:
            xs = (S.COL_E if i <= 4 else S.COL_W) + 0.61 - (i if i <= 4 else i - 5) * P
            xt = EXIT3[i]
            # parallel 45 degree pieces need 0.43 mm between their starts: the one that shifts most starts highest
            ys = 50.3 - 0.13 * {0: 0, 1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 1, 7: 2}[i]
            tail = [(xs, y), (xs, ys), (xt, ys - abs(xt - xs)), (xt, 49.4 if i <= 4 else 48.6)]
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
    for net, idx, w, xc, xv, xw, goal, ya, xk in FAN_IN4:
        d = idx * P
        mid = S.offset_poly(S.FAN_BASE, d)[1:-1]
        v = cx.via_ok(net, xv, 51.9)
        err = None if v is not None else f"no via at ({xv}, 51.9)"
        if not err:
            cx.commit(v)
            pts3 = [goal, (xc, 47.5 + abs(goal[0] - xc)), (xc, 51.9 - 0.25 - abs(xv - xc)), (xv, 51.9 - 0.25), (xv, 51.9)]
            err = S._poly(cx, net, IN3, pts3, w)
            yl = 52.84 + d
            err = err or S._poly(cx, net, IN4, [(xv, 51.9), (xv, ya), (xk, ya), (xk - (yl - ya), yl)] + mid + [(xw, yl), (xw, 49.4)], w)
        print(f"fan: In4 lane {idx} {net} {w} mm: " + (err or f"In3 from {goal} through the J4 column, via ({xv}, 51.9), west end ({xw}, 49.4)"))


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

    def build(self, net, w, walls=(), hv=False):
        blk = bytearray(self.keepouts())
        hw = w / 2

        def clr(onet, lc=0.0):
            if hv and onet and ((net in S.HV) != (onet in S.HV)):
                return lc if (lc and onet in S.HV) else 2.5
            if hv and net in S.HV and onet in S.HV:
                return max(1.0, lc)
            return max(0.15, lc)
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
                    self.disc(blk, x, y, 0.2286 + clr(t.GetNetname()) + hw + 0.06)
                continue
            x1, y1 = T(t.GetEnd().x), -T(t.GetEnd().y)
            if max(x, x1) < xa or min(x, x1) > xb or max(y, y1) < ya or min(y, y1) > yb:
                continue
            r = T(t.GetWidth()) / 2 + clr(t.GetNetname()) + hw + 0.06
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
                c = clr(p.GetNetname(), T(lc) if lc else 0.0) + hw + 0.06
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
        if legal > 30:
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
    #     Order: the tap with the westmost entry lies southmost in the band and westmost in the corridor, so it goes
    #     first, under its own ceiling (0.5 mm per tap below the wall); the others nest outside it.
    goal4 = {net: goal for net, _, _, _, _, _, goal, _, _ in FAN_IN4}
    for k, net in enumerate(TAP_ORDER):
        # pass 7: the wall ends at x 89.6 (east of the U20 pins there is nothing to stay under, and the fixed vias
        # at (90.0, 38.7) and (91.3, 40.15) of v5 step 19 stand in the band); ceilings 0.6 mm apart
        # (0.6 mm apart filled the band down to y 38.5 and left no room for the sigma-delta pair to U6: 0.5 mm)
        wall = [(81.9, 40.9 - 0.5 * (4 - k), 89.6, 50.5)]
        vs = [(T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T
              and t.GetNetname() == net and T(t.GetPosition().x) > 90 and -T(t.GetPosition().y) < 20]
        if not vs:
            print(f"runs: {net}: no via at the U7 / U2 block")
            continue
        goal, wl = (entry[net], wall) if net in entry else (goal4[net], ())
        ok = run(cx, east3, net, IN3, vs[0], goal, W, wl, what=f"block via ({vs[0][0]:.2f}, {vs[0][1]:.2f}) -> " + ("lane entry" if net in entry else "J4 column (In4 lane)"))
        if not ok:
            for fp in b.GetFootprints():
                for pd in fp.Pads():
                    if ok or pd.GetNetname() != net or pd.HasHole() or T(pd.GetPosition().x) < 90 or fp.GetReference().startswith("U"):
                        continue
                    v = new_via_at(b, cx, fp.GetReference(), pd.GetNumber(), 2.5)
                    if v is not None:
                        ok = run(cx, east3, net, IN3, v, goal, W, wl, what=f"second try, via ({v[0]:.2f}, {v[1]:.2f}) at {fp.GetReference()}-{pd.GetNumber()} ->")
    # --- 15V_ISO from the through-hole pin U8-1, 3V3_ISO from a new via into its In2 plane, to the J4 column
    p = pad_of(b, "U8", "1")
    run(cx, east3, "15V_ISO", IN3, (T(p.GetPosition().x), -T(p.GetPosition().y)), goal4["15V_ISO"], 0.4, what="U8-1 -> J4 column (In4 lane)")
    done = False
    for n in range(60):
        x, y = 103.05 + 0.5 * (n % 20), 40.35 - 0.5 * (n // 20)
        v = cx.via_ok("3V3_ISO", x, y)
        if v is None:
            continue
        pts = east3.route(east3.build("3V3_ISO", 0.4), (x, y), goal4["3V3_ISO"])
        if pts is None:
            continue
        cx.commit(v)
        S.MARGIN = 0.002
        err = S._poly(cx, "3V3_ISO", IN3, pts, 0.4)
        print(f"runs: 3V3_ISO plane via ({x:.2f}, {y:.2f}) -> J4 column (In4 lane): " + (f"path found but {err}" if err else "drawn"))
        done = True
        break
    if not done:
        print("runs: 3V3_ISO: no plane via place in x 103..113, y 39.3..40.4 from which the J4 column is reached")
    # --- west ends on In3: relay and taps onto their old In2 tracks, the sigma-delta pair to vias at R50-2 / U4-7
    xw = {net: (x, 49.4) for net, _, _, _, _, x, _, _, _ in FAN_IN4}
    to_old_track(b, cx, west4, TAP_ORDER[5], IN4, xw[TAP_ORDER[5]], W)
    for net, ref, num in (("INU_ADCLK", "U4", "7"), ("MDATA_INU", "R50", "2")):
        v = new_via_at(b, cx, ref, num)
        if v is None:
            print(f"runs: {net} west end: NO PLACE for a via within 3 mm of {ref}-{num}")
        else:
            run(cx, west3, net, IN3, exit3[net], v, W, what=f"west end -> via ({v[0]:.2f}, {v[1]:.2f}) at {ref}-{num}")
    to_old_track(b, cx, west3, "GPIO_BYPASS_RLY_ISO", IN3, exit3["GPIO_BYPASS_RLY_ISO"], W)
    for net in [TAP_ORDER[4], TAP_ORDER[3], TAP_ORDER[2], TAP_ORDER[1], TAP_ORDER[0]]:      # west exits first
        to_old_track(b, cx, west3, net, IN3, exit3[net], W)
    # --- west ends on In4, around the west end of J8
    to_old_track(b, cx, west4, "15V_ISO", IN4, xw["15V_ISO"], 0.4)
    for ref, num in (("U4", "8"), ("C37", "2")):
        v = new_via_at(b, cx, ref, num)
        if v is not None:
            run(cx, west4, "3V3_ISO", IN4, xw["3V3_ISO"], v, 0.4, what=f"west end -> via ({v[0]:.2f}, {v[1]:.2f}) at {ref}-{num}")
            break
    else:
        print("runs: 3V3_ISO west end: NO PLACE for a via at U4-8 or C37-2")


def aux(b, cx):
    """Pass 7: short links in the aux area (x 64..110, y -58..-2), driven by the open connections of a DRC run made just
    before (AUX_DRC = its JSON report). For each open pair on one outer layer: a simple link, else the grid router
    with the HV rule in its obstacle map; every segment gated by Ctx.clear (per-pad rule). Pairs on two different
    layers are reported, not drawn (they need a via)."""
    import json
    import re
    S.MARGIN = 0.02
    rep = json.load(open(os.environ["AUX_DRC"]))
    for u in rep.get("unconnected_items", []):
        its = u["items"]
        m = re.search(r"\[([^\]]+)\]", its[0]["description"])
        net = m.group(1) if m else ""
        pts = [(i["pos"]["x"], -i["pos"]["y"]) for i in its]
        if len(pts) != 2 or any(not (64 <= x <= 110 and -58 <= y <= -2) for x, y in pts) or any(i["description"].startswith("Zone") for i in its):
            continue
        lays = [re.search(r" on (\S+\.Cu)", i["description"]) for i in its]
        lays = [x.group(1) if x and " - " not in i["description"] else None for x, i in zip(lays, its)]
        what = " | ".join(i["description"][:40] for i in its)
        d = math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1])
        named = {x for x in lays if x}
        if len(named) > 1 or (named and not named & {"F.Cu", "B.Cu"}):
            print(f"aux: {net} ({pts[0][0]:.1f}, {pts[0][1]:.1f}) - ({pts[1][0]:.1f}, {pts[1][1]:.1f}), {d:.1f} mm: on {' and '.join(sorted(named))}, needs a via: not drawn [{what}]")
            continue
        done = None
        for ln in (sorted(named) or ["F.Cu", "B.Cu"]):
            layer = b.GetLayerID(ln)
            w = 0.3
            if S.link(cx, net, pts[0], pts[1], layer=layer, w=w):
                done = ln + ", simple link"
                break
            if d < 30:
                g = Grid(b, layer, (math.floor(min(pts[0][0], pts[1][0]) - 6) + 0.05, math.floor(min(pts[0][1], pts[1][1]) - 6) + 0.05,
                                    math.ceil(max(pts[0][0], pts[1][0]) + 6) + 0.05, math.ceil(max(pts[0][1], pts[1][1]) + 6) + 0.05))
                p = g.route(g.build(net, w, hv=True), pts[0], pts[1])
                if p is not None and S._poly(cx, net, layer, p, w) is None:
                    done = ln + ", grid router"
                    break
        print(f"aux: {net} ({pts[0][0]:.1f}, {pts[0][1]:.1f}) - ({pts[1][0]:.1f}, {pts[1][1]:.1f}), {d:.1f} mm: "
              + (f"drawn on {done}" if done else "NO legal link on " + " / ".join(sorted(named) or ["F.Cu", "B.Cu"])) + f" [{what}]")


def aux_hv_runs(b, cx):
    """AUX_VIN (R136-1 group to the trunk at R98-2) and AUX_LOVP (R143-2 to the rest of the net): F.Cu, grid router
    with the HV rule in its obstacle map, every segment gated by Ctx.clear (per-pad rule)."""
    g = Grid(b, pcbnew.F_Cu, (64.05, -56.05, 84.05, -2.05))
    S.MARGIN = 0.02
    jobs = [("AUX_VIN", "R136", "1", [("R98", "2")]), ("AUX_LOVP", "R143", "2", None)]
    for net, ref, num, targets in jobs:
        pad = pad_of(b, ref, num)
        a = (T(pad.GetPosition().x), -T(pad.GetPosition().y))
        if targets:
            goals = [(T(pad_of(b, r, n).GetPosition().x), -T(pad_of(b, r, n).GetPosition().y)) for r, n in targets]
        else:
            goals = sorted(((T(t.GetPosition().x), -T(t.GetPosition().y)) for t in b.GetTracks()
                            if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net),
                           key=lambda q: math.hypot(q[0] - a[0], q[1] - a[1]))[:4]
        done = False
        for c in goals:
            pts = g.route(g.build(net, 0.3, hv=True), a, c)
            if pts is None:
                continue
            err = S._poly(cx, net, pcbnew.F_Cu, pts, 0.3)
            print(f"aux: {net} {ref}-{num} -> ({c[0]:.2f}, {c[1]:.2f}) on F.Cu: " + (f"path found but {err}" if err else "drawn"))
            done = not err
            if done:
                break
        if not done:
            print(f"aux: {net} {ref}-{num}: no legal F.Cu path to {len(goals)} target(s) under the 2.5 mm rule")


def main():
    mode, src, dst = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    cx = S.Ctx(b)
    {"fan": fan, "runs": runs, "aux": aux}[mode](b, cx)
    b.Save(dst)


main()
