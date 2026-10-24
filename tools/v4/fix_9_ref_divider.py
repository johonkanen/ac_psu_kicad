#!/usr/bin/env python3
"""v4 fix 9 (run once, kipy): R19 / R32 (REF3025 1.65 V divider top, 820R below) 420R -> 422R:
420R is not an E96 value and not stocked at JLC; 422R gives 2.5 V x 820 / 1242 = 1.6506 V
(420R: 1.6532 V, 430R would give 1.640 V). Footprint values only, no copper change."""
from v4board import Board

b = Board(4109)
if b.fp("R19").GetValue() == "422R":
    raise SystemExit("fix 9 already applied")
for ref in ("R19", "R32"):
    b.set_value(ref, "422R")
b.save("fix 9: R19/R32 422R")
