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
from drawlib import IN1, IN2, IN3, IN4, B, SIG_W, say, end_via, chain, end_at_track  # noqa: E402

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

    def go(net, start, legs, what, walls=None):
        cx.pierce = pierce
        ok[net] = chain(cx, net, start, legs, what, walls=walls)

    # --- path A. Transfer vias in the corridor on a diagonal, south-east to north-west in the order the B legs nest
    #     around the corner of the barrier strip (15V_ISO, PWM_Q8, RLY, PWM_TRANS6, PWM_Q7; 5V_ISOL outermost, its via
    #     west of the strip curve). Pinch layers: In1 PWM_Q8 (south lane) + PWM_TRANS6, In2 RLY (south lane, it
    #     leaves first) + PWM_Q7, In3 15V_ISO, In4 5V_ISOL; at J24 the In1 pair turns up west of the pin column
    #     (PWM_TRANS6 first, to pin 5; PWM_Q8 outside it to pin 3).
    j24 = {n: xy(geo.pad(b, "J24", n).GetPosition()) for n in ("1", "3", "5", "6", "7")}
    # corridor lanes on B (y), inner to outer, and their transfer vias in one row at y 51.4 at the mouth of the
    # pinch (below the step-05 pair, east of its transition vias at x 40.4; In4 free there: the ISOGND strip starts
    # at y 52). Every B leg: the grid router from the source to the corridor entry (54 + 0.6 k, y), straight west to
    # the via's x and down to it; the lowest lane takes the eastmost via so that no descent crosses a lower lane.
    # Pinch layers: In1 PWM_Q7 (east lane, from the westmost via, so its leg runs straight down the strip edge) and
    # PWM_Q8 (west lane, passing north of that via); In2 the relay line, In3 15V_ISO, In4 PWM_TRANS6. 5V_ISOL is
    # left to the router (no B path to the corridor north of the others).
    lanes = {"15V_ISO": (52.0, 43.8), "PWM_Q8": (52.6, 43.15), "GPIO_BYPASS_RLY_ISO": (53.05, 42.5),
             "PWM_TRANS6": (53.5, 41.85), "PWM_Q7": (53.95, 41.2)}
    VY = 51.4
    vias = {}
    for net, (y, x) in lanes.items():
        v = cx.via_ok(net, x, VY)
        if v is None:
            say(f"west: transfer via of {net} at ({x}, {VY}) NOT legal")
            continue
        cx.commit(v)
        vias[net] = (x, VY)

    def blegs(net, w):
        y, x = lanes[net]
        k = list(lanes).index(net)
        return [(B, w, EAST, (54.0 + 0.6 * k, y)), (B, w, "straight", [(x, y), (x, VY)])]

    starts = {"15V_ISO": ("C156", "1", 0.3, (0, -1)), "PWM_Q8": ("U19", "11", SIG_W, (0, 1)),
              "GPIO_BYPASS_RLY_ISO": ("U19", "15", SIG_W, (0, 1)), "PWM_TRANS6": ("U20", "10", SIG_W, (0, 1)),
              "PWM_Q7": ("U20", "11", SIG_W, (0, 1))}
    holes = []
    e15 = end_at_track(cx, "15V_ISO", 10.27, 19.17, made=holes, pierce={"ISODC+"})   # the relay supply's old In2
    #                                                    end (under the ISO DC-link pours F / B), reached on In3
    # the two 0.15 mm lanes of In1 through the pinch, drawn straight (the grid cannot place two): centres at
    # x 38.87 (2.5 mm + from the J37 pads) and x 39.28 (0.125 mm from the barrier strip), y 46.8 .. 45.3
    LW, LE = [(38.87, 46.8), (38.87, 45.3)], [(39.28, 46.8), (39.28, 45.3)]

    def pinch(layer, lane):      # the mouth only (x >= 37.5): no detour round J37
        return [(layer, NECK_W, (37.5, 44.0, 46.0, 52.6), lane[0]), (layer, NECK_W, "straight", [lane[1]])]
    tails = {
        "15V_ISO": [(IN3, SUP_W, WEST, j24["6"]), (IN3, SUP_W, WEST, e15)],
        "PWM_Q7": pinch(IN1, LE) + [(IN1, NECK_W, WEST, (16.0, 41.1)),
                                    (IN1, NECK_W, WEST, j24["1"])],
        "PWM_Q8": pinch(IN1, LW) + [(IN1, NECK_W, WEST, (16.0, 41.45)),
                                    (IN1, NECK_W, "straight", [(12.2, 41.45), (12.2, 46.07), j24["3"]])],
        "GPIO_BYPASS_RLY_ISO": [(IN2, NECK_W, WEST, (25.26, 40.66))],
        "PWM_TRANS6": [(IN4, NECK_W, WEST, (16.0, 41.45)), (IN4, NECK_W, "straight", [(12.2, 41.45), (12.2, 44.8), j24["5"]])],
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
        w = SUP_W if net == "15V_ISO" else SIG_W
        # the corridor north of this lane is walled off while its leg is drawn: it comes in from the south-east
        go(net, s, blegs(net, w), f"{ref}-{num} -> corridor via", walls=[[(39.0, lanes[net][0] + 0.3, 60.0, 59.0)]])
    for net in ("PWM_Q7", "PWM_Q8", "GPIO_BYPASS_RLY_ISO", "PWM_TRANS6", "15V_ISO"):
        if ok.get(net) and not (net == "15V_ISO" and e15 is None):
            go(net, vias[net], tails[net], f"{net}: corridor via -> path A")
    cx.pierce = {"ISODC+"}
    say(f"west: {geo.hv_holes(cx, holes, 'west')} HV keep-outs at the 15V_ISO end via")
    say("west: drawn " + ", ".join(n for n, v in ok.items() if v) + "; NOT drawn: " +
        (", ".join(n for n, v in ok.items() if not v) or "-"))
    b.Save(dst)


if __name__ == "__main__":
    main()
