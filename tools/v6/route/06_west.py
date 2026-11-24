#!/usr/bin/env python3
"""Routing chain step 06 (kipy): the ISO nets that leave the card area westwards, drawn by script.

  kipy 06_west.py IN OUT

All of them pass north of the J11 tower (the corridor x 41..57, y 51.1..58.8) and then the J37 / J38 terminals,
whose pads and DC tongues keep 2.5 mm (routing_list.md place "past J37 / J38"):
- path A, the pinch between J37 and the barrier strip (0.64 mm, two lanes per inner layer) and south of the
  terminals to J24 / the relay line: PWM_Q7, PWM_Q8 (In1), PWM_TRANS6, GPIO_BYPASS_RLY_ISO (In2), 15V_ISO (In3),
  5V_ISOL (In4);
- path B (the via column x 28.75 between the two tongues) is drawn in step 05: the divider taps and the
  sigma-delta pair.
East of the corridor the nets come on B.Cu (the band y 41.5 .. 49.7 under the control card; In3 there holds the
step-05 pair and taps, In1 / In2 / In4 are planes).
Each run is a chain of one-layer grid-router legs joined by vias; a net whose leg fails is taken out again whole.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo  # noqa: E402
from geo import xy  # noqa: E402
from drawlib import IN1, IN2, IN3, IN4, B, SIG_W, say, end_via, chain  # noqa: E402

FC = pcbnew.F_Cu
SUP_W, NECK_W = 0.4, 0.15
EAST = (40.0, 36.5, 119.5, 59.0)      # B / In3 legs east of the corridor
WEST = (4.0, 18.0, 58.0, 59.0)        # In1..In4 legs from the corridor to J24 / the old track ends
FAR = (-102.0, 18.0, 31.0, 71.4)      # taps and 5V_ISOL west of the column


def main():
    src, dst = sys.argv[1:3]
    b = pcbnew.LoadBoard(src)
    cx = geo.Ctx(b)
    pierce = set()
    cx.via_pierce = {"ISOGND", "3V3_ISO", "ISOPGND"}
    ok = {}

    def go(net, start, legs, what):
        cx.pierce = pierce
        ok[net] = chain(cx, net, start, legs, what)

    # --- path A. Transfer vias in the corridor on a diagonal, south-east to north-west in the order the B legs nest
    #     around the corner of the barrier strip (15V_ISO, PWM_Q8, RLY, PWM_TRANS6, PWM_Q7; 5V_ISOL outermost, its via
    #     west of the strip curve). Pinch layers: In1 PWM_Q8 (south lane) + PWM_TRANS6, In2 RLY (south lane, it
    #     leaves first) + PWM_Q7, In3 15V_ISO, In4 5V_ISOL; at J24 the In1 pair turns up west of the pin column
    #     (PWM_TRANS6 first, to pin 5; PWM_Q8 outside it to pin 3).
    j24 = {n: xy(geo.pad(b, "J24", n).GetPosition()) for n in ("1", "3", "5", "6", "7")}
    # corridor lanes on B (y) and their transfer vias (x), inner to outer; every B leg is the grid router from the
    # source to the corridor entry (55.0, y), then straight west to its via. 5V_ISOL (outermost) dips south-west
    # past the other vias to its via west of the strip curve (In4 is free there, the ISOGND strip starts at y 52).
    lanes = {"15V_ISO": (51.65, 52.6), "PWM_Q8": (52.25, 51.4), "GPIO_BYPASS_RLY_ISO": (52.85, 50.2),
             "PWM_TRANS6": (53.45, 49.0), "PWM_Q7": (54.05, 47.8), "5V_ISOL": (54.75, None)}
    vias = {}
    for net, (y, x) in lanes.items():
        p = (x, y) if x is not None else (39.9, 50.3)
        v = cx.via_ok(net, *p)
        if v is None:
            say(f"west: transfer via of {net} at {p} NOT legal")
            continue
        cx.commit(v)
        vias[net] = p

    def blegs(net, w):
        y, x = lanes[net]
        tail = [(x, y)] if x is not None else [(43.0, y), (39.9, 50.3)]
        return [(B, w, EAST, (55.0, y)), (B, w, "straight", tail)]

    starts = {"15V_ISO": ("C156", "1", 0.3, (0, -1)), "PWM_Q8": ("U19", "11", SIG_W, (0, 1)),
              "GPIO_BYPASS_RLY_ISO": ("U19", "15", SIG_W, (0, 1)), "PWM_TRANS6": ("U20", "10", SIG_W, (0, 1)),
              "PWM_Q7": ("U20", "11", SIG_W, (0, 1)), "5V_ISOL": ("C157", "1", 0.3, (0, -1))}
    tails = {
        "15V_ISO": [(IN3, SUP_W, WEST, j24["6"]), (IN2, SUP_W, WEST, (10.27, 19.17))],
        "PWM_Q8": [(IN1, NECK_W, WEST, (16.0, 41.1)), (IN1, NECK_W, "straight", [(11.75, 41.1), (11.75, 46.07), j24["3"]])],
        "GPIO_BYPASS_RLY_ISO": [(IN2, NECK_W, WEST, (25.26, 40.66))],
        "PWM_TRANS6": [(IN1, NECK_W, WEST, (16.0, 41.45)), (IN1, NECK_W, "straight", [(12.2, 41.45), (12.2, 44.8), j24["5"]])],
        "PWM_Q7": [(IN2, NECK_W, WEST, (16.0, 41.45)), (IN2, NECK_W, "straight", [(12.2, 41.45), (12.2, 47.34), j24["1"]])],
        "5V_ISOL": [(IN4, SUP_W, WEST, j24["7"]), (IN4, SUP_W, FAR, xy(geo.pad(b, "U30", "1").GetPosition()))],
    }
    for net in lanes:
        if net not in vias:
            ok[net] = False
            continue
        ref, num, w0, pref = starts[net]
        s = end_via(cx, ref, num, w=w0, prefer=pref)
        if s is None:
            ok[net] = False
            continue
        w = SUP_W if net in ("15V_ISO", "5V_ISOL") else SIG_W
        go(net, s, blegs(net, w) + tails[net], f"{ref}-{num} -> path A")
    say("west: drawn " + ", ".join(n for n, v in ok.items() if v) + "; NOT drawn: " +
        (", ".join(n for n, v in ok.items() if not v) or "-"))
    b.Save(dst)


if __name__ == "__main__":
    main()
