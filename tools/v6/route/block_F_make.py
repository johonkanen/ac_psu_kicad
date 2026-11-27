#!/usr/bin/env python3
"""Makes tools/v6/route/block_F_copper.csv from the drawn design below (kipy; development tool of block_F_chain.sh).

  kipy block_F_make.py BASE.kicad_pcb

Block F's copper is drawn, not routed: at 3227a58 every connection inside F is made already and the work is eight
crossing nets on inner layers that are empty in F (In1 / In3; In2 carries the kept v4 divider and sigma-delta runs).
BASE is the 3227a58 board; the script reads the pads the design touches from it (pad rows) and checks that every
kept / dead / cut item exists. IPC frame, mm, y up.
"""
import csv
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import block_F as BF  # noqa: E402

FIELDS = ["kind", "net", "layer", "x1", "y1", "x2", "y2", "w", "tag"]

# ports of the crossing nets that F adds (net -> (edge point, layer, neighbour)); the kept ones are in block_F.md
PORTS = {
    "MDATA": ((-2.0, -42.0), "In3.Cu", "A"),
    "ADCLK": ((-2.0, -44.0), "In2.Cu", "A"),
    "ISOGND": ((13.27, 38.0), "In1.Cu", "D2 (J24-9 straight north)"),
    "15V_ISO": ((16.4, 38.0), "In3.Cu", "D2 (D's In3 run at (16.4, 43) to J24-6)"),
    "Net-(U7B--)": ((26.0, 38.0), "In1.Cu", "D2 (column between J38 and J37)"),
    "Net-(U2-+)": ((26.6, 38.0), "In1.Cu", "D2 (column)"),
    "Net-(U2--)": ((27.2, 38.0), "In1.Cu", "D2 (column)"),
}

# kept copper the new copper starts from
NEED = [
    ("ISOGND", "In1.Cu", (-55.134, 19.169), (10.269, 19.169)),
    ("15V_ISO", "In2.Cu", (-55.134, 19.169), (10.269, 19.169)),
    ("Net-(U2--)", "In2.Cu", (-6.512, 27.372), (14.072, 27.372)),
    ("Net-(U2-+)", "In2.Cu", (-10.844, 29.481), (14.175, 29.481)),
    ("Net-(U7B--)", "In2.Cu", (17.389, 35.514), (5.414, 35.514)),
    ("ADCLK", "In2.Cu", (5.572, -26.528), (3.913, -28.187)),
    ("ADCLK", "In2.Cu", (3.913, -28.187), (3.913, -45.913)),
    ("GND", "In1.Cu", (-57.440, -40.600), (1.100, -40.600)),
    ("MDATA", "In3.Cu", (40.500, -22.000), (40.000, -22.000)),
    # pass-1 U7B-+ link to D2 (kept: it is what F would draw; its port is (2.85, 38) In1)
    ("Net-(U7B-+)", "In1.Cu", (2.850, 38.450), (2.850, 37.300)),
]
NEEDVIA = [("Net-(U7B-+)", (2.870, 37.300))]
# kept v4 copper that ends at no pad: the ISOGND / 15V_ISO diagonals to the old ISO card place. ADCLK's tail into
# block C (down x 3.913, to the IPC via at (7.884, -47.485)) stays: until E joins R22-2 to the kept run, that via is
# what gives the pad-less ADCLK group its net in assign_nets --check; the F branch to A tees off the tail at y -43.5
DEAD = [
    ("ISOGND", "In1.Cu", (10.269, 19.169), (23.000, 31.900)),
    ("15V_ISO", "In2.Cu", (10.269, 19.169), (23.000, 31.900)),
]
DEADVIA = []
CUT = []

# new copper: (net, layer, width, polyline) and vias (net, point, diameter, drill)
TRACKS = [
    # AFE sigma-delta pair to A: MDATA on In3 down E's edge and west along y -42 (clear of the analog In2 lanes
    # R2 / R5 / U1A at y -18.9 .. -24.7 and of C11's DC+ pad); ADCLK tees off its kept In2 run at y -43.5, west along y -44
    ("MDATA", "In3.Cu", 0.2, [(40.0, -22.0), (39.0, -23.0), (39.0, -41.0), (38.0, -42.0), (-2.0, -42.0)]),
    ("ADCLK", "In2.Cu", 0.152, [(3.913, -43.5), (3.413, -44.0), (-2.0, -44.0)]),
    # ISO card supplies to J24 (D2): ISOGND on In1 under J24-9, 15V_ISO on In3 (In2 is crossed by the U2 taps)
    ("ISOGND", "In1.Cu", 0.508, [(10.269, 19.169), (12.6, 21.5), (12.6, 37.33), (13.27, 38.0)]),
    ("15V_ISO", "In2.Cu", 0.508, [(10.269, 19.169), (13.5, 19.169)]),
    ("15V_ISO", "In3.Cu", 0.508, [(13.5, 19.169), (16.4, 22.069), (16.4, 38.0)]),
    # divider taps to the D2 column between J38 and J37: In1 (F.Cu above is ISOPGND east of x 23.6; In2 is cut by
    # the GPIO_BYPASS_RLY_ISO run), the northern tap westmost so the three do not cross
    ("Net-(U7B--)", "In1.Cu", 0.2, [(17.389, 35.514), (25.5, 35.514), (26.0, 36.014), (26.0, 38.0)]),
    ("Net-(U2-+)", "In1.Cu", 0.2, [(14.175, 29.481), (26.1, 29.481), (26.6, 29.981), (26.6, 38.0)]),
    ("Net-(U2--)", "In1.Cu", 0.2, [(14.072, 27.372), (26.7, 27.372), (27.2, 27.872), (27.2, 38.0)]),
    # C148-2 (GND, on the F / C edge) to A's GND In1 run, which ends in F
    ("GND", "In1.Cu", 0.5, [(1.1, -40.6), (2.77, -42.27), (2.77, -44.9)]),
    ("GND", "F.Cu", 0.5, [(2.77, -44.9), (2.77, -46.0)]),
]
VIAS = [
    ("15V_ISO", (13.5, 19.169), 0.6, 0.3),
    ("Net-(U7B--)", (17.389, 35.514), 0.4572, 0.3),
    ("Net-(U2-+)", (14.175, 29.481), 0.4572, 0.3),
    ("Net-(U2--)", (14.072, 27.372), 0.4572, 0.3),
    ("GND", (2.77, -44.9), 0.6, 0.3),
]
# pads the new copper ends on or whose kept runs it extends (the ends the ports serve)
PADS = ["C148-2", "R82-1", "R85-1", "R68-1", "R67-1", "J24-9", "J24-6", "C11-1", "C11-2"]


def f6(v):
    return f"{v:.6f}"


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    out = []
    for tag in PADS:
        ref, num = tag.rsplit("-", 1)
        p = next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
        x, y = BF.xy(p.GetPosition())
        out.append(dict(kind="pad", net=p.GetNetname(), x1=f6(x), y1=f6(y), tag=tag))
    for kind, lst in (("needtrack", NEED), ("deadtrack", DEAD)):
        for n, L, a, c in lst:
            out.append(dict(kind=kind, net=n, layer=L, x1=f6(a[0]), y1=f6(a[1]), x2=f6(c[0]), y2=f6(c[1])))
    for kind, lst in (("needvia", NEEDVIA), ("deadvia", DEADVIA)):
        for n, p in lst:
            out.append(dict(kind=kind, net=n, x1=f6(p[0]), y1=f6(p[1])))
    for n, L, (oa, oc), (a, c) in CUT:
        out.append(dict(kind="cuttrack", net=n, layer=L, x1=f6(a[0]), y1=f6(a[1]), x2=f6(c[0]), y2=f6(c[1]),
                        tag=f"{f6(oa[0])} {f6(oa[1])} {f6(oc[0])} {f6(oc[1])}"))
    for n, L, w, pts in TRACKS:
        for a, c in zip(pts, pts[1:]):
            out.append(dict(kind="track", net=n, layer=L, x1=f6(a[0]), y1=f6(a[1]), x2=f6(c[0]), y2=f6(c[1]),
                            w=f6(w)))
    for n, p, d, dr in VIAS:
        out.append(dict(kind="via", net=n, x1=f6(p[0]), y1=f6(p[1]), x2=f6(dr), w=f6(d)))
    with open(BF.CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    import collections
    print("block_F_make:", dict(collections.Counter(r["kind"] for r in out)))
    BF._ROWS.clear()
    todo, missing = BF.find_items(b)
    bad = [r for r in BF.rows("track") + BF.rows("via") if not BF.fenced(r)]
    if missing or bad:
        sys.exit(f"block_F_make: missing {missing}; outside F {[BF.fmt(r) for r in bad]}")
    print("block_F_make: every kept / dead / cut item found, every new item inside F or on its edge")


if __name__ == "__main__":
    main()
