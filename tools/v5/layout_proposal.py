#!/usr/bin/env python3
"""Phase 1 of V5_LAYOUT_PLAN.md: check the proposed domain areas of tools/v5/card_layout.py against
today's board and write the tables and renders of reports/v5_layout/. No board change.

  python3 tools/v5/layout_proposal.py          (calls itself under tools/p2k/bin/kipy to read the board)

Writes reports/v5_layout/parts.csv, conflicts.txt, summary.txt and proposal_{F,B,In1,In2,keepout}.png.
"""
import collections
import csv
import json
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v5"))
import card_layout as L  # noqa: E402

OUT = os.path.join(ROOT, "reports", "v5_layout")
TMP = os.path.join(ROOT, "build", "v5_layout")


# ---- board dump (kipy) -----------------------------------------------------------------------
def dump(path):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "tools", "v4"))
    sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
    import pcbnew
    import board_common as bc
    import domains
    T = pcbnew.ToMM
    b = pcbnew.LoadBoard(bc.BOARD)
    comps, nets = bc.export_netlist()
    dom = domains.classify(nets)
    out = {"fps": [], "tracks": [], "zones": []}
    for fp in b.GetFootprints():
        cy = fp.GetCourtyard(fp.GetLayer())
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        pads = []
        for p in fp.Pads():
            pb = p.GetBoundingBox()
            pads.append([p.GetNumber(), p.GetNetname().split("/")[-1], dom.get(p.GetNetname()),
                         round(T(pb.GetLeft()), 3), round(-T(pb.GetBottom()), 3), round(T(pb.GetRight()), 3),
                         round(-T(pb.GetTop()), 3), p.GetDrillSize().x > 0])
        out["fps"].append(dict(ref=fp.GetReference(), val=fp.GetValue(), fpid=str(fp.GetFPID().GetLibItemName()),
                               x=round(T(fp.GetPosition().x), 3), y=round(-T(fp.GetPosition().y), 3),
                               rot=fp.GetOrientationDegrees(), side="B" if fp.IsFlipped() else "F",
                               bb=[round(T(bb.GetLeft()), 2), round(-T(bb.GetBottom()), 2), round(T(bb.GetRight()), 2),
                                   round(-T(bb.GetTop()), 2)], pads=pads, sheet=comps.get(fp.GetReference(), {}).get("sheetname", "")))
    for t in b.GetTracks():
        s, e = t.GetStart(), t.GetEnd()
        via = t.GetClass() == "PCB_VIA"
        out["tracks"].append(["via" if via else b.GetLayerName(t.GetLayer()), round(T(s.x), 3), round(-T(s.y), 3),
                              round(T(e.x), 3), round(-T(e.y), 3), round(T(t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth()), 3),
                              t.GetNetname().split("/")[-1], dom.get(t.GetNetname())])
    for z in b.Zones():
        o = z.Outline()
        out["zones"].append(dict(name=z.GetZoneName(), net=z.GetNetname().split("/")[-1], dom=dom.get(z.GetNetname()),
                                 layer=b.GetLayerName(z.GetFirstLayer()), rule=z.GetIsRuleArea(),
                                 pts=[[round(T(o.CVertex(i).x), 2), round(-T(o.CVertex(i).y), 2)] for i in range(o.TotalVertices())]))
    json.dump(out, open(path, "w"))


# ---- geometry ----------------------------------------------------------------------------------
def seg_pt(p, a, b):
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def seg_seg(a, b, c, d):
    if _cross(a, b, c, d):
        return 0.0
    return min(seg_pt(a, c, d), seg_pt(b, c, d), seg_pt(c, a, b), seg_pt(d, a, b))


def inside(p, poly):
    n, r = len(poly), False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
            r = not r
    return r


def edges(poly):
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def poly_dist(p, q):
    if inside(p[0], q) or inside(q[0], p):
        return 0.0
    return min(seg_seg(a, b, c, d) for a, b in edges(p) for c, d in edges(q))


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def in_card(bb):
    return bb[2] > L.CARD[0] and bb[0] < L.CARD[2] and bb[3] > L.CARD[1] and bb[1] < L.CARD[3]


# ---- analysis ----------------------------------------------------------------------------------
ISLAND_B_V5 = set("W1 D16 C137 C138 C139 C140 C141 C142 C143 C144 R131 R132 R133 R134 R135 U28 L2 J13 PEC2".split())


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    bj = os.path.join(TMP, "board.json")
    subprocess.run([os.path.join(ROOT, "tools", "p2k", "bin", "kipy"), os.path.abspath(__file__), "--dump", bj], check=True)
    d = json.load(open(bj))
    fps = {f["ref"]: f for f in d["fps"]}
    log = []
    say = lambda s="": (log.append(s), print(s))

    # 1. the areas keep 5.0 mm from each other
    say("== gaps between the proposed copper areas (need >= %.1f mm)" % L.GAP)
    polys = {k: v[1] for k, v in L.AREAS.items()}
    names = sorted(polys)
    ok = True
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if L.AREAS[a][0] == L.AREAS[b][0]:
                continue
            g = poly_dist(polys[a], polys[b])
            ok &= g >= L.GAP - 1e-6
            say(f"  {a:2} <-> {b:2}  {g:6.2f} mm" + ("" if g >= L.GAP - 1e-6 else "   ** TOO SMALL **"))
    g = min(poly_dist(polys["CA"], p) for p in L.I_AROUND_CA)
    ok &= g >= L.GAP - 1e-6
    say(f"  CA <-> ISO copper west/north of J11 (pours pulled back)  {g:6.2f} mm")
    say("  areas: " + ", ".join(f"{k} {area(polys[k]):.0f} mm2" for k in names))

    # 2. parts table
    rows, hard = [], []
    staged_out = 0
    for ref, f in sorted(fps.items(), key=lambda kv: (kv[1]["sheet"], kv[0])):
        staged = f["y"] < -84
        doms = sorted({p[2] for p in f["pads"] if p[2]})
        if ref in L.PLACE:
            ar, side, x, y, note = L.PLACE[ref]
            rows.append([ref, f["val"], f["fpid"], "/".join(doms), "place" if staged else "move", "" if staged else f["side"],
                         "" if staged else f["x"], "" if staged else f["y"], ar, side, x, y, note])
            continue
        if staged:
            if ref in ISLAND_B_V5 or f["sheet"].startswith("11"):
                hard.append(f"{ref}: v5 part without a proposed position")
            staged_out += 1
            continue
        if not in_card(f["bb"]):
            continue
        # fixed part: every pad must lie in an area of its own domain, >= GAP from the other domains' areas
        where = set()
        for p in f["pads"]:
            pr = rect(p[3], p[4], p[5], p[6])
            c = ((p[3] + p[5]) / 2, (p[4] + p[6]) / 2)
            own = [k for k in names if inside(c, polys[k])]
            where.update(own)
            if not p[2]:
                continue
            for k in names:
                if L.AREAS[k][0] != p[2]:
                    g = poly_dist(pr, polys[k])
                    if g < L.GAP - 1e-6:
                        hard.append(f"{ref}-{p[0]} ({p[1]}, {p[2]}) fixed, {g:.2f} mm from area {k}")
            if own and L.AREAS[own[0]][0] != p[2]:
                hard.append(f"{ref}-{p[0]} ({p[1]}, {p[2]}) fixed, inside area {own[0]}")
        rows.append([ref, f["val"], f["fpid"], "/".join(doms), "fixed", f["side"], f["x"], f["y"], "|".join(sorted(where)) or "-",
                     f["side"], f["x"], f["y"], ""])
    with open(os.path.join(OUT, "parts.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow("ref value footprint domain action side_now x_now y_now area side x y note".split())
        w.writerows(rows)
    cnt = collections.Counter(r[4] for r in rows)
    say(f"== parts: {cnt['place']} v5 parts placed, {cnt['move']} v4 parts moved, {cnt['fixed']} fixed in the card outline; "
        f"{staged_out} v5 parts stay staged (aux flyback, out of scope)")
    say("== fixed pads that break the proposal: %d" % len(hard))
    for h in hard:
        say("  " + h)
        ok = False

    # 3. tracks / vias to delete: foreign domain inside or < 5 mm from an area, or on a net of a moved pad
    moved_nets = set()
    for ref in L.PLACE:
        f = fps[ref]
        if f["y"] > -84:
            moved_nets.update(p[1] for p in f["pads"] if p[1] and p[1] not in
                              ("GND", "VCC", "ISOGND", "3V3_ISO", "CTRLGND", "CTRLGND_A", "3V3_CTRL", "5V_CTRL"))
    kill = collections.Counter()
    for t in d["tracks"]:
        a, b = (t[1], t[2]), (t[3], t[4])
        if not (L.CARD[0] - 6 < a[0] < L.CARD[2] + 1 and L.CARD[1] - 16 < a[1] < L.CARD[3] + 6):
            continue
        why = None
        for k in names:
            if t[7] and L.AREAS[k][0] != t[7]:
                g = 0 if inside(a, polys[k]) else min(seg_seg(a, b, c, e) for c, e in edges(polys[k])) - t[5] / 2
                if g < L.GAP - 1e-6:
                    why = f"{t[7]} copper in / near area {k}"
                    break
        if why is None and t[7] == "C" and inside(a, polys["CA"]):
            why = "J11 fan-out in CA (re-routed)"
        if why is None and t[6] in moved_nets and in_card((a[0], a[1], a[0], a[1])):
            why = "net of a moved part"
        if why:
            kill[("via" if t[0] == "via" else "track", why)] += 1
    say("== v4 tracks and vias to delete in phase 3 (become ratsnest): %d" % sum(kill.values()))
    for (kind, why), n in sorted(kill.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        say(f"  {n:4} {kind:5} {why}")
    say("== zones that touch the card area today (replaced / pulled back in phase 3)")
    for z in d["zones"]:
        if z["rule"] or len(z["pts"]) < 3:
            continue
        xs, ys = [p[0] for p in z["pts"]], [p[1] for p in z["pts"]]
        if in_card((min(xs), min(ys), max(xs), max(ys))):
            near = [k for k in names if L.AREAS[k][0] != z["dom"] and poly_dist([tuple(p) for p in z["pts"]], polys[k]) < L.GAP]
            say(f"  {z['layer']:6} {z['net']:10} {z['dom']}  {z['name']}" + (f"  -> pull back from {', '.join(near)}" if near else ""))

    # 4. slots inside the strips, top-side positions against the card's tails
    say("== slots: %d, %.1f mm wide" % (len(L.SLOTS), L.SLOT_W))
    for name, a, b in L.SLOTS:
        g = min(seg_seg(a, b, c, e) for k in names for c, e in edges(polys[k])) - L.SLOT_W / 2
        ok &= g >= 0.5
        say(f"  {name:14} ({a[0]}, {a[1]}) - ({b[0]}, {b[1]})  {math.dist(a, b):5.1f} mm long, {g:.2f} mm from the nearest copper area")
    say("== top-side parts under the card's through-hole tails (keep-out = drill/2 + %.1f mm)" % L.KEEP_MARGIN)
    hits = collections.defaultdict(set)
    for r in rows:
        f = fps[r[0]]
        if r[9] not in ("F", "THT"):
            continue
        w, h = (f["bb"][2] - f["bb"][0]) / 2, (f["bb"][3] - f["bb"][1]) / 2
        if r[4] != "fixed":
            w = h = min(w, h)       # rotation not fixed yet: the smaller half-size around the rough position
        box = rect(r[10] - w, r[11] - h, r[10] + w, r[11] + h)
        for hn, hx, hy, dr in list(L.CARD_HOLES) + list(L.TI60_HOLES):
            if inside((hx, hy), box) or min(seg_pt((hx, hy), c, e) for c, e in edges(box)) < dr / 2 + L.KEEP_MARGIN:
                hits[(hn, r[4])].add(r[0])
    for (hn, act), refs in sorted(hits.items()):
        say(f"  {hn:14} {act:5} {' '.join(sorted(refs))}")
    open(os.path.join(OUT, "check.txt"), "w").write("\n".join(log) + "\n")
    draw(d, rows)
    print("layout_proposal:", "OK" if ok else "PROBLEMS (see above)")
    return 0 if ok else 1


# courtyard w x h (mm) of the larger parts in their proposed orientation
SIZE = {**{u: (10.9, 12.0) for u in ("U16", "U19", "U20", "U21")}, "U22": (6.5, 13.1), "U23": (13.1, 6.5), "U24": (13.1, 6.5),
        "W1": (9.2, 4.2), "U8": (12.2, 9.1), "D16": (3.6, 7.1), "J13": (3.6, 6.2), "J14": (3.6, 6.2), "C137": (10.6, 8.9),
        "C138": (10.6, 8.9), "L2": (6.8, 6.6), "U25": (6.5, 3.6), "U26": (6.5, 3.6), "U7": (6.0, 3.7), "U27": (3.5, 4.2),
        "U28": (3.5, 4.2), "U2": (3.5, 4.2), "U10": (3.5, 4.2), "R97": (2.4, 5.0)}


# ---- renders -------------------------------------------------------------------------------------
def draw(d, rows):
    from PIL import Image, ImageDraw
    x0, x1, y0, y1, ppm = 28.0, 121.0, -40.0, 58.0, 16
    COL = {"C": (30, 160, 60), "P": (215, 50, 50), "I": (50, 90, 220)}
    px = lambda p: ((p[0] - x0) * ppm, (y1 - p[1]) * ppm)
    fps = {f["ref"]: f for f in d["fps"]}

    def base(layers, name):
        png = os.path.join(TMP, name + "_bg.png")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "v4", "render_area.py"), str(x0), str(x1), str(y0), str(y1),
                        png, "--layers", layers, "--ppm", str(ppm)], check=True, capture_output=True)
        im = Image.open(png).convert("RGBA")
        white = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(white, im)
        return Image.blend(white, im, 0.45)

    def overlay(im, side=None, holes=False):
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        for k, (dom, poly) in L.AREAS.items():
            dr.polygon([px(p) for p in poly], fill=COL[dom] + (55,), outline=COL[dom] + (255,))
            cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
            dr.text(px((cx - 2, cy)), {"CA": "CTRL (J11)", "CB": "CTRL (J12)", "P": "PRIMARY", "I": "ISO", "IS": "ISO (aux)"}[k], fill=COL[dom] + (255,))
        for p in L.I_AROUND_CA:
            dr.line([px(q) for q in p[1:-1]], fill=COL["I"] + (255,), width=2)
        for _, _, pl in L.LINES:
            for a, b in zip(pl, pl[1:]):
                n = max(2, int(math.dist(a, b) / 1.0))
                for i in range(0, n, 2):
                    dr.line([px((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)),
                             px((a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n))], fill=(0, 0, 0, 255), width=2)
        for _, a, b in L.SLOTS:
            dr.line([px(a), px(b)], fill=(255, 140, 0, 255), width=int(L.SLOT_W * ppm))
        dr.rectangle([px((L.CARD[0], L.CARD[3])), px((L.CARD[2], L.CARD[1]))], outline=(0, 0, 0, 255), width=3)
        if holes:
            for hs, col in ((L.CARD_HOLES, (150, 0, 150, 255)), (L.TI60_HOLES, (150, 110, 0, 255))):
                for _, hx, hy, drl in hs:
                    r = (drl / 2 + L.KEEP_MARGIN) * ppm
                    X, Y = px((hx, hy))
                    dr.ellipse([X - r, Y - r, X + r, Y + r], outline=col, width=2)
        if side:
            seen = set()
            for r in rows:
                if r[4] == "fixed" or (r[9] not in (side, "THT")):
                    continue
                f = fps[r[0]]
                key = (r[10], r[11])
                big = max(f["bb"][2] - f["bb"][0], f["bb"][3] - f["bb"][1]) > 4.4 or r[0].startswith(("U", "J", "PEC", "W", "L"))
                if big:
                    w, h = SIZE.get(r[0], (f["bb"][2] - f["bb"][0], f["bb"][3] - f["bb"][1]))
                    dr.rectangle([px((r[10] - w / 2, r[11] + h / 2)), px((r[10] + w / 2, r[11] - h / 2))], outline=(0, 0, 0, 255), width=2)
                    dr.text(px((r[10] - w / 2 + 0.2, r[11] + h / 2 - 0.2)), r[0], fill=(0, 0, 0, 255))
                elif key not in seen:
                    grp = [q[0] for q in rows if (q[10], q[11]) == key and q[4] != "fixed"]
                    dr.ellipse([px((r[10] - 0.5, r[11] + 0.5)), px((r[10] + 0.5, r[11] - 0.5))], fill=(0, 0, 0, 255))
                    dr.text(px((r[10] + 0.6, r[11] + 0.6)), grp[0] + (f" +{len(grp) - 1}" if len(grp) > 1 else ""), fill=(0, 0, 0, 255))
                seen.add(key)
        for k in range(30, 121, 10):
            dr.text(px((k, y1 - 0.3)), str(k), fill=(90, 90, 90, 255))
        for k in range(-40, 58, 10):
            dr.text(px((x0 + 0.3, k)), str(k), fill=(90, 90, 90, 255))
        return Image.alpha_composite(im, ov).convert("RGB")

    for layers, name, side, holes in (("F.Cu,F.SilkS,Edge.Cuts", "proposal_F", "F", True), ("B.Cu,B.SilkS,Edge.Cuts", "proposal_B", "B", False),
                                      ("In1.Cu,Edge.Cuts", "proposal_In1", None, False), ("In2.Cu,Edge.Cuts", "proposal_In2", None, False)):
        overlay(base(layers, name), side, holes).save(os.path.join(OUT, name + ".png"))
        print("layout_proposal: wrote", name + ".png")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        dump(sys.argv[2])
    else:
        sys.exit(main())
