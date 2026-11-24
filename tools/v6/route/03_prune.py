#!/usr/bin/env python3
"""Routing chain step 03 (kipy): prune dangling copper before routing.

Copper that ends nowhere after the v6 deletions (strips cleared, sense groups moved, tracks cut at the aux area edges
by step 01 and near the card DC pads by step 4b) is pulled back to its last pad, via junction or same-net pour: a
track end (or via) that touches nothing else of its net is deleted, repeatedly, but only where the free end lies in
a v6 area (lib/v6_copper.csv unrouted / area rows on all layers, the aux areas PX / IA). Dangling ends elsewhere (v5
pending layout) are left alone. Zones must be filled (the chain refills with kicad-cli before this step).
"""
import csv
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BOARD = os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
T = pcbnew.ToMM
AUX = [(67.0, -54.6, 82.9, -4.0), (88.0, -48.0, 97.5, -25.5)]


def boxes():
    out = list(AUX)
    with open(os.path.join(ROOT, "lib", "v6_copper.csv")) as fh:
        for r in csv.DictReader(l for l in fh if not l.startswith("#")):
            if r["kind"] in ("unrouted", "area") and r["layer"] == "*":
                x0, x1 = sorted((float(r["x"]), float(r["x1"])))
                y0, y1 = sorted((float(r["y"]), float(r["y1"])))
                out.append((x0, y0, x1, y1))
    return out


BOX = boxes()


def inside(p):
    x, y = T(p.x), -T(p.y)
    return any(a <= x <= c and b <= y <= d for a, b, c, d in BOX)


b = pcbnew.LoadBoard(BOARD)
pads = [p for f in b.GetFootprints() for p in f.Pads()]
zones = [z for z in b.Zones() if not z.GetIsRuleArea()]


def touched(net, layer, pt, me, items):
    for p in pads:
        if p.GetNetname() == net and p.IsOnLayer(layer) and p.HitTest(pt):
            return True
    for z in zones:
        if z.GetNetname() == net and z.IsOnLayer(layer) and z.HitTestFilledArea(layer, pt):
            return True
    for t in items.get(net, ()):
        if t is me or t.m_Uuid == me.m_Uuid:
            continue
        if t.GetClass() == "PCB_VIA":
            if t.HitTest(pt):
                return True
        elif t.GetLayer() == layer and (t.HitTest(pt, 1) or (me.GetClass() == "PCB_VIA" and me.HitTest(t.GetStart()))
                                        or (me.GetClass() == "PCB_VIA" and me.HitTest(t.GetEnd()))):
            return True
    return False


nets, total = {}, 0
for rnd in range(200):
    items = {}
    for t in b.GetTracks():
        items.setdefault(t.GetNetname(), []).append(t)
    dead = []
    for net, ts in items.items():
        if not net:
            continue
        for t in ts:
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                if not inside(p):
                    continue
                links = sum(1 for L in t.GetLayerSet().CuStack() if touched(net, L, p, t, items))
                if links <= 1:
                    dead.append(t)
            else:
                for p in (t.GetStart(), t.GetEnd()):
                    if inside(p) and not touched(net, t.GetLayer(), p, t, items):
                        dead.append(t)
                        break
    if not dead:
        break
    for t in dead:
        nets[t.GetNetname()] = nets.get(t.GetNetname(), 0) + 1
        b.Delete(t)
    total += len(dead)
pcbnew.SaveBoard(BOARD, b)
print(f"prune: {total} dangling items deleted in {rnd} rounds; nets: " +
      " ".join(f"{k.split('/')[-1]} ({v})" for k, v in sorted(nets.items())))
