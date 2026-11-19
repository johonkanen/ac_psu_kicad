#!/usr/bin/env python3
"""v5 step 14 (run once, kipy): preload R108 on the regulated 15 V output of the aux flyback 4.7k -> 3.3k
(user 2026-11-19: "change r108").

The reference design of the controller needed about 5 mA on the regulated rail to keep the outputs up at light
load. 3.3k gives 4.5 mA and 68 mW in the 0805 part (125 mW). Value only; the footprint and position stay.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board  # noqa: E402

b = Board(5014)
fp = b.fp("R108")
new = b.comps["R108"]["value"]
if fp.GetValue() == new:
    raise SystemExit("v5 step 14 already applied (R108 is " + new + ")")
if (fp.GetValue(), new) != ("4.7k", "3.3k"):
    raise SystemExit(f"R108: board {fp.GetValue()}, netlist {new}")
b.log.append(f"R108: value {fp.GetValue()} -> {new}")
fp.SetValue(new)
b.save("v5 step 14: R108 3.3k")
