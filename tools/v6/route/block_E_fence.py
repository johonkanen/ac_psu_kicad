#!/usr/bin/env python3
"""Fences and port pads of the block-E router steps (kipy; IPC frame, y up). Development tool of block_E_chain.sh.

  kipy block_E_fence.py prep IN OUT DOMAIN NETS     temporary keep-outs: outside E (and block G), the other domains
                                                    (fence.DOMAIN_FENCES), no tracks on the card planes, no vias in
                                                    foreign pours; one temporary port pad (footprint "TPE...") per
                                                    crossing net of NETS, PORT_IN mm inside its window point
  kipy block_E_fence.py finish IN OUT               removes the keep-outs and port pads; a routed track that ends on
                                                    a port pad gets the straight piece to the window point
  kipy block_E_fence.py domains OUT.json            net -> domain (tools/v4/domains.py), for the chain
"""
import json
import math
import os
import sys

import pcbnew

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import fence  # noqa: E402
from block_E_ports import PORTS, PORT_IN  # noqa: E402

F, T = pcbnew.FromMM, pcbnew.ToMM
AL = fence.AL
E = (40.0, -46.0, 118.7, 46.0)
G = (67.0, -54.6, 97.5, -4.0)
OUT = [(-140, -100, E[0], 100), (E[2], -100, 140, 100), (E[0], -100, E[2], E[1]), (E[0], E[3], E[2], 100), G]


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def port_inner(net):
    x, y = PORTS[net]["at"]
    side = PORTS[net]["edge"]
    if side == "N":
        return x, y - PORT_IN
    if side == "S":
        return x, y + PORT_IN
    if side == "W":
        return x + PORT_IN, y
    return x - PORT_IN, y


def add_port(b, net):
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference("TPE" + str(len([f for f in b.GetFootprints() if f.GetReference().startswith("TPE")]) + 1))
    fp.SetValue("block E port " + net)
    layer = b.GetLayerID(PORTS[net]["layer"])
    x, y = port_inner(net)
    fp.SetPosition(P(x, y))
    b.Add(fp)
    pad = pcbnew.PAD(fp)
    pad.SetNumber("1")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(F(0.3), F(0.3)))
    ls = pcbnew.LSET()
    ls.AddLayer(layer)
    pad.SetLayerSet(ls)
    pad.SetPosition(P(x, y))
    pad.SetNet(b.FindNet(net))
    fp.Add(pad)


def prep(src, dst, dom, nets):
    b = pcbnew.LoadBoard(src)
    fence.clear(b)
    for f in [f for f in b.GetFootprints() if f.GetReference().startswith("TPE")]:
        b.Delete(f)
    for i, r in enumerate(OUT):
        fence.keepout(b, f"block E out {i}", r, AL)
    for i, r in enumerate(fence.DOMAIN_FENCES[dom]):
        fence.keepout(b, f"domain {dom} {i}", r, AL)
    for i, r in enumerate(fence.PLANES):
        fence.keepout(b, f"planes {i}", r, ["In1.Cu", "In2.Cu", "In4.Cu"], vias=False)
    n = fence.pour_vias(b, set(nets))
    k = 0
    for net in nets:
        if net in PORTS:
            add_port(b, net)
            k += 1
    b.Save(dst)
    print(f"prep {dom}: {n} pour via keep-outs, {k} port pads")


def finish(src, dst):
    b = pcbnew.LoadBoard(src)
    fence.clear(b)
    ports = {}
    for f in [f for f in b.GetFootprints() if f.GetReference().startswith("TPE")]:
        for p in f.Pads():
            ports[p.GetNetname()] = p
    reached = []
    for net, p in ports.items():
        q = p.GetPosition()
        L = p.GetLayer() if p.GetLayerSet().Seq().size() == 1 else None
        L = p.GetLayerSet().Seq()[0]
        hit = [t for t in b.GetTracks() if t.GetNetname() == net and t.Type() != pcbnew.PCB_VIA_T
               and t.GetLayer() == L and (t.GetStart() == q or t.GetEnd() == q)]
        hitv = [t for t in b.GetTracks() if t.GetNetname() == net and t.Type() == pcbnew.PCB_VIA_T and t.GetPosition() == q]
        if hit or hitv:
            w = hit[0].GetWidth() if hit else F(0.2)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(q)
            t.SetEnd(P(*PORTS[net]["at"]))
            t.SetWidth(w)
            t.SetLayer(L)
            t.SetNet(p.GetNet())
            b.Add(t)
            reached.append(net)
    for f in [f for f in b.GetFootprints() if f.GetReference().startswith("TPE")]:
        b.Delete(f)
    b.Save(dst)
    missing = sorted(set(ports) - set(reached))
    print(f"finish: {len(reached)} ports reached" + (f"; not reached: {', '.join(missing)}" if missing else ""))


def domains_json(out):
    sys.path[:0] = [os.path.join(H, "..", ".."), os.path.join(H, "..", "..", "v4")]
    import board_common as bc
    import domains
    _, nl = bc.export_netlist()
    json.dump(domains.classify(nl), open(out, "w"), indent=0, sort_keys=True)


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "prep":
        prep(sys.argv[2], sys.argv[3], sys.argv[4], [n for n in sys.argv[5].split(",") if n])
    elif m == "finish":
        finish(sys.argv[2], sys.argv[3])
    else:
        domains_json(sys.argv[2])
