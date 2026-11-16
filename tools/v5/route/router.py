#!/usr/bin/env python3
"""Grid maze router for the card area (system python3 with numpy, scipy, PIL; no pcbnew).

Reads the geometry written by extract.py, rasters every copper layer on a 0.05 mm grid and routes one
connection at a time with the A* core in astar.c. Rules built in (routing_brief.md):
  * clearance 0.15 mm to other nets, 0.25 mm to Edge.Cuts (slots), hole to hole 0.25 mm;
  * a net keeps the insulation gap of tools/v4/domains.py (5.0 / 2.5 mm) from the copper AND from the
    card_layout.AREAS polygons of the other domains, on all layers together;
  * nothing in a barrier strip (rule areas), no via and no F.Cu/B.Cu track in the DC bus band, F.Cu, B.Cu
    and In4 free in the corridor north of J11, new copper only in the `unrouted` rectangles of lib/v5_copper.csv;
  * In1/In4 are never routed; In2 only when a connection names it.
All coordinates mm, IPC frame (Y up). The result is a list of tracks and vias (JSON) for apply.py.
"""
import ctypes
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools", "v5"))
sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
import card_layout as L  # noqa: E402

G = 0.05
CU = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
LI = {n: i for i, n in enumerate(CU)}
CLR = 0.15
EDGE_EXTRA = 0.10          # Edge.Cuts: 0.25 mm
EPS = 0.045                # raster margin
VIA_D, VIA_DRILL = 0.4572, 0.3
VR = VIA_D / 2
HOLE2HOLE = 0.25
GAP = {frozenset("PI"): 5.0, frozenset("PE"): 2.5, frozenset("IE"): 2.5, frozenset("PC"): 5.0, frozenset("IC"): 5.0}
UNROUTED = [(22.0, -22.0, 118.65, 54.0), (85.0, -40.0, 118.65, -22.0), (0.0, 36.0, 22.0, 54.0)]
BUS_BAND = L.BUS_BAND
J11_NORTH = (40.0, 51.1, 56.0, 55.0)


def _lib():
    so = os.path.join(ROOT, "build", "route", "astar.so")
    src = os.path.join(HERE, "astar.c")
    if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(so), exist_ok=True)
        subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", so, src], check=True)
    lib = ctypes.CDLL(so)
    lib.route.restype = ctypes.c_int
    return lib


def circle(x, y, r, n=24):
    return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def stadium(a, b, w, n=10):
    r = w / 2
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    pts = [(b[0] + r * math.cos(ang - math.pi / 2 + math.pi * k / n), b[1] + r * math.sin(ang - math.pi / 2 + math.pi * k / n)) for k in range(n + 1)]
    pts += [(a[0] + r * math.cos(ang + math.pi / 2 + math.pi * k / n), a[1] + r * math.sin(ang + math.pi / 2 + math.pi * k / n)) for k in range(n + 1)]
    return pts


class Router:
    def __init__(self, extract, log=None):
        with open(extract) as f:
            d = json.load(f)
        self.d = d
        self.X0, self.Y0, x1, y1 = d["win"]
        self.W = int(round((x1 - self.X0) / G)) + 1
        self.H = int(round((y1 - self.Y0) / G)) + 1
        self.dom = d["dom"]
        self.netid = {}
        self.own = np.zeros((6, self.H, self.W), np.int16)
        self.holes = np.zeros((self.H, self.W), bool)       # every drilled hole (hole-to-hole rule)
        self.padany = np.zeros((self.H, self.W), bool)      # every SMD pad (no via in a pad)
        self.dommask = {k: np.zeros((self.H, self.W), bool) for k in "PICE"}
        self.pads = {f"{p['ref']}-{p['num']}": p for p in d["pads"]}
        self.tracks = list(d["tracks"])
        self.vias = list(d["vias"])
        self.new_tracks, self.new_vias = [], []
        self.planefill = {}
        self.lib = _lib()
        self._pf = {}
        self.logf = log
        self.failed = []
        self._build()

    # -- grid -------------------------------------------------------------------------------
    def ix(self, x):
        return int(round((x - self.X0) / G))

    def iy(self, y):
        return int(round((y - self.Y0) / G))

    def xy(self, ix, iy):
        return round(self.X0 + ix * G, 4), round(self.Y0 + iy * G, 4)

    def nid(self, net):
        if not net:
            return -1
        if net not in self.netid:
            self.netid[net] = len(self.netid) + 1
        return self.netid[net]

    def log(self, s):
        print(s)
        if self.logf:
            self.logf.write(s + "\n")

    def _mask(self, rings_list, grow=0.0):
        """(x0, y0, mask) of polygons [[outline, hole, ...], ...] on the grid."""
        xs = [p[0] for rings in rings_list for p in rings[0]]
        ys = [p[1] for rings in rings_list for p in rings[0]]
        if not xs:
            return None
        gx0, gx1 = max(0, self.ix(min(xs) - grow) - 2), min(self.W - 1, self.ix(max(xs) + grow) + 2)
        gy0, gy1 = max(0, self.iy(min(ys) - grow) - 2), min(self.H - 1, self.iy(max(ys) + grow) + 2)
        if gx1 < gx0 or gy1 < gy0:
            return None
        im = Image.new("L", (gx1 - gx0 + 1, gy1 - gy0 + 1), 0)
        dr = ImageDraw.Draw(im)
        for rings in rings_list:
            for k, ring in enumerate(rings):
                pts = [((p[0] - self.X0) / G - gx0 + 0.5, (p[1] - self.Y0) / G - gy0 + 0.5) for p in ring]   # pixel i spans [i, i + 1)
                if len(pts) >= 3:
                    dr.polygon(pts, fill=0 if k else 1)
        m = np.asarray(im, bool)
        if grow > 0:
            m = ndimage.distance_transform_edt(~m) * G <= grow
        return gx0, gy0, m

    def _paint(self, arr2d, rings_list, val, grow=0.0):
        r = self._mask(rings_list, grow)
        if r is None:
            return
        gx0, gy0, m = r
        arr2d[gy0:gy0 + m.shape[0], gx0:gx0 + m.shape[1]][m] = val

    def _paint_dom(self, net, rings_list):
        dm = self.dom.get(net)
        if dm:
            self._paint(self.dommask[dm], rings_list, True)

    def _build(self):
        d = self.d
        for z in d["zones"]:
            li = LI[z["layer"]]
            self._paint_dom(z["net"], z["fill"])
            if z["layer"] in ("In1.Cu", "In2.Cu", "In4.Cu"):
                self.planefill.setdefault((z["net"], z["layer"]), []).extend(z["fill"])
                continue        # planes and inner pours are refilled around new vias
            self._paint(self.own[li], z["fill"], self.nid(z["net"]))
        for t in self.tracks:
            self._add_track_raster(t)
        for p in d["pads"]:
            for ln, rings in p["layers"].items():
                self._paint(self.own[LI[ln]], rings, self.nid(p["net"]))
                self._paint_dom(p["net"], rings)
            if p["drill"][0] > 0:
                r = max(p["drill"]) / 2
                self._paint(self.holes, [[circle(p["x"], p["y"], r)]], True)
                if not p["layers"]:
                    for li in range(6):
                        self._paint(self.own[li], [[circle(p["x"], p["y"], r + EDGE_EXTRA)]], -1)
            else:
                for ln, rings in p["layers"].items():
                    self._paint(self.padany, rings, True)
        for v in self.vias:
            self._add_via_raster(v)
        for e in d["edge"]:
            for li in range(6):
                self._paint(self.own[li], e, -1, grow=EDGE_EXTRA)
        rule = np.zeros((self.H, self.W), bool)       # barrier strips: no copper inside, no clearance beyond
        for r in d["rules"]:
            if r["no_tracks"]:
                self._paint(rule, r["poly"], True)
        self.ruledist = ndimage.distance_transform_edt(~rule).astype(np.float32) * G
        for k, (dm, poly) in L.AREAS.items():
            self._paint(self.dommask[dm], [[poly]], True)
        for poly in L.I_AROUND_CA:
            self._paint(self.dommask["I"], [[poly]], True)
        # slack[X] = distance to the nearest copper / area of another domain, minus the gap required
        self.slack = {}
        dist = {k: (ndimage.distance_transform_edt(~m).astype(np.float32) * G if m.any() else None) for k, m in self.dommask.items()}
        for x in "PIC":
            s = np.full((self.H, self.W), 99.0, np.float32)
            for o in "PICE":
                g = GAP.get(frozenset(x + o))
                if o != x and g and dist[o] is not None:
                    np.minimum(s, dist[o] - g, out=s)
            self.slack[x] = s
        # where new copper may be at all
        self.allowed = np.zeros((self.H, self.W), bool)
        for x0, y0, x1, y1 in UNROUTED:
            self.allowed[self.iy(y0):self.iy(y1) + 1, self.ix(x0):self.ix(x1) + 1] = True
        self.allowed = ndimage.binary_erosion(self.allowed, iterations=2)
        self.edge_in = ndimage.distance_transform_edt(self.allowed).astype(np.float32) * G     # depth inside the rectangles

    def _add_track_raster(self, t):
        li = LI[t["layer"]]
        # PIL fills every pixel a polygon touches: draw tracks and vias half a cell smaller
        w = max(t["w"] - G, G)
        poly = [[stadium(t["a"], t["b"], w)]] if t["a"] != t["b"] else [[circle(t["a"][0], t["a"][1], w / 2)]]
        self._paint(self.own[li], poly, self.nid(t["net"]))
        self._paint_dom(t["net"], poly)

    def _add_via_raster(self, v):
        c = [[circle(v["x"], v["y"], v["d"] / 2 - G / 2)]]
        for li in range(6):
            self._paint(self.own[li], c, self.nid(v["net"]))
        self._paint_dom(v["net"], c)
        self._paint(self.holes, [[circle(v["x"], v["y"], v["drill"] / 2)]], True)

    # -- adding copper ----------------------------------------------------------------------
    def add_track(self, net, layer, pts, w, check=True):
        """Polyline track. Returns False (and adds nothing) if check finds it too close to something."""
        segs = [(tuple(a), tuple(b)) for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 1e-6]
        if check:
            bad = self.check_track(net, layer, pts, w)
            if bad:
                self.log(f"  !! track {net} {layer} {pts}: {bad}")
                return False
        for a, b in segs:
            t = {"net": net, "layer": layer, "w": w, "a": [round(a[0], 4), round(a[1], 4)], "b": [round(b[0], 4), round(b[1], 4)]}
            self.tracks.append(t)
            self.new_tracks.append(t)
            self._add_track_raster(t)
        return True

    def add_via(self, net, x, y, check=True, in_pad=False):
        if check:
            bad = self.check_via(net, x, y, in_pad)
            if bad:
                self.log(f"  !! via {net} ({x}, {y}): {bad}")
                return False
        v = {"net": net, "x": round(x, 4), "y": round(y, 4), "d": VIA_D, "drill": VIA_DRILL}
        self.vias.append(v)
        self.new_vias.append(v)
        self._add_via_raster(v)
        return True

    def _win(self, x0, y0, x1, y1, halo):
        gx0, gx1 = max(0, self.ix(x0 - halo)), min(self.W - 1, self.ix(x1 + halo))
        gy0, gy1 = max(0, self.iy(y0 - halo)), min(self.H - 1, self.iy(y1 + halo))
        return gx0, gy0, gx1 + 1, gy1 + 1

    def _fdist(self, li, nid, win):
        gx0, gy0, gx1, gy1 = win
        o = self.own[li, gy0:gy1, gx0:gx1]
        foreign = (o != 0) & (o != nid)
        if not foreign.any():
            return np.full(o.shape, 99.0, np.float32)
        return ndimage.distance_transform_edt(~foreign).astype(np.float32) * G

    def _static_block(self, layer, win):
        """Cells closed for any new track centre on this layer (rules of the brief)."""
        gx0, gy0, gx1, gy1 = win
        b = ~self.allowed[gy0:gy1, gx0:gx1]
        rects = []
        if layer in ("F.Cu", "B.Cu"):
            rects.append(BUS_BAND)
        if layer in ("F.Cu", "B.Cu", "In4.Cu"):
            rects.append(J11_NORTH)
        for x0, y0, x1, y1 in rects:
            a, c = max(gx0, self.ix(x0 - 0.3)), min(gx1, self.ix(x1 + 0.3) + 1)
            e, f = max(gy0, self.iy(y0 - 0.3)), min(gy1, self.iy(y1 + 0.3) + 1)
            if a < c and e < f:
                b[e - gy0:f - gy0, a - gx0:c - gx0] = True
        return b

    def _novia(self, win):
        gx0, gy0, gx1, gy1 = win
        b = ~self.allowed[gy0:gy1, gx0:gx1].copy()
        for x0, y0, x1, y1 in (BUS_BAND, J11_NORTH):
            a, c = max(gx0, self.ix(x0 - 0.4)), min(gx1, self.ix(x1 + 0.4) + 1)
            e, f = max(gy0, self.iy(y0 - 0.4)), min(gy1, self.iy(y1 + 0.4) + 1)
            if a < c and e < f:
                b[e - gy0:f - gy0, a - gx0:c - gx0] = True
        return b

    def blocked(self, net, layer, w, win, eps=EPS):
        nid = self.nid(net)
        gx0, gy0, gx1, gy1 = win
        b = self._fdist(LI[layer], nid, win) < CLR + w / 2 + eps
        b |= self._static_block(layer, win)
        b |= self.ruledist[gy0:gy1, gx0:gx1] < w / 2 + 0.03
        b |= self.edge_in[gy0:gy1, gx0:gx1] < w / 2 - 0.05          # the whole track width stays inside the rectangles
        dm = self.dom.get(net)
        if dm in self.slack:
            b |= self.slack[dm][gy0:gy1, gx0:gx1] < w / 2 + 0.02        # areas and pads are painted generously
        return b

    def via_ok(self, net, win, eps=EPS, pad_gap=0.05):
        nid = self.nid(net)
        gx0, gy0, gx1, gy1 = win
        ok = ~self._novia(win)
        for li in range(6):
            ok &= self._fdist(li, nid, win) >= CLR + VR + eps
        dm = self.dom.get(net)
        if dm in self.slack:
            ok &= self.slack[dm][gy0:gy1, gx0:gx1] >= VR + 0.02
        ok &= self.ruledist[gy0:gy1, gx0:gx1] >= VR + 0.03
        h = self.holes[gy0:gy1, gx0:gx1]
        if h.any():
            ok &= ndimage.distance_transform_edt(~h) * G >= VIA_DRILL / 2 + HOLE2HOLE + eps
        p = self.padany[gy0:gy1, gx0:gx1]
        if p.any() and pad_gap is not None:
            ok &= ndimage.distance_transform_edt(~p) * G >= VR + pad_gap
        return ok

    def check_track(self, net, layer, pts, w, eps=0.0):
        """'' if the polyline keeps every rule (exact to about half a grid cell), else the reason."""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        win = self._win(min(xs), min(ys), max(xs), max(ys), 1.0)
        gx0, gy0, gx1, gy1 = win
        m = np.zeros((gy1 - gy0, gx1 - gx0), bool)
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.dist(a, b) / (G / 2)))
            for k in range(n + 1):
                x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
                m[self.iy(y) - gy0, self.ix(x) - gx0] = True
        nid = self.nid(net)
        fd = self._fdist(LI[layer], nid, win)
        if (fd[m] < CLR + w / 2 + eps - 0.03).any():
            j = np.argwhere(m & (fd < CLR + w / 2 + eps - 0.03))[0]
            return f"clearance {fd[j[0], j[1]] - w / 2:.3f} at {self.xy(j[1] + gx0, j[0] + gy0)}"
        if self._static_block(layer, win)[m].any():
            return "in a closed area (bus band / north of J11 / outside the unrouted rectangles)"
        if (self.ruledist[gy0:gy1, gx0:gx1][m] < w / 2).any():
            return "in a barrier strip"
        dm = self.dom.get(net)
        if dm in self.slack and (self.slack[dm][gy0:gy1, gx0:gx1][m] < w / 2).any():
            return "domain gap"
        return ""

    def check_via(self, net, x, y, in_pad=False):
        win = self._win(x, y, x, y, 1.5)
        ok = self.via_ok(net, win, eps=0.0, pad_gap=None if in_pad else 0.0)
        return "" if ok[self.iy(y) - win[1], self.ix(x) - win[0]] else "via site not free"

    # -- connectivity of one net inside a window ----------------------------------------------
    def _labels(self, net, win):
        gx0, gy0, gx1, gy1 = win
        nid = self.nid(net)
        h, w = gy1 - gy0, gx1 - gx0
        vol = np.zeros((11, h, w), bool)
        for li in range(6):
            vol[2 * li] = self.own[li, gy0:gy1, gx0:gx1] == nid
        link = np.zeros((h, w), bool)
        for v in self.vias:
            if v["net"] == net and gx0 <= self.ix(v["x"]) < gx1 and gy0 <= self.iy(v["y"]) < gy1:
                link[self.iy(v["y"]) - gy0, self.ix(v["x"]) - gx0] = True
        lay = {}
        for p in self.d["pads"]:
            if p["net"] == net and p["drill"][0] > 0 and gx0 <= self.ix(p["x"]) < gx1 and gy0 <= self.iy(p["y"]) < gy1:
                link[self.iy(p["y"]) - gy0, self.ix(p["x"]) - gx0] = True
        for k in range(1, 11, 2):
            vol[k] = link
        st = np.zeros((3, 3, 3), bool)
        st[1] = True
        st[0, 1, 1] = st[2, 1, 1] = True
        lab, n = ndimage.label(vol, structure=st)
        return lab[0::2]

    def _centre_cells(self, net, win, layers):
        """{layer index in `layers`: bool array} of the cells a track of this net may start or end on:
        pad centres, via centres and the centre lines of its tracks."""
        gx0, gy0, gx1, gy1 = win
        h, w = gy1 - gy0, gx1 - gx0
        out = np.zeros((len(layers), h, w), bool)

        def put(k, x, y):
            i, j = self.ix(x) - gx0, self.iy(y) - gy0
            if 0 <= i < w and 0 <= j < h:
                out[k, j, i] = True
        for p in self.d["pads"]:
            if p["net"] == net:
                for k, ln in enumerate(layers):
                    if ln in p["layers"]:
                        put(k, p["x"], p["y"])
        for v in self.vias:
            if v["net"] == net:
                for k in range(len(layers)):
                    put(k, v["x"], v["y"])
        for t in self.tracks:
            if t["net"] == net and t["layer"] in layers:
                k = layers.index(t["layer"])
                a, b = t["a"], t["b"]
                if max(a[0], b[0]) < self.X0 + gx0 * G or min(a[0], b[0]) > self.X0 + gx1 * G:
                    continue
                n = max(1, int(math.dist(a, b) / (G / 2)))
                for q in range(n + 1):
                    put(k, a[0] + (b[0] - a[0]) * q / n, a[1] + (b[1] - a[1]) * q / n)
        return out

    def _exact(self, net, layer, x, y):
        """The exact anchor (pad centre, via centre or point on a track centre line) next to a grid point."""
        best = None
        for p in self.d["pads"]:
            if p["net"] == net and layer in p["layers"] and abs(p["x"] - x) < 0.06 and abs(p["y"] - y) < 0.06:
                return p["x"], p["y"]
        for v in self.vias:
            if v["net"] == net and abs(v["x"] - x) < 0.06 and abs(v["y"] - y) < 0.06:
                return v["x"], v["y"]
        for t in self.tracks:
            if t["net"] == net and t["layer"] == layer:
                a, b = t["a"], t["b"]
                dx, dy = b[0] - a[0], b[1] - a[1]
                ll = dx * dx + dy * dy
                u = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / ll))
                px, py = a[0] + u * dx, a[1] + u * dy
                dd = math.hypot(px - x, py - y)
                if dd < 0.08 and (best is None or dd < best[0]):
                    best = (dd, px, py)
        return (best[1], best[2]) if best else (x, y)

    def _anchor_xy(self, a):
        if isinstance(a, str):
            p = self.pads[a]
            return p["x"], p["y"]
        return a[0], a[1]

    # -- routing ----------------------------------------------------------------------------
    def connect(self, net, a, b=None, w=0.2, layers=("F.Cu", "In3.Cu", "B.Cu"), via=3.0, turn=0.4, margin=5.0, lcost=None,
                cost=(), close=(), novia=(), box=None, eps=EPS, quiet=False, plane=None, avoid=()):
        """Route net from the copper connected to `a` to the copper connected to `b` (pad 'REF-PIN' or
        point (x, y[, layer])); b None: to any other copper of the net inside the window.
        via: cost of a via in mm of track; lcost {layer: factor}; cost [(layers, rect, extra factor)];
        close [(layers, rect)] closes cells for this connection; novia [rect]; box overrides the window."""
        layers = list(layers)
        ax, ay = self._anchor_xy(a)
        pts = [(ax, ay)] + ([self._anchor_xy(b)] if b is not None else [])
        if box is None:
            box = (min(p[0] for p in pts) - margin, min(p[1] for p in pts) - margin, max(p[0] for p in pts) + margin, max(p[1] for p in pts) + margin)
        box = (min([box[0]] + [p[0] - 2.0 for p in pts]), min([box[1]] + [p[1] - 2.0 for p in pts]),
               max([box[2]] + [p[0] + 2.0 for p in pts]), max([box[3]] + [p[1] + 2.0 for p in pts]))
        win = self._win(*box, 0.0)
        gx0, gy0, gx1, gy1 = win
        h, wd = gy1 - gy0, gx1 - gx0
        lab = self._labels(net, win)
        cells = self._centre_cells(net, win, layers)

        def label_of(anchor):
            x, y = self._anchor_xy(anchor)
            i, j = self.ix(x) - gx0, self.iy(y) - gy0
            if isinstance(anchor, str):
                lys = list(self.pads[anchor]["layers"])
            else:
                lys = [anchor[2]] if len(anchor) > 2 else CU
            for ln in lys:
                if lab[LI[ln], j, i]:
                    return lab[LI[ln], j, i]
            return 0
        la = label_of(a)
        srcm = np.zeros((len(layers), h, wd), bool)
        tgtm = np.zeros((len(layers), h, wd), bool)
        if la:
            for k, ln in enumerate(layers):
                srcm[k] = cells[k] & (lab[LI[ln]] == la)
        else:       # a bare point
            for k, ln in enumerate(layers):
                if isinstance(a, str) or len(a) < 3 or a[2] == ln:
                    srcm[k, self.iy(ay) - gy0, self.ix(ax) - gx0] = True
        if plane is not None:       # to a new via that lands in the planes of the net (the via is added at the end)
            if not self._pf:
                self.prepare_planes()
            site = self.via_ok(net, win, eps) & self.plane_ok(net, plane, win)
            for x0, y0, x1, y1 in avoid:
                site[max(0, self.iy(y0) - gy0):max(0, self.iy(y1) - gy0 + 1), max(0, self.ix(x0) - gx0):max(0, self.ix(x1) - gx0 + 1)] = False
            for k in range(len(layers)):
                tgtm[k] = site
        elif b is None:
            for k, ln in enumerate(layers):
                tgtm[k] = cells[k] & (lab[LI[ln]] != la) & (lab[LI[ln]] != 0)
        else:
            lb = label_of(b)
            if lb and lb == la:
                if not quiet:
                    self.log(f"  {net}: {a} and {b} are connected already")
                return True
            bx, by = self._anchor_xy(b)
            if lb:
                for k, ln in enumerate(layers):
                    tgtm[k] = cells[k] & (lab[LI[ln]] == lb)
            else:
                for k, ln in enumerate(layers):
                    if isinstance(b, str) or len(b) < 3 or b[2] == ln:
                        tgtm[k, self.iy(by) - gy0, self.ix(bx) - gx0] = True
        blk = np.zeros((len(layers), h, wd), np.uint8)
        xc = np.zeros((len(layers), h, wd), np.uint8)
        for k, ln in enumerate(layers):
            blk[k] = self.blocked(net, ln, w, win, eps)
        for lys, (x0, y0, x1, y1) in close:
            for k, ln in enumerate(layers):
                if ln in lys:
                    blk[k, max(0, self.iy(y0) - gy0):max(0, self.iy(y1) - gy0 + 1), max(0, self.ix(x0) - gx0):max(0, self.ix(x1) - gx0 + 1)] = 1
        for lys, (x0, y0, x1, y1), c in cost:
            for k, ln in enumerate(layers):
                if ln in lys:
                    xc[k, max(0, self.iy(y0) - gy0):max(0, self.iy(y1) - gy0 + 1), max(0, self.ix(x0) - gx0):max(0, self.ix(x1) - gx0 + 1)] = min(255, int(c * 100))
        if len(layers) > 1 and via is not None:
            vok = self.via_ok(net, win, eps).astype(np.uint8)
            for x0, y0, x1, y1 in novia:
                vok[max(0, self.iy(y0) - gy0):max(0, self.iy(y1) - gy0 + 1), max(0, self.ix(x0) - gx0):max(0, self.ix(x1) - gx0 + 1)] = 0
        else:
            vok = np.zeros((h, wd), np.uint8)
        srcm &= blk == 0
        if not srcm.any():
            self.log(f"  !! {net}: no free start cell at {a}")
            self.failed.append((net, a, b, "no start"))
            return False
        if not (tgtm & (blk == 0)).any():
            self.log(f"  !! {net}: no free target cell at {b}")
            self.failed.append((net, a, b, "no target"))
            return False
        tgtm &= blk == 0
        src = np.argwhere(srcm)[:, [0, 2, 1]].astype(np.int32).copy()
        tj = np.argwhere(tgtm)
        lm = (ctypes.c_int32 * len(layers))(*[int(100 * (lcost or {}).get(ln, 1.0)) for ln in layers])
        maxout = 200000
        out = (ctypes.c_int32 * (3 * maxout))()
        nexp = ctypes.c_int64(0)
        blk_c, xc_c, vok_c, tg_c = (np.ascontiguousarray(x) for x in (blk, xc, vok, tgtm.astype(np.uint8)))
        n = self.lib.route(wd, h, len(layers), blk_c.ctypes.data_as(ctypes.c_void_p), xc_c.ctypes.data_as(ctypes.c_void_p),
                           vok_c.ctypes.data_as(ctypes.c_void_p), tg_c.ctypes.data_as(ctypes.c_void_p),
                           src.ctypes.data_as(ctypes.c_void_p), len(src), lm, int(via * 100 / G) if via is not None else 0,
                           int(turn * 100 / G) if turn < 1 else int(turn), int(tj[:, 2].min()), int(tj[:, 1].min()), int(tj[:, 2].max()), int(tj[:, 1].max()),
                           out, maxout, ctypes.byref(nexp))
        if n <= 0:
            self.log(f"  !! {net}: no path {a} -> {b} (layers {'/'.join(layers)}, w {w}, {nexp.value} states)")
            self.failed.append((net, a, b, "no path"))
            return False
        path = [(layers[out[3 * i]], out[3 * i + 1] + gx0, out[3 * i + 2] + gy0) for i in range(n)][::-1]
        length, nv = self._commit(net, path, w)
        if plane is not None:
            self.add_via(net, *self.xy(path[-1][1], path[-1][2]), check=False)
            nv += 1
        if not quiet:
            self.log(f"  {net}: {a} -> {b}: {length:.1f} mm, {nv} vias, w {w}")
        return True

    def _commit(self, net, path, w):
        runs, cur = [], [path[0]]
        for p in path[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur)
                cur = [p]
            else:
                cur.append(p)
        runs.append(cur)
        length, nv = 0.0, 0
        for k, run in enumerate(runs):
            layer = run[0][0]
            pts = [self.xy(i, j) for _, i, j in run]
            # collinear points out
            sp = [pts[0]]
            for q in range(1, len(pts) - 1):
                a, b, c = sp[-1], pts[q], pts[q + 1]
                if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
                    sp.append(b)
            if len(pts) > 1:
                sp.append(pts[-1])
            if k == 0:
                e = self._exact(net, layer, *sp[0])
                if e != sp[0]:
                    sp.insert(0, e)
            if k == len(runs) - 1:
                e = self._exact(net, layer, *sp[-1])
                if e != sp[-1]:
                    sp.append(e)
            if k > 0:
                self.add_via(net, *pts[0], check=False)
                nv += 1
            if len(sp) > 1:
                self.add_track(net, layer, sp, w, check=False)
                length += sum(math.dist(a, b) for a, b in zip(sp, sp[1:]))
        return length, nv

    # -- plane vias ---------------------------------------------------------------------------
    def plane_ok(self, net, plane_layers, win, inset=0.45):
        """Cells where a via of this net lands well inside the fill of its plane(s)."""
        gx0, gy0, gx1, gy1 = win
        ok = np.ones((gy1 - gy0, gx1 - gx0), bool)
        for ln in plane_layers:
            m = np.zeros((self.H, self.W), bool) if (net, ln) not in self._pf else self._pf[(net, ln)]
            ok &= m[gy0:gy1, gx0:gx1]
        return ok

    def prepare_planes(self, inset=0.45):
        self._pf = {}
        for (net, ln), rings in self.planefill.items():
            m = np.zeros((self.H, self.W), bool)
            self._paint(m, rings, True)
            self._pf[(net, ln)] = ndimage.distance_transform_edt(m) * G >= inset

    def on_plane(self, pad, plane_layers, own=None):
        """True if the copper of the pad already holds a via (or through-hole pad) of its net that lands in the
        plane(s); own (mm): only a via within that distance of the pad centre counts."""
        p = self.pads[pad]
        net = p["net"]
        win = self._win(p["x"], p["y"], p["x"], p["y"], 8.0)
        gx0, gy0, gx1, gy1 = win
        if not self._pf:
            self.prepare_planes()
        lab = self._labels(net, win)
        ok = self.plane_ok(net, plane_layers, win)
        la = 0
        for ln in p["layers"]:
            la = la or lab[LI[ln], self.iy(p["y"]) - gy0, self.ix(p["x"]) - gx0]
        if not la:
            return False
        pts = [(v["x"], v["y"]) for v in self.vias if v["net"] == net]
        pts += [(q["x"], q["y"]) for q in self.d["pads"] if q["net"] == net and q["drill"][0] > 0 and len(q["layers"]) == 6]
        for x, y in pts:
            i, j = self.ix(x) - gx0, self.iy(y) - gy0
            if 0 <= i < gx1 - gx0 and 0 <= j < gy1 - gy0 and lab[0, j, i] == la and ok[j, i]:
                if own is None or math.hypot(x - p["x"], y - p["y"]) <= own:
                    return True
        return False

    def plane_via(self, pad, plane_layers, w=0.4, maxlen=2.0, prefer=None, eps=EPS, at=None, w_min=0.25, avoid=()):
        """Stub from pad 'REF-PIN' to a new via that lands in the planes of the pad's net.
        prefer (dx, dy): direction in which the via is wanted; at (x, y): exact via position."""
        p = self.pads[pad]
        net = p["net"]
        layer = [ln for ln in ("F.Cu", "B.Cu") if ln in p["layers"]]
        if len(layer) != 1:
            self.log(f"  {pad}: through-hole pad, no plane via")
            return True
        layer = layer[0]
        win = self._win(p["x"], p["y"], p["x"], p["y"], maxlen + 1.0)
        gx0, gy0, gx1, gy1 = win
        if not self._pf:
            self.prepare_planes()
        vok = self.via_ok(net, win, eps) & self.plane_ok(net, plane_layers, win)
        for x0, y0, x1, y1 in avoid:
            vok[max(0, self.iy(y0) - gy0):max(0, self.iy(y1) - gy0 + 1), max(0, self.ix(x0) - gx0):max(0, self.ix(x1) - gx0 + 1)] = False
        if at is not None:
            cand = [(0.0, self.iy(at[1]) - gy0, self.ix(at[0]) - gx0)]
        else:
            jj, ii = np.nonzero(vok)
            cand = []
            for j, i in zip(jj, ii):
                x, y = self.xy(i + gx0, j + gy0)
                dd = math.hypot(x - p["x"], y - p["y"])
                if dd > maxlen:
                    continue
                score = dd
                if prefer:
                    score -= 0.6 * ((x - p["x"]) * prefer[0] + (y - p["y"]) * prefer[1]) / (dd + 1e-9) * min(dd, 1.0)
                cand.append((score, j, i))
            cand.sort()
        for ww in ([w, w_min] if w_min < w else [w]):
            blk = self.blocked(net, layer, ww, win, eps)
            for score, j, i in cand[:400]:
                x, y = self.xy(i + gx0, j + gy0)
                # straight stub, or one 45 degree bend
                for pts in self._stubs((p["x"], p["y"]), (x, y)):
                    if self._free(blk, pts, win):
                        self.add_via(net, x, y, check=False)
                        self.add_track(net, layer, pts, ww, check=False)
                        self.log(f"  {pad} {net}: via at ({x:.2f}, {y:.2f}), stub {sum(math.dist(a, b) for a, b in zip(pts, pts[1:])):.2f} mm w {ww}")
                        return True
        self.log(f"  !! {pad} {net}: no plane via site within {maxlen} mm")
        self.failed.append((net, pad, None, "no plane via"))
        return False

    @staticmethod
    def _stubs(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        out = [[a, b]] if (abs(dx) < 1e-6 or abs(dy) < 1e-6 or abs(abs(dx) - abs(dy)) < 1e-6) else []
        m = min(abs(dx), abs(dy))
        sx, sy = math.copysign(m, dx), math.copysign(m, dy)
        if not out:
            out.append([a, (a[0] + dx - sx, a[1] + dy - sy), b])     # straight first, then diagonal
            out.append([a, (a[0] + sx, a[1] + sy), b])               # diagonal first
        return out

    def _free(self, blk, pts, win):
        gx0, gy0, gx1, gy1 = win
        # the first 0.3 mm leave the pad: the pad's own neighbours limit the stub, checked along the whole stub
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.dist(a, b) / (G / 2)))
            for k in range(n + 1):
                x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
                j, i = self.iy(y) - gy0, self.ix(x) - gx0
                if not (0 <= j < blk.shape[0] and 0 <= i < blk.shape[1]) or blk[j, i]:
                    return False
        return True

    # -- trying things ------------------------------------------------------------------------
    def snapshot(self):
        return (self.own.copy(), self.holes.copy(), {k: v.copy() for k, v in self.dommask.items()}, len(self.tracks), len(self.vias),
                len(self.new_tracks), len(self.new_vias), len(self.failed))

    def restore(self, snap):
        own, holes, dm, nt, nv, nnt, nnv, nf = snap
        self.own[:] = own
        self.holes[:] = holes
        for k in dm:
            self.dommask[k][:] = dm[k]
        del self.tracks[nt:], self.vias[nv:], self.new_tracks[nnt:], self.new_vias[nnv:], self.failed[nf:]

    # -- output -----------------------------------------------------------------------------
    def save(self, path):
        with open(path, "w") as f:
            json.dump({"tracks": self.new_tracks, "vias": self.new_vias}, f, indent=0)
        self.log(f"router: {len(self.new_tracks)} track segments, {len(self.new_vias)} vias -> {path}")

    def load_routes(self, path):
        """Copper of an earlier stage: on the grid, not in this stage's output."""
        with open(path) as f:
            r = json.load(f)
        for t in r["tracks"]:
            self.tracks.append(t)
            self._add_track_raster(t)
        for v in r["vias"]:
            self.vias.append(v)
            self._add_via_raster(v)

    def png(self, path, rect, layers=("F.Cu", "In3.Cu", "B.Cu"), ppm=20, net=None):
        """Debug picture: F red, In3 green, B blue (first three layers given); net: highlighted white."""
        gx0, gy0, gx1, gy1 = self._win(*rect, 0.0)
        img = np.zeros((gy1 - gy0, gx1 - gx0, 3), np.uint8)
        for k, ln in enumerate(layers[:3]):
            o = self.own[LI[ln], gy0:gy1, gx0:gx1]
            img[..., k] = np.where(o > 0, 200, np.where(o < 0, 70, 0))
        if net:
            nid = self.nid(net)
            for ln in layers:
                img[self.own[LI[ln], gy0:gy1, gx0:gx1] == nid] = 255
        im = Image.fromarray(img[::-1])
        if ppm != 20:
            im = im.resize((int(im.width * ppm / 20), int(im.height * ppm / 20)), Image.NEAREST)
        im.save(path)
