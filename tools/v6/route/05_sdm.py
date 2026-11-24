#!/usr/bin/env python3
"""Routing chain step 05 (kipy): the two sigma-delta links drawn by script (planning session rule 2, 2026-11-24).

  kipy 05_sdm.py IN OUT

Clock and data of one modulator side by side on In3, each pair with its domain's ground and supply as guard tracks
where no ground plane lies under it (In4 has a plane only in the card areas and in the ISO strip):

- ISO link: U21 (MDATA_INU pin 12, INU_ADCLK from pin 14 through R258 when the board has it) -> U4 / R50 west of J9.
  In3 from U21 through the passage north of J11 (over the In4 ISOGND planes) to x 40.4, In2 past J37 (its DC+ tongue
  is on In1 / In3 / B), the via column x 28.75 between the J37 and J38 tongues, In3 north of J38 (over the In4 ISOGND
  strip) and on west to U4 with ISOGND and 3V3_ISO (U4 VDD2) beside the pair.
- AFE link: U15 B5 (MDATA, pin 10) / R22 (ADCLK, 39R at U15) -> R55 / U5 below FILTER_OUT1. In3 from the primary
  card area (over its In4 GND plane) to U5, with GND and VCC (U5 VDD2) beside the pair.

Every piece is tested by geo.Ctx (2.5 mm to high-voltage nets, domain gaps, pours, keep-outs) before it is added; a
via or stub inside a high-voltage pour near U5 cuts that pour back by 2.5 mm (geo.hv_holes keep-outs). The old copper
of the four nets is deleted first. Prints length and what each run passes over.
"""
import math
import os
import sys
import time

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import F, T, P, xy  # noqa: E402

from drawlib import (IN1, IN2, IN3, B, SIG_W, GUARD_W, AVOID, say, strip, end_via, via_near, run, straight,  # noqa: E402
                     east_pad_of, chain, end_at_track)

FC = pcbnew.F_Cu


# the via column x 28.75 between the J37 / J38 tongues: ten slots at 0.612 mm from y 52.99 (lanes from the east on
# F / In2 must keep 2.5 mm from the J37 pads: y >= 52.89) to 58.48 (2.5 mm from the ISO lane); 06_west.py takes
# the other six for the divider taps
COLUMN = {"ISOGND": 52.99, "3V3_ISO": 53.602, "MDATA_INU": 54.214, "INU_ADCLK": 54.826}
# the six divider taps (U7 / U2 block -> the old track ends west of J24), slots from the south (inner lane at the
# corner of the barrier strip) to the north; they are drawn before the pair, which then stays south of them
TAPS = [  # net, source (pad or old track end), west end (old track end), column slot y; in nesting order: the
    #       east exit of the U7 / U2 block at (104 + 0.5 i, 17), the waypoint (69, 46.8 + 0.5 i) north of U21, the
    #       corridor slot, and on In1 west of the column the south lane peels off first
    ("Net-(U7B--)", ("U7", "6"), (17.39, 35.51), 55.438),
    ("Net-(U7B-+)", (100.77, 9.72), (2.87, 37.30), 56.05),
    ("Net-(U7A--)", (96.69, 12.13), (-4.57, 48.00), 56.662),
    ("Net-(U7A-+)", (96.69, 11.25), (-6.25, 44.15), 57.274),
    ("Net-(U2--)", ("U2", "4"), (-6.51, 27.37), 57.886),
    ("Net-(U2-+)", ("C101", "2"), (-10.84, 29.48), 58.498),
]


def taps(b):
    """In3 from the U7 / U2 block up the east column and west along the band north of U21 (waypoint x 69, the
    south lane first), round J25 to (60, slot y), straight west in the corridor north of where the pair will run to
    a via at x 41.6, F
    west to the column, In1 from the column west (north of J38) to a via at the old track end."""
    cx = geo.Ctx(b)
    cx.via_pierce = {"ISOGND", "3V3_ISO", "ISOPGND"}
    holes, ok = [], {}
    prev = None
    for i, (net, src_, wend, ys) in enumerate(TAPS):
        mine = []
        s = (end_via(cx, src_[0], src_[1], net=net, made=mine) if isinstance(src_[0], str)
             else end_at_track(cx, net, *src_, made=mine))
        c = cx.via_ok(net, 28.75, ys, margin=0.003)
        v = cx.via_ok(net, 41.6, ys, margin=0.003)
        e = None
        if s is not None and c is not None and v is not None:
            cx.commit(c, v)
            mine += [c, v]
            e = end_at_track(cx, net, *wend, made=mine, pierce={"/05 VSI/INDUCTOR_OUTPUT", "ISODC+"})
        else:
            say(f"sdm: tap {net}: no source via / column via (28.75, {ys}) / corridor via (41.6, {ys})")
        ok[net] = e is not None and chain(
            cx, net, s, [(IN3, SIG_W, (90.0, -6.0, 119.5, 22.0), (104.0 + 0.6 * i, 17.0)),
                         (IN3, SIG_W, (56.0, 10.0, 119.5, 59.0), (60.0, ys)),
                         (IN3, SIG_W, "straight", [(41.6, ys)]),
                         (FC, SIG_W, "straight", [(28.75, ys)]),
                         (IN1, SIG_W, "straight", [(27.4, ys)]),
                         (IN1, SIG_W, (-20.0, 18.0, 31.0, 61.0), e)], f"tap {i + 1}",
            leaders=[None, (SIG_W, prev[1])] if prev else None)
        if ok[net]:
            holes += mine
            prev = cx.paths
        else:                       # take the source / column / corridor / end vias out again
            for o in mine:
                b.Delete(o)
            keep = cx.via_pierce
            cx.__init__(b)
            cx.via_pierce = keep
    cx.pierce = {"/05 VSI/INDUCTOR_OUTPUT", "ISODC+"}
    n = geo.hv_holes(cx, holes, "tap")
    say(f"sdm: taps drawn: {sum(ok.values())} of {len(ok)}; {n} HV keep-outs at their west ends")


def iso_link(b):
    cx = geo.Ctx(b)
    cx.via_pierce = {"ISOGND", "3V3_ISO", "ISOPGND"}
    cx.pierce = {"/05 VSI/INDUCTOR_OUTPUT", "/05 VSI/INU_FILTER_INPUT"}   # ISO planes: antipads by
    total = {}                                 # the refill; the HV pours at U4: cut back by hv_holes
    made = []
    # east ends
    ck = east_pad_of(b, "INU_ADCLK", "U4")
    e_clk = end_via(cx, *ck, prefer=(0, 1))
    e_dat = end_via(cx, "U21", "12", prefer=(0, 1))
    e_3v3 = via_near(cx, "3V3_ISO", 59.4, 44.3)      # the plane's corner at the barrier strip: the inner lane
    if None in (e_clk, e_dat, e_3v3):
        return cx, total, made
    # transition vias: In3 -> In2 east of J37 (x 40.4), In2 -> In3 in the column between the tongues (x 28.75)
    ys = COLUMN
    tv, cv = {}, {}
    for n in ("INU_ADCLK", "MDATA_INU", "3V3_ISO"):
        w1, w2 = [], []
        v = cx.via_ok(n, 40.4, ys[n], margin=0.003, why=w1)
        c = cx.via_ok(n, 28.75, ys[n], margin=0.003, why=w2)
        if v is None or c is None:
            say(f"sdm: transition via of {n} at x 40.4 / 28.75, y {ys[n]} NOT legal: {w1} {w2}")
            return cx, total, made
        cx.commit(v, c)
        tv[n], cv[n] = (40.4, ys[n]), (28.75, ys[n])
    g0 = (28.75, ys["ISOGND"])                     # the guard starts on the In4 ISOGND strip in the column
    g = cx.via_ok("ISOGND", *g0, margin=0.003)                   # (east of the J38 tongue, which cuts the strip on In4)
    if g is None:
        say("sdm: ISOGND column via NOT legal")
        return cx, total, made
    cx.commit(g)
    box_e = (37.0, 36.0, 82.0, 60.0)
    p_3v3 = run(cx, "3V3_ISO", IN3, e_3v3, tv["3V3_ISO"], GUARD_W, box_e, what="east, plane -> x 40.4")
    p_dat = p_3v3 and run(cx, "MDATA_INU", IN3, e_dat, tv["MDATA_INU"], SIG_W, box_e, leader=(GUARD_W, p_3v3), what="east, U21 -> x 40.4")
    p_clk = p_dat and run(cx, "INU_ADCLK", IN3, e_clk, tv["INU_ADCLK"], SIG_W, box_e, leader=(SIG_W, p_dat), what="east, U21 side -> x 40.4")
    if not p_clk:
        return cx, total, made
    for n, w in (("INU_ADCLK", SIG_W), ("MDATA_INU", SIG_W), ("3V3_ISO", GUARD_W)):
        if not straight(cx, n, IN2, [tv[n], cv[n]], w, "past J37 on In2"):
            return cx, total, made
    # west ends at U4
    w_clk = end_via(cx, "U4", "7", prefer=(1, 0), made=made)
    w_dat = end_via(cx, "R50", "2", prefer=(0, 1), made=made)
    w_gnd = end_via(cx, "C162", "2", net="ISOGND", prefer=(0, -1), w=0.25, made=made)   # U30 input capacitor (U30-2 is
    #       within 2.5 mm of its own HV output pins: the router joins it to C162 later)
    w_3v3 = end_via(cx, "C37", "2", net="3V3_ISO", prefer=(0, -1), w=0.25, made=made)
    if None in (w_clk, w_dat, w_gnd, w_3v3):
        return cx, total, made
    box_w = (-101.0, 26.0, 31.0, 71.4)
    q_clk = run(cx, "INU_ADCLK", IN3, cv["INU_ADCLK"], w_clk, SIG_W, box_w, avoid=AVOID, what="west, column -> U4-7")
    q_dat = q_clk and run(cx, "MDATA_INU", IN3, cv["MDATA_INU"], w_dat, SIG_W, box_w, leader=(SIG_W, q_clk), avoid=AVOID, what="west, column -> R50")
    q_3v3 = q_dat and run(cx, "3V3_ISO", IN3, cv["3V3_ISO"], w_3v3, GUARD_W, box_w, leader=(SIG_W, q_clk), avoid=AVOID, what="guard, column -> C37-2")
    # (the guard leaves the column straight west above the J38 pads: the grid cannot hit that 0.05 mm gap)
    q_gnd = q_3v3 and straight(cx, "ISOGND", IN3, [g0, (17.5, g0[1])], GUARD_W, "guard, column -> x 17.5") and \
        run(cx, "ISOGND", IN3, (17.5, g0[1]), w_gnd, GUARD_W, box_w, leader=(GUARD_W, q_3v3), avoid=AVOID, what="guard, x 17.5 -> C162-2")
    if q_clk and q_dat:
        total["INU_ADCLK"] = geo.plen(p_clk) + 11.65 + geo.plen(q_clk)
        total["MDATA_INU"] = geo.plen(p_dat) + 11.65 + geo.plen(q_dat)
    return cx, total, made


def afe_link(b):
    cx = geo.Ctx(b)
    cx.via_pierce = {"GND", "VCC"}
    cx.pierce = {"/01 afe/FILTER_INPUT", "/01 afe/LEMOUT"}
    total = {}
    made = []
    # the modulator's data output U5-6 -> R55-1 (33R at the source), B.Cu, before the pair's end vias crowd U5
    m = run(cx, "Net-(U5-MDAT)", B, geo.pad_xy(b, "U5", "6"), geo.pad_xy(b, "R55", "1"), SIG_W, (-42.0, -83.6, -24.0, -70.0),
            made=made, what="U5-6 -> R55-1")
    if m is None:
        say("sdm: Net-(U5-MDAT) left to the router")
    e_dat = end_via(cx, "U15", "10", prefer=(0, -1), made=made)
    e_clk = end_via(cx, "R22", "2", prefer=(0, -1), made=made)
    e_gnd = via_near(cx, "GND", 51.0, -1.2, made=made)
    e_vcc = via_near(cx, "VCC", 53.0, -2.4, made=made)
    w_dat = end_via(cx, "R55", "2", prefer=(1, 0), made=made)
    w_clk = end_via(cx, "U5", "7", prefer=(0, 1), made=made)
    w_gnd = end_via(cx, "C64", "1", net="GND", prefer=(0, -1), w=0.25, made=made)
    w_vcc = end_via(cx, "C64", "2", net="VCC", prefer=(1, 0), w=0.25, made=made)
    if None in (e_dat, e_clk, e_gnd, e_vcc, w_dat, w_clk, w_gnd, w_vcc):
        return cx, total, made
    box = (-46.0, -83.6, 62.0, 6.0)
    q_clk = run(cx, "ADCLK", IN3, e_clk, w_clk, SIG_W, box, avoid=AVOID, made=made, what="R22 -> U5-7")
    q_dat = q_clk and run(cx, "MDATA", IN3, e_dat, w_dat, SIG_W, box, leader=(SIG_W, q_clk), avoid=AVOID, made=made, what="U15-10 -> R55")
    q_gnd = q_dat and run(cx, "GND", IN3, e_gnd, w_gnd, GUARD_W, box, leader=(SIG_W, q_clk), avoid=AVOID, made=made, what="guard -> C64-1")
    q_vcc = q_gnd and run(cx, "VCC", IN3, e_vcc, w_vcc, GUARD_W, box, leader=(SIG_W, q_dat), avoid=AVOID, made=made, what="guard -> C64-2")
    if q_clk and q_dat:
        total["ADCLK"], total["MDATA"] = geo.plen(q_clk), geo.plen(q_dat)
    return cx, total, made


RESERVE = "v6 route reserve sdm "
# the room the late ISO link step needs (planning update 2026-11-24: the sense groups and their links are routed
# last, as steps that can be dropped): kept free of the steps in between by keep-outs (tracks and vias), deleted by
# the links step itself. (name, rectangle x0 y0 x1 y1, layers)
RESERVES = [
    ("column and In2 north of J37", (27.6, 52.6, 41.0, 55.1), None),
    ("corridor In3", (40.4, 52.6, 58.5, 55.1), ("In3.Cu",)),
    ("U21 to the corridor In3", (58.5, 40.0, 78.0, 47.0), ("In3.Cu",)),
    ("north of J38 In3", (5.0, 52.6, 28.4, 56.6), ("In3.Cu",)),
    ("west run In3", (-62.0, 52.6, 5.0, 60.0), ("In3.Cu",)),
]


def reserve(b):
    import fence
    for name, r, layers in RESERVES:
        fence.keepout(b, name, r, list(layers) if layers else fence.AL, prefix=RESERVE)
    say(f"sdm: {len(RESERVES)} keep-outs reserve the room of the late ISO link")


def main():
    src, dst, mode = sys.argv[1:4]
    b = pcbnew.LoadBoard(src)
    if mode == "taps":
        reserve(b)
        taps(b)
        b.Save(dst)
        return
    import fence
    say(f"sdm: {fence.clear(b, RESERVE)} reserve keep-outs removed")
    strip(b, {"MDATA", "ADCLK", "MDATA_INU", "INU_ADCLK", "INU_ADCLK_U21"})
    n = 0
    ti, ta = {}, {}
    if mode in ("links", "iso"):
        cxi, ti, madei = iso_link(b)
        n += geo.hv_holes(cxi, madei, "sdm")
    if mode in ("links", "afe"):
        cx, ta, made = afe_link(b)
        n += geo.hv_holes(cx, made, "sdm")
    say(f"sdm: {n} HV keep-outs (pour cut back 2.5 mm) for the link vias / stubs in HV pours")
    for k, v in {**ti, **ta}.items():
        say(f"sdm: length {k} {v:.1f} mm")
    b.Save(dst)


if __name__ == "__main__":
    main()
