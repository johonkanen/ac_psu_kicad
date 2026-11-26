#!/usr/bin/env python3
"""Phase 4: IPC-D-356 netlist exported from the KiCad board vs the Proteus IPC-D-356A file
(stdlib only, system python3; kicad-cli for the export).

Exports kicad/ac_psu.kicad_pcb with `kicad-cli pcb export ipcd356`, parses it (KiCad writes
units CUST 0 = 0.0001 inch, net names of more than 14 characters as NNAME aliases, refdes
truncated to 6 characters like Proteus, vias with refdes VIA, the mounting holes H1..H4 as N/C)
and matches every Proteus record (p2k ipc356) to a KiCad record:
  pads   same truncated refdes and pin id, nearest position (two pads numbered 1 on
         ACIN/ACOUT, FILTER_IN/FILTER_OUT share the truncated refdes), within TOL;
  vias   nearest KiCad via within TOL;
  holes  nearest KiCad N/C THT record without a Proteus refdes within TOL.
Checked per matched pair: position (TOL), side (access code: KiCad writes the bottom as the
copper layer count, Proteus as 16), THT vs SMD record type, drill (KiCad may be larger, Phase 3
decision, never smaller), and the net: Proteus nets map one-to-one onto KiCad nets through the
pads (pad-set equivalence, names differ for the #00xxx and sheet-local nets); a Proteus N/C pad
(or one without a net: R87-4/5, mounting holes) must be on a KiCad unconnected-(...) net or N/C.
Unmatched records on either side are errors. Pad sizes are only summarised.

Usage: python3 tools/ipc356_diff.py [--kicad FILE] [-v]
"""
import argparse
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import ipc356  # noqa: E402
import deviations  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "kicad" / "ac_psu.kicad_pcb"
CLI = ROOT / "tools" / "p2k" / "bin" / "kicad-cli"
TOL = 0.05        # mm, position
DRILL_TOL = 0.005  # mm (KiCad writes 0.0001 inch = 0.00254 mm)
COPPER_LAYERS = (4, 6)   # KiCad numbers the bottom as the copper layer count: 4 until v5 step 3, then 6

# KiCad leaves the 'M' (mid-point) column blank and pads with spaces, Proteus writes M + D/blanks
DATA_RE = re.compile(
    r"[M\s]*(?:D(?P<drill>\d{4})(?P<plated>[PU]))?\s*"
    r"A(?P<access>\d\d)"
    r"X(?P<x>[+-]\d{6})Y(?P<y>[+-]\d{6})"
    r"X(?P<w>\d{4})(?:Y(?P<h>\d{4}))?(?:R(?P<rot>\d{3}))?"
    r"\s*S(?P<mask>\d)\s*$")


def export(path):
    r = subprocess.run([str(CLI), "pcb", "export", "ipcd356", "-o", str(path), str(BOARD)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not path.exists():
        sys.exit(f"ipc356_diff: kicad-cli export failed:\n{r.stdout}{r.stderr}")


def parse_kicad(path):
    """KiCad IPC-D-356 records -> list of dicts (mm, Y up, like ipc356.parse)."""
    scale = None
    names = {}
    recs = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("P  UNITS"):
            u = line.split()[2:]
            scale = 0.00254 if u[0] == "CUST" and u[1] == "0" else 0.001 if u[0] == "SI" else None  # 0.0001 inch
            if scale is None:
                raise ValueError(f"{path}: units {line!r}")
        elif line.startswith("P  NNAME"):
            nid, name = line[3:].split(None, 1)
            names[nid] = name.strip()
        op = line[:3]
        if op not in ("317", "327"):
            continue
        net_field = line[3:17].strip()
        refdes = line[20:26].strip()
        pin = line[27:31].strip()
        m = DATA_RE.match(line[31:])
        if not m:
            raise ValueError(f"{path}: line {lineno}: cannot parse {line!r}")
        net = names.get("NNAME" + net_field, net_field)
        acc = m["access"]
        side = "both" if acc == "00" else "top" if acc == "01" else "bottom" if int(acc) in COPPER_LAYERS else acc
        w = int(m["w"]) * scale
        h = int(m["h"]) * scale if m["h"] else 0.0
        recs.append(dict(
            net=net, refdes=refdes, pin=pin, x_mm=int(m["x"]) * scale, y_mm=int(m["y"]) * scale,
            side=side, pad_w=w, pad_h=h or w, is_tht=op == "317",   # KiCad writes Y0000 for round pads
            drill=int(m["drill"]) * scale if m["drill"] else 0.0,
            kind="via" if refdes == "VIA" else "pad" if net != "N/C" or pin else "hole", line=lineno))
    for r in recs:   # mounting holes: KiCad gives them refdes H1..H4 and net N/C
        if r["kind"] == "pad" and r["net"] == "N/C" and re.fullmatch(r"H\d+", r["refdes"]):
            r["kind"] = "hole"
    return recs


def kicad_unconnected(net):
    return net == "N/C" or net.startswith("unconnected-(")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kicad", type=Path, help="KiCad IPC-D-356 file (default: export it)")
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    _, prot = ipc356.parse(ipc356.DEFAULT_IPC)
    prot = deviations.apply_records(prot)   # v4 net changes (lib/v4_deviations.csv)
    v4parts, v4vias = deviations.added_parts(), deviations.vias()
    swapped = deviations.footprint_changes()
    swap_net = {}   # ref -> IPC (v4) net of its pins; their pads are checked by terminal area + net
    swap_prot = [p for p in prot if p["kind"] == "pad" and p["refdes"] in swapped]
    for p in swap_prot:
        swap_net[p["refdes"]] = p["net"]
    prot = [p for p in prot if not (p["kind"] == "pad" and p["refdes"] in swapped)]
    # v5 moved parts: their Proteus pad records leave the position comparison; pin -> net is kept
    movedset = deviations.moved_parts()
    moved_net = {(p["refdes_raw"], p["pin"]): ("N/C" if p["net_raw"] == "N/C" or not p["net"] else p["net"])
                 for p in prot if p["kind"] == "pad" and p["refdes"] in movedset}
    prot = [p for p in prot if not (p["kind"] == "pad" and p["refdes"] in movedset)]
    movedrecs = []
    if args.kicad:
        kic = parse_kicad(args.kicad)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "ac_psu.d356"
            export(p)
            kic = parse_kicad(p)

    errors = []
    # candidates per key
    by_key = {}
    for r in kic:
        key = (r["kind"], r["refdes"] if r["kind"] == "pad" else "", r["pin"] if r["kind"] == "pad" else "")
        by_key.setdefault(key, []).append(r)
    used = set()
    pairs = []
    worst = 0.0
    cut_nets = deviations.v5_cut_nets()
    v5gone = []
    for p in prot:
        key = (p["kind"], p["refdes_raw"] if p["kind"] == "pad" else "", p["pin"] if p["kind"] == "pad" else "")
        cands = [r for r in by_key.get(key, []) if id(r) not in used]
        if p["kind"] == "via" and (deviations.in_pending(p["x_mm"], p["y_mm"]) or p["net"] in cut_nets
                                   or deviations.in_unrouted(p["x_mm"], p["y_mm"])):
            near = [r for r in cands if math.hypot(r["x_mm"] - p["x_mm"], r["y_mm"] - p["y_mm"]) <= TOL]
            if not near:
                v5gone.append(p)   # v5: deleted with the old copper (pending GUI layout / cut chain)
                continue
        if not cands:
            errors.append(f"Proteus {p['kind']} {p['refdes']}-{p['pin']} at ({p['x_mm']}, {p['y_mm']}): no KiCad record")
            continue
        r = min(cands, key=lambda r: math.hypot(r["x_mm"] - p["x_mm"], r["y_mm"] - p["y_mm"]))
        d = math.hypot(r["x_mm"] - p["x_mm"], r["y_mm"] - p["y_mm"])
        if d > TOL:
            errors.append(f"Proteus {p['kind']} {p['refdes']}-{p['pin']} at ({p['x_mm']}, {p['y_mm']}): nearest KiCad record {d:.3f} mm away")
            continue
        used.add(id(r))
        worst = max(worst, d)
        pairs.append((p, r))
    v4recs = []
    swaprecs = []
    newvias = []
    v4gone = [v for v in v4vias if deviations.in_unrouted(v[0], v[1]) and not any(
        r["kind"] == "via" and math.hypot(v[0] - r["x_mm"], v[1] - r["y_mm"]) < TOL for r in kic)]
    v4vias = [v for v in v4vias if v not in v4gone]   # v4 vias deleted with the card-area re-layout
    for r in kic:
        if id(r) not in used:
            if r["kind"] == "pad" and (r["refdes"], r["pin"]) in moved_net:
                movedrecs.append((r, moved_net[(r["refdes"], r["pin"])]))
                continue
            if r["kind"] == "via" and deviations.in_unrouted(r["x_mm"], r["y_mm"]) and not any(
                    math.hypot(v[0] - r["x_mm"], v[1] - r["y_mm"]) < TOL for v in v4vias):
                newvias.append(r)     # v5: a via of the new card-area layout
                continue
            tref = deviations.in_terminal_area(r["x_mm"], r["y_mm"]) if r["kind"] == "pad" else None
            if tref and tref[:6] == r["refdes"]:
                swaprecs.append((r, tref))
                continue
            if r["kind"] == "pad" and r["refdes"] in v4parts and r["pin"] in v4parts[r["refdes"]]["pins"]:
                v4recs.append((r, v4parts[r["refdes"]]["pins"][r["pin"]]))
                continue
            hit = [v for v in v4vias if r["kind"] == "via" and math.hypot(v[0] - r["x_mm"], v[1] - r["y_mm"]) < TOL]
            if hit:
                v4recs.append((r, hit[0][2]))
                continue
            errors.append(f"KiCad {r['kind']} {r['refdes']}-{r['pin']} at ({r['x_mm']:.3f}, {r['y_mm']:.3f}) net {r['net']}: no Proteus record (line {r['line']})")

    # net mapping by pad-set equivalence (component pads with a real net on both sides)
    fwd, back = {}, {}
    for p, r in pairs:
        if p["kind"] == "pad" and p["net"] and p["net_raw"] != "N/C" and not kicad_unconnected(r["net"]):
            fwd.setdefault(p["net"], set()).add(r["net"])
            back.setdefault(r["net"], set()).add(p["net"])
    for r, want in movedrecs:   # v5 moved pads map nets too (a net may have only moved pads left)
        if want != "N/C" and not kicad_unconnected(r["net"]):
            fwd.setdefault(want, set()).add(r["net"])
            back.setdefault(r["net"], set()).add(want)
    for n, ks in sorted(fwd.items()):
        if len(ks) > 1:
            errors.append(f"Proteus net {n} spans KiCad nets {sorted(ks)}")
    for k, ns in sorted(back.items()):
        if len(ns) > 1:
            errors.append(f"KiCad net {k} spans Proteus nets {sorted(ns)}")
    mapping = {n: next(iter(ks)) for n, ks in fwd.items() if len(ks) == 1}
    pnets = {p["net"] for p in prot if p.get("net")}
    for r, want in v4recs:   # v4 pads / vias: on the listed net (v5: renamed / new nets)
        want = deviations.new_net(want)
        if want == "N/C":
            if not kicad_unconnected(r["net"]):
                errors.append(f"v5 pad {r['refdes']}-{r['pin']}: N/C in the list, KiCad net {r['net']}")
            continue
        if want not in pnets and (r["net"] == want or (len(r["net"]) >= 12 and want.startswith(r["net"]))):
            continue   # a new v5 net (no Proteus image; the IPC export truncates long names)
        if want not in mapping and r["net"] == want and want not in back:
            continue   # v6: a Proteus net that lost all its Proteus pads (power stage removed); the name is kept
        if mapping.get(want) != r["net"]:
            errors.append(f"v4 {r['kind']} {r['refdes']}-{r['pin']} at ({r['x_mm']:.3f}, {r['y_mm']:.3f}): "
                          f"KiCad net {r['net']}, listed {want} -> {mapping.get(want)}")
    for r, want in movedrecs:   # v5 moved parts: on the IPC pin's net, wherever they are
        if want == "N/C":
            if not kicad_unconnected(r["net"]):
                errors.append(f"moved {r['refdes']}-{r['pin']}: N/C in IPC, KiCad net {r['net']}")
        elif mapping.get(want) != r["net"] and not (want not in pnets and (r["net"] == want or (len(r["net"]) >= 12 and want.startswith(r["net"])))):
            errors.append(f"moved {r['refdes']}-{r['pin']}: KiCad net {r['net']}, IPC net {want} -> {mapping.get(want)}")
    if len(movedrecs) != len(moved_net):
        errors.append(f"moved parts: {len(moved_net)} IPC pads, {len(movedrecs)} KiCad records")
    if movedrecs or newvias or v4gone:
        print(f"ipc356_diff: {len(movedrecs)} pads of {len(movedset)} v5 moved parts (nets checked, not positions); "
              f"{len(newvias)} new vias and {len(v4gone)} deleted v4 vias in the unrouted areas")
    for r, tref in swaprecs:   # swapped footprints: in their terminal area, on the IPC pin's net
        if swap_net.get(tref) == "N/C" and kicad_unconnected(r["net"]):
            continue   # v6: a terminal that became a wire landing point without a net (pin row ... -> N/C)
        want = deviations.new_net(swap_net.get(tref) or "")
        if want not in pnets and r["net"] == want:
            continue   # v6: the terminal's net renamed (INDUCTOR_INPUT -> SW_INV_B, section 15)
        if mapping.get(swap_net.get(tref)) != r["net"]:
            errors.append(f"v4 footprint swap {tref} pad at ({r['x_mm']:.3f}, {r['y_mm']:.3f}): KiCad net {r['net']}, "
                          f"IPC net {swap_net.get(tref)} -> {mapping.get(swap_net.get(tref))}")
    missing = sorted(set(swapped) - {t for _, t in swaprecs})
    if missing:
        errors.append(f"v4 footprint swaps without KiCad pad records: {' '.join(missing)}")
    # a pin with several pads (v6: the four press-fit pins of a REDCUBE terminal share number 1) counts once
    npadrec = sum(1 for r, _ in v4recs if r["kind"] == "pad")
    nv4p = len({(r["refdes"], r["pin"]) for r, _ in v4recs if r["kind"] == "pad"})
    if nv4p != sum(len(p["pins"]) for p in v4parts.values()) or len(v4recs) - npadrec != len(v4vias):
        errors.append(f"v4 records: {nv4p} pads, {len(v4recs) - npadrec} vias found; "
                      f"listed {sum(len(p['pins']) for p in v4parts.values())} pads, {len(v4vias)} vias")

    stats = Counter()
    size_diff = Counter()
    drill_larger = Counter()
    for p, r in pairs:
        what = f"{p['kind']} {p['refdes']}-{p['pin']}" if p["kind"] == "pad" else f"{p['kind']} at ({p['x_mm']}, {p['y_mm']})"
        stats[p["kind"]] += 1
        if p["is_tht"] != r["is_tht"]:
            errors.append(f"{what}: Proteus {'THT' if p['is_tht'] else 'SMD'}, KiCad {'THT' if r['is_tht'] else 'SMD'}")
        if p["side"] != r["side"]:
            errors.append(f"{what}: side Proteus {p['side']}, KiCad {r['side']}")
        if r["drill"] < p["drill"] - DRILL_TOL:
            errors.append(f"{what}: drill Proteus {p['drill']}, KiCad {r['drill']:.4f} is smaller")
        elif r["drill"] > p["drill"] + DRILL_TOL:
            drill_larger[(p["drill"], round(r["drill"], 3))] += 1
        # nets
        p_nc = p["net_raw"] == "N/C" or not p["net"]
        if p["kind"] == "hole":
            if not kicad_unconnected(r["net"]):
                errors.append(f"{what}: mounting hole on KiCad net {r['net']}")
        elif p_nc:
            if not kicad_unconnected(r["net"]):
                errors.append(f"{what}: N/C in Proteus, KiCad net {r['net']}")
            stats["N/C pads"] += 1
        elif kicad_unconnected(r["net"]):
            errors.append(f"{what}: Proteus net {p['net']}, KiCad unconnected ({r['net']})")
        elif mapping.get(p["net"]) != r["net"]:
            errors.append(f"{what}: Proteus net {p['net']} -> {mapping.get(p['net'])}, KiCad net {r['net']}")
        if p["kind"] == "pad":
            dw = abs(p["pad_w"] - r["pad_w"]) > 0.01 or abs(p["pad_h"] - r["pad_h"]) > 0.01
            dr = abs(p["pad_w"] - r["pad_h"]) > 0.01 or abs(p["pad_h"] - r["pad_w"]) > 0.01   # rotated 90
            if dw and dr:
                size_diff[re.sub(r"\d+$", "", p["refdes"]) or p["refdes"]] += 1

    print(f"ipc356_diff: Proteus {len(prot)} records, KiCad {len(kic)}; matched {len(pairs)} "
          f"({stats['pad']} pads incl. {stats['N/C pads']} N/C, {stats['via']} vias, {stats['hole']} holes), "
          f"worst position offset {worst:.3f} mm (limit {TOL})")
    if v5gone:
        print(f"ipc356_diff: {len(v5gone)} Proteus vias deleted by v5 (pending-layout areas / cut v5 chains)")
    print(f"ipc356_diff: {len(mapping)} Proteus nets mapped 1:1 onto KiCad nets, "
          f"{len(errors)} mismatches")
    if not deviations.proteus_mode():
        print(f"ipc356_diff: v4 deviations applied ({deviations.summary()}); "
              f"{len(v4recs)} KiCad records of v4 parts/vias, {len(swaprecs)} of v4 footprint swaps "
              f"({len(swap_prot)} Proteus pad records replaced), nets checked")
    if drill_larger:
        print("ipc356_diff: KiCad drill larger (footprint kept): " +
              ", ".join(f"{n}x {a}->{b}" for (a, b), n in sorted(drill_larger.items())))
    if size_diff:
        print("ipc356_diff: pads with another size in KiCad (info): " +
              ", ".join(f"{k} {n}" for k, n in sorted(size_diff.items())))
    for e in errors[:50]:
        print("ipc356_diff: ERROR " + e)
    print("ipc356_diff: " + ("OK" if not errors else "FAILED"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
