#!/usr/bin/env python3
"""Aux flyback routes as one step (V6_PLAN.md section 10): replays the copper of tools/v6/aux_routes_copper.csv onto
the current board (run under tools/p2k/bin/kipy, fixed seed 6100).

  tools/p2k/bin/kipy tools/v6/aux_routes.py [--board IN] [--out OUT] [--dry]

Default IN = OUT = kicad/ac_psu.kicad_pcb. Zones are added unfilled: fill afterwards (memory rule, V6_PLAN 10a).

Order:
  1. every pad the routes connect to (CSV rows "pad": ref, pad, net, x, y) is checked: it must exist, carry that net
     and sit within 0.01 mm of the position; any difference -> exit 1, nothing saved
  2. foreign remnants inside the areas PX / IA are removed (rows "foreign": net, layer or empty for all layers):
     tracks of those nets wholly inside an area are deleted, tracks that cross an area edge are cut at the edge,
     vias inside are deleted (dangling runs to the v5 gate-card headers; listed in reports/v6/aux_routes.md)
  3. clearance of the v5 aux In2 GND pour 1.0 -> 0.5 mm (row "zoneclr", old value checked), part moves (rows
     "move"), then tracks, vias (locked) and zones

The boundary list (where the nets that leave the areas cross the area edge; the main chain treats these as fixed
entry points) is the BOUNDARY table below and in reports/v6/aux_routes.md.
"""
import csv
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CSV = os.path.join(HERE, "aux_routes_copper.csv")
F, T = pcbnew.FromMM, pcbnew.ToMM
AREAS = {"PX": (67.0, -54.6, 82.9, -4.0), "IA": (88.0, -48.0, 97.5, -25.5)}
VIA, DRILL = 0.4572, 0.3

# net, area, crossing point (IPC mm), layer, what continues outside (filled in by the helper; see the report)
BOUNDARY = [
    ("15V", "PX", (82.45, -54.6), "F.Cu", "0.4 mm track ends on the south edge: on to J23-6 / U9-1 (old 15V run at (89.73, -53.8))"),
    ("15V", "PX", (67.0, -19.8), "B.Cu", "0.5 mm track ends on the west edge: on to J21-6 / J22-6"),
    ("GND", "PX", (69.0, -12.4), "In4.Cu", "zone 'v6 aux P In4.Cu GND north' overlaps the card-P In4 GND plane on x 69.0..69.65, y -20.66..-4.2"),
    ("DC+", "PX", (68.85, -32.5), "F.Cu", "no crossing: the chain feed, C68-2 and the R98-1 via end in the F.Cu DC+ pour inside PX"),
    ("15V_ISO", "IA", (90.95, -25.5), "B.Cu", "0.8 mm track ends on the north edge: on to U8-1 / the 15V_ISO pours (y -15.6)"),
    ("ISOGND", "IA", (96.9, -25.5), "B.Cu", "0.6 mm track ends on the north edge: 0.9 mm below the ISOGND B.Cu pour 15 (y -24.58)"),
]


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
        pads_ = [p for p in fp.Pads() if p.GetNumber() == num]
        if not pads_:
            bad.append(f"{ref}-{num}: pad missing")
            continue
        want = (float(r["x1"]), float(r["y1"]))
        ok = False
        for p in pads_:
            x, y = xy(p.GetPosition())
            if p.GetNetname() == r["net"] and math.hypot(x - want[0], y - want[1]) <= 0.01:
                ok = True
        if not ok:
            p = pads_[0]
            x, y = xy(p.GetPosition())
            bad.append(f"{ref}-{num}: expected [{r['net']}] at ({want[0]:.3f}, {want[1]:.3f}), found [{p.GetNetname()}] at ({x:.3f}, {y:.3f})")
    return bad


def _inside_t(a, c, box):
    """Liang-Barsky: parameter range [t0, t1] of segment a-c inside box, or None."""
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
    return t0, t1


def clip_foreign(b, nets):
    """Remove the parts of foreign tracks / vias that lie inside the areas. nets: [(net, layer name or None)]."""
    log = []
    want = {}
    for n, l in nets:
        want.setdefault(n, set()).add(l)
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if n not in want:
            continue
        lname = None if t.Type() == pcbnew.PCB_VIA_T else b.GetLayerName(t.GetLayer())
        if None not in want[n] and lname not in want[n]:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = xy(t.GetPosition())
            if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in AREAS.values()):
                log.append(f"via [{n}] ({x:.3f}, {y:.3f}) deleted")
                b.Delete(t)
            continue
        a, c = xy(t.GetStart()), xy(t.GetEnd())
        for box in AREAS.values():
            r = _inside_t(a, c, box)
            if r is None or r[1] - r[0] < 1e-9:
                continue
            t0, t1 = r
            pa = (a[0] + t0 * (c[0] - a[0]), a[1] + t0 * (c[1] - a[1]))
            pc = (a[0] + t1 * (c[0] - a[0]), a[1] + t1 * (c[1] - a[1]))
            keep = []
            if t0 > 1e-9:
                keep.append((a, pa))
            if t1 < 1 - 1e-9:
                keep.append((pc, c))
            desc = f"track {lname} [{n}] ({a[0]:.3f}, {a[1]:.3f})-({c[0]:.3f}, {c[1]:.3f})"
            if not keep:
                log.append(desc + " deleted")
                b.Delete(t)
            else:
                t.SetStart(P(*keep[0][0]))
                t.SetEnd(P(*keep[0][1]))
                for s, e in keep[1:]:
                    t2 = pcbnew.PCB_TRACK(b)
                    t2.SetStart(P(*s))
                    t2.SetEnd(P(*e))
                    t2.SetWidth(t.GetWidth())
                    t2.SetLayer(t.GetLayer())
                    t2.SetNet(t.GetNet())
                    b.Add(t2)
                log.append(desc + " cut at the area edge: kept " + ", ".join(f"({s[0]:.3f}, {s[1]:.3f})-({e[0]:.3f}, {e[1]:.3f})" for s, e in keep))
            break
    return log


def add_zone(b, r):
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
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if r["w"] == "full" else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(F(0.5))
    z.SetThermalReliefSpokeWidth(F(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    z.SetLocked(True)
    b.Add(z)
    return z


def zone_clearance(b, r):
    """Clearance of an aux-area pour (rows "zoneclr": name, old, new); the zone must exist with the old value."""
    zs = [z for z in b.Zones() if z.GetZoneName() == r["x1"]]
    if len(zs) != 1 or abs(T(zs[0].GetLocalClearance() or 0) - float(r["y1"])) > 1e-3:
        sys.exit(f"aux_routes: zone {r['x1']!r} with clearance {r['y1']} mm not found (found {len(zs)}); nothing done")
    zs[0].SetLocalClearance(F(float(r["x2"])))


def move(b, r):
    fp = b.FindFootprintByReference(r["tag"])
    x, y, rot = float(r["x1"]), float(r["y1"]), float(r["x2"])
    side = r["y2"]
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
    v.SetWidth(pcbnew.F_Cu, F(VIA))
    v.SetDrill(F(DRILL))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(b.GetNetcodeFromNetname(r["net"]))
    v.SetLocked(True)
    return v


def replay(b, log):
    pads = rows("pad")
    bad = check_pads(b, pads)
    if bad:
        for m in bad:
            print("aux_routes: PAD MOVED OR CHANGED:", m, file=sys.stderr)
        sys.exit(f"aux_routes: {len(bad)} pad(s) differ from the table; nothing done (ask the aux helper to redraw)")
    log.append(f"{len(pads)} pads checked: all at their positions with their nets")
    for r in rows("track") + rows("via") + rows("zone"):
        if b.FindNet(r["net"]) is None:
            sys.exit(f"aux_routes: net {r['net']} missing on the board")
    # already applied?
    names = {z.GetZoneName() for z in b.Zones()}
    if any(r["x1"] in names for r in rows("zone")):
        sys.exit("aux_routes: an aux zone is already on the board (step applied?)")
    fr = [(r["net"], r["layer"] or None) for r in rows("foreign")]
    for line in clip_foreign(b, fr):
        log.append("foreign: " + line)
    for r in rows("zoneclr"):
        zone_clearance(b, r)
        log.append(f"zone {r['x1']!r}: clearance {r['y1']} -> {r['x2']} mm")
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
            log.append(f"zone {r['x1']} [{r['net']}] {r['layer']} prio {r['y1']} clearance {r['x2']}")
        else:
            continue
        n[k] += 1
    log.append(f"added {n['track']} tracks, {n['via']} vias, {n['zone']} zones")


def main():
    args = sys.argv[1:]
    board = os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
    out = None
    if "--board" in args:
        board = args[args.index("--board") + 1]
    if "--out" in args:
        out = args[args.index("--out") + 1]
    out = out or board
    pcbnew.KIID.SeedGenerator(6100)
    b = pcbnew.LoadBoard(board)
    log = []
    replay(b, log)
    for line in log:
        print("aux_routes:", line)
    if "--dry" in args:
        print("aux_routes: --dry, not saved")
        return
    pcbnew.SaveBoard(out, b)
    print("aux_routes: saved", out)


if __name__ == "__main__":
    main()
