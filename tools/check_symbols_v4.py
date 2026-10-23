#!/usr/bin/env python3
"""p2k check_symbols with the v4 deviations applied (added parts' pins count as reference pins,
merged-away nets are gone, new nets exist). Thin wrapper, see tools/deviations.py."""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "p2k"))
import deviations  # noqa: E402
from p2k import board, check_symbols as cs  # noqa: E402


def ipc_pins_v4():
    ipc = json.load(open(board.path("reference", "ipc356_pads.json")))
    pins, nets = defaultdict(set), set()
    for p in deviations.apply_records(ipc["pads"]):
        if p["kind"] == "pad":
            pins[p["refdes"]].add(p["pin"])
            nets.add(p["net"])
    for ref, p in deviations.added_parts().items():
        pins[ref] |= set(p["pins"])
        nets |= set(p["pins"].values())
    return pins, nets


cs.ipc_pins = ipc_pins_v4
sys.exit(cs.main())
