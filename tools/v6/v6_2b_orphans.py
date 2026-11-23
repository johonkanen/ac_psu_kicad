#!/usr/bin/env python3
"""v6 step 2, second part (run once, kipy, after v6_2_clear_strips.py): copper that lost every pad.

With the power stage and the strips gone, some runs outside the strips end nowhere at both ends (PWM and supply
runs to the old gate-card headers, cut v5 chains) and two pour pieces have no pad left. They carry a net but
belong to no pad: tools/assign_nets.py reports them as "group has no pad". This step deletes exactly those groups
(the grouping is the one of tools/assign_nets.py, on the filled board); the planes of the unrouted card area
("v5 card ...") stay, as that check allows.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board  # noqa: E402
import assign_nets as AN  # noqa: E402

b = Board(6003)
total = 0
for rnd in range(6):
    zones = b.b.Zones()
    pcbnew.ZONE_FILLER(b.b).Fill(zones)
    layers = AN.load_copper()
    if b.b.GetCopperLayerCount() == 6:
        layers = list(layers[:3]) + [AN._ExtraLayer("In3.Cu"), AN._ExtraLayer("In4.Cu")] + list(layers[3:])
    items = AN.build_items(b.b, layers, "C", AN.ipc_via_nets(b.b))
    res = AN.analyse(items, AN.connect(items, layers))
    dead = {}
    for g, members in res["groups"].items():
        if res["net_of"].get(g):
            continue
        for i in members:
            it = items[i]
            if it.kind in ("track", "via", "zone") and it.obj.GetNetname():
                if it.kind == "zone" and it.obj.GetZoneName().startswith("v5 card"):
                    continue
                dead[id(it.obj)] = it
    if not dead:
        break
    seen = set()
    for it in dead.values():
        key = it.obj.m_Uuid.AsString()
        if key in seen:
            continue
        seen.add(key)
        b.log.append(f"round {rnd + 1}: {it.label} [{it.obj.GetNetname()}] deleted: its group has no pad")
        b.b.Delete(it.obj)
    total += len(seen)
    pcbnew.SaveBoard(AN.bc.BOARD, b.b)
    b.b = pcbnew.LoadBoard(AN.bc.BOARD)
b.log.append(f"{total} items without a pad deleted")
b.save("v6 step 2b: copper groups without a pad deleted")
