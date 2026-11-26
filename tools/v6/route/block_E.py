#!/usr/bin/env python3
"""Block E (control-card area, V6_PLAN.md section 16) as one replay step: clean start, then the block's copper from
tools/v6/route/block_E_copper.csv (run under tools/p2k/bin/kipy, fixed seed 6300).

  tools/p2k/bin/kipy tools/v6/route/block_E.py [--board IN] [--out OUT] [--dry] [--clean-only]

Default IN = OUT = kicad/ac_psu.kicad_pcb (the routing-pass-1 board of v6-baseboard 6226a75). Zones are added
unfilled: fill afterwards with `kicad-cli pcb drc --refill-zones --save-board` (memory rule, V6_PLAN 10a).

Order:
  1. every pad the block's copper connects to (rows "pad": tag REF-PAD, net, x1 y1) is checked: it must exist, carry
     that net and sit within 0.01 mm of its position; any difference -> exit 1, nothing saved
  2. clean start: the copper that routing pass 1 (chain steps 04-98) added inside block E (E minus block G) is
     removed. Rows "deltrack" (net, layer, ends) / "delvia" (net, position) name each item; rows "cuttrack" are
     pass-1 tracks that cross the E edge: the part inside E goes, the part outside (x1 y1 - x2 y2 kept, w = the
     original end inside E "ex ey") stays. A row whose item is not on the board -> exit 1, nothing saved.
     The list was made by block_E_make.py against build/v6route/03_prune.kicad_pcb (chain.sh 00 03 with
     BASE_REV=870c026, the board pass 1 started from): matching by net, layer and geometry (0.001 mm).
  3. part moves (rows "move": ref, x, y, rotation, side), then tracks and vias (locked) and zones

Every copper item of block E lies inside E (x 40 .. 118.7, y -46 .. 46, block G excluded) except the stub ends of the
crossing nets, which end exactly on their window (PORTS below; block_E.md has the list).
"""
import csv
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CSV = os.path.join(HERE, "block_E_copper.csv")
F, T = pcbnew.FromMM, pcbnew.ToMM
SEED = 6300
VIA, DRILL = 0.4572, 0.3
E = (40.0, -46.0, 118.7, 46.0)
G = (67.0, -54.6, 97.5, -4.0)


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def xy(v):
    return T(v.x), -T(v.y)


def rows(kind=None):
    with open(CSV) as fh:
        return [r for r in csv.DictReader(fh) if kind is None or r["kind"] == kind]


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


def clean(b, log):
    """Remove the listed pass-1 items; all or nothing (returns the list of missing rows)."""
    index = {}
    for t in b.GetTracks():
        index.setdefault(item_key(b, t), []).append(t)
    todo, missing = [], []
    for r in rows("deltrack") + rows("cuttrack") + rows("delvia"):
        if r["kind"] == "delvia":
            k = vkey(r["net"], (float(r["x1"]), float(r["y1"])))
        elif r["kind"] == "deltrack":
            k = tkey(r["net"], r["layer"], (float(r["x1"]), float(r["y1"])), (float(r["x2"]), float(r["y2"])))
        else:   # cuttrack: tag = original "ax ay bx by"
            o = [float(v) for v in r["tag"].split()]
            k = tkey(r["net"], r["layer"], (o[0], o[1]), (o[2], o[3]))
        lst = index.get(k)
        if not lst:
            missing.append(f"{r['kind']} {r['net']} {r['layer']} {r['x1']} {r['y1']} {r['x2']} {r['y2']} {r['tag']}")
            continue
        todo.append((r, lst.pop()))
    if missing:
        return missing
    n = {"deltrack": 0, "delvia": 0, "cuttrack": 0}
    for r, t in todo:
        n[r["kind"]] += 1
        if r["kind"] == "cuttrack":
            t.SetStart(P(float(r["x1"]), float(r["y1"])))
            t.SetEnd(P(float(r["x2"]), float(r["y2"])))
        else:
            b.Delete(t)
    log.append(f"clean start: {n['deltrack']} pass-1 tracks and {n['delvia']} vias inside E deleted, "
               f"{n['cuttrack']} tracks crossing the E edge cut back to it")
    return []


def move(b, r):
    fp = b.FindFootprintByReference(r["tag"])
    x, y, rot, side = float(r["x1"]), float(r["y1"]), float(r["x2"]), r["y2"]
    if (side == "B") != fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(P(x, y))


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


def add_zone(b, r):
    """zone rows: layer, net, tag = 'x y;x y;...', x1 = name, y1 = priority, x2 = clearance, y2 = min width"""
    z = pcbnew.ZONE(b)
    z.SetLayer(b.GetLayerID(r["layer"]))
    z.SetNetCode(b.GetNetcodeFromNetname(r["net"]))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for p in r["tag"].split(";"):
        x, y = (float(v) for v in p.split())
        ch.Append(F(x), F(-y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    z.SetZoneName(r["x1"])
    z.SetAssignedPriority(int(r["y1"]))
    z.SetLocalClearance(F(float(r["x2"])))
    z.SetMinThickness(F(float(r["y2"])))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(F(0.5))
    z.SetThermalReliefSpokeWidth(F(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    z.SetLocked(True)
    b.Add(z)


def replay(b, log, clean_only=False):
    pads = rows("pad")
    bad = check_pads(b, pads)
    if bad:
        for m in bad:
            print("block_E: PAD MOVED OR CHANGED:", m, file=sys.stderr)
        sys.exit(f"block_E: {len(bad)} pad(s) differ from the table; nothing saved (redraw block E)")
    log.append(f"{len(pads)} pads checked: all at their positions with their nets")
    for r in rows("track") + rows("via") + rows("zone"):
        if b.FindNet(r["net"]) is None:
            sys.exit(f"block_E: net {r['net']} missing on the board; nothing saved")
    missing = clean(b, log)
    if missing:
        for m in missing[:20]:
            print("block_E: NOT ON THE BOARD:", m, file=sys.stderr)
        sys.exit(f"block_E: {len(missing)} clean-up item(s) not found (not the pass-1 board, or E applied already); "
                 "nothing saved")
    if clean_only:
        return
    for r in rows("move"):
        move(b, r)
        log.append(f"move {r['tag']} -> ({r['x1']}, {r['y1']}) rot {r['x2']} side {r['y2']}")
    n = {"track": 0, "via": 0, "zone": 0}
    for r in rows():
        k = r["kind"]
        if k == "track":
            b.Add(mktrack(b, r))
        elif k == "via":
            b.Add(mkvia(b, r))
        elif k == "zone":
            add_zone(b, r)
        else:
            continue
        n[k] += 1
    log.append(f"added {n['track']} tracks, {n['via']} vias, {n['zone']} zones")
    # the pad check once more after the moves: a pad that moved without a "move" row refuses the save
    bad = check_pads(b, [p for p in pads if p["tag"].rsplit("-", 1)[0] not in {m["tag"] for m in rows("move")}])
    if bad:
        sys.exit("block_E: pads moved during the replay: " + "; ".join(bad) + "; nothing saved")


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
    replay(b, log, clean_only="--clean-only" in args)
    for line in log:
        print("block_E:", line)
    if "--dry" in args:
        print("block_E: --dry, not saved")
        return
    pcbnew.SaveBoard(out, b)
    print("block_E: saved", out)


if __name__ == "__main__":
    main()
