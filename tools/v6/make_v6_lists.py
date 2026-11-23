#!/usr/bin/env python3
"""Write the v6 rows of lib/part_map.csv and lib/v6_deviations.csv from tools/v6/v6_parts.py (the CSV files
are the reviewed, committed record that the checks compare against).

  python3 tools/v6/make_v6_lists.py          part_map rows (new parts added, removed parts dropped) and the
                                             remove / part / value rows
  python3 tools/v6/make_v6_lists.py --nets   also the add rows (every pin of a new part, from the schematic
                                             netlist) and the pin rows (existing parts whose pin moved to another
                                             net); run after the sheets are drawn, then review the diff
"""
import csv
import io
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)
import v6_parts as V  # noqa: E402

ROOT = os.path.dirname(TOOLS)
PART_MAP = os.path.join(ROOT, "lib", "part_map.csv")
DEV = os.path.join(ROOT, "lib", "v6_deviations.csv")
FIX = "v6"
HEADER = """# Intended deviations of the v6 design (baseboard for six half-bridge power cards, V6_PLAN.md) from the Proteus
# v3 original, on top of lib/v4_deviations.csv and lib/v5_deviations.csv (same kinds, read by tools/deviations.py).
# Written by tools/v6/make_v6_lists.py from tools/v6/v6_parts.py (remove, part, value) and, with --nets, from the
# schematic netlist (add, pin).
"""


def write_part_map():
    with open(PART_MAP) as f:
        lines = f.read().splitlines()
    head = [l for l in lines if l.startswith("#") or l.startswith("refdes,")]
    rows = [r for r in csv.reader(l for l in lines if not (l.startswith("#") or l.startswith("refdes,")))]
    new = {p[0] for p in V.PARTS}
    rows = [r for r in rows if r[0] not in V.REMOVED and r[0] not in new]
    rows += [[ref, str(sheet), f"ac_psu:{sym}", value] for ref, sheet, sym, value, fp, note in V.PARTS]

    def key(r):
        stem = r[0].rstrip("0123456789")
        return (stem, int(r[0][len(stem):] or 0), r[0])
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
        out.append(dict(kind="remove", ref=ref, pin="", **{"from": ""}, to="", fix=FIX, note=V.REMOVED_NOTE[ref]))
    for ref, sheet, sym, value, fp, note in V.PARTS:
        out.append(dict(kind="part", ref=ref, pin="", **{"from": ""}, to=fp, fix=FIX, note=note))
        out.append(dict(kind="value", ref=ref, pin="", **{"from": ""}, to=value, fix=FIX, note=""))
    return out


def net_rows():
    """As tools/v5/make_v5_lists.py net_rows: add rows for the new parts, pin rows for pins of kept parts that
    changed net. Reference nets are matched to KiCad nets by their members."""
    import board_common as bc
    import deviations
    comps, nets = bc.export_netlist()
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes if not n.startswith("unconnected-")}
    nc = {(r, p) for n, nodes in nets.items() for r, p in nodes if n.startswith("unconnected-")}
    new = {p[0] for p in V.PARTS}
    with open(os.path.join(ROOT, "reference", "ipc356_pads.json")) as f:
        ipc = {(deviations.kref(p["refdes"]), p["pin"]): p["net"] for p in json.load(f)["pads"] if p["kind"] == "pad"}
    v6 = _read(DEV)
    try:
        _write([r for r in v6 if r["kind"] not in ("pin", "add")])
        ref_nets = deviations.apply_pin_nets(dict(ipc))
    finally:
        _write(v6)
    ref_nets = {rp: n for rp, n in ref_nets.items() if n not in ("N/C", "(no net)", None) and rp[0] not in new}
    stated = {rp: ref_nets.pop(rp) for rp in list(ref_nets) if rp in V.PIN_TO}
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
    for (r, p), n in sorted(stated.items()):
        proteus = {b: a for a, b in deviations.refdes_map().items()}.get(r, r)
        assert pin_net.get((r, p), "").split("/")[-1] == V.PIN_TO[(r, p)], (r, p, pin_net.get((r, p)))   # sheet-local nets
        out.append(dict(kind="pin", ref=proteus, pin=p, **{"from": ipc.get((r, p), n)}, to=V.PIN_TO[(r, p)], fix=FIX,
                        note=f"v6: current sense at the quiet end of the choke (was {n})"))
    for (r, p), n in sorted(ref_nets.items()):
        if r in V.REMOVED or not n:
            continue
        k = pin_net.get((r, p), "N/C" if (r, p) in nc else None)
        if k is None or k == image.get(n):
            continue
        proteus = {b: a for a, b in deviations.refdes_map().items()}.get(r, r)   # rows keep the Proteus refdes
        out.append(dict(kind="pin", ref=proteus, pin=p, **{"from": ipc.get((r, p), n)}, to=inverse.get(k, k), fix=FIX,
                        note=f"v6 (was {n})"))
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
    print(f"make_v6_lists: {len(rows)} rows in lib/v6_deviations.csv, part_map: +{len(V.PARTS)} / -{len(V.REMOVED)}")


if __name__ == "__main__":
    main()
