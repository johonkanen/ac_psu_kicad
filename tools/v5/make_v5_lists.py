#!/usr/bin/env python3
"""Write the v5 rows of lib/part_map.csv and lib/v5_deviations.csv from tools/v5/v5_parts.py
(one-shot tool for the v5 schematic change; the CSV files are the reviewed, committed record that
the checks compare against).

  python3 tools/v5/make_v5_lists.py          part_map rows (new parts added, removed parts dropped)
                                             and the remove / rename / part / value rows
  python3 tools/v5/make_v5_lists.py --nets   also the add rows (every pin of a new part, from the
                                             schematic netlist) and the pin rows (existing parts
                                             whose pin moved to another net, after merges/renames);
                                             run after the sheets are drawn, then review the diff
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)
import v5_parts as V  # noqa: E402

ROOT = os.path.dirname(TOOLS)
PART_MAP = os.path.join(ROOT, "lib", "part_map.csv")
DEV = os.path.join(ROOT, "lib", "v5_deviations.csv")

HEADER = """# Intended deviations of the v5 design (aux flyback + control-card isolation) from the Proteus v3
# original, on top of lib/v4_deviations.csv (same kinds, read by tools/deviations.py), plus:
#   remove  ref is a Proteus part deleted in v5 (its pins leave the reference)
#   rename  from = IPC net, to = new net name (every pad, via and track of `from`)
# Written by tools/v5/make_v5_lists.py from tools/v5/v5_parts.py (part, value, remove, rename) and,
# with --nets, from the schematic netlist (add, pin). Plans: V5_PLAN.md, CTRL_ISOLATION_PLAN.md.
"""
FIX = "v5"


def write_part_map():
    with open(PART_MAP) as f:
        lines = f.read().splitlines()
    head = [l for l in lines if l.startswith("#") or l.startswith("refdes,")]
    rows = [r for r in csv.reader(l for l in lines if not (l.startswith("#") or l.startswith("refdes,")))]
    new = {p[0] for p in V.PARTS}
    rows = [r for r in rows if r[0] not in V.REMOVED and r[0] not in new]
    rows += [[ref, str(sheet), f"ac_psu:{sym}", value] for ref, sheet, sym, value, fp, note in V.PARTS]

    def key(r):
        ref = r[0]
        stem = ref.rstrip("0123456789")
        return (stem, int(ref[len(stem):] or 0), ref)
    rows.sort(key=key)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in rows:
        w.writerow(r)
    with open(PART_MAP, "w") as f:
        f.write("\n".join(head) + "\n" + buf.getvalue())


def base_rows():
    out = []
    for ref in V.REMOVED:
        out.append(dict(kind="remove", ref=ref, pin="", **{"from": ""}, to="", fix=FIX, note="v5: IW1830/EF20 aux supply replaced"))
    for a, b in V.RENAMES.items():
        out.append(dict(kind="rename", ref="", pin="", **{"from": a}, to=b, fix=FIX, note="v5 D6: 15 V aux outputs"))
    for ref, sheet, sym, value, fp, note in V.PARTS:
        out.append(dict(kind="part", ref=ref, pin="", **{"from": ""}, to=fp, fix=FIX, note=note))
        out.append(dict(kind="value", ref=ref, pin="", **{"from": ""}, to=value, fix=FIX, note=""))
    return out


def net_rows():
    """add rows for the new parts and pin rows for moved pins. Nets are matched by their members
    (IPC auto names like #00227 differ from KiCad's Net-(...) names): every reference net maps to
    the KiCad net holding most of its (kept) pins; rows use the reference name where a KiCad net
    is such an image, else the KiCad name (a new v5 net)."""
    import json
    from collections import Counter
    import board_common as bc
    import deviations
    comps, nets = bc.export_netlist()
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes if not n.startswith("unconnected-")}
    nc = {(r, p) for n, nodes in nets.items() for r, p in nodes if n.startswith("unconnected-")}
    new = {p[0] for p in V.PARTS}
    with open(os.path.join(ROOT, "reference", "ipc356_pads.json")) as f:
        ipc = {(p["refdes"], p["pin"]): p["net"] for p in json.load(f)["pads"] if p["kind"] == "pad"}
    v5 = _read(DEV)
    try:
        _write([r for r in v5 if r["kind"] not in ("pin", "add")])
        ref_nets = deviations.apply_pin_nets(dict(ipc))
    finally:
        _write(v5)
    ref_nets = {rp: n for rp, n in ref_nets.items() if n not in ("N/C", "(no net)", None) and rp[0] not in new}
    members = {}
    for rp, n in ref_nets.items():
        members.setdefault(n, []).append(rp)
    image, inverse = {}, {}
    for n, rps in members.items():
        c = Counter(pin_net[rp] for rp in rps if rp in pin_net)
        if c:
            k = c.most_common(1)[0][0]
            image[n] = k
            inverse.setdefault(k, n)
    out = []
    for ref, sheet, sym, value, fp, note in V.PARTS:
        pins = sorted((p for (r, p) in set(pin_net) | nc if r == ref), key=lambda p: (len(p), p))
        for p in pins:
            k = pin_net.get((ref, p), "N/C")
            out.append(dict(kind="add", ref=ref, pin=p, **{"from": ""}, to=inverse.get(k, k), fix=FIX, note=""))
    for (r, p), n in sorted(ref_nets.items()):
        k = pin_net.get((r, p))
        if k is None or k == image.get(n):
            continue
        if (r, p) not in ipc:
            sys.exit(f"make_v5_lists: v4 part pin {r}-{p} moved from {n} to {k}: edit lib/v4_deviations.csv")
        out.append(dict(kind="pin", ref=r, pin=p, **{"from": ipc[(r, p)]}, to=inverse.get(k, k), fix=FIX,
                        note=f"v5 (was {n})"))
    return out


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def _write(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, ["kind", "ref", "pin", "from", "to", "fix", "note"], lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    with open(DEV, "w") as f:
        f.write(HEADER + buf.getvalue())


def main():
    write_part_map()
    rows = base_rows()
    _write(rows)
    if "--nets" in sys.argv:
        rows += net_rows()
        _write(rows)
    print(f"make_v5_lists: {len(rows)} rows in lib/v5_deviations.csv, part_map: +{len(V.PARTS)} / -{len(V.REMOVED)}")


if __name__ == "__main__":
    main()
