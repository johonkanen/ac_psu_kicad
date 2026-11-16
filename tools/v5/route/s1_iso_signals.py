#!/usr/bin/env python3
"""Routing stage 1: ISO-side signals of the isolator row (routing list groups 1, 3 and 9).

  python3 tools/v5/route/s1_iso_signals.py EXTRACT.json OUT.json

Sigma-delta pairs U21 -> U4 / U6, PWM bundle U19/U20 -> J4/J6/J8, ISO_DAB_SDM_RAW_VOLTAGE.
One via at each isolator pin, at the south end of the pad (under the package edge), then In3 north under the
pads and the DC bus band. The U6 pair runs east on In3 south of the via row, so it does not cross the bundle. West of J11 only five tracks fit on In3
inside the `unrouted` rectangles (y < 54): one between the two rows of J8 and four north of them.
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
P = r.pads
IN3 = ("In3.Cu",)
ROW = [(IN3, (52.0, 38.0, 100.5, 41.3), 2.0)]      # leave the via row northwards, not along it


def pin_via(pad, y, w=0.2):
    """Via in line with an isolator pin, stub on the pad's layer."""
    p = P[pad]
    ok = r.add_via(p["net"], p["x"], y, in_pad=True)
    return ok and r.add_track(p["net"], "B.Cu", [(p["x"], p["y"]), (p["x"], y)], w)


r.log("== vias at the isolator pins: south end of the pads")
# A via north of the pads would push the ISODC+ pour (clearance 1.95 mm) into the bus band. South of the pads,
# at y 38.95, the via ring touches the pad end and leaves room for two In3 tracks along the edge of the ISO area.
VS = 38.95
for pad in ("U21-11", "U21-12", "U21-13", "U21-14", "U19-10", "U19-11", "U19-12", "U19-14", "U19-15",
            "U20-12", "U20-13", "U20-14", "U20-15"):
    pin_via(pad, VS)

r.log("== group 1: U6 pair, In3 along the south edge of the ISO band, then south at x 100.4 / 100.75")
x11, x13 = P["U21-11"]["x"], P["U21-13"]["x"]
YA, YB = 38.12, 38.45
r.add_track("MDATA_DAB", "In3.Cu", [(x11, VS), (x11 + (VS - YA), YA), (100.4, YA), (100.4, 37.0)], 0.152)
r.add_track("ADCLK_DAB", "In3.Cu", [(x13, VS), (x13 + (VS - YB), YB), (100.75, YB), (100.75, 37.0)], 0.152)
SOUTH = dict(layers=("In3.Cu", "F.Cu"), lcost={"F.Cu": 3.0}, via=4.0, w=0.152, box=(98.0, 15.0, 114.0, 39.5))
r.connect("MDATA_DAB", (100.4, 37.0, "In3.Cu"), "R72-2", **SOUTH)
r.connect("ADCLK_DAB", (100.75, 37.0, "In3.Cu"), "U6-7", **SOUTH)

r.log("== west of J11: five tracks on In3 (J8 rows at y 50.93 / 52.2)")
ym = (P["J8-44"]["y"] + P["J8-43"]["y"]) / 2
x43, y43 = P["J8-43"]["x"], P["J8-43"]["y"]
x44, y44 = P["J8-44"]["x"], P["J8-44"]["y"]
x47, y47 = P["J8-47"]["x"], P["J8-47"]["y"]
XE = 50.5
WEST = [("MDATA_INU", ym, [(25.5, ym), (25.5, 49.0)]),
        ("INU_ADCLK", 52.85, [(25.05, 52.85), (25.05, 49.0)]),
        ("PWM_Q5", 53.2, [(24.4, 53.2), (24.4, y44 + (24.4 - x44)), (x44, y44)]),
        ("PWM_Q7", 53.55, [(x43, 53.55), (x43, y43)]),
        ("PWM_TRANS6", 53.9, [(x47, 53.9), (x47, y47)])]
for net, y, tail in WEST:
    r.add_track(net, "In3.Cu", [(XE, y)] + tail, 0.152)
# from the pin vias: north, then one 45 degree run each through the opening between the J11 keep-out and J6
# pin 48 (lines x + y = c, 0.5 apart = 0.35 mm between the tracks)
SRC = [("MDATA_INU", "U21-12", 103.9), ("INU_ADCLK", "U21-14", 104.4), ("PWM_Q5", "U19-10", 104.9), ("PWM_Q7", "U19-11", 105.4),
       ("PWM_TRANS6", "U19-12", 105.9)]
for (net, y, tail), (_, pad, c) in zip(WEST, SRC):
    xs = P[pad]["x"]
    if c - xs >= VS:
        pts = [(xs, VS), (xs, c - xs), (c - y, y), (XE, y)]
    else:           # the via is already north-east of its line: start on the diagonal, step west onto the line
        c0 = xs + VS
        pts = [(xs, VS), (c0 - 47.3, 47.3), (c - 47.3, 47.3), (c - y, y), (XE, y)]
    r.add_track(net, "In3.Cu", pts, 0.152)
# down to U4 / R50 between the first two pin groups of J8
r.connect("MDATA_INU", (25.5, 49.0, "In3.Cu"), "R50-2", layers=("In3.Cu", "B.Cu"), lcost={"B.Cu": 2.0}, via=2.0, box=(22.0, 38.0, 30.0, 50.0))
r.connect("INU_ADCLK", (25.05, 49.0, "In3.Cu"), "U4-7", layers=("In3.Cu", "B.Cu"), lcost={"B.Cu": 2.0}, via=2.0, box=(20.0, 38.0, 30.0, 50.0))

r.log("== J6: PWM_Q8, PWM_TRANS5 (between the pin rows), PWM_Q6")
y6 = (P["J6-47"]["y"] + P["J6-48"]["y"]) / 2
x47, y47 = P["J6-47"]["x"], P["J6-47"]["y"]
r.add_track("PWM_TRANS5", "In3.Cu", [(x47, y47), (x47 + (y47 - y6), y6), (59.6, y6)], 0.152)
BOX6 = (55.0, 38.0, 84.0, 53.9)
r.connect("PWM_Q8", "U19-14", "J6-44", layers=IN3, cost=ROW, box=BOX6)
r.connect("PWM_TRANS5", "U19-15", (59.6, y6, "In3.Cu"), layers=IN3, cost=ROW, box=BOX6)
r.connect("PWM_Q6", "U20-12", "J6-43", layers=IN3, cost=ROW, box=BOX6)

r.log("== J4: PWM_TRANS4, DAB_PWM_LO_SEC, DAB_PWM_HI_SEC")
BOX4 = (76.0, 38.0, 93.0, 53.9)
r.connect("PWM_TRANS4", "U20-13", "J4-47", layers=IN3, cost=ROW, box=BOX4)
r.connect("DAB_PWM_LO_SEC", "U20-14", "J4-44", layers=IN3, cost=ROW, box=BOX4)
r.connect("DAB_PWM_HI_SEC", "U20-15", "J4-43", layers=IN3, cost=ROW, box=BOX4)

r.log("== group 9: ISO_DAB_SDM_RAW_VOLTAGE")
r.connect("ISO_DAB_SDM_RAW_VOLTAGE", (100.2405, 42.0498), "J4-25", layers=IN3, box=(97.0, 40.0, 104.0, 53.0))

r.save(sys.argv[2])
if "--png" in sys.argv:
    r.png(sys.argv[2] + ".png", (18, 14, 119, 56), ppm=14)
r.log(f"stage 1: {len(r.failed)} failed: {r.failed}")
