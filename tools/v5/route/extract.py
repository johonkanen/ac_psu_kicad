#!/usr/bin/env python3
"""Board geometry for the card-area router (run under tools/p2k/bin/kipy).

  tools/p2k/bin/kipy tools/v5/route/extract.py BOARD OUT.json

Fills the zones and writes everything the router needs as JSON, mm in the IPC frame (Y up):
pads (polygon per copper layer, hole), tracks, vias, zone fills, rule areas, Edge.Cuts, and the
insulation domain of every net (tools/v4/domains.py).
"""
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [TOOLS, os.path.join(TOOLS, "v4"), os.path.join(TOOLS, "p2k")]
import board_common as bc  # noqa: E402
import domains  # noqa: E402

T, F = pcbnew.ToMM, pcbnew.FromMM
WIN = (-25.0, -45.0, 123.0, 62.0)
CU = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
ERR = F(0.002)


def polys(ps):
    """SHAPE_POLY_SET -> [[outline, hole, ...], ...], each a list of [x, y]."""
    out = []
    for i in range(ps.OutlineCount()):
        rings = []
        o = ps.Outline(i)
        rings.append([[round(T(o.CPoint(k).x), 4), round(-T(o.CPoint(k).y), 4)] for k in range(o.PointCount())])
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            rings.append([[round(T(hh.CPoint(k).x), 4), round(-T(hh.CPoint(k).y), 4)] for k in range(hh.PointCount())])
        out.append(rings)
    return out


def inwin(bb):
    return not (T(bb.GetRight()) < WIN[0] or T(bb.GetLeft()) > WIN[2] or -T(bb.GetTop()) < WIN[1] or -T(bb.GetBottom()) > WIN[3])


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    zones = board.Zones()
    pcbnew.ZONE_FILLER(board).Fill(zones)
    lid = {n: board.GetLayerID(n) for n in CU}
    _, nets = bc.export_netlist()
    dom = domains.classify(nets)
    out = {"win": WIN, "pads": [], "tracks": [], "vias": [], "zones": [], "rules": [], "edge": [], "dom": dom,
           "netpads": {n: [f"{r}-{p}" for r, p in nodes] for n, nodes in nets.items()}}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not inwin(pad.GetBoundingBox()):
                continue
            ly = {}
            for n in CU:
                if pad.IsOnLayer(lid[n]):
                    ps = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(ps, lid[n], 0, ERR, pcbnew.ERROR_OUTSIDE)
                    ly[n] = polys(ps)
            d = pad.GetDrillSize()
            out["pads"].append({"ref": fp.GetReference(), "num": pad.GetNumber(), "net": pad.GetNetname(),
                                "x": round(T(pad.GetPosition().x), 4), "y": round(-T(pad.GetPosition().y), 4),
                                "layers": ly, "drill": [T(d.x), T(d.y)], "side": "B" if fp.IsFlipped() else "F",
                                "bb": [T(pad.GetBoundingBox().GetLeft()), -T(pad.GetBoundingBox().GetBottom()),
                                       T(pad.GetBoundingBox().GetRight()), -T(pad.GetBoundingBox().GetTop())]})
    for t in board.GetTracks():
        if not inwin(t.GetBoundingBox()):
            continue
        if t.GetClass() == "PCB_VIA":
            out["vias"].append({"net": t.GetNetname(), "x": round(T(t.GetPosition().x), 4), "y": round(-T(t.GetPosition().y), 4),
                                "d": T(t.GetWidth(pcbnew.F_Cu)), "drill": T(t.GetDrill()), "id": t.m_Uuid.AsString()})
        else:
            if t.GetClass() == "PCB_ARC":
                print("extract: arc track taken as a segment", file=sys.stderr)
            out["tracks"].append({"net": t.GetNetname(), "layer": board.GetLayerName(t.GetLayer()), "w": T(t.GetWidth()),
                                  "a": [round(T(t.GetStart().x), 4), round(-T(t.GetStart().y), 4)],
                                  "b": [round(T(t.GetEnd().x), 4), round(-T(t.GetEnd().y), 4)], "id": t.m_Uuid.AsString()})
    for z in zones:
        if not inwin(z.GetBoundingBox()):
            continue
        names = [board.GetLayerName(l) for l in z.GetLayerSet().CuStack()]
        if z.GetIsRuleArea():
            out["rules"].append({"name": z.GetZoneName(), "layers": names, "poly": polys(z.Outline()),
                                 "no_tracks": z.GetDoNotAllowTracks(), "no_vias": z.GetDoNotAllowVias(),
                                 "no_fill": z.GetDoNotAllowZoneFills()})
            continue
        for n in names:
            fill = z.GetFilledPolysList(lid[n])
            lc = z.GetLocalClearance()
            out["zones"].append({"name": z.GetZoneName(), "net": z.GetNetname(), "layer": n, "prio": z.GetAssignedPriority(),
                                 "clr": T(lc) if isinstance(lc, int) else 0.0,
                                 "outline": polys(z.Outline()), "fill": polys(fill)})
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and inwin(d.GetBoundingBox()):
            ps = pcbnew.SHAPE_POLY_SET()
            d.TransformShapeToPolygon(ps, pcbnew.Edge_Cuts, F(0.01), ERR, pcbnew.ERROR_OUTSIDE)
            out["edge"].append(polys(ps))
    for fp in board.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.Edge_Cuts and inwin(g.GetBoundingBox()):
                ps = pcbnew.SHAPE_POLY_SET()
                g.TransformShapeToPolygon(ps, pcbnew.Edge_Cuts, F(0.01), ERR, pcbnew.ERROR_OUTSIDE)
                out["edge"].append(polys(ps))
    with open(sys.argv[2], "w") as f:
        json.dump(out, f)
    print(f"extract: {len(out['pads'])} pads, {len(out['tracks'])} tracks, {len(out['vias'])} vias, {len(out['zones'])} zone layers, "
          f"{len(out['rules'])} rule areas, {len(out['edge'])} edge items -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
