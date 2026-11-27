#!/usr/bin/env python3
"""Makes tools/v6/route/block_A_copper.csv from the drawn design below (kipy; development tool of block_A_chain.sh).

  kipy block_A_make.py BASE_FILLED.kicad_pcb [OUT.kicad_pcb]

BASE_FILLED is the d639e0e board refilled (geo.Ctx reads the pour fills). Every piece is drawn by script and tested
by geo.Ctx: 2.5 mm between a high-voltage net (hv.py; here also the switch node SW_AFE_1) and any other net on a
layer, 1.0 mm between two high-voltage nets, the domain gaps, pours and keep-outs. The side-1 nets of U5 (SHUNT1,
SHUNT2, U5 VIN+ / VIN-, SDM_RAW_VOLTAGE, D8-K) count as one group among themselves (their Proteus spacing, as
09_sense_replay.py). New pieces may enter the pours in PIERCE (FILTER_INPUT F.Cu pour 24, LEMOUT B.Cu pour 10, JEE,
AC_IN_1, PGND); those pours are then cut back by fill keep-outs around every object in A that the fill comes closer
to than the rule (pads and old copper included, not around objects that a pour of their own net touches).

What block A adds (block_A.md):
  - AFE_CHOKE1: FILTER_OUT1 (choke lead) to R48 pin 4 by zones on F.Cu / In1 / In2 and a via field north of the pad
    (12 vias 0.6 / 0.3) with a B.Cu zone over pin 4; the old 2 mm B.Cu stub between R48 pins 3 / 4 is deleted.
  - U5 VIN-: the replayed loop from C91-2 over R48 (0.5 mm from pin 4) is deleted; C91-2 joins VIN- by two vias
    and In1. SHUNT1: R58-2, boxed in by that loop before, goes straight to C52-2 on B.Cu.
  - GND / GPIO_BYPASS_RLY In1 (F's ports -40.6 / -39.3): their kept v4 runs passed 1.0 mm from CM1 pin 3 and
    1.8 mm from C21 pin 1; redrawn from the end of their first diagonals to x -20.
  - U5 side 2: MDAT to R55, GND to C64 / U29-2 on B.Cu; vias under the U5 body for VCC (In4) and ADCLK (In2);
    MDATA from R55 on In3; GND (In1) and 5V (In4) from the U29 pins past C160 to block C.
  - 15V: the relay group's In2 run (dead v4 copper that cut the FILTER_IN1 link zone on In2) deleted, a new In4 run
    from its via to block C.
  - Ports on x = -2: F's MDATA (-42, In3) and ADCLK (-44, In2) met; to C: 15V -48.6 In4, GND -49.86 In1,
    VCC -52.4 In4, 5V -53.6 In4.
"""
import collections
import csv
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo  # noqa: E402
import drawlib as D  # noqa: E402
from geo import F, T, xy  # noqa: E402
from hv import is_hv as _is_hv  # noqa: E402

FC, IN1, IN2, IN3, IN4, BC = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu
FIELDS = ["kind", "net", "layer", "x1", "y1", "x2", "y2", "w", "tag"]
CSV = os.path.join(HERE, "block_A_copper.csv")

FILTER_INPUT, LEMOUT = "/01 afe/FILTER_INPUT", "/01 afe/LEMOUT"
GROUP = {"SHUNT1", "SHUNT2", "Net-(U5-VIN+)", "Net-(U5-VIN-)", "SDM_RAW_VOLTAGE", "Net-(D8-K)"}


def is_hv(n):
    return bool(n) and (_is_hv(n) or n.split("/")[-1] == "SW_AFE_1")


_rule0 = geo.Ctx.rule


def rule(net, onet, lc=0.0):
    if net and onet and net.split("/")[-1] in GROUP and onet.split("/")[-1] in GROUP:
        return max(geo.CLR, lc)
    return _rule0(net, onet, lc)


geo.is_hv = is_hv
geo.Ctx.rule = staticmethod(rule)

# ---- the design ------------------------------------------------------------------------------------------------
PORTS = {   # crossing nets: edge point, layer, neighbour
    "MDATA": ((-2.0, -42.0), "In3.Cu", "F (its run west along y -42 from E)"),
    "ADCLK": ((-2.0, -44.0), "In2.Cu", "F (its tee off the kept v4 run)"),
    "15V": ((-2.0, -48.6), "In4.Cu", "C: J21-6 (4.0, -49.86), from the north side of the pin row"),
    "GND": ((-2.0, -49.86), "In1.Cu", "C: J21-2 (1.46, -49.86), straight east"),
    "VCC": ((-2.0, -52.4), "In4.Cu", "C: its VCC copper at (2.6, -52.2) B.Cu"),
    "5V": ((-2.0, -53.6), "In4.Cu", "C: J21-7 (5.27, -51.13), from the south side of the pin row"),
}
# kept copper the new copper joins (must exist)
NEED = [
    ("ADCLK", "In2.Cu", (3.413, -44.0), (-2.0, -44.0)),
    ("MDATA", "In3.Cu", (38.0, -42.0), (-2.0, -42.0)),
    ("SHUNT1", "B.Cu", (-33.55, -66.5), (-33.55, -64.45)),
    ("15V", "B.Cu", (-116.372, -69.8), (-117.1, -69.8)),
    # the first diagonals of the v4 In1 runs out of the relay-area vias stay (the channel past R20-3 is too narrow
    # for two new runs with the router's margin)
    ("GND", "In1.Cu", (-103.412, -65.352), (-96.46, -58.4)),
    ("GPIO_BYPASS_RLY", "In1.Cu", (-102.855, -63.795), (-96.66, -57.6)),
]
NEEDVIA = [("15V", (-116.372, -69.799)), ("GND", (-103.412, -65.471)), ("GPIO_BYPASS_RLY", (-103.215, -63.795))]
NEEDZONE = ["v6 SW_AFE_1 F.Cu", "v6 SW_AFE_1 In1.Cu", "v6 FILTER_IN1 link In1.Cu", "v6 FILTER_IN1 link In2.Cu"]
# dead copper deleted: the 15V In2 run east of its via (cuts the FILTER_IN1 link zone on In2, ends at no pad) and
# the AFE_CHOKE1 B.Cu stub between R48 pins 3 and 4 (0.0 mm from the LEMOUT pin)
DEAD_NETS = {"15V": ("In2.Cu", (-118.0, -82.0, -54.0, -68.0)), "AFE_CHOKE1": ("B.Cu", (-39.0, -61.0, -35.0, -56.0))}
# explicit dead pieces (net, layer, ends):
#  - the replayed U5 VIN- loop from C91-2 over the top of R48 (0.5 mm from the AFE_CHOKE1 pin 4, between pins 4 / 2)
#    and down to R58-1: it boxed R58-2 (SHUNT1) in; C91-2 joins VIN- by vias and In1 instead
#  - the west parts of the kept v4 In1 runs of GND / GPIO_BYPASS_RLY (F's ports -40.6 / -39.3): 1.0 mm from the CM1
#    pin 3 (CMFILT1) and 1.8 mm from the C21 pin 1 (LEMOUT); drawn again with the 2.5 mm rule up to x -20
DEAD = [("Net-(U5-VIN-)", "B.Cu", a, c) for a, c in [
            ((-40.2, -66.25), (-40.2, -63.85)), ((-40.2, -63.85), (-40.0, -63.65)), ((-40.0, -63.65), (-36.9, -63.65)),
            ((-36.9, -63.65), (-33.55, -67.0)), ((-33.55, -67.0), (-33.55, -67.1)), ((-33.55, -67.1), (-33.75, -67.3)),
            ((-33.75, -67.3), (-33.8, -67.3)), ((-33.8, -67.3), (-35.5, -69.0))]] + \
       [("GND", "In1.Cu", a, c) for a, c in [
            ((-96.46, -58.4), (-95.4, -58.4)), ((-95.4, -58.4), (-75.24, -58.4)), ((-75.24, -58.4), (-57.44, -40.6))]] + \
       [("GPIO_BYPASS_RLY", "In1.Cu", a, c) for a, c in [
            ((-96.66, -57.6), (-95.6, -57.6)), ((-95.6, -57.6), (-75.974, -57.6)), ((-75.974, -57.6), (-57.674, -39.3))]]
# kept runs shortened (net, layer, old ends, new ends): their west ends move to x -20, where the new runs join
CUT = [("GND", "In1.Cu", ((-57.44, -40.6), (1.1, -40.6)), ((-20.0, -40.6), (1.1, -40.6))),
       ("GPIO_BYPASS_RLY", "In1.Cu", ((-57.674, -39.3), (28.26, -39.3)), ((-20.0, -39.3), (28.26, -39.3)))]

# pads the new copper ends on (checked by the replay)
PADS = ["U5-5", "U5-6", "U5-7", "U5-8", "R55-1", "R55-2", "C64-1", "C64-2", "U29-1", "U29-2", "U29-4", "U29-6",
        "C160-1", "C160-2", "R58-2", "R58-1", "C52-2", "C91-2", "R48-1", "R48-3", "R48-4", "FILTER_OUT1-1", "R20-6",
        "D10-C", "R90-1", "R89-2"]
# pours that new pieces may enter; each is cut back by fill keep-outs around every object in A that needs it
PIERCE = {FILTER_INPUT, LEMOUT, "/01 afe/JEE", "AC_IN_1", "PGND"}

SIG, PWR = 0.2, 0.3


def poly_zone(b, net, layer, pts, name, prio, clr):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNetCode(b.GetNetcodeFromNetname(net))
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts:
        ch.Append(F(x), F(-y))
    ch.SetClosed(True)
    z.Outline().AddOutline(ch)
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)
    z.SetMinThickness(F(0.2))
    z.SetLocalClearance(F(clr))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    b.Add(z)
    z.thisown = False
    return z


FAIL_BOARD = []


def need(cond, msg):
    if not cond:
        D.say("block_A_make: FAILED: " + msg)
        if FAIL_BOARD and len(sys.argv) > 2:
            pcbnew.SaveBoard(sys.argv[2] + ".fail.kicad_pcb", FAIL_BOARD[0])
        sys.exit(1)


def main():
    src = sys.argv[1]
    out_board = sys.argv[2] if len(sys.argv) > 2 else None
    b = pcbnew.LoadBoard(src)
    FAIL_BOARD.append(b)
    rows = []

    # -- dead copper -------------------------------------------------------------------------------------------------
    dead = []
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if n in DEAD_NETS and t.Type() != pcbnew.PCB_VIA_T:
            L, box = DEAD_NETS[n]
            a, c = xy(t.GetStart()), xy(t.GetEnd())
            if b.GetLayerName(t.GetLayer()) == L and all(box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
                                                          for p in (a, c)):
                dead.append((n, L, a, c, t))
    def r3(p):
        return (round(p[0], 3), round(p[1], 3))
    want = {(n, L) + tuple(sorted([r3(a), r3(c)])) for n, L, a, c in DEAD}
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            continue
        a, c = xy(t.GetStart()), xy(t.GetEnd())
        k = (t.GetNetname(), b.GetLayerName(t.GetLayer())) + tuple(sorted([r3(a), r3(c)]))
        if k in want:
            want.discard(k)
            dead.append((k[0], k[1], a, c, t))
    need(not want, f"explicit dead pieces not found: {sorted(want)}")
    for n, L, (oa, oc), (na, nc) in CUT:
        k = (n, L) + tuple(sorted([r3(oa), r3(oc)]))
        hit = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and (t.GetNetname(), b.GetLayerName(
            t.GetLayer())) + tuple(sorted([r3(xy(t.GetStart())), r3(xy(t.GetEnd()))])) == k]
        need(len(hit) == 1, f"cut track {k} not found")
        hit[0].SetStart(geo.P(*na))
        hit[0].SetEnd(geo.P(*nc))
        rows.append(dict(kind="cuttrack", net=n, layer=L, x1=na[0], y1=na[1], x2=nc[0], y2=nc[1],
                         tag=f"{oa[0]:.6f} {oa[1]:.6f} {oc[0]:.6f} {oc[1]:.6f}"))
    D.say(f"dead copper: {collections.Counter(d[0] for d in dead)}; {len(CUT)} kept runs shortened")
    for n, L, a, c, t in dead:
        rows.append(dict(kind="deadtrack", net=n, layer=L, x1=a[0], y1=a[1], x2=c[0], y2=c[1]))
        b.Delete(t)

    cx = geo.Ctx(b)
    cx.pierce = set(PIERCE)
    made = []          # new tracks / vias (for the keep-outs and the CSV)

    def via(net, x, y, d=geo.VIA, dr=geo.DRILL):
        geo_v, geo_d = geo.VIA, geo.DRILL
        geo.VIA, geo.DRILL = d, dr
        try:
            why = []
            v = cx.via_ok(net, x, y, why=why)
        finally:
            geo.VIA, geo.DRILL = geo_v, geo_d
        need(v is not None, f"via {net} at ({x}, {y}): {why}")
        cx.commit(v)
        made.append(v)
        return (x, y)

    def line(net, layer, pts, w, what=""):
        err = cx.poly(net, layer, pts, w)
        need(err is None, f"{net} {what} on {b.GetLayerName(layer)}: {err}")
        made.extend(cx.last)
        D.say(f"{net} {what}: {geo.plen(pts):.1f} mm on {b.GetLayerName(layer)}")

    def route(net, layer, a, c, w, box, what="", walls=(), step=None, port=False):
        if port:                    # the last 4 mm straight onto the port (not along the block edge)
            route(net, layer, a, (c[0] - 4.0, c[1]), w, box, what, walls, step)
            line(net, layer, [(c[0] - 4.0, c[1]), c], w, what + ": straight onto the port")
            return
        mine = []
        pts = D.run(cx, net, layer, a, c, w, box, made=mine, what=what, walls=walls, step=step)
        need(pts is not None, f"{net} {what}: no route on {b.GetLayerName(layer)}")
        D.say("    " + " ".join(f"({x:.2f},{y:.2f})" for x, y in pts))
        made.extend(mine)
        return pts

    pad = lambda r, n: geo.pad_xy(b, r, n)  # noqa: E731

    # -- AFE_CHOKE1: via field north of R48-4, zones F / In1 / In2 to FILTER_OUT1, B.Cu zone over pin 4 ------------
    ach = "AFE_CHOKE1"
    vias_ach = []
    for vy in (-55.7, -56.7):
        for vx in (-39.6, -38.6, -37.6, -36.6):
            vias_ach.append(via(ach, vx, vy, 0.6, 0.3))
    for vx in (-39.6, -38.6, -37.6, -36.6):
        vias_ach.append(via(ach, vx, -54.7, 0.6, 0.3))
    # tracks tie the field to R48-4 (B.Cu) and to FILTER_OUT1 (In1): a via that touches only zones takes the net of
    # the pour it stands in at the refill, so every via gets a track to a pad of its own net
    for vx in (-39.6, -38.6, -37.6):
        line(ach, BC, [(vx, -54.7), (vx, -58.6)], 1.0, f"field column x {vx} into R48-4")
    for vy in (-54.7, -55.7, -56.7):
        line(ach, BC, [(-39.6, vy), (-36.6, vy)], 1.0, f"field row y {vy}")
    line(ach, IN1, [(-36.6, -54.7), (-33.0, -52.0)], 1.0, "field to FILTER_OUT1")
    # copper of the link: the FILTER_OUT1 pad (x -35.5 .. -30.5, y -54.5 .. -49.5) and the field (x -40.2 .. -36.0,
    # y -57.3 .. -54.1); 2.5 mm keep-away from other nets comes from the zone clearance
    link = [(-40.4, -57.5), (-40.4, -54.0), (-36.6, -49.2), (-30.2, -49.2), (-30.2, -54.8), (-35.6, -54.8),
            (-35.8, -57.5)]
    zones = [("F.Cu", link, 46, 1.0), ("In1.Cu", link, 46, 2.5), ("In2.Cu", link, 46, 2.5),
             ("B.Cu", [(-40.4, -63.2), (-40.4, -54.0), (-36.0, -54.0), (-36.0, -63.2)], 16, 1.0)]
    for L, pts, prio, clr in zones:
        rows.append(dict(kind="zone", net=ach, layer=L, x1=prio, y1=clr, x2=0.2,
                         tag=f"v6 AFE_CHOKE1 link {L}|" + ";".join(f"{x:.3f} {y:.3f}" for x, y in pts)))
        poly_zone(b, ach, b.GetLayerID(L), pts, f"v6 AFE_CHOKE1 link {L}", prio, clr)
    D.say(f"AFE_CHOKE1: {len(vias_ach)} vias, zones on {', '.join(z[0] for z in zones)}")
    # the zones are not filled here: wall their outlines (+2.5 mm) off for the other nets' grid runs on In1 / In2
    ach_walls = [([(-40.4, -57.5), (-40.4, -54.0), (-36.6, -49.2), (-30.2, -49.2), (-30.2, -54.8), (-35.6, -54.8),
                   (-35.8, -57.5), (-40.4, -57.5)], 2.5 + 0.3)]

    # -- SHUNT1: R58-2 by two vias and In1 ------------------------------------------------------------------------
    # with the VIN- loop gone, R58-2 reaches C52-2 straight on B.Cu
    line("SHUNT1", BC, [pad("R58", "2"), (-33.3, -68.0)], SIG, "R58-2 to C52-2")
    # VIN-: C91-2 to the R58-1 / C52-1 run by two vias and In1
    va = via("Net-(U5-VIN-)", -41.0, -66.25)
    line("Net-(U5-VIN-)", BC, [pad("C91", "2"), va], SIG, "C91-2 to its via")
    vb = via("Net-(U5-VIN-)", -35.7, -68.988)       # on the R58-1 / C52-1 run
    route("Net-(U5-VIN-)", IN1, va, vb, SIG, (-42.0, -70.0, -32.0, -62.0), "C91-2 via to the R58-1 via")

    # -- U5 side 2 on B.Cu ------------------------------------------------------------------------------------------
    u5 = {n: pad("U5", n) for n in "5678"}
    line("Net-(U5-MDAT)", BC, [u5["6"], (u5["6"][0], -79.3), (-30.3, -79.3), (-29.3, -78.3), (-29.3, -76.6),
                               (-28.7, -76.0), pad("R55", "1")], SIG, "U5-6 to R55-1")
    c64g, c64v, u29g, u29p = pad("C64", "1"), pad("C64", "2"), pad("U29", "2"), pad("U29", "1")
    line("GND", BC, [u5["5"], (u5["5"][0], -82.3), (c64g[0], -82.3), c64g], PWR, "U5-5 to C64-1")
    line("GND", BC, [(c64g[0], -82.3), (-25.3, -82.3), (-25.3, u29g[1] - 0.6), (-24.7, u29g[1]), u29g], PWR,
         "C64-1 to U29-2")
    vv = via("VCC", -26.55, -77.35)
    line("VCC", BC, [c64v, (-27.0, -77.9), vv], PWR, "C64-2 to its via")
    vu8 = via("VCC", u5["8"][0], -78.55)
    line("VCC", BC, [u5["8"], vu8], PWR, "U5-8 to its via")
    vck = via("ADCLK", u5["7"][0], -77.6)
    line("ADCLK", BC, [u5["7"], vck], SIG, "U5-7 to its via")
    vmd = via("MDATA", -26.3, -76.0)
    line("MDATA", BC, [pad("R55", "2"), vmd], SIG, "R55-2 to its via")
    # C160: vias beside its pads (5V north of pin 1, GND south of pin 2)
    c1, c2 = pad("C160", "1"), pad("C160", "2")
    v5c = via("5V", c1[0], -64.85)
    line("5V", BC, [c1, v5c], PWR, "C160-1 to its via")
    vgc = via("GND", c2[0], -67.15)
    line("GND", BC, [c2, vgc], PWR, "C160-2 to its via")

    # -- inner runs ---------------------------------------------------------------------------------------------
    # VCC In4: U5-8 via -> C64-2 via -> north west of U29 -> port
    line("VCC", IN4, [vu8, (-38.0, -79.4), (-29.0, -79.4), vv], PWR, "U5-8 via to C64-2 via")
    # west of the U29 column (the gap between U29-4 and J5 is left to 5V / GND), then north-east to the port
    route("VCC", IN4, vv, (-27.6, -62.0), PWR, (-31.0, -80.0, -24.0, -58.0), "C64-2 via, west of U29")
    route("VCC", IN4, (-27.6, -62.0), PORTS["VCC"][0], PWR, (-31.0, -64.0, -1.9, -45.0), "on to the C port",
          walls=ach_walls, port=True)
    # 5V In4: U29-1 -> past J5 / U29-4 -> C160-1 via -> port
    route("5V", IN4, u29p, v5c, PWR, (-25.0, -80.0, -12.0, -60.0), "U29-1 to the C160 via")
    route("5V", IN4, v5c, PORTS["5V"][0], PWR, (-25.0, -66.0, -1.9, -45.0), "C160 via to the C port", port=True)
    # GND In1: U29-2 -> C160-2 via -> port
    route("GND", IN1, u29g, vgc, PWR, (-25.0, -80.0, -12.0, -60.0), "U29-2 to the C160 via")
    route("GND", IN1, vgc, PORTS["GND"][0], PWR, (-25.0, -68.0, -1.9, -45.0), "C160 via to the C port",
          walls=ach_walls, port=True)
    # ADCLK In2, MDATA In3 to F's ports
    route("ADCLK", IN2, vck, PORTS["ADCLK"][0], SIG, (-40.0, -81.0, -1.9, -40.0), "U5 via to the F port",
          walls=ach_walls, port=True)
    route("MDATA", IN3, vmd, PORTS["MDATA"][0], SIG, (-40.0, -81.0, -1.9, -40.0), "R55 via to the F port", port=True)
    # 15V In4: relay group via -> port (north of the sense nets)
    route("15V", IN4, (-116.372, -69.799), PORTS["15V"][0], 0.4, (-121.0, -83.0, -1.9, -40.0),
          "relay via to the C port", step=0.2, port=True)

    # GPIO_BYPASS_RLY / GND In1 from the relay-area vias to their kept runs at x -20 (F's ports -39.3 / -40.6)
    # from the ends of the kept first diagonals: GND first, past C21 pin 1 with 2.5 mm, then GPIO_BYPASS_RLY
    # north-west of it, lifted to y -39.2 past C21
    route("GND", IN1, (-96.46, -58.4), (-48.0, -40.6), 0.762, (-100.0, -66.0, -40.0, -36.0),
          "kept diagonal to y -40.6 west of C21", step=0.1)
    line("GND", IN1, [(-48.0, -40.6), (-46.5, -39.85), (-40.1, -39.85), (-39.35, -40.6), (-20.0, -40.6)], 0.762,
         "past C21 pin 1 (2.5 mm) to the kept run")
    route("GPIO_BYPASS_RLY", IN1, (-96.66, -57.6), (-50.0, -39.2), 0.152, (-100.0, -66.0, -45.0, -36.0),
          "kept diagonal to y -39.2 west of C21", step=0.1)
    line("GPIO_BYPASS_RLY", IN1, [(-50.0, -39.2), (-38.0, -39.2), (-37.9, -39.3), (-20.0, -39.3)], 0.152,
         "past C21 to the kept run")

    # -- fill keep-outs: the HV pours FILTER_INPUT (F.Cu) / LEMOUT (B.Cu) cut back from every object that needs it --
    from blocks import block_of
    objs = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if block_of(*xy(p.GetPosition())) == "A":
                objs.append(p)
    for t in b.GetTracks():
        q = t.GetPosition() if t.Type() == pcbnew.PCB_VIA_T else t.GetStart()
        if block_of(*xy(q)) == "A":
            objs.append(t)
    keep = {}
    for L in (FC, BC):
        ps = pcbnew.SHAPE_POLY_SET()
        for o in objs:
            if not o.IsOnLayer(L):
                continue
            n = o.GetNetname()
            if n == "AFE_CHOKE1" or not n:   # inside its own zones, which keep the pours 1.0 mm away
                continue
            # a keep-out stops every fill, its own net's too: none around an object that a pour of its own net on
            # this layer touches (it would lose that connection; e.g. C79-1 in the DC+ pour)
            shp = o.GetEffectiveShape(L)
            if any(zn == n and fill.OutlineCount() and fill.Collide(shp, F(0.3)) for zn, fill, _, _ in cx.zones[L]):
                continue
            for znet, fill, zb, zc in cx.zones[L]:
                if znet not in cx.pierce or znet == n or not fill.OutlineCount():
                    continue
                r = rule(n, znet)
                if r <= zc + 1e-6:
                    continue
                if not fill.Collide(shp, F(r - 0.01)):     # the fill is closer than the rule
                    continue
                o.TransformShapeToPolygon(ps, L, F(r + 0.08), F(0.01), pcbnew.ERROR_OUTSIDE)
        ps.Simplify()
        keep[L] = ps
    nk = 0
    for L, ps in keep.items():
        for k in range(ps.OutlineCount()):
            ol = ps.Outline(k)
            pts = [(round(T(ol.CPoint(i).x), 3), round(-T(ol.CPoint(i).y), 3)) for i in range(ol.PointCount())]
            name = f"v6 block A HV keep-out {b.GetLayerName(L)} {k + 1}"
            rows.append(dict(kind="keepout", layer=b.GetLayerName(L),
                             tag=name + "|" + ";".join(f"{x:.3f} {y:.3f}" for x, y in pts)))
            z = pcbnew.ZONE(b)
            z.SetIsRuleArea(True)
            z.SetLayer(L)
            z.SetDoNotAllowZoneFills(True)
            z.SetDoNotAllowTracks(False)
            z.SetDoNotAllowVias(False)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(False)
            ch = pcbnew.SHAPE_LINE_CHAIN()
            for x, y in pts:
                ch.Append(F(x), F(-y))
            ch.SetClosed(True)
            z.Outline().AddOutline(ch)
            z.SetZoneName(name)
            b.Add(z)
            z.thisown = False
            nk += 1
    D.say(f"fill keep-outs: {nk} ({', '.join(f'{b.GetLayerName(L)} {ps.OutlineCount()}' for L, ps in keep.items())})")

    # -- CSV ------------------------------------------------------------------------------------------------------
    pre = []
    for tag in PADS:
        ref, num = tag.rsplit("-", 1)
        p = geo.pad(b, ref, num)
        x, y = xy(p.GetPosition())
        pre.append(dict(kind="pad", net=p.GetNetname(), x1=x, y1=y, tag=tag))
    for n, L, a, c in NEED:
        pre.append(dict(kind="needtrack", net=n, layer=L, x1=a[0], y1=a[1], x2=c[0], y2=c[1]))
    for n, p in NEEDVIA:
        pre.append(dict(kind="needvia", net=n, x1=p[0], y1=p[1]))
    for name in NEEDZONE:
        pre.append(dict(kind="needzone", tag=name))
    for o in made:
        if o.Type() == pcbnew.PCB_VIA_T:
            x, y = xy(o.GetPosition())
            rows.append(dict(kind="via", net=o.GetNetname(), x1=x, y1=y, x2=T(o.GetDrillValue()),
                             w=T(o.GetWidth(FC))))
        else:
            a, c = xy(o.GetStart()), xy(o.GetEnd())
            rows.append(dict(kind="track", net=o.GetNetname(), layer=b.GetLayerName(o.GetLayer()), x1=a[0],
                             y1=a[1], x2=c[0], y2=c[1], w=T(o.GetWidth())))
    order = {"pad": 0, "needtrack": 1, "needvia": 2, "needzone": 3, "deadtrack": 4, "cuttrack": 4.5, "track": 5, "via": 6,
             "zone": 7, "keepout": 8}
    allr = sorted(pre + rows, key=lambda r: order[r["kind"]])

    def f6(v):
        return f"{v:.6f}" if isinstance(v, float) else ("" if v is None else str(v))
    with open(CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for r in allr:
            w.writerow({k: f6(r.get(k)) for k in FIELDS})
    D.say(f"block_A_make: {dict(collections.Counter(r['kind'] for r in allr))} -> {CSV}")
    if out_board:
        pcbnew.SaveBoard(out_board, b)
        D.say(f"block_A_make: dev board {out_board}")


if __name__ == "__main__":
    main()
