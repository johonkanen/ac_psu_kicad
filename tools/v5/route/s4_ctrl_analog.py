#!/usr/bin/env python3
"""Routing stage 4: CTRL analog chain at J11 (routing list group 5, without the plane vias of stage 7).

  python3 tools/v5/route/s4_ctrl_analog.py EXTRACT.json OUT.json [earlier ROUTES.json ...]
  python3 tools/v5/route/s4_ctrl_analog.py EXTRACT.json OUT.json [ROUTES ...] --search N [--seed S]

AMC1311 outputs (N / P) to the difference amplifiers U25 / U26, the amplifier nodes, the three outputs to the
filters at J11, the LDO U27 (5V_CTRL_A from J14, CTRL_NR) and the spare amplifier.
The resistor block R116..R127 (bottom side) has 0.75 mm between its pad rows: one 0.152 mm track, no via.
A maze router that takes one connection at a time closes such a block for itself, so the order matters:
--search tries N random orders (seeded) and prints the best one; ORDER below is the order that was kept.
"""
import random
import sys

import router

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}
if "--search" in opt:
    args = [a for a in args if a not in (opt["--search"], opt.get("--seed"))]
r = router.Router(args[0], log=open(args[1] + ".log", "w"))
for p in args[2:]:
    r.load_routes(p)
ALL = ("B.Cu", "In3.Cu", "F.Cu")
CA = (44.0, 20.5, 96.0, 33.2)
W = 0.152

T = {}
for ch, (u22n, u22p, rn, rp, rm, rpl, um, upl, uo) in {
        "1": ("U22-6", "U22-7", "R116", "R118", "R117", "R119", "U25-2", "U25-3", "U25-1"),
        "2": ("U23-6", "U23-7", "R120", "R122", "R121", "R123", "U25-6", "U25-5", "U25-7"),
        "3": ("U24-6", "U24-7", "R124", "R126", "R125", "R127", "U26-2", "U26-3", "U26-1")}.items():
    T[f"N{ch}"] = (f"ISOADA{ch}_N", u22n, f"{rn}-1")
    T[f"P{ch}"] = (f"ISOADA{ch}_P", u22p, f"{rp}-1")
    T[f"Ma{ch}"] = (f"ISOADA{ch}_M", f"{rn}-2", f"{rm}-1")
    T[f"Mb{ch}"] = (f"ISOADA{ch}_M", um, f"{rm}-1")
    T[f"La{ch}"] = (f"ISOADA{ch}_PL", f"{rp}-2", f"{rpl}-1")
    T[f"Lb{ch}"] = (f"ISOADA{ch}_PL", upl, f"{rpl}-1")
    T[f"O{ch}"] = (f"ISOADA{ch}_OUT", uo, f"{rm}-2")
T["SP"] = ("OPA_SPARE", "U26-7", "U26-6")
FILTER = {}        # the three long output runs to R128..R130 are in stage 3
ORDER = ["Ma1", "La1", "Mb1", "Lb1", "N1", "P1", "O1", "Ma2", "La2", "Mb2", "Lb2", "N2", "P2", "O2",
         "Ma3", "La3", "Mb3", "Lb3", "N3", "P3", "O3", "SP"]


def run(order, quiet=True):
    done = []
    for k in order:
        if k in FILTER:
            net, a, b = FILTER[k]
            ok = r.connect(net, a, b, w=W, layers=("In3.Cu", "B.Cu", "F.Cu"), lcost={"B.Cu": 2.0, "F.Cu": 2.0}, via=1.5, box=CA, quiet=quiet)
        else:
            net, a, b = T[k]
            ok = r.connect(net, a, b, w=W, layers=("B.Cu",), box=CA, quiet=True) or \
                r.connect(net, a, b, w=W, layers=ALL, box=CA, via=0.8, lcost={"F.Cu": 1.5, "In3.Cu": 1.2}, quiet=quiet)
        if ok:
            done.append(k)
    return done


r.log("== LDO U27")
r.connect("CTRL_NR", "U27-4", "C134-1", w=0.2, layers=("B.Cu",), box=CA)
for pad in ("U27-3", "C136-1", "J14-1"):
    r.connect("5V_CTRL_A", pad, "U27-1", w=0.4, layers=("B.Cu",), box=CA) or r.connect("5V_CTRL_A", pad, "U27-1", w=0.4, layers=ALL, box=CA)

if "--search" in opt:
    rnd = random.Random(int(opt.get("--seed", 1)))
    snap = r.snapshot()
    logf, r.logf = r.logf, None
    best = (len(run(ORDER)), list(ORDER))
    print("ORDER as kept:", best[0], "of", len(ORDER), flush=True)
    for i in range(int(opt["--search"])):
        r.restore(snap)
        order = list(ORDER)
        rnd.shuffle(order)
        order = [k for k in order if k in FILTER] + [k for k in order if k not in FILTER]     # the long runs first
        n = len(run(order))
        if n > best[0]:
            best = (n, order)
            print(f"try {i}: {n} of {len(order)}: {order}", flush=True)
        if n == len(order):
            break
    print("best:", best)
    sys.exit(0)

r.log("== difference amplifiers and outputs")
done = run(ORDER, quiet=False)
r.save(args[1])
r.log(f"stage 4: {len(done)} of {len(ORDER)} amplifier connections; not routed: {[k for k in ORDER if k not in done]}")
