#!/usr/bin/env python3
"""v5 step 16 (run once, kipy): channels of U19 / U20 after routing pass 2
(reports/v5_layout/routing_pass2.md on branch routing-pass2; user 2026-11-19: "go ahead with your recommendations").

Step 15 put the J8 nets PWM_Q7 / Q5 / TRANS6 on U19 pins 13 .. 15, right under the bus wire pad BUSP2 (63.5, 45.5):
its 2.5 mm keep-out leaves no via site there and pass 2 found no path for them. They go to U20 pins 11 / 12 / 10
(x 82.4 .. 84.9, under the gap between J6 and J4); the relay line goes from U20 pin 12 to U19 pin 15 (x 66.83,
outside the keep-out). U19 pins 13 / 14 are free now. Pad nets only (tools/sheets/sheet11.py); no part moves.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "v4"), os.path.dirname(HERE)]
from v4board import Board  # noqa: E402

b = Board(5016)
net = lambda ref, num: next(q for q in b.fp(ref).Pads() if q.GetNumber() == num).GetNetname()
if net("U20", "10") == "PWM_TRANS6":
    raise SystemExit("v5 step 16 already applied (U20-10 is PWM_TRANS6)")
if net("U19", "15") != "PWM_TRANS6":
    raise SystemExit("U19-15 is not PWM_TRANS6: v5 step 15 first")
for ref in ("U19", "U20"):
    if not b.sync_pads(ref):
        raise SystemExit(f"{ref}: no pad net changes (regenerate sheet 11 first)")
want = {("U19", "10"): "PWM_TRANS5", ("U19", "11"): "PWM_Q8", ("U19", "12"): "PWM_Q6", ("U19", "15"): "GPIO_BYPASS_RLY_ISO",
        ("U20", "10"): "PWM_TRANS6", ("U20", "11"): "PWM_Q7", ("U20", "12"): "PWM_Q5", ("U20", "13"): "PWM_TRANS4",
        ("U20", "14"): "DAB_PWM_LO_SEC", ("U20", "15"): "DAB_PWM_HI_SEC"}
for (ref, num), n in want.items():
    if net(ref, num) != n:
        raise SystemExit(f"{ref}-{num}: {net(ref, num)}, expected {n}")
for t in b.b.GetTracks():
    if t.GetNetname().startswith(("PWM_Q", "PWM_TRANS4", "PWM_TRANS5", "PWM_TRANS6", "DAB_PWM_", "GPIO_BYPASS_RLY_ISO")) and \
            58.0 < t.GetStart().x / 1e6 < 92.0 and 28.0 < -t.GetStart().y / 1e6 < 43.0:
        raise SystemExit(f"track of {t.GetNetname()} at the isolator row")
b.save("v5 step 16: U19 / U20 channels")
