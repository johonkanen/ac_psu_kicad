#!/usr/bin/env python3
"""Makes the data of block_E.py (tools/v6/route/block_E_copper.csv), run under tools/p2k/bin/kipy.

  kipy block_E_make.py clean BOARD03 BOARD          clean-up rows: pass-1 copper of BOARD inside E that is not on
                                                    BOARD03 (build/v6route/03_prune.kicad_pcb), matched by net,
                                                    layer and geometry (0.001 mm)
  kipy block_E_make.py copper BASE ROUTED           copper rows: tracks / vias / "block E" zones of ROUTED that are
                                                    not on BASE (the cleaned board), and a pad row for every pad
                                                    they touch
Rows of the other kind already in the CSV are kept.
"""
import collections
import csv
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_E as BE  # noqa: E402

FIELDS = ["kind", "net", "layer", "x1", "y1", "x2", "y2", "w", "tag"]
CLEAN_KINDS = {"deltrack", "delvia", "cuttrack"}
DEAD_KINDS = {"deadtrack", "deadvia"}


def in_box(p, r, eps=1e-6):
    return r[0] - eps <= p[0] <= r[2] + eps and r[1] - eps <= p[1] <= r[3] + eps


def inE(p):
    return in_box(p, BE.E) and not in_box(p, BE.G, -1e-6)


def clip(a, c, box):
    x0, y0, x1, y1 = box
    t0, t1 = 0.0, 1.0
    dx, dy = c[0] - a[0], c[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return (t0, t1)


def inside_intervals(a, c):
    """parameter intervals of segment a-c inside E minus G"""
    e = clip(a, c, BE.E)
    if not e:
        return []
    g = clip(a, c, BE.G)
    if not g or g[1] <= e[0] or g[0] >= e[1]:
        return [e]
    out = []
    if g[0] > e[0]:
        out.append((e[0], g[0]))
    if g[1] < e[1]:
        out.append((g[1], e[1]))
    return out


def load():
    if not os.path.exists(BE.CSV):
        return []
    with open(BE.CSV) as fh:
        return list(csv.DictReader(fh))


def save(rs):
    with open(BE.CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for r in rs:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def f3(v):
    return f"{v:.6f}"


def make_clean(b3p, bp):
    b3, b = pcbnew.LoadBoard(b3p), pcbnew.LoadBoard(bp)
    have = collections.Counter(BE.item_key(b3, t) for t in b3.GetTracks())
    out, multi = [], []
    for t in b.GetTracks():
        k = BE.item_key(b, t)
        if have[k] > 0:
            have[k] -= 1
            continue
        n = t.GetNetname()
        if t.Type() == pcbnew.PCB_VIA_T:
            p = BE.xy(t.GetPosition())
            if inE(p):
                out.append(dict(kind="delvia", net=n, x1=f3(p[0]), y1=f3(p[1])))
            continue
        a, c = BE.xy(t.GetStart()), BE.xy(t.GetEnd())
        L = b.GetLayerName(t.GetLayer())
        iv = [i for i in inside_intervals(a, c) if i[1] - i[0] > 1e-9]
        if not iv:
            continue
        keep = []
        last = 0.0
        for t0, t1 in iv:
            if t0 > last + 1e-9:
                keep.append((last, t0))
            last = t1
        if last < 1 - 1e-9:
            keep.append((last, 1.0))
        pt = lambda s: (a[0] + s * (c[0] - a[0]), a[1] + s * (c[1] - a[1]))  # noqa: E731
        keep = [(pt(s), pt(e)) for s, e in keep if (e - s) * max(abs(c[0] - a[0]), abs(c[1] - a[1])) > 0.001]
        if not keep:
            out.append(dict(kind="deltrack", net=n, layer=L, x1=f3(a[0]), y1=f3(a[1]), x2=f3(c[0]), y2=f3(c[1])))
        else:
            if len(keep) > 1:   # grazes a corner of E: left whole (it belongs to the blocks outside)
                multi.append((n, L, a, c))
                continue
            s, e = keep[0]
            out.append(dict(kind="cuttrack", net=n, layer=L, x1=f3(s[0]), y1=f3(s[1]), x2=f3(e[0]), y2=f3(e[1]),
                            tag=f"{f3(a[0])} {f3(a[1])} {f3(c[0])} {f3(c[1])}"))
    if multi:
        print("block_E_make: tracks grazing E (left whole):", multi)
    rs = [r for r in load() if r["kind"] not in CLEAN_KINDS] + out
    save(rs)
    c = collections.Counter(r["kind"] for r in out)
    print("block_E_make: clean rows", dict(c))


def make_copper(basep, routedp):
    base, rb = pcbnew.LoadBoard(basep), pcbnew.LoadBoard(routedp)
    have = collections.Counter(BE.item_key(base, t) for t in base.GetTracks())
    out = []
    pts = []
    for t in rb.GetTracks():
        k = BE.item_key(rb, t)
        if have[k] > 0:
            have[k] -= 1
            continue
        n = t.GetNetname()
        if t.Type() == pcbnew.PCB_VIA_T:
            p = BE.xy(t.GetPosition())
            out.append(dict(kind="via", net=n, x1=f3(p[0]), y1=f3(p[1]), x2=f3(BE.T(t.GetDrill())),
                            w=f3(BE.T(t.GetWidth(pcbnew.F_Cu)))))
            pts.append((n, p, None))
        else:
            a, c = BE.xy(t.GetStart()), BE.xy(t.GetEnd())
            L = rb.GetLayerName(t.GetLayer())
            out.append(dict(kind="track", net=n, layer=L, x1=f3(a[0]), y1=f3(a[1]), x2=f3(c[0]), y2=f3(c[1]),
                            w=f3(BE.T(t.GetWidth()))))
            pts += [(n, a, L), (n, c, L)]
    zn = {z.GetZoneName() for z in base.Zones()}
    for z in rb.Zones():
        if z.GetIsRuleArea() or not z.GetZoneName().startswith("block E") or z.GetZoneName() in zn:
            continue
        o = z.Outline().Outline(0)
        poly = ";".join(f"{f3(BE.T(o.CPoint(i).x))} {f3(-BE.T(o.CPoint(i).y))}" for i in range(o.PointCount()))
        out.append(dict(kind="zone", net=z.GetNetname(), layer=rb.GetLayerName(z.GetLayer()), x1=z.GetZoneName(),
                        y1=z.GetAssignedPriority(), x2=f3(BE.T(z.GetLocalClearance() or 0)),
                        y2=f3(BE.T(z.GetMinThickness())), tag=poly))
    # pads touched by the new copper (end point inside the pad)
    pads = {}
    byn = collections.defaultdict(list)
    for n, p, L in pts:
        byn[n].append(p)
    for fp in rb.GetFootprints():
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n not in byn:
                continue
            for p in byn[n]:
                if pad.HitTest(BE.P(*p)):
                    q = BE.xy(pad.GetPosition())
                    pads[(fp.GetReference(), pad.GetNumber())] = dict(kind="pad", net=n, x1=f3(q[0]), y1=f3(q[1]),
                                                                       tag=f"{fp.GetReference()}-{pad.GetNumber()}")
                    break
    # kept copper of BASE that ROUTED no longer has (deleted as dead by block_E_dead.py)
    gone = collections.Counter(BE.item_key(rb, t) for t in rb.GetTracks())
    for t in base.GetTracks():
        k = BE.item_key(base, t)
        if gone[k] > 0:
            gone[k] -= 1
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            p = BE.xy(t.GetPosition())
            out.append(dict(kind="deadvia", net=t.GetNetname(), x1=f3(p[0]), y1=f3(p[1])))
        else:
            a, c = BE.xy(t.GetStart()), BE.xy(t.GetEnd())
            out.append(dict(kind="deadtrack", net=t.GetNetname(), layer=base.GetLayerName(t.GetLayer()),
                            x1=f3(a[0]), y1=f3(a[1]), x2=f3(c[0]), y2=f3(c[1])))
    rs = [r for r in load() if r["kind"] in CLEAN_KINDS or r["kind"] == "move"]
    rs = sorted(pads.values(), key=lambda r: r["tag"]) + rs + out
    save(rs)
    c = collections.Counter(r["kind"] for r in out)
    print("block_E_make: copper rows", dict(c), "pads", len(pads))


if __name__ == "__main__":
    {"clean": make_clean, "copper": make_copper}[sys.argv[1]](*sys.argv[2:4])
