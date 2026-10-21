#!/usr/bin/env python3
"""Phase 4: gerber round trip - KiCad's copper gerbers vs the Proteus CADCAM gerbers
(system python3: numpy, scipy, PIL; kicad-cli for the export).

Exports the copper layers and the plated drill of kicad/ac_psu.kicad_pcb with kicad-cli
(gerbers, drill as gerber), parses both sets with tools/gerber.py and rasterises every
copper layer of both on the same grid (RES mm per pixel, objects drawn in file order with
their polarity, so Proteus' clear regions cut the pours exactly as a plotter would).
Per layer:
  raw XOR area, and the differing area after a TOL mm tolerance (a pixel counts only when it
  is farther than TOL from any copper of the other set - absorbs the rounding of pad corners,
  zone edges and the raster itself);
  the difference clusters (8-connected), each with side (only Proteus / only KiCad), area,
  position (IPC frame), the nearest IPC pad with its net, the nearest via, and a category:
    pad shape   inside the XOR of the two sets' pad flashes: a KiCad pad kept with the KiCad
                library size or shape (0402/0603/1206 passives, J12, TPS73033, round-rect
                corners, ...);
    clearance   Proteus copper within CLEARANCE + TOL of a KiCad pad that is larger than the
                Proteus pad: KiCad's 0.15 mm zone clearance around the bigger pad;
    zone fill   Proteus copper thinner than the zone minimum width (slivers KiCad does not
                fill);
    other       everything else - a finding, listed in full.
  An overlay PNG per layer (reports/roundtrip/<layer>.png, OVERLAY_RES mm per pixel): common
  copper grey, only-Proteus red, only-KiCad cyan, differences absorbed by the tolerance dim.
Drills: every Proteus drill flash must have a KiCad drill within TOL and vice versa; a KiCad
drill may be larger (footprints kept with the KiCad drill: C_Disc, J12, PWM1, R10, C24 - Phase 3
decision) but never smaller than the Proteus drill (DRILL_TOL).
Report: reports/roundtrip/roundtrip.txt (per layer: areas, categories, every cluster of at
least MIN_AREA mm^2, coverage misses, pad shape clusters per footprint; drill table).
Exit status 1 (--check) when an 'other' cluster of at least MIN_AREA mm^2 exists, a draw or
flash is not covered, or a drill does not match.

Usage: python3 tools/gerber_roundtrip.py [--check] [--kicad-dir DIR] [--keep]
  --kicad-dir  reuse KiCad gerbers exported earlier (default: export to a temp dir)
  --keep       keep the exported gerbers in reports/roundtrip/kicad_gerbers/
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import gerber  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
CADCAM = os.path.join(ROOT, "source", "cadcam")
IPC_JSON = os.path.join(ROOT, "reference", "ipc356_pads.json")
OUT = os.path.join(ROOT, "reports", "roundtrip")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")

RES = 0.025          # mm per pixel of the comparison raster
TOL = 0.05           # mm, geometric tolerance (same as the pad position tolerance)
CLEARANCE = 0.15     # mm, KiCad board clearance
ZONE_MIN_WIDTH = 0.1  # mm, zone minimum width (pours_to_zones.py)
MIN_AREA = 0.01      # mm^2, clusters below this are only counted
OVERLAY_RES = 0.1    # mm per pixel of the overlay PNGs
DRILL_TOL = 0.005    # mm, drill diameter tolerance (KiCad plots drills with 1 um, Proteus 0.1 um)

# (Proteus gerber name, KiCad layer, kicad-cli file suffix)
LAYERS = [
    ("Top Copper", "F.Cu", "gtl"),
    ("Inner  1", "In1.Cu", "g1"),
    ("Inner  2", "In2.Cu", "g2"),
    ("Bottom Copper", "B.Cu", "gbl"),
]
PAD_FUNCTIONS = ("ComponentPad", "SMDPad,CuDef", "OtherPad")


def proteus_path(name):
    import glob
    paths = glob.glob(os.path.join(CADCAM, f"* - CADCAM {name}.GBR"))
    if len(paths) != 1:
        sys.exit(f"gerber {name!r} not found in {CADCAM}")
    return paths[0]


def export_kicad(outdir):
    layers = ",".join(k for _, k, _ in LAYERS)
    for args in (["pcb", "export", "gerbers", "-o", outdir + "/", "--layers", layers, BOARD],
                 ["pcb", "export", "drill", "-o", outdir + "/", "--format", "gerber", BOARD]):
        r = subprocess.run([CLI] + args, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"kicad-cli {' '.join(args[:3])} failed:\n{r.stdout}{r.stderr}")


def board_bbox():
    """Bounding box of the Proteus board outline (Mechanical 1), mm."""
    g = gerber.parse(proteus_path("Mechanical 1"))
    xs, ys = [], []
    for d in g.of(gerber.Draw):
        xs += [d.x1, d.x2]
        ys += [d.y1, d.y2]
    return min(xs), min(ys), max(xs), max(ys)


class Canvas:
    """Rasteriser: mm (Y up) -> pixels (row 0 = top edge), PIL 'L' image, 255 = copper."""

    def __init__(self, bbox, margin=1.0):
        x0, y0, x1, y1 = bbox
        self.x0, self.y1 = x0 - margin, y1 + margin
        self.w = int(math.ceil((x1 - x0 + 2 * margin) / RES))
        self.h = int(math.ceil((y1 - y0 + 2 * margin) / RES))
        self.im = Image.new("L", (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)

    def px(self, x, y):
        return ((x - self.x0) / RES, (self.y1 - y) / RES)

    def mm(self, col, row):
        return (self.x0 + col * RES, self.y1 - row * RES)

    def circle(self, cx, cy, dia, v):
        r = dia / 2 / RES
        px, py = self.px(cx, cy)
        self.d.ellipse([px - r, py - r, px + r, py + r], fill=v)

    def poly(self, pts, v):
        if len(pts) >= 3:
            self.d.polygon([self.px(x, y) for x, y in pts], fill=v)

    def rect(self, cx, cy, w, h, v):
        w, h = w / 2, h / 2
        self.poly([(cx - w, cy - h), (cx + w, cy - h), (cx + w, cy + h), (cx - w, cy + h)], v)

    def line(self, x1, y1, x2, y2, w, v):
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L > 0:
            nx, ny = -dy / L * w / 2, dx / L * w / 2
            self.poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], v)
            self.circle(x2, y2, w, v)
        self.circle(x1, y1, w, v)

    def flash(self, f, v):
        ap = f.ap
        if ap.shape == "C":
            self.circle(f.x, f.y, ap.params[0], v)
        elif ap.shape == "R":
            self.rect(f.x, f.y, ap.params[0], ap.params[1], v)
        elif ap.shape == "O":
            w, h = ap.params
            if abs(w - h) < 1e-9:
                self.circle(f.x, f.y, w, v)
            elif w > h:
                self.line(f.x - (w - h) / 2, f.y, f.x + (w - h) / 2, f.y, h, v)
            else:
                self.line(f.x, f.y - (h - w) / 2, f.x, f.y + (h - w) / 2, w, v)
        else:
            for p in ap.primitives:
                if p[0] == "poly":
                    self.poly([(f.x + x, f.y + y) for x, y in p[1]], v)
                else:
                    self.circle(f.x + p[2], f.y + p[3], p[1], v)

    def obj(self, o, v=None):
        if v is None:
            v = 255 if o.dark else 0
        if isinstance(o, gerber.Flash):
            self.flash(o, v)
        elif isinstance(o, gerber.Draw):
            if o.ap.shape != "C":
                raise ValueError(f"draw with a {o.ap.shape} aperture")
            self.line(o.x1, o.y1, o.x2, o.y2, o.ap.params[0], v)
        else:
            for c in o.contours:
                self.poly(c, v)

    def array(self):
        return np.asarray(self.im) > 0


def disk(r_px):
    r = int(math.ceil(r_px))
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return (xx * xx + yy * yy) <= r_px * r_px + 1e-9


def grow(mask, r_mm):
    return ndimage.binary_dilation(mask, structure=disk(r_mm / RES))


def render(g, bbox):
    """(copper, pads) boolean rasters of one gerber: everything in file order, and the pad
    flashes (ComponentPad / SMDPad / OtherPad) alone."""
    full, pads = Canvas(bbox), Canvas(bbox)
    for o in g.objects:
        if isinstance(o, gerber.Draw) and o.ap.function == "Profile":
            continue   # Proteus draws the board outline into every copper gerber: not copper
        full.obj(o)
        if isinstance(o, gerber.Flash) and o.ap.function in PAD_FUNCTIONS:
            pads.obj(o)
        elif isinstance(o, gerber.Region) and "P" in o.attrs:   # KiCad custom pad shape
            pads.obj(o)
    return full.array(), pads.array(), full


def coverage(g, other, canvas, explained):
    """Draws and flashes of gerber g whose centre line / centre is not on copper of the other
    set (other = boolean raster, 1 px of slack). Catches features thinner than 2 * TOL, which
    the XOR with tolerance cannot see. Samples inside `explained` (the clearance / pad shape
    masks) are counted separately. Returns [(kind, x, y, width/dia, function, attrs, off,
    explained, samples)]."""
    cover = ndimage.binary_dilation(other, structure=np.ones((3, 3)))
    h, w = cover.shape
    missing = []

    def on_copper(x, y):
        c, r = canvas.px(x, y)
        c, r = int(c), int(r)
        if not (0 <= r < h and 0 <= c < w):
            return False
        return True if cover[r, c] else ("explained" if explained[r, c] else False)

    for o in g.objects:
        if not o.dark:
            continue
        if isinstance(o, gerber.Draw):
            if o.ap.function == "Profile":
                continue
            n = max(2, int(math.hypot(o.x2 - o.x1, o.y2 - o.y1) / (RES / 2)) + 1)
            res = Counter(on_copper(o.x1 + (o.x2 - o.x1) * i / (n - 1), o.y1 + (o.y2 - o.y1) * i / (n - 1)) for i in range(n))
            if res[False] or res["explained"]:
                missing.append(("draw", (o.x1 + o.x2) / 2, (o.y1 + o.y2) / 2, o.ap.params[0], o.ap.function, o.attrs,
                                res[False], res["explained"], n))
        elif isinstance(o, gerber.Flash):
            r = on_copper(o.x, o.y)
            if r is not True:
                missing.append(("flash", o.x, o.y, o.ap.params[0] if o.ap.params else 0, o.ap.function, o.attrs,
                                int(r is False), int(r == "explained"), 1))
    return missing


def load_footprints():
    import csv
    out = {}
    with open(os.path.join(ROOT, "lib", "footprint_map.csv")) as f:
        for row in csv.DictReader(r for r in f if not r.startswith("#")):
            out[row["refdes"]] = row["footprint"]
    return out


FOOTPRINTS = load_footprints()


def load_ipc():
    with open(IPC_JSON) as f:
        recs = json.load(f)["pads"]
    pads = {k: [] for _, k, _ in LAYERS}
    for p in recs:
        if p["kind"] != "pad":
            continue
        for _, k, _ in LAYERS:
            if p["side"] == "both" or (k == "F.Cu" and p["side"] == "top") or (k == "B.Cu" and p["side"] == "bottom"):
                pads[k].append(p)
    vias = [p for p in recs if p["kind"] == "via"]
    return pads, vias


def nearest(recs, x, y):
    if not recs:
        return None, math.inf
    xy = np.array([(p["x_mm"], p["y_mm"]) for p in recs])
    d = np.hypot(xy[:, 0] - x, xy[:, 1] - y)
    i = int(d.argmin())
    return recs[i], float(d[i])


def compare_layer(layer, gp, gk, bbox, ipc_pads, ipc_vias, report):
    """Rasterise, XOR, cluster and classify one layer. Returns (summary dict, overlay arrays)."""
    P, Ppads, canvas = render(gp, bbox)
    K, Kpads, _ = render(gk, bbox)
    px_area = RES * RES
    # classification masks
    xor = P ^ K
    onlyP = P & ~grow(K, TOL)
    onlyK = K & ~grow(P, TOL)
    diff = onlyP | onlyK
    # classification masks
    pad_xor = grow(Ppads ^ Kpads, TOL)
    k_bigger = Kpads & ~Ppads
    clearance = grow(k_bigger, CLEARANCE + TOL) & ~Kpads
    miss_P = coverage(gp, K, canvas, clearance | pad_xor)   # Proteus items without KiCad copper under them
    miss_K = coverage(gk, P, canvas, pad_xor)               # KiCad items without Proteus copper under them
    unexpl_P = [m for m in miss_P if m[6]]
    unexpl_K = [m for m in miss_K if m[6]]
    # Proteus copper too thin for the zone fill: copper that an opening of ZONE_MIN_WIDTH removes
    thin = P & ~ndimage.binary_opening(P, structure=disk(ZONE_MIN_WIDTH / 2 / RES))
    labels, n = ndimage.label(diff, structure=np.ones((3, 3)))
    objs = ndimage.find_objects(labels)
    clusters = []
    for i, sl in enumerate(objs, 1):
        m = labels[sl] == i
        area = int(m.sum()) * px_area
        side = "Proteus" if onlyP[sl][m].sum() >= onlyK[sl][m].sum() else "KiCad"
        rows, cols = np.nonzero(m)
        cy = sl[0].start + rows.mean()
        cx = sl[1].start + cols.mean()
        x, y = canvas.mm(cx + 0.5, cy + 0.5)
        hgt, wid = (sl[0].stop - sl[0].start) * RES, (sl[1].stop - sl[1].start) * RES
        if pad_xor[sl][m].all():
            cat = "pad shape"
        elif side == "Proteus" and clearance[sl][m].all():
            cat = "clearance"
        elif side == "Proteus" and (thin[sl][m] | pad_xor[sl][m] | clearance[sl][m]).all():
            cat = "zone fill"
        else:
            cat = "other"
        pad, dp = nearest(ipc_pads, x, y)
        via, dv = nearest(ipc_vias, x, y)
        clusters.append(dict(cat=cat, side=side, area=area, x=x, y=y, w=wid, h=hgt,
                             pad=f"{pad['refdes']}-{pad['pin']} ({pad['net'] or pad['net_raw']}) {dp:.2f} mm" if pad else "-",
                             via=f"via ({via['net']}) {dv:.2f} mm" if via else "-"))
    clusters.sort(key=lambda c: -c["area"])
    by_cat = Counter()
    area_cat = Counter()
    for c in clusters:
        if c["area"] >= MIN_AREA:
            by_cat[c["cat"]] += 1
            area_cat[c["cat"]] += c["area"]
    summ = dict(layer=layer, miss_P=unexpl_P, miss_K=unexpl_K,
                copper_P=int(P.sum()) * px_area, copper_K=int(K.sum()) * px_area,
                xor=int(xor.sum()) * px_area, onlyP=int(onlyP.sum()) * px_area, onlyK=int(onlyK.sum()) * px_area,
                clusters=len(clusters), small=sum(1 for c in clusters if c["area"] < MIN_AREA),
                by_cat=by_cat, area_cat=area_cat, other=[c for c in clusters if c["cat"] == "other" and c["area"] >= MIN_AREA])
    report.append(f"== {layer}: Proteus copper {summ['copper_P']:.1f} mm^2, KiCad copper {summ['copper_K']:.1f} mm^2")
    report.append(f"   raw XOR {summ['xor']:.2f} mm^2; after {TOL} mm tolerance: only Proteus {summ['onlyP']:.2f} mm^2, "
                  f"only KiCad {summ['onlyK']:.2f} mm^2, {len(clusters)} clusters ({summ['small']} below {MIN_AREA} mm^2)")
    for cat in ("pad shape", "clearance", "zone fill", "other"):
        if by_cat[cat]:
            report.append(f"   {cat:10s} {by_cat[cat]:4d} clusters, {area_cat[cat]:.2f} mm^2")
    nd_p, nf_p = sum(isinstance(o, gerber.Draw) for o in gp.objects), sum(isinstance(o, gerber.Flash) for o in gp.objects)
    nd_k, nf_k = sum(isinstance(o, gerber.Draw) for o in gk.objects), sum(isinstance(o, gerber.Flash) for o in gk.objects)
    report.append(f"   coverage: Proteus {nd_p} draws / {nf_p} flashes, {len(unexpl_P)} not on KiCad copper "
                  f"({len(miss_P) - len(unexpl_P)} explained by clearance / pad shape); "
                  f"KiCad {nd_k} draws / {nf_k} flashes, {len(unexpl_K)} not on Proteus copper "
                  f"({len(miss_K) - len(unexpl_K)} explained by pad shape)")
    for who, miss in (("Proteus", miss_P), ("KiCad", miss_K)):
        for kind, x, y, wd, fn, at, bad, expl, n in miss:
            pad, dp = nearest(ipc_pads, x, y)
            tag = "MISSING  " if bad else "explained"
            report.append(f"   {tag} {who} {kind} {fn} {wd} mm at ({x:.3f}, {y:.3f}) {at or ''} "
                          f"{bad} samples off copper, {expl} in clearance/pad shape, of {n}; "
                          f"near {pad['refdes']}-{pad['pin']} ({pad['net'] or pad['net_raw']}) {dp:.2f} mm")
    # pad shape clusters per footprint (nearest IPC pad -> refdes -> footprint)
    per_fp = {}
    for c in clusters:
        if c["cat"] == "pad shape" and c["area"] >= MIN_AREA:
            ref = c["pad"].split("-")[0]
            e = per_fp.setdefault(FOOTPRINTS.get(ref, ref), [0, 0.0, 0.0, set()])
            e[0] += 1
            e[1 if c["side"] == "KiCad" else 2] += c["area"]
            e[3].add(ref)
    for fp, (n, ak, ap_, refs) in sorted(per_fp.items(), key=lambda kv: -(kv[1][1] + kv[1][2])):
        report.append(f"   pad shape  {n:4d} clusters, only KiCad {ak:6.2f} mm^2, only Proteus {ap_:6.2f} mm^2  {fp}  "
                      f"({len(refs)} parts: {' '.join(sorted(refs)[:6])}{' ...' if len(refs) > 6 else ''})")
    order = {"other": 0, "clearance": 1, "zone fill": 2, "pad shape": 3}
    for c in sorted(clusters, key=lambda c: (order[c["cat"]], -c["area"])):
        if c["area"] < MIN_AREA:
            continue
        report.append(f"   {c['cat']:10s} only {c['side']:7s} {c['area']:6.3f} mm^2 at ({c['x']:8.3f}, {c['y']:8.3f}) "
                      f"{c['w']:.2f}x{c['h']:.2f} mm  near {c['pad']}, {c['via']}")
    return summ, (P, K, xor, onlyP, onlyK)


def overlay(layer, arrays):
    P, K, xor, onlyP, onlyK = arrays
    f = int(round(OVERLAY_RES / RES))
    h, w = P.shape
    H, W = -(-h // f), -(-w // f)

    def pool(m):
        pad = np.zeros((H * f, W * f), bool)
        pad[:h, :w] = m
        return pad.reshape(H, f, W, f).any(axis=(1, 3))

    common = pool(P & K)
    img = np.zeros((H, W, 3), np.uint8)
    img[common] = (90, 90, 90)
    img[pool(xor)] = (120, 110, 40)
    img[pool(onlyP)] = (255, 60, 60)
    img[pool(onlyK)] = (0, 200, 255)
    Image.fromarray(img).save(os.path.join(OUT, layer.replace(".", "_") + ".png"))


def compare_drills(kdir, report):
    gp = gerber.parse(proteus_path("Drill TOP-BOT Plated"))
    gk = gerber.parse(os.path.join(kdir, "ac_psu-PTH-drl.gbr"))
    P = [(f.x, f.y, f.ap.params[0], f.ap.function) for f in gp.of(gerber.Flash)]
    K = [(f.x, f.y, f.ap.params[0], f.ap.function) for f in gk.of(gerber.Flash)]
    kxy = np.array([(x, y) for x, y, _, _ in K])
    used = np.zeros(len(K), bool)
    pairs = Counter()
    errors = []
    for x, y, d, fn in P:
        dist = np.hypot(kxy[:, 0] - x, kxy[:, 1] - y)
        dist[used] = np.inf
        i = int(dist.argmin())
        if dist[i] > TOL:
            errors.append(f"Proteus {fn} {d} mm at ({x}, {y}) has no KiCad drill within {TOL} mm")
            continue
        used[i] = True
        dk = K[i][2]
        pairs[(d, dk)] += 1
        if dk < d - DRILL_TOL:
            errors.append(f"drill at ({x}, {y}): Proteus {d} mm, KiCad {dk} mm is smaller")
    for i in np.nonzero(~used)[0]:
        x, y, d, fn = K[i]
        errors.append(f"KiCad {fn} {d} mm at ({x}, {y}) has no Proteus drill")
    report.append(f"== drills: Proteus {len(P)}, KiCad {len(K)}, matched {int(used.sum())} within {TOL} mm")
    for (d, dk), n in sorted(pairs.items()):
        note = "" if abs(d - dk) <= DRILL_TOL else ("  KiCad footprint drill kept (larger)" if dk > d else "  SMALLER")
        report.append(f"   {n:4d} x Proteus {d:.4f} mm -> KiCad {dk:.4f} mm{note}")
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--kicad-dir")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tmp = None
    if args.kicad_dir:
        kdir = args.kicad_dir
    elif args.keep:
        kdir = os.path.join(OUT, "kicad_gerbers")
        shutil.rmtree(kdir, ignore_errors=True)
        os.makedirs(kdir)
        export_kicad(kdir)
    else:
        tmp = tempfile.mkdtemp(prefix="ac_psu_gerbers_")
        kdir = tmp
        export_kicad(kdir)
    try:
        bbox = board_bbox()
        ipc_pads, ipc_vias = load_ipc()
        report = [f"Gerber round trip: KiCad plot of kicad/ac_psu.kicad_pcb vs the Proteus CADCAM gerbers",
                  f"raster {RES} mm/px, tolerance {TOL} mm, clusters >= {MIN_AREA} mm^2 counted, "
                  f"positions in the IPC frame (mm, Y up)",
                  f"board outline {bbox[0]} .. {bbox[2]} x {bbox[1]} .. {bbox[3]} mm", ""]
        summaries = []
        for pname, klayer, ext in LAYERS:
            gp = gerber.parse(proteus_path(pname))
            gk = gerber.parse(os.path.join(kdir, f"ac_psu-{klayer.replace('.', '_')}.{ext}"))
            summ, arrays = compare_layer(klayer, gp, gk, bbox, ipc_pads[klayer], ipc_vias, report)
            overlay(klayer, arrays)
            summaries.append(summ)
            report.append("")
        drill_errors = compare_drills(kdir, report)
        for e in drill_errors:
            report.append("   ERROR " + e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(OUT, "roundtrip.txt"), "w") as f:
        f.write("\n".join(report) + "\n")
    other = sum(len(s["other"]) for s in summaries)
    missing = sum(len(s["miss_P"]) + len(s["miss_K"]) for s in summaries)
    for s in summaries:
        cats = ", ".join(f"{s['by_cat'][c]} {c}" for c in ("pad shape", "clearance", "zone fill", "other") if s["by_cat"][c])
        print(f"roundtrip: {s['layer']:6s} XOR {s['xor']:7.2f} mm^2, beyond {TOL} mm: only Proteus {s['onlyP']:6.2f}, "
              f"only KiCad {s['onlyK']:6.2f} mm^2; clusters >= {MIN_AREA} mm^2: {cats or 'none'}; "
              f"draws/flashes off the other copper: {len(s['miss_P'])} Proteus, {len(s['miss_K'])} KiCad")
    for s in summaries:
        for c in s["other"]:
            print(f"roundtrip: {s['layer']} OTHER only {c['side']} {c['area']:.3f} mm^2 at ({c['x']:.3f}, {c['y']:.3f}) near {c['pad']}, {c['via']}")
    print(f"roundtrip: drills {len(drill_errors)} mismatches; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png")
    for e in drill_errors[:10]:
        print("roundtrip: ERROR " + e)
    ok = other == 0 and missing == 0 and not drill_errors
    print("roundtrip: " + ("OK" if ok else f"FAILED ({other} unexplained clusters, {missing} draws/flashes without copper "
                                            f"in the other set, {len(drill_errors)} drill mismatches)"))
    sys.exit(0 if ok or not args.check else 1)


if __name__ == "__main__":
    main()
