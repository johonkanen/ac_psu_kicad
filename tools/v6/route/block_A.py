#!/usr/bin/env python3
"""Block A (AFE input / filter / AFE sense, V6_PLAN.md section 16) as one replay step: the block's copper from
tools/v6/route/block_A_copper.csv (run under tools/p2k/bin/kipy, fixed seed 6500).

  tools/p2k/bin/kipy tools/v6/route/block_A.py [--board IN] [--out OUT] [--dry]

Default IN = OUT = kicad/ac_psu.kicad_pcb (v6-baseboard d639e0e: blocks E and F replayed). Zones are not filled
here: refill afterwards with `kicad-cli pcb drc --refill-zones --save-board` (memory rule, V6_PLAN 10a).

Block A is the area blocks.block_of() == "A": x -128.3 .. -2, y -83.1 .. -12. At d639e0e eight connections inside A
were open, all at the AFE current sense (R48 / U5 / U29) and the AFE choke landing FILTER_OUT1; the rest of A (EMI
filter, dividers, relay) was joined by kept v4 copper. block_A.md lists what the CSV draws and why.

Rows of the CSV, in order of use:
  pad        tag REF-PAD, net, x1 y1: must exist with that net within 0.01 mm
  needtrack  net, layer, ends / needvia (net, x1 y1) / needzone (tag = zone name): kept copper the new copper
             joins or keeps; must exist
  deadtrack  net, layer, ends: kept copper that is dead or breaks a rule after the re-plan; deleted
  cuttrack   net, layer, new ends x1 y1 x2 y2, tag = the original ends "ax ay bx by": shortened
  track / via (x2 = drill, w = diameter): added, locked
  zone       net, layer, x1 = priority, y1 = clearance, x2 = min width, tag = "name|x y;x y;...": copper zone added
  keepout    layer, tag = "name|x y;...": rule area that keeps zone fills out (the high-voltage pours cut back
             2.5 mm / 1.0 mm from the objects of other nets; tracks and vias are allowed in it)
Any pad that differs or any listed item that is missing -> exit 1, nothing saved. Every new track end / via / zone
corner lies inside A or exactly on an A edge (block_A.md lists the ports); keep-outs may reach 3 mm past A.
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

CSV = os.path.join(HERE, "block_A_copper.csv")
F, T = pcbnew.FromMM, pcbnew.ToMM
SEED = 6500
VIA, DRILL = 0.4572, 0.3
AB = BLOCKS["A"][1]


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
    return f"{r['kind']} {r['net']} {r['layer']} {r['x1']} {r['y1']} {r['x2']} {r['y2']} {r['tag'][:60]}"


def find_items(b):
    """needed / dead / cut items on the board: all or nothing (returns (todo, missing))"""
    index = {}
    for t in b.GetTracks():
        index.setdefault(item_key(b, t), []).append(t)
    todo, missing = [], []
    for r in rows("needtrack") + rows("needvia"):
        if not index.get(row_key(r)):
            missing.append(fmt(r))
    names = {z.GetZoneName() for z in b.Zones()}
    for r in rows("needzone"):
        if r["tag"] not in names:
            missing.append(fmt(r))
    for r in rows("zone") + rows("keepout"):
        if r["tag"].split("|")[0] in names:
            missing.append("already on the board: " + fmt(r))
    for r in rows("deadtrack") + rows("deadvia") + rows("cuttrack"):
        lst = index.get(row_key(r))
        if not lst:
            missing.append(fmt(r))
            continue
        todo.append((r, lst.pop()))
    return todo, missing


def on_edge(p, eps=1e-3):
    x, y = p
    return ((abs(x - AB[0]) < eps or abs(x - AB[2]) < eps) and AB[1] - eps <= y <= AB[3] + eps) or \
           ((abs(y - AB[1]) < eps or abs(y - AB[3]) < eps) and AB[0] - eps <= x <= AB[2] + eps)


def pts_of(r):
    return [tuple(float(v) for v in q.split()) for q in r["tag"].split("|")[1].split(";")]


def fenced(r):
    if r["kind"] in ("zone", "keepout"):
        pts = pts_of(r)
        if r["kind"] == "keepout":
            m = 3.0
            return all(AB[0] - m <= x <= AB[2] + m and AB[1] - m <= y <= AB[3] + m for x, y in pts)
    else:
        pts = [(float(r["x1"]), float(r["y1"]))]
        if r["kind"] == "track":
            pts.append((float(r["x2"]), float(r["y2"])))
    return all(block_of(*p) == "A" or on_edge(p) for p in pts)


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


def chain(pts):
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts:
        ch.Append(F(x), F(-y))
    ch.SetClosed(True)
    return ch


def mkzone(b, r):
    z = pcbnew.ZONE(b)
    z.SetLayer(b.GetLayerID(r["layer"]))
    z.SetNetCode(b.GetNetcodeFromNetname(r["net"]))
    z.Outline().AddOutline(chain(pts_of(r)))
    z.SetZoneName(r["tag"].split("|")[0])
    z.SetAssignedPriority(int(float(r["x1"])))
    z.SetLocalClearance(F(float(r["y1"])))
    z.SetMinThickness(F(float(r["x2"])))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    z.SetLocked(True)
    return z


def mkkeepout(b, r):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetLayer(b.GetLayerID(r["layer"]))
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.Outline().AddOutline(chain(pts_of(r)))
    z.SetZoneName(r["tag"].split("|")[0])
    z.SetLocked(True)
    return z


def replay(b, log):
    pads = rows("pad")
    bad = check_pads(b, pads)
    if bad:
        for m in bad:
            print("block_A: PAD MOVED OR CHANGED:", m, file=sys.stderr)
        sys.exit(f"block_A: {len(bad)} pad(s) differ from the table; nothing saved (redraw block A)")
    log.append(f"{len(pads)} pads checked: all at their positions with their nets")
    for r in rows("track") + rows("via") + rows("zone"):
        if b.FindNet(r["net"]) is None:
            sys.exit(f"block_A: net {r['net']} missing on the board; nothing saved")
    for r in rows("track") + rows("via") + rows("zone") + rows("keepout"):
        if not fenced(r):
            sys.exit(f"block_A: row outside block A: {fmt(r)}; nothing saved")
    todo, missing = find_items(b)
    if missing:
        for m in missing[:20]:
            print("block_A: NOT ON THE BOARD:", m, file=sys.stderr)
        sys.exit(f"block_A: {len(missing)} listed item(s) not found (not the d639e0e board, or A applied already); "
                 "nothing saved")
    log.append(f"{len(rows('needtrack')) + len(rows('needvia')) + len(rows('needzone'))} kept items (tracks, vias, "
               "zones) the new copper joins or keeps: all present")
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
    k = {"track": 0, "via": 0, "zone": 0, "keepout": 0}
    for r in rows():
        maker = {"track": mktrack, "via": mkvia, "zone": mkzone, "keepout": mkkeepout}.get(r["kind"])
        if maker is None:
            continue
        o = maker(b, r)
        b.Add(o)
        if r["kind"] in ("zone", "keepout"):
            o.thisown = False
        k[r["kind"]] += 1
    log.append(f"added {k['track']} tracks, {k['via']} vias (locked), {k['zone']} copper zones, {k['keepout']} fill "
               "keep-outs; no part moves")
    bad = check_pads(b, pads)
    if bad:
        sys.exit("block_A: pads moved during the replay: " + "; ".join(bad) + "; nothing saved")


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
        print("block_A:", line)
    if "--dry" in args:
        print("block_A: --dry, not saved")
        return
    pcbnew.SaveBoard(out, b)
    print("block_A: saved", out)


if __name__ == "__main__":
    main()
