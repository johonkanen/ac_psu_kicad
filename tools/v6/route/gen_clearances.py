#!/usr/bin/env python3
"""Write the router's per-net clearance files from hv.py and the board's nets (kipy).

  kipy gen_clearances.py [BOARD]

hv_clearances.json: every high-voltage net (hv.py) and every PE-domain net at 2.5 mm (the default of the router steps:
the router keeps 2.5 mm between a routed net and their copper).
sense_clearances.json: every other net at 2.5 mm (for the steps that route the side-1 HV nets of U4 / U5: 2.5 mm to
everything low-voltage, the board's 0.15 mm between two HV nets).
"""
import json
import os
import sys

import pcbnew

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
from hv import is_hv  # noqa: E402

b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, "..", "..", "..", "kicad", "ac_psu.kicad_pcb"))
nets = sorted({p.GetNetname() for p in b.GetPads() if p.GetNetname() and not p.GetNetname().startswith("unconnected")})
sys.path[:0] = [os.path.join(H, "..", ".."), os.path.join(H, "..", "..", "v4")]
import board_common as bc  # noqa: E402
import domains  # noqa: E402
_, nl = bc.export_netlist()
dom = domains.classify(nl)
# HV nets, and every net of the PE domain (the PE terminals and the Y-capacitor nodes tied to them: E-P / E-I 2.5 mm)
hv = {n: 2.5 for n in nets if is_hv(n) or dom.get(n) == "E"}
lv = {n: 2.5 for n in nets if not is_hv(n)}
json.dump(hv, open(os.path.join(H, "hv_clearances.json"), "w"), indent=1, sort_keys=True)
json.dump(lv, open(os.path.join(H, "sense_clearances.json"), "w"), indent=0, sort_keys=True)
print(f"clearances: {len(hv)} HV / PE nets, {len(lv)} low-voltage nets")
