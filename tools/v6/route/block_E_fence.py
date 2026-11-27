#!/usr/bin/env python3
"""Fences and port pads of the block-E router steps (kipy; IPC frame, y up). Development tool of block_E_chain.sh.

  kipy block_E_fence.py prep IN OUT DOMAIN NETS     temporary keep-outs: outside E (and block G), the other domains
                                                    (fence.DOMAIN_FENCES), no tracks on the card planes, no vias in
                                                    foreign pours; one temporary port pad (footprint "TPE...") per
                                                    crossing net of NETS, PORT_IN mm inside its window point
  kipy block_E_fence.py finish CUR IN OUT DST       CUR + the router's new copper (OUT minus IN) -> DST; a new track
                                                    that ends on a port pad gets the straight piece to the window point
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
    loc = localize(b, set(nets))
    k = 0
    for net in nets:
        if net in PORTS:
            add_port(b, net)
            k += 1
    b.Save(dst)
    print(f"prep {dom}: {n} pour via keep-outs, {k} port pads; localized: {loc}")


def inE(x, y):
    return E[0] <= x <= E[2] and E[1] <= y <= E[3] and not (G[0] < x < G[2] and G[1] < y < G[3])


def localize(b, nets):
    """The step's nets end at the block: on the router's input copy their pads outside E lose the net and their
    copper wholly outside E goes (zones too), so the router neither tries the far pads nor routes to far islands.
    finish() copies only the new copper back onto the real board."""
    np = nt = nz = 0
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() in nets and not inE(*xy(p.GetPosition())):
                p.SetNetCode(0)
                np += 1
    for t in list(b.GetTracks()):
        if t.GetNetname() not in nets:
            continue
        pts = [xy(t.GetPosition())] if t.Type() == pcbnew.PCB_VIA_T else [xy(t.GetStart()), xy(t.GetEnd())]
        if not any(inE(*q) for q in pts):
            b.Delete(t)
            nt += 1
    for z in list(b.Zones()):
        if z.GetIsRuleArea() or z.GetNetname() not in nets:
            continue
        bb = z.GetBoundingBox()
        x0, x1, y0, y1 = T(bb.GetX()), T(bb.GetRight()), -T(bb.GetBottom()), -T(bb.GetY())
        if x1 < E[0] or x0 > E[2] or y1 < E[1] or y0 > E[3] or (G[0] <= x0 and x1 <= G[2] and G[1] <= y0 and y1 <= G[3]):
            b.Delete(z)
            nz += 1
    return f"{np} pads, {nt} tracks / vias, {nz} zones"


def xy(v):
    return T(v.x), -T(v.y)


def item_key(b, t):
    import block_E as BE
    return BE.item_key(b, t)


def finish(cur, inp, outp, dst):
    """cur + (copper of outp not in inp) -> dst; a new track ending on a port pad gets the piece to the edge."""
    import collections
    b, bi, bo = pcbnew.LoadBoard(cur), pcbnew.LoadBoard(inp), pcbnew.LoadBoard(outp)
    have = collections.Counter(item_key(bi, t) for t in bi.GetTracks())
    new = []
    for t in bo.GetTracks():
        k = item_key(bo, t)
        if have[k] > 0:
            have[k] -= 1
            continue
        new.append(t)
    for t in new:
        if t.Type() == pcbnew.PCB_VIA_T:
            v = pcbnew.PCB_VIA(b)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetPosition(t.GetPosition())
            v.SetWidth(pcbnew.F_Cu, t.GetWidth(pcbnew.F_Cu))
            v.SetDrill(t.GetDrill())
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNetCode(b.GetNetcodeFromNetname(t.GetNetname()))
            b.Add(v)
        else:
            c = pcbnew.PCB_TRACK(b)
            c.SetStart(t.GetStart())
            c.SetEnd(t.GetEnd())
            c.SetWidth(t.GetWidth())
            c.SetLayer(t.GetLayer())
            c.SetNetCode(b.GetNetcodeFromNetname(t.GetNetname()))
            b.Add(c)
    ports = {}
    for f in bo.GetFootprints():
        if f.GetReference().startswith("TPE"):
            for p in f.Pads():
                ports[p.GetNetname()] = p
    reached = []
    allt = list(bo.GetTracks())
    edge_have = {(t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) for t in b.GetTracks()
                 if t.Type() != pcbnew.PCB_VIA_T}
    for net, p in ports.items():
        q = p.GetPosition()
        L = p.GetLayerSet().Seq()[0]
        near = lambda v: math.hypot(T(v.x - q.x), T(v.y - q.y)) <= 0.2  # noqa: E731 (track end on the pad)
        hit = [t for t in allt if t.GetNetname() == net and t.Type() != pcbnew.PCB_VIA_T
               and t.GetLayer() == L and (near(t.GetStart()) or near(t.GetEnd()))]
        hitv = [t for t in allt if t.GetNetname() == net and t.Type() == pcbnew.PCB_VIA_T and near(t.GetPosition())]
        e = P(*PORTS[net]["at"])
        if (net, q.x, q.y, e.x, e.y) in edge_have:      # the piece to the edge is there already (an earlier step)
            reached.append(net)
            continue
        if hit or hitv:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(q)
            t.SetEnd(P(*PORTS[net]["at"]))
            t.SetWidth(hit[0].GetWidth() if hit else F(0.2))
            t.SetLayer(L)
            t.SetNetCode(b.GetNetcodeFromNetname(net))
            b.Add(t)
            reached.append(net)
    b.Save(dst)
    missing = sorted(set(ports) - set(reached))
    print(f"finish: {len(new)} new items, {len(reached)} ports reached" + (f"; not reached: {', '.join(missing)}" if missing else ""))


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
        finish(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        domains_json(sys.argv[2])
