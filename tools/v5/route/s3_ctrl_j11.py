#!/usr/bin/env python3
"""Routing stage 3: J11 fan-out (routing list group 4).

  python3 tools/v5/route/s3_ctrl_j11.py EXTRACT.json OUT.json [earlier ROUTES.json ...]

J11 is 2 x 19 pins at 1.27 mm (pads 0.812 mm). The CTRL area around rows 9..18 (pins 19..38, y > 33) is
only the pin column, 2.9 mm wide. Past a pin row a layer has three channels: M between the two pin columns
(x 45.535, 0.153 mm to both pads) and E1 / E2 east of the east column (x 46.81 / 47.115; the area ends at
x 47.3). On F.Cu, In3.Cu and B.Cu that is 9 tracks for the 19 signals of pins 19..37. Routed here: the four
sigma-delta lines, PWM_Q5..Q8 and PWM_TRANS6 (the ISO-side group 3 signals with the J8 / J6 runs).
NOT routed: pins 18..23, 25, 27, 29, 35, 36 (PWM_G1..G4, DAB_PWM_PRI_HI/LO, PWM_TRANS4/5, DAB_PWM_HI/LO_SEC,
relay). See the report: the column needs a wider CTRL area or more layers.

Channels per layer (rows E2 > E1; a west pin crosses M to reach E1/E2, so M's pin is lower):
  B.Cu    M pin 26 MDATA_DAB_CTRL, E1 pin 34 MDATA_INU_CTRL, E2 pin 37 PWM_Q7_CTRL  (no via: along y 32.1..32.9
          above the pads of U21 / U19, in the order of the pads)
  In3.Cu  M pin 24 ADCLK_DAB_CTRL, E1 pin 32 INU_ADCLK_CTRL, E2 pin 33 PWM_Q8_CTRL  (in the order of the pads)
  F.Cu    M pin 28 PWM_TRANS6_CTRL, E1 pin 30 PWM_Q5_CTRL, E2 pin 31 PWM_Q6_CTRL  (pin 28 passes south of pin 30's via;
          no split of the nine signals into three triples is free of such an inversion)
Pins 1..17 leave east at their own height (east column) or through the gap below their row (west column).
"""
import sys

import router

r = router.Router(sys.argv[1], log=open(sys.argv[2] + ".log", "w"))
for p in sys.argv[3:]:
    r.load_routes(p)
P = r.pads
W = 0.152
XW, XE = P["J11-2"]["x"], P["J11-1"]["x"]
XM, XE1, XE2, XO, XS = (XW + XE) / 2, 46.81, 47.115, 47.6, 46.95
Y0, PITCH = P["J11-1"]["y"], 1.27
YE2, YE1 = 32.86, 32.555       # the two tracks that turn east right under the column (area edge y 33.0)


def row(pin):
    return (pin - 1) // 2


def yr(k):
    return Y0 + PITCH * k


def west(pin):
    return pin % 2 == 0


def gap(pin):
    """y of the gap below the row of a pin."""
    return yr(row(pin)) - PITCH / 2


def column(layer, m, e1, e2, m_exit):
    """Three tracks down the pin column on one layer; returns {pin: end point}."""
    out = {}
    for pin, x, yturn, ch in ((e2, XE2, YE2, 0.0), (e1, XE1, YE1, 0.179)):
        net, y = P[f"J11-{pin}"]["net"], yr(row(pin))
        # E1 turns with a small chamfer: pin 17 leaves south-east right below it
        if west(pin):
            pts = [(XW, y), (XM, gap(pin)), (x, gap(pin)), (x, yturn + ch), (x + ch, yturn), (XO, yturn)]
        else:
            pts = [(XE, y), (x, y - (x - XE)), (x, yturn + ch), (x + ch, yturn), (XO, yturn)]
        r.add_track(net, layer, pts, W, check=False)
        out[pin] = (XO, yturn, layer)
    net, y = P[f"J11-{m}"]["net"], yr(row(m))
    r.add_track(net, layer, [(XW if west(m) else XE, y), (XM, gap(m)), (XM, m_exit), (XO, m_exit)], W, check=False)
    out[m] = (XO, m_exit, layer)
    return out


def leave(layer, pin):
    """Pin of rows 0..8 east to x XO."""
    net, y = P[f"J11-{pin}"]["net"], yr(row(pin))
    pts = [(XW, y), (XM, gap(pin)), (XS, gap(pin))] if west(pin) else [(XE, y), (XS, y)]
    r.add_track(net, layer, pts, W, check=False)
    return (XS, pts[-1][1], layer)


r.log("== J11 pin column (exact geometry, checked by DRC)")
VB, VF = 29.5, 21.4
ALL = ("In3.Cu", "F.Cu", "B.Cu")
CA = (44.0, 20.5, 96.0, 33.2)


def pad_via(pad, y, w=0.2):
    p = P[pad]
    layer = "B.Cu" if "B.Cu" in p["layers"] else "F.Cu"
    return r.add_via(p["net"], p["x"], y) and r.add_track(p["net"], layer, [(p["x"], p["y"]), (p["x"], y)], w)


end = {}
end.update(column("B.Cu", 26, 34, 37, gap(17)))
end.update(column("In3.Cu", 24, 32, 33, gap(15)))
end.update(column("F.Cu", 28, 30, 31, gap(17)))
# pin 17: south-east into the gap below row 8 on In3 (its own east side is taken by E1 on every layer)
y17 = yr(row(17))
r.add_track(P["J11-17"]["net"], "In3.Cu", [(XE, y17), (XE + (y17 - gap(17)), gap(17)), (XO, gap(17))], W, check=False)
end[17] = (XO, gap(17), "In3.Cu")
for pin in (6, 12, 13, 14, 15, 16):
    end[pin] = leave("F.Cu", pin)
for pin in (7, 8, 10):
    end[pin] = leave("In3.Cu", pin)
for pin in (1, 3, 4, 9, 11):
    end[pin] = leave("B.Cu", pin)

r.log("== B.Cu: three tracks above the CTRL pads of U21 / U19, no via")
for pin, pad in ((26, "U21-6"), (34, "U21-5"), (37, "U19-6")):
    x, y, _ = end[pin]
    r.add_track(P[pad]["net"], "B.Cu", [(x, y), (P[pad]["x"], y), (P[pad]["x"], P[pad]["y"])], W)

r.log("== In3 / F.Cu: along the top of the area, down to a via at the south end of the pad")
for pin, pad in ((24, "U21-4"), (32, "U21-3"), (33, "U19-3"), (30, "U19-7"), (31, "U20-5")):
    x, y, layer = end[pin]
    pad_via(pad, VB)
    r.add_track(P[pad]["net"], layer, [(x, y), (P[pad]["x"], y), (P[pad]["x"], VB)], W)
pad_via("U19-5", VB)
for pad in ("U15-6", "U15-5", "U15-4", "U15-3", "U15-2"):
    pad_via(pad, VF)

r.log("== ISOADA1..3_CTRL: vias at the output filters (the middle one between the two pads of its node)")
AV = {}
for pin, a, b, via in ((4, "R128-2", "C129-1", (52.6, 26.11)), (3, "R129-2", "C130-1", None), (1, "R130-2", "C131-1", (56.2, 26.11))):
    net = P[a]["net"]
    r.add_track(net, "F.Cu", [(P[a]["x"], P[a]["y"]), (P[b]["x"], P[b]["y"])], 0.25)
    if via is None:
        via = (P[a]["x"], (P[a]["y"] + P[b]["y"]) / 2)
        r.add_via(net, *via, in_pad=True)
    else:
        r.add_via(net, *via)
        r.add_track(net, "F.Cu", [(P[a]["x"], P[a]["y"]), via], 0.2)
    AV[pin] = via

r.log("== U15: pin 6 on F.Cu (the one track between PEC1 and the pads), pins 7, 8, 10 on In3 and 9, 11 on B.Cu south of PEC1")
r.connect("MDATA_ISO", end[6], "U15-7", layers=("F.Cu",), w=W, box=CA) or r.connect("MDATA_ISO", end[6], "U15-7", layers=ALL, w=W, box=CA)
for pin, pad in ((8, "U15-5"), (7, "U15-6"), (10, "U15-3"), (9, "U15-4"), (11, "U15-2")):
    ly = (end[pin][2],)
    r.connect(P[pad]["net"], end[pin], (P[pad]["x"], VF), layers=ly, w=W, box=CA) or \
        r.connect(P[pad]["net"], end[pin], pad, layers=ALL, w=W, box=CA)

r.log("== U13: F.Cu north of PEC1 and J14, then pin 28 (F.Cu) and pin 17")
for pin, pad in ((12, "U13-7"), (14, "U13-5"), (13, "U13-6"), (16, "U13-3"), (15, "U13-4")):
    r.connect(P[pad]["net"], end[pin], pad, layers=("F.Cu",), w=W, box=CA) or \
        r.connect(P[pad]["net"], end[pin], pad, layers=ALL, w=W, box=CA)
r.connect("PWM_TRANS6_CTRL", end[28], (P["U19-5"]["x"], VB), layers=("F.Cu",), w=W, box=CA) or \
    r.connect("PWM_TRANS6_CTRL", end[28], "U19-5", layers=ALL, w=W, box=CA)
r.connect("PWM_TRANS3_ISO", end[17], "U13-2", layers=ALL, w=W, box=CA, via=1.5)

r.log("== ISOADA1..3_CTRL: J11 pins 4, 3, 1 on B.Cu to the vias")
for pin in (4, 3, 1):
    net = P[f"J11-{pin}"]["net"]
    r.connect(net, end[pin], AV[pin], layers=("B.Cu",), w=W, box=CA) or r.connect(net, end[pin], AV[pin], layers=ALL, w=W, box=CA)

r.save(sys.argv[2])
r.log(f"stage 3: {len(r.failed)} failed: {r.failed}")
