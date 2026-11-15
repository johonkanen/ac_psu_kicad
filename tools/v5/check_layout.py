#!/usr/bin/env python3
"""Card-area layout check (V5_LAYOUT_PLAN.md phase 2; run under tools/p2k/bin/kipy).

Data: tools/v5/card_layout.py. Checks, for the parts placed or moved by the card-area layout:
  1. the copper areas keep 5.0 mm from each other; every slot lies inside a barrier strip
  2. every pad lies in a copper area of its own domain (barrier parts: each side in its area)
  3. no courtyard overlap with any other part on the same side
  4. top side under the card: height <= 2.65 mm; bottom side: <= 10 mm, >= 4 mm from a mounting hole
  5. no top-side part under a through-hole tail of the Ti135 or the Ti60 card
  6. the slots are on Edge.Cuts; no tracks on the ground layers In1/In4 inside the card area;
     no copper of any domain inside a barrier strip (pads, tracks, vias, zone fills, all layers)
  7. every plane zone of the card area is filled as one island
Before the placement (tools/v5/v5_4_card_area.py) only check 1 runs.

Usage: tools/p2k/bin/kipy tools/v5/check_layout.py [--board FILE] [-v]
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path[:0] = [HERE, TOOLS, os.path.join(TOOLS, "v4"), os.path.join(TOOLS, "p2k")]
import board_common as bc  # noqa: E402
import card_layout as L  # noqa: E402
import domains  # noqa: E402
from layout_proposal import edges, inside, poly_dist, rect, seg_pt, seg_seg  # noqa: E402

T, F = pcbnew.ToMM, pcbnew.FromMM
STAGING_Y = -84.0
POLY = {k: v[1] for k, v in L.AREAS.items()}
DOM = {k: v[0] for k, v in L.AREAS.items()}


def sps(poly):
    s = pcbnew.SHAPE_POLY_SET()
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in poly:
        ch.Append(F(x), F(-y))
    ch.SetClosed(True)
    s.AddOutline(ch)
    return s


def strips():
    """The barrier strips inside / around the card: everything within 2.5 mm of a barrier centre line."""
    s = pcbnew.SHAPE_POLY_SET()
    for _, _, pl in L.LINES:
        for a, b in zip(pl, pl[1:]):
            seg = pcbnew.SHAPE_POLY_SET()
            pcbnew.TransformOvalToPolygon(seg, pcbnew.VECTOR2I(F(a[0]), F(-a[1])), pcbnew.VECTOR2I(F(b[0]), F(-b[1])),
                                          F(L.GAP - 0.02), F(0.005), pcbnew.ERROR_INSIDE)
            s.Append(seg)
    s.Simplify()
    return s


def static_checks(err):
    names = sorted(POLY)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if DOM[a] != DOM[b] and poly_dist(POLY[a], POLY[b]) < L.GAP - 1e-6:
                err.append(f"areas {a} and {b}: {poly_dist(POLY[a], POLY[b]):.2f} mm apart")
    if min(poly_dist(POLY["CA"], p) for p in L.I_AROUND_CA) < L.GAP - 1e-6:
        err.append("area CA: less than 5 mm from the ISO copper around J11")
    allpolys = list(POLY.values()) + L.I_AROUND_CA
    for name, a, b in L.SLOTS:
        g = min(seg_seg(a, b, c, e) for p in allpolys for c, e in edges(p)) - L.SLOT_W / 2
        if g < 0.5 or any(inside(a, p) or inside(b, p) for p in allpolys):
            err.append(f"slot {name}: {g:.2f} mm from a copper area (need 0.5)")
        if L.SLOT_W < 1.0:
            err.append("slot width below 1.0 mm")


def main():
    path = sys.argv[sys.argv.index("--board") + 1] if "--board" in sys.argv else bc.BOARD
    verbose = "-v" in sys.argv
    board = pcbnew.LoadBoard(path)
    err, info = [], []
    static_checks(err)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    missing = [r for r in L.PLACE if r not in fps]
    if missing:
        err.append("not on the board: " + " ".join(missing))
    staged = [r for r in L.PLACE if r in fps and -T(fps[r].GetPosition().y) < STAGING_Y]
    if "U19" in staged:
        print(f"check_layout: areas and {len(L.SLOTS)} slots consistent; the card area is not placed yet "
              f"({len(staged)} parts staged): placement checks skipped")
        for e in err:
            print("check_layout: ERROR " + e)
        print("check_layout: " + ("FAILED" if err else "OK"))
        return 1 if err else 0
    if staged:
        err.append("still in the staging area: " + " ".join(staged))
    _, nets = bc.export_netlist()
    dom = domains.classify(nets)
    x0, y0, x1, y1 = L.CARD
    holes = [(n, x, y, d / 2 + L.KEEP_MARGIN) for n, x, y, d in list(L.CARD_HOLES) + list(L.TI60_HOLES)]
    mount = [(-99, 0)]
    mount = [(T(fp.GetPosition().x), -T(fp.GetPosition().y)) for r, fp in fps.items() if r in ("H1", "H2", "H3", "H4")]

    def court(fp):
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        if c.OutlineCount() == 0:
            c = pcbnew.SHAPE_POLY_SET()
            bb = fp.GetBoundingBox(False)
            c.AddOutline(sps(rect(T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop()))).Outline(0))
        return c

    def tht(fp):
        return any(p.GetDrillSize().x > 0 for p in fp.Pads())

    # 2. pads in their areas
    for ref in L.PLACE:
        fp = fps.get(ref)
        if fp is None or ref in staged:
            continue
        for pad in fp.Pads():
            d = dom.get(pad.GetNetname())
            if not d:
                continue
            bb = pad.GetBoundingBox()
            corners = rect(T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop()))
            if not any(DOM[k] == d and all(inside(c, POLY[k]) for c in corners) for k in POLY):
                err.append(f"{ref}-{pad.GetNumber()} ({domains.short(pad.GetNetname())}, {d}) at "
                           f"({T(pad.GetPosition().x):.2f}, {-T(pad.GetPosition().y):.2f}): outside the {d} copper areas")
        want = L.PLACE[ref][1]
        side = "B" if fp.IsFlipped() else "F"
        if want in ("F", "B") and side != want:
            err.append(f"{ref}: on side {side}, card_layout says {want}")
    # 3. courtyards
    allfp = [fp for fp in fps.values() if -T(fp.GetPosition().y) > STAGING_Y]
    for ref in L.PLACE:
        fp = fps.get(ref)
        if fp is None or ref in staged:
            continue
        ca, bba = court(fp), fp.GetBoundingBox(False)
        for o in allfp:
            oref = o.GetReference()
            if oref == ref or (oref in L.PLACE and oref < ref):
                continue
            if o.IsFlipped() != fp.IsFlipped() and not (tht(fp) or tht(o)):
                continue
            if not bba.Intersects(o.GetBoundingBox(False)):
                continue
            ov = ca.CloneDropTriangulation()
            ov.BooleanIntersection(court(o))
            if ov.OutlineCount() and ov.Area() > F(0.05) * F(0.05):
                # a through-hole part meets an SMD part of the other side only with its pads
                if o.IsFlipped() != fp.IsFlipped():
                    t, s = (fp, o) if tht(fp) else (o, fp)
                    if not any(court(s).Collide(p.GetEffectiveShape(), 0) for p in t.Pads() if p.GetDrillSize().x > 0):
                        continue
                err.append(f"{ref} / {oref}: courtyards overlap")
    # 4. heights, 5. card tails
    under = lambda fp: x0 < T(fp.GetPosition().x) < x1 and y0 < -T(fp.GetPosition().y) < y1
    nfixed_tail = set()
    for fp in allfp:
        ref = fp.GetReference()
        placed = ref in L.PLACE
        name = str(fp.GetFPID().GetLibItemName())
        cx, cy = T(fp.GetPosition().x), -T(fp.GetPosition().y)
        if placed and ref not in L.NO_HEIGHT:
            h = L.HEIGHT.get(name)
            if h is None:
                err.append(f"{ref}: no height for footprint {name} (card_layout.HEIGHT)")
            elif not fp.IsFlipped() and under(fp) and h > L.H_TOP_UNDER_CARD:
                err.append(f"{ref}: {h} mm on top under the card (limit {L.H_TOP_UNDER_CARD})")
            elif fp.IsFlipped() and h > L.H_BOTTOM:
                err.append(f"{ref}: {h} mm on the bottom (limit {L.H_BOTTOM})")
        elif not placed and not fp.IsFlipped() and under(fp) and ref not in L.NO_HEIGHT and L.HEIGHT.get(name, 0) > L.H_TOP_UNDER_CARD:
            info.append(f"v4 part {ref} ({name}) is {L.HEIGHT[name]} mm on top under the card (fixed, as on the built board)")
        if placed and (fp.IsFlipped() or tht(fp)):
            for mx, my in mount:
                c = court(fp)
                if c.Collide(pcbnew.VECTOR2I(F(mx), F(-my)), F(L.MOUNT_HOLE_R)):
                    err.append(f"{ref}: within {L.MOUNT_HOLE_R} mm of the mounting hole at ({mx:.1f}, {my:.1f})")
        if not fp.IsFlipped() or tht(fp):
            c = court(fp)
            for hn, hx, hy, r in holes:
                if c.Collide(pcbnew.VECTOR2I(F(hx), F(-hy)), F(r)):
                    if placed and ref not in ("J13", "J14"):
                        err.append(f"{ref}: under a tail of {hn} at ({hx:.2f}, {hy:.2f})")
                    elif not placed and ref not in ("J11", "J12"):
                        nfixed_tail.add(ref)
    if nfixed_tail:
        info.append("v4 parts under card tails (fixed, tails trimmed): " + " ".join(sorted(nfixed_tail)))
    # 6. slots, ground layers, strips
    cuts = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and d.GetClass() == "PCB_SHAPE":
            bb = d.GetBoundingBox()
            cuts.append((T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())))
    for name, a, b in L.SLOTS:
        want = (min(a[0], b[0]) - L.SLOT_W / 2, min(a[1], b[1]) - L.SLOT_W / 2, max(a[0], b[0]) + L.SLOT_W / 2, max(a[1], b[1]) + L.SLOT_W / 2)
        if not any(all(abs(c[i] - want[i]) < 0.15 for i in range(4)) for c in cuts):
            err.append(f"slot {name}: not on Edge.Cuts")
    strip = strips()
    ntr = 0
    for t in board.GetTracks():
        px, py = T(t.GetStart().x), -T(t.GetStart().y)
        if t.GetClass() != "PCB_VIA" and t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In4_Cu) and x0 < px < x1 and y0 < py < y1:
            ntr += 1
        if strip.Collide(t.GetEffectiveShape(), 0):
            err.append(f"{t.GetClass()} [{t.GetNetname()}] at ({px:.2f}, {py:.2f}) inside a barrier strip")
    if ntr:
        err.append(f"{ntr} tracks on In1/In4 inside the card area (ground layers are not routed)")
    for fp in allfp:
        for pad in fp.Pads():
            if pad.GetNetname() and dom.get(pad.GetNetname()) and strip.Collide(pad.GetEffectiveShape(), 0):
                err.append(f"pad {fp.GetReference()}-{pad.GetNumber()} [{pad.GetNetname()}] inside a barrier strip")
    # 7. zones: one island, not in a strip
    nz = 0
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        if not z.GetZoneName().startswith("v5 card"):
            continue
        nz += 1
        for lid in z.GetLayerSet().CuStack():
            fill = z.GetFilledPolysList(lid)
            if fill.OutlineCount() != 1:
                err.append(f"zone {z.GetZoneName()} [{z.GetNetname()}] {board.GetLayerName(lid)}: {fill.OutlineCount()} islands")
            ov = fill.CloneDropTriangulation()
            ov.BooleanIntersection(strip)
            if ov.OutlineCount() and ov.Area() > F(0.05) * F(0.05):
                err.append(f"zone {z.GetZoneName()} {board.GetLayerName(lid)}: fill inside a barrier strip")
    if nz == 0:
        err.append("no 'v5 card ...' plane zones on the board")
    for i in info if verbose else info[:3]:
        print("check_layout: " + i)
    for e in err[:60]:
        print("check_layout: ERROR " + e)
    print(f"check_layout: {len(L.PLACE)} placed / moved parts in their domain areas, {len(L.SLOTS)} slots, {nz} plane zones; "
          f"{len(err)} errors")
    print("check_layout: " + ("FAILED" if err else "OK"))
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
