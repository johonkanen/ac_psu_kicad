#!/usr/bin/env python3
"""Put routed copper on a board (run under tools/p2k/bin/kipy).

  tools/p2k/bin/kipy tools/v5/route/apply.py IN.kicad_pcb OUT.kicad_pcb ROUTES.json [ROUTES.json ...]

Each ROUTES.json holds {"tracks": [{net, layer, w, a, b}], "vias": [{net, x, y, d, drill}]} in mm, IPC frame
(written by router.py). Zones are refilled before saving. UUIDs are reproducible (seed 5005).
"""
import json
import sys

import pcbnew

F = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def main():
    pcbnew.KIID.SeedGenerator(5005)
    board = pcbnew.LoadBoard(sys.argv[1])
    nt = nv = 0
    for path in sys.argv[3:]:
        with open(path) as f:
            r = json.load(f)
        for t in r["tracks"]:
            ni = board.FindNet(t["net"])
            if ni is None:
                sys.exit(f"apply: net {t['net']} is not on the board")
            k = pcbnew.PCB_TRACK(board)
            k.SetStart(P(*t["a"]))
            k.SetEnd(P(*t["b"]))
            k.SetWidth(F(t["w"]))
            k.SetLayer(board.GetLayerID(t["layer"]))
            k.SetNet(ni)
            board.Add(k)
            k.thisown = False
            nt += 1
        for v in r["vias"]:
            ni = board.FindNet(v["net"])
            if ni is None:
                sys.exit(f"apply: net {v['net']} is not on the board")
            k = pcbnew.PCB_VIA(board)
            k.SetViaType(pcbnew.VIATYPE_THROUGH)
            k.SetPosition(P(v["x"], v["y"]))
            k.SetWidth(F(v["d"]))
            k.SetDrill(F(v["drill"]))
            k.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            k.SetNet(ni)
            board.Add(k)
            k.thisown = False
            nv += 1
    zones = board.Zones()
    pcbnew.ZONE_FILLER(board).Fill(zones)
    pcbnew.SaveBoard(sys.argv[2], board)
    print(f"apply: {nt} track segments, {nv} vias -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
