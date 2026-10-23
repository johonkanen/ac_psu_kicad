#!/usr/bin/env python3
"""v4 fix 1 (run once, kipy): the isolated 20 V return RET_ISO (TR2-6, C15-2, C36-2, R49-1, its
F.Cu/B.Cu pours and 2 vias) becomes ISOGND and is joined to the ISOGND copper:
  - every RET_ISO pad / track / via / zone -> ISOGND;
  - new In1.Cu ISOGND zone under the former RET_ISO area out to U8 (x 91.0..108.6,
    y -24.0..-13.0): TR2-6 and U8-2 (THT) connect in it, and it meets the existing In1 ISOGND
    plane at x >= 105.6;
  - 3 extra stitching vias between the F/B pours and the In1 zone near C15-2, C36-2, R49-1."""
from v4board import Board

b = Board(4101)
if b.b.FindNet("RET_ISO") is None or not any(t.GetNetname() == "RET_ISO" for t in b.b.GetTracks()):
    raise SystemExit("fix 1 already applied")
for ref in ("TR2", "C15", "C36", "R49"):
    b.sync_pads(ref)
b.renet("RET_ISO", "ISOGND")
b.zone("In1.Cu", [(91.0, -13.0), (108.6, -13.0), (108.6, -24.0), (91.0, -24.0)], "ISOGND",
       "v4 fix 1 ISOGND under the 20 V iso return", 90)
for x, y in ((96.0, -15.5), (94.5, -17.25), (95.0, -19.25)):
    b.via(x, y, "ISOGND")
b.save("fix 1: RET_ISO -> ISOGND")
