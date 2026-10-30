#!/usr/bin/env python3
"""v4 fix 12 (run once, kipy): fix 8's silkscreen reference placement again, after fix 11 added
C95-C110 (their references are at the KiCad footprint default and overlap; existing references
that the new pads now cover move as well). Same rules and code as fix 8 (copied, seed 4112).

Fix 8's description: Only the Reference fields on F.SilkS / B.SilkS change (position, angle 0/90,
and 0.8 mm text for parts where 1.0 mm does not fit); copper and footprint graphics stay.

A reference that is already clear stays where it is. The others get the best free candidate:
above / below / left / right of the footprint's courtyard (horizontal and vertical text, pushed
out in 0.25 mm steps), the courtyard corners and the body centre. Hard rules: no overlap with
exposed copper (pads, + 0.1 mm), other silk (+ 0.05 mm) or other references (+ 0.3 mm so they stay
readable, + 0.05 mm where nothing else fits), and at least
0.3 mm inside the board outline. Among the free candidates the score prefers the own footprint
(distance) and avoids covering other footprints' courtyards. Nothing free: the text stays.
Geometry: axis-aligned text boxes against KiCad's own polygons (pads, silk strokes, outline).
"""
import math

import pcbnew
from v4board import Board, F, T

PAD_CLR, SILK_CLR, REF_CLR, EDGE_CLR, GAP = 0.1, 0.05, 0.3, 0.3, 0.15
SIZES = (1.0, 0.8)                      # text height/width in mm; 0.8 only as a fallback
THICK = {1.0: 0.15, 0.8: 0.15}
STEPS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


# ---------------------------------------------------------------- geometry (mm, KiCad y down)

def poly_rings(ps):
    """SHAPE_POLY_SET -> [(outer, [holes])] with point lists in mm."""
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        outer = [(T(ol.CPoint(k).x), T(ol.CPoint(k).y)) for k in range(ol.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hl = ps.Hole(i, h)
            holes.append([(T(hl.CPoint(k).x), T(hl.CPoint(k).y)) for k in range(hl.PointCount())])
        out.append((outer, holes))
    return out


def bbox_of(rings):
    xs = [p[0] for o, _ in rings for p in o]
    ys = [p[1] for o, _ in rings for p in o]
    return (min(xs), min(ys), max(xs), max(ys))


def inside(pt, pts):
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def seg_hits_box(a, b, box):
    """Liang-Barsky: does segment a-b touch the box (x0, y0, x1, y1)?"""
    x0, y0, x1, y1 = box
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def box_hits_rings(box, rings):
    x0, y0, x1, y1 = box
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for outer, holes in rings:
        for pts in [outer] + holes:
            for a, b in zip(pts, pts[1:] + pts[:1]):
                if seg_hits_box(a, b, box):
                    return True
        if inside(corners[0], outer) and not any(inside(corners[0], h) for h in holes):
            return True                                      # box inside a filled area
        if x0 <= outer[0][0] <= x1 and y0 <= outer[0][1] <= y1:
            return True                                      # area inside the box
    return False


def overlap(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def grow(box, d):
    return (box[0] - d, box[1] - d, box[2] + d, box[3] + d)


class Index:
    """Obstacles (bbox, rings) in 5 mm buckets."""
    def __init__(self):
        self.cells = {}

    def _keys(self, box):
        for i in range(int(math.floor(box[0] / 5)), int(math.floor(box[2] / 5)) + 1):
            for j in range(int(math.floor(box[1] / 5)), int(math.floor(box[3] / 5)) + 1):
                yield i, j

    def add(self, box, rings, tag):
        item = (box, rings, tag)
        for k in self._keys(box):
            self.cells.setdefault(k, []).append(item)

    def hit(self, box, skip=None):
        seen = set()
        for k in self._keys(box):
            for item in self.cells.get(k, ()):
                if id(item) in seen or item[2] == skip:
                    continue
                seen.add(id(item))
                if overlap(box, item[0]) and (item[1] is None or box_hits_rings(box, item[1])):
                    return item[2]
        return None


# ---------------------------------------------------------------- board

b = Board(4112)
brd = b.b
FS, BS = brd.GetLayerID("F.SilkS"), brd.GetLayerID("B.SilkS")
CU = {FS: pcbnew.F_Cu, BS: pcbnew.B_Cu}
CRT = {FS: pcbnew.F_CrtYd, BS: pcbnew.B_CrtYd}
ERR = F(0.005)

if brd.FindFootprintByReference("C95") is None:
    raise SystemExit("fix 12 needs fix 11 (C95-C110)")
# marker: this placement moves C109's reference to 0.8 mm text (a clear reference stays put, so a
# second run would change nothing anyway)
if brd.FindFootprintByReference("C109").GetField(pcbnew.FIELD_T_REFERENCE).GetTextHeight() == F(0.8):
    raise SystemExit("fix 12 already applied")


def shape_rings(item, layer, clr=0.0):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolySet(ps, layer, F(clr), ERR, pcbnew.ERROR_OUTSIDE)
    return poly_rings(ps)


pads = {FS: Index(), BS: Index()}
silk = {FS: Index(), BS: Index()}
crt = {FS: Index(), BS: Index()}
refs = {}
for fp in brd.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        for sl, cu in CU.items():
            if pad.IsOnLayer(cu) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                rings = poly_rings(pad.GetEffectivePolygon(cu, pcbnew.ERROR_OUTSIDE))
                if rings:
                    pads[sl].add(grow(bbox_of(rings), PAD_CLR), rings, ref)
    for g in fp.GraphicalItems():
        if g.GetLayer() in (FS, BS):
            rings = shape_rings(g, g.GetLayer())
            if rings:
                silk[g.GetLayer()].add(bbox_of(rings), rings, ref)
    for sl, cl in CRT.items():
        cy = fp.GetCourtyard(cl)
        if cy.OutlineCount():
            bb = cy.BBox()
            crt[sl].add((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())), None, ref)
    f = fp.GetField(pcbnew.FIELD_T_REFERENCE)
    if f.IsVisible() and f.GetLayer() in (FS, BS):
        refs[ref] = (fp, f)
    for fld in fp.GetFields():
        if fld.GetId() != f.GetId() and fld.IsVisible() and fld.GetLayer() in (FS, BS):
            rings = shape_rings(fld, fld.GetLayer())
            silk[fld.GetLayer()].add(bbox_of(rings), rings, ref)
for d in brd.GetDrawings():
    if d.GetLayer() in (FS, BS):
        rings = shape_rings(d, d.GetLayer())
        if rings:
            silk[d.GetLayer()].add(bbox_of(rings), rings, None)

outline_ps = pcbnew.SHAPE_POLY_SET()
brd.GetBoardPolygonOutlines(outline_ps, False)
outline = poly_rings(outline_ps)


def in_board(box):
    gb = grow(box, EDGE_CLR)
    corners = [(gb[0], gb[1]), (gb[2], gb[1]), (gb[2], gb[3]), (gb[0], gb[3])]
    for outer, holes in outline:
        if all(inside(c, outer) for c in corners):
            return not any(seg_hits_box(a, b2, gb) for pts in holes for a, b2 in zip(pts, pts[1:] + pts[:1])) \
                and not any(seg_hits_box(a, b2, gb) for a, b2 in zip(outer, outer[1:] + outer[:1]))
    return False


def text_box(f):
    ps = pcbnew.SHAPE_POLY_SET()
    f.TransformShapeToPolySet(ps, f.GetLayer(), 0, ERR, pcbnew.ERROR_OUTSIDE)
    return bbox_of(poly_rings(ps))


placed = {FS: Index(), BS: Index()}


def free(ref, sl, box, ref_clr=REF_CLR):
    if pads[sl].hit(grow(box, PAD_CLR)) is not None:
        return False
    if silk[sl].hit(grow(box, SILK_CLR)) is not None:
        return False
    if placed[sl].hit(grow(box, ref_clr)) is not None:
        return False
    return in_board(box)


def courtyard_cover(ref, sl, box):
    """Area of other footprints' courtyard boxes under the text (soft penalty)."""
    a = 0.0
    seen = set()
    for k in crt[sl]._keys(box):
        for item in crt[sl].cells.get(k, ()):
            if item[2] == ref or id(item) in seen:
                continue
            seen.add(id(item))
            c = item[0]
            w = min(box[2], c[2]) - max(box[0], c[0])
            h = min(box[3], c[3]) - max(box[1], c[1])
            if w > 0 and h > 0:
                a += w * h
    return a


def candidates(fp, f, sl):
    cy = fp.GetCourtyard(CRT[sl])
    if cy.OutlineCount():
        bb = cy.BBox()
    else:
        bb = fp.GetBoundingBox(False)
    L, Tp, R, Bt = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
    cx, cyy = (L + R) / 2, (Tp + Bt) / 2
    out = []
    for size in SIZES:
        for ang in (0.0, 90.0):
            f.SetTextSize(pcbnew.VECTOR2I(F(size), F(size)))
            f.SetTextThickness(F(THICK[size]))
            f.SetTextAngleDegrees(ang)
            f.SetPosition(pcbnew.VECTOR2I(F(cx), F(cyy)))
            tb = text_box(f)
            hw, hh = (tb[2] - tb[0]) / 2, (tb[3] - tb[1]) / 2
            ox, oy = (tb[0] + tb[2]) / 2 - cx, (tb[1] + tb[3]) / 2 - cyy    # box centre vs anchor
            spots = [(cx, cyy, 0.4)]                                         # body centre
            for s in STEPS:
                d = GAP + s
                spots += [(cx, Tp - d - hh, s), (cx, Bt + d + hh, s),       # above / below
                          (L - d - hw, cyy, s + 0.2), (R + d + hw, cyy, s + 0.2),
                          (L + hw, Tp - d - hh, s + 0.3), (R - hw, Tp - d - hh, s + 0.3),
                          (L + hw, Bt + d + hh, s + 0.3), (R - hw, Bt + d + hh, s + 0.3)]
            for x, y, cost in spots:
                box = (x - hw, y - hh, x + hw, y + hh)
                pen = cost + (0.5 if ang else 0.0) + (3.0 if size < 1.0 else 0.0)
                out.append((pen, size, ang, x - ox, y - oy, box))
    return out


def apply(f, size, ang, x, y):
    f.SetTextSize(pcbnew.VECTOR2I(F(size), F(size)))
    f.SetTextThickness(F(THICK[size]))
    f.SetTextAngleDegrees(ang)
    f.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))


# pass 1: keep every reference that is already clear (in board order)
todo = []
clear_boxes = []
for ref, (fp, f) in sorted(refs.items()):
    sl = f.GetLayer()
    box = text_box(f)
    if free(ref, sl, box):
        placed[sl].add(box, None, ref)
        clear_boxes.append((sl, box, ref))
    else:
        todo.append(ref)
state = {}
for ref in todo:
    fp, f = refs[ref]
    state[ref] = (f.GetPosition(), f.GetTextAngleDegrees(), f.GetTextSize(), f.GetTextThickness())


def restore(ref):
    fp, f = refs[ref]
    pos, ang, size, th = state[ref]
    f.SetPosition(pos); f.SetTextAngleDegrees(ang); f.SetTextSize(size); f.SetTextThickness(th)


def place_all(stuck):
    """Pass 2: the references in todo (fewest free candidates first); `stuck` ones stay where
    they are and block their spot from the start. Returns (moved log lines, refs without spot)."""
    for k in (FS, BS):
        placed[k] = Index()
    for sl, box, ref in clear_boxes:
        placed[sl].add(box, None, ref)
    for ref in stuck:
        restore(ref)
        placed[refs[ref][1].GetLayer()].add(text_box(refs[ref][1]), None, ref)
    order = []
    for ref in todo:
        if ref in stuck:
            continue
        fp, f = refs[ref]
        sl = f.GetLayer()
        cands = candidates(fp, f, sl)
        restore(ref)
        order.append((sum(1 for c in cands if free(ref, sl, c[5])), ref, cands))
    lines, kept = [], []
    for n, ref, cands in sorted(order, key=lambda o: (o[0], o[1])):
        fp, f = refs[ref]
        sl = f.GetLayer()
        best = None
        for ref_clr in (REF_CLR, SILK_CLR):        # second try: references closer together
            for pen, size, ang, x, y, box in cands:
                if not free(ref, sl, box, ref_clr):
                    continue
                score = pen + 2.0 * courtyard_cover(ref, sl, box)
                if best is None or score < best[0]:
                    best = (score, size, ang, x, y, box)
            if best is not None:
                break
        if best is None:
            kept.append(ref)
            placed[sl].add(text_box(f), None, ref)
            continue
        _, size, ang, x, y, box = best
        old = state[ref][0]
        apply(f, size, ang, x, y)
        placed[sl].add(text_box(f), None, ref)
        lines.append(f"{ref}: ({T(old.x):.3f},{-T(old.y):.3f}) -> ({x:.3f},{-y:.3f}) angle {ang:g} size {size:g}")
    return lines, kept


# a reference that finds no spot keeps its old one; place everything again with those fixed, so
# no other reference was put on top of them
stuck = set()
while True:
    lines, kept = place_all(stuck)
    if not set(kept) - stuck:
        break
    stuck |= set(kept)
b.log += lines
b.log.insert(0, f"{len(refs)} references on silk: {len(refs) - len(todo)} already clear, {len(lines)} moved, "
                f"{len(stuck)} without a free spot (left as they were: {' '.join(sorted(stuck))})")
b.save("fix 12: silkscreen references after fix 11 (C95-C110)")
