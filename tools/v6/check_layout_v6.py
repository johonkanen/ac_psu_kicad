#!/usr/bin/env python3
"""v6 layout rules for the six power cards (V6_PLAN.md section 5 as changed by the planning session 2026-11-23).

  tools/p2k/bin/kipy tools/v6/check_layout_v6.py

  1. Card envelope: inside the card spans (x 15.2 ... 117.3) no part taller than 4 mm within 18 mm of either
     heatsink wall (the routed card reaches about 16 mm from the wall, its bottom edge 4 mm above the board).
  2. Card terminals (J31 ... J42) and CTRL headers (J21 ... J26): bodies >= 20 mm from the wall (courtyard + 0.3 mm
     margin), terminal screw centres >= 22 mm (straight screwdriver from above). Listed exceptions only.
  3. Lug circles (8 mm, on the 7 mm terminal top): >= 2.5 mm in plan view from the courtyard of every through-hole
     part (taken as taller than 5 mm: headers, terminals, capacitors) and from other lugs; flat SMD parts and pads
     below the lug do not count.
  4. Control card: no lug circle or terminal / header body within 2.5 mm of the control card outline (the card
     stands 5.3 mm above the board; outline from V5_LAYOUT_PLAN.md).
Exit 1 on any finding that is not listed in EXCEPT.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.join(os.path.dirname(HERE), "v5"),
                os.path.dirname(HERE)]
import board_common as bc  # noqa: E402
import card_layout as L  # noqa: E402

T = pcbnew.ToMM
WALL_P, WALL_I = -83.05, 71.75
CARD_X = (15.2, 117.3)
ENVELOPE, H_ENV = 18.0, 4.0
BODY_MIN, SCREW_MIN, MARGIN = 20.0, 22.0, 0.3
LUG_R, LUG_GAP = 4.0, 2.5
CTRL_CARD = (42.599, -18.766, 118.599, 46.361)
TERMINALS = [f"J{n}" for n in range(31, 39)]     # REDCUBE; J39 ... J42 are pigtail holes (0 mm on top)
HEADERS = [f"J{n}" for n in range(21, 27)]
HEIGHT = dict(L.HEIGHT)
# soldered wire landings (pigtail holes, the SW landing pins AFE_OUT1 / J5 / J7 / INU_OUT2): 0 mm, the wire is not checked
HEIGHT.update({"WirePigtail_D6.0mm_Drill3.0mm": 0.0, "Terminal_D4.0mm_Drill2.55mm": 0.0, "Wuerth_REDCUBE-PressFit_7462810_M3": 7.0, "Samtec_SHF-105-01-L-D-TH": 5.33,
               "Converter_DCDC_Mornsun_B05xxS-1WR3_SIP-4": 10.2, "R_0603_1608Metric": 0.55, "C_0603_1608Metric": 0.9,
               "D_SOD-323": 1.1, "D_SOD-123": 1.35})
# 5. inductor profiles (V6_PLAN sections 14 / 15, planning session 2026-11-26): upright toroids, R 26.6 mm, 27.9 mm
#    thick across the wall, centred between their leads, standing on a 5 mm spacer; under the rim at distance d along
#    the wall the free height is s + R - sqrt(R^2 - d^2). Top-side parts in the body's strip must fit under it; a part
#    reaching less than 1 mm into the strip is tangent. Heights of parts not in HEIGHT: assumptions below.
INDUCTORS = {"AFE choke": (-17.0, -63.85, 5.0, ("J5", "FILTER_OUT1")), "inverter inductor": (-72.0, 57.0, 5.0, ("J7", "J9"))}
IND_R, IND_HALF, IND_TOL = 26.6, 27.9 / 2, 1.0
IND_HEIGHT = {"C_Disc_D12.5mm_W5.0mm_P7.50mm": 16.0,          # assumption (to verify)
              "Terminal_D4.0mm_Drill3.0mm": 6.0, "Wuerth_REDCUBE-THR_74650074_M4_PTH": 11.0,
              "Wuerth_REDCUBE-PressFit_7462810_M3": 11.0, "WireHole_D5.0mm_Drill2.3mm": 0.0,
              "WirePigtail_D6.0mm_Drill3.0mm": 99.0}          # a soldered wire rises from a pigtail: wholly outside
# J5S (step 5c, user 2026-11-27): the AFE leg 1 SW wire is soldered in under the choke rim and bends out towards the
# wall; about 8 mm of wire height there instead of a wire standing up
IND_REF_HEIGHT = {"J5S": 8.0}
# finding prefix -> reason (planning session decisions)
EXCEPT = {
    "J25: body": "header between the control card edge and the 18 mm line (Fable 2026-11-23)",
    "J26: body": "header between the control card edge and the 18 mm line (Fable 2026-11-23)",
    "J31: body": "AFE leg 1 pair beside the area of the bulk caps: 19.95 mm (Fable 2026-11-23)",
    "J32: body": "AFE leg 1 pair beside the area of the bulk caps: 19.95 mm (Fable 2026-11-23)",
}


def box(fp):
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
    return T(bb.GetLeft()), -T(bb.GetBottom()), T(bb.GetRight()), -T(bb.GetTop())


def poly(fp):
    c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if c.OutlineCount() == 0:
        x0, y0, x1, y1 = box(fp)
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    o = c.Outline(0)
    return [(T(o.CPoint(i).x), -T(o.CPoint(i).y)) for i in range(o.PointCount())]


def inside(px, py, pts):
    res = False
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            res = not res
    return res


def pt_poly(px, py, pts):
    if inside(px, py, pts):
        return 0.0
    best = 1e9
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = x2 - x1, y2 - y1
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - x1 - t * dx, py - y1 - t * dy))
    return best


def tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def pads_c(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return sum(T(p.x) for p in ps) / len(ps), -sum(T(p.y) for p in ps) / len(ps)


def main():
    b = pcbnew.LoadBoard(bc.BOARD)
    fps = [f for f in b.GetFootprints() if -T(f.GetPosition().y) > -88.0]     # not in the staging area
    by = {f.GetReference(): f for f in fps}
    err, info = [], []
    # 1. envelope
    for f in fps:
        x0, y0, x1, y1 = box(f)
        if not (x1 > CARD_X[0] and x0 < CARD_X[1]):
            continue
        if y0 < WALL_P + ENVELOPE or y1 > WALL_I - ENVELOPE:
            name = str(f.GetFPID().GetLibItemName())
            h = HEIGHT.get(name)
            ref = f.GetReference()
            if ref in L.NO_HEIGHT:
                continue
            if h is None:
                err.append(f"{ref}: no height known for {name} inside the card envelope")
            elif h > H_ENV and not f.IsFlipped():
                err.append(f"{ref}: {h} mm tall within {ENVELOPE} mm of a wall in the card span")
    # 2. terminal and header bodies, screws
    for ref in TERMINALS + HEADERS + ["J39", "J40", "J41", "J42"]:
        f = by.get(ref)
        if f is None:
            err.append(f"{ref}: not placed")
            continue
        x0, y0, x1, y1 = box(f)
        d = min(y0 - WALL_P, WALL_I - y1) + MARGIN
        if ref in ("J39", "J40", "J41", "J42"):
            hole = min(min(p.GetPosition().y for p in f.Pads()), 1e18)
            cy_ = [(-T(p.GetPosition().y)) for p in f.Pads()]
            if any(WALL_I - y < 10.0 or WALL_I - y > 16.0 for y in cy_):
                err.append(f"{ref}: pigtail hole outside 10 ... 16 mm from the wall")
            continue
        if d < BODY_MIN:
            err.append(f"{ref}: body {d:.2f} mm from the wall (>= {BODY_MIN})")
        if ref in TERMINALS:
            cx, cy = pads_c(f)
            s = min(cy - WALL_P, WALL_I - cy)
            if s < SCREW_MIN:
                err.append(f"{ref}: screw centre {s:.2f} mm from the wall (>= {SCREW_MIN})")
    # 3. lugs, 4. control card
    cx0, cy0, cx1, cy1 = CTRL_CARD
    for ref in TERMINALS:
        f = by.get(ref)
        if f is None:
            continue
        cx, cy = pads_c(f)
        worst = (99.0, "")
        for o in fps:
            oref = o.GetReference()
            if oref == ref or not tht(o) or HEIGHT.get(str(o.GetFPID().GetLibItemName()), 99) < 5.0:
                continue      # flat soldered landing pins and pigtail holes lie under the lug
            if oref in TERMINALS:
                ox, oy = pads_c(o)
                d, what = math.hypot(ox - cx, oy - cy) - 2 * LUG_R, f"{oref} lug"
            else:
                d, what = pt_poly(cx, cy, poly(o)) - LUG_R, f"{oref} courtyard"
            if d < worst[0]:
                worst = (d, what)
        info.append(f"{ref}: lug circle {worst[0]:.2f} mm from {worst[1]}")
        if worst[0] < LUG_GAP:
            err.append(f"{ref}: lug circle {worst[0]:.2f} mm from {worst[1]} (>= {LUG_GAP})")
        dcard = math.hypot(max(cx0 - cx, 0, cx - cx1), max(cy0 - cy, 0, cy - cy1)) - LUG_R
        if dcard < LUG_GAP:
            err.append(f"{ref}: lug circle {dcard:.2f} mm from the control card outline (>= {LUG_GAP})")
    for ref in HEADERS:
        f = by.get(ref)
        if f is None:
            continue
        x0, y0, x1, y1 = box(f)
        dx, dy = max(cx0 - x1, x0 - cx1, 0), max(cy0 - y1, y0 - cy1, 0)
        if math.hypot(dx, dy) < LUG_GAP and not (dx > 0 or dy > 0) or math.hypot(dx, dy) < 0.5:
            err.append(f"{ref}: header under or at the control card outline ({math.hypot(dx, dy):.2f} mm)")
    # 5. inductor profiles
    for name, (xc, yc, s_, leads) in INDUCTORS.items():
        for f in fps:
            if f.IsFlipped() or f.GetReference() in leads:
                continue
            c = f.GetCourtyard(pcbnew.F_CrtYd)
            pts = poly(f)
            xs = []
            for i in range(len(pts)):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
                for k in range(21):
                    x, y = x1 + (x2 - x1) * k / 20, y1 + (y2 - y1) * k / 20
                    if yc - IND_HALF + IND_TOL <= y <= yc + IND_HALF - IND_TOL:
                        xs.append(x)
            if not xs:
                continue
            d = max(min(xs) - xc, xc - max(xs), 0.0)
            if d >= IND_R:
                continue
            free = s_ + IND_R - math.sqrt(IND_R * IND_R - d * d)
            name_fp = str(f.GetFPID().GetLibItemName())
            h = IND_REF_HEIGHT.get(f.GetReference(), IND_HEIGHT.get(name_fp, HEIGHT.get(name_fp)))
            if h is None:
                h = 35.0 if name_fp.startswith("CP_Radial_D35") else (30.0 if name_fp.startswith("C_Rect") else None)
            if h is None:
                err.append(f"{f.GetReference()}: under the {name} (free {free:.1f} mm) with no height known for {name_fp}")
            elif h > free:
                err.append(f"{f.GetReference()}: {h} mm tall under the {name}, free {free:.1f} mm at d {d:.1f} mm")
            else:
                info.append(f"{f.GetReference()}: under the {name}, {h} mm in {free:.1f} mm free (d {d:.1f} mm)")
    acc = [e for e in err if any(e.startswith(k) for k in EXCEPT)]
    err = [e for e in err if e not in acc]
    for line in info:
        print("check_layout_v6: " + line)
    for e in acc:
        print("check_layout_v6: accepted " + e)
    for e in err:
        print("check_layout_v6: ERROR " + e)
    print("check_layout_v6: " + ("OK" if not err else f"FAILED ({len(err)})"))
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
