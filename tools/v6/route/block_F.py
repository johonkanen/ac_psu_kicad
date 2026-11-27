#!/usr/bin/env python3
"""Block F (bulk caps / dividers, V6_PLAN.md section 16) as one replay step: the block's copper from
tools/v6/route/block_F_copper.csv (run under tools/p2k/bin/kipy, fixed seed 6400).

  tools/p2k/bin/kipy tools/v6/route/block_F.py [--board IN] [--out OUT] [--dry]

Default IN = OUT = kicad/ac_psu.kicad_pcb (v6-baseboard 3227a58: block E replayed). Zones are not touched: refill
afterwards with `kicad-cli pcb drc --refill-zones --save-board` (memory rule, V6_PLAN 10a).

Block F is the area blocks.block_of() == "F": the rectangle x -38 .. 40, y -46 .. 46 minus block A in its south-west
corner (x < -2, y < -12) and block D2 along its north edge (y > 38). At 3227a58 every pad-to-pad connection inside F
is already made by kept v4 copper (the divider chains R65 .. R70, R80 .. R85, the bulk-cap pads in their pours);
pass 1 added only a 15V B.Cu trunk of block C that grazes F's south-east corner and the U7B-+ via / In1 run to D2,
both kept (block_F.md). What F adds is the crossing nets: the AFE sigma-delta pair MDATA / ADCLK from E's west ports
to A, the divider taps U2+- / U7B-- and the ISO supplies ISOGND / 15V_ISO to D2, and the GND of C148.

Rows of the CSV, in order of use:
  pad        tag REF-PAD, net, x1 y1: must exist with that net within 0.01 mm
  needtrack  net, layer, ends (x1 y1 x2 y2) / needvia (net, x1 y1): kept copper the new copper joins; must exist
  deadtrack  net, layer, ends / deadvia (net, x1 y1): kept v4 copper that ends at no pad after the re-plan; deleted
  cuttrack   net, layer, new ends x1 y1 x2 y2, tag = the original ends "ax ay bx by": shortened
  track / via (x2 = drill, w = diameter): added, locked
Any pad that differs or any listed item that is missing -> exit 1, nothing saved. After the replay every new track
end / via lies inside F or exactly on an F edge (block_F.md lists the ports).
"""
import csv
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
from blocks import BLOCKS, block_of  # noqa: E402

CSV = os.path.join(HERE, "block_F_copper.csv")
F, T = pcbnew.FromMM, pcbnew.ToMM
SEED = 6400
VIA, DRILL = 0.4572, 0.3
FB = BLOCKS["F"][1]


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def xy(v):
    return T(v.x), -T(v.y)


_ROWS = []


def rows(kind=None):
    if not _ROWS:
        with open(CSV) as fh:
            _ROWS.extend(csv.DictReader(fh))
    return [r for r in _ROWS if kind is None or r["kind"] == kind]


def check_pads(b, pads):
    bad = []
    for r in pads:
        ref, num = r["tag"].rsplit("-", 1)
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            bad.append(f"{ref}: footprint missing")
            continue
        cand = [p for p in fp.Pads() if p.GetNumber() == num]
        if not cand:
            bad.append(f"{ref}-{num}: pad missing")
            continue
        want = (float(r["x1"]), float(r["y1"]))
        if not any(p.GetNetname() == r["net"] and math.dist(xy(p.GetPosition()), want) <= 0.01 for p in cand):
            x, y = xy(cand[0].GetPosition())
            bad.append(f"{ref}-{num}: expected [{r['net']}] at ({want[0]:.3f}, {want[1]:.3f}), "
                       f"found [{cand[0].GetNetname()}] at ({x:.3f}, {y:.3f})")
    return bad


def r3(v):
    return round(v + 0.0, 3)


def tkey(net, layer, a, c):
    a, c = (r3(a[0]), r3(a[1])), (r3(c[0]), r3(c[1]))
    return ("t", net, layer) + tuple(sorted([a, c]))


def vkey(net, p):
    return ("v", net, r3(p[0]), r3(p[1]))


def item_key(b, t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return vkey(t.GetNetname(), xy(t.GetPosition()))
    return tkey(t.GetNetname(), b.GetLayerName(t.GetLayer()), xy(t.GetStart()), xy(t.GetEnd()))


def row_key(r):
    if r["kind"] in ("needvia", "deadvia", "via"):
        return vkey(r["net"], (float(r["x1"]), float(r["y1"])))
    if r["kind"] == "cuttrack":
        o = [float(v) for v in r["tag"].split()]
        return tkey(r["net"], r["layer"], (o[0], o[1]), (o[2], o[3]))
    return tkey(r["net"], r["layer"], (float(r["x1"]), float(r["y1"])), (float(r["x2"]), float(r["y2"])))


def fmt(r):
    return f"{r['kind']} {r['net']} {r['layer']} {r['x1']} {r['y1']} {r['x2']} {r['y2']} {r['tag']}"


def find_items(b):
    """needed / dead / cut items on the board: all or nothing (returns (todo, missing))"""
    index = {}
    for t in b.GetTracks():
        index.setdefault(item_key(b, t), []).append(t)
    todo, missing = [], []
    for r in rows("needtrack") + rows("needvia"):
        if not index.get(row_key(r)):
            missing.append(fmt(r))
    for r in rows("deadtrack") + rows("deadvia") + rows("cuttrack"):
        lst = index.get(row_key(r))
        if not lst:
            missing.append(fmt(r))
            continue
        todo.append((r, lst.pop()))
    return todo, missing


def on_edge(p, eps=1e-3):
    x, y = p
    return (abs(x - FB[0]) < eps or abs(x - FB[2]) < eps or abs(y - FB[1]) < eps or abs(y - FB[3]) < eps
            or (abs(x + 2.0) < eps and y <= -12.0 + eps) or (abs(y + 12.0) < eps and x <= -2.0 + eps)
            or (abs(y - 38.0) < eps))


def fenced(r):
    pts = [(float(r["x1"]), float(r["y1"]))]
    if r["kind"] == "track":
        pts.append((float(r["x2"]), float(r["y2"])))
    return all(block_of(*p) == "F" or on_edge(p) for p in pts)


def mktrack(b, r):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(P(float(r["x1"]), float(r["y1"])))
    t.SetEnd(P(float(r["x2"]), float(r["y2"])))
    t.SetWidth(F(float(r["w"])))
    t.SetLayer(b.GetLayerID(r["layer"]))
    t.SetNetCode(b.GetNetcodeFromNetname(r["net"]))
    t.SetLocked(True)
    return t


def mkvia(b, r):
    v = pcbnew.PCB_VIA(b)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(P(float(r["x1"]), float(r["y1"])))
    v.SetWidth(pcbnew.F_Cu, F(float(r["w"] or VIA)))
    v.SetDrill(F(float(r["x2"] or DRILL)))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(b.GetNetcodeFromNetname(r["net"]))
    v.SetLocked(True)
    return v


def replay(b, log):
    pads = rows("pad")
    bad = check_pads(b, pads)
    if bad:
        for m in bad:
            print("block_F: PAD MOVED OR CHANGED:", m, file=sys.stderr)
        sys.exit(f"block_F: {len(bad)} pad(s) differ from the table; nothing saved (redraw block F)")
    log.append(f"{len(pads)} pads checked: all at their positions with their nets")
    for r in rows("track") + rows("via"):
        if b.FindNet(r["net"]) is None:
            sys.exit(f"block_F: net {r['net']} missing on the board; nothing saved")
        if not fenced(r):
            sys.exit(f"block_F: row outside block F: {fmt(r)}; nothing saved")
    todo, missing = find_items(b)
    if missing:
        for m in missing[:20]:
            print("block_F: NOT ON THE BOARD:", m, file=sys.stderr)
        sys.exit(f"block_F: {len(missing)} listed item(s) not found (not the 3227a58 board, or F applied already); "
                 "nothing saved")
    log.append(f"{len(rows('needtrack')) + len(rows('needvia'))} kept items the new copper joins: all present")
    n = {"deadtrack": 0, "deadvia": 0, "cuttrack": 0}
    for r, t in todo:
        n[r["kind"]] += 1
        if r["kind"] == "cuttrack":
            t.SetStart(P(float(r["x1"]), float(r["y1"])))
            t.SetEnd(P(float(r["x2"]), float(r["y2"])))
        else:
            b.Delete(t)
    log.append(f"dead kept copper deleted: {n['deadtrack']} tracks, {n['deadvia']} vias; {n['cuttrack']} tracks "
               "shortened")
    k = {"track": 0, "via": 0}
    for r in rows():
        if r["kind"] == "track":
            b.Add(mktrack(b, r))
        elif r["kind"] == "via":
            b.Add(mkvia(b, r))
        else:
            continue
        k[r["kind"]] += 1
    log.append(f"added {k['track']} tracks, {k['via']} vias (locked); no zones, no part moves")
    bad = check_pads(b, pads)
    if bad:
        sys.exit("block_F: pads moved during the replay: " + "; ".join(bad) + "; nothing saved")


def main():
    args = sys.argv[1:]
    board = os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
    out = None
    if "--board" in args:
        board = args[args.index("--board") + 1]
    if "--out" in args:
        out = args[args.index("--out") + 1]
    out = out or board
    pcbnew.KIID.SeedGenerator(SEED)
    b = pcbnew.LoadBoard(board)
    log = []
    replay(b, log)
    for line in log:
        print("block_F:", line)
    if "--dry" in args:
        print("block_F: --dry, not saved")
        return
    pcbnew.SaveBoard(out, b)
    print("block_F: saved", out)


if __name__ == "__main__":
    main()
