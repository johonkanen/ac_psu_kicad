#!/usr/bin/env python3
"""Parse the Proteus IPC-D-356A netlist into a pad table.

Writes (default, into reference/):
  ipc356_pads.json / ipc356_pads.csv   one row per pad/via/hole record
  pin_nets_by_component.md             per refdes: pin -> net (redraw cheat sheet)
  pins_by_net.md                       per net: list of refdes-pin

Applied fix-ups:
  * refdes truncated to 6 chars by Proteus are restored by pad coordinate
    (TRUNCATED_REFDES below, names checked against the schematic PDF);
  * Proteus power-net names are aliased (NET_ALIASES).

Coordinates are kept exactly as in the IPC file: mm, Y axis pointing up
(KiCad's Y points down; flip when placing).

  tools/ipc356.py            regenerate the reference files
  tools/ipc356.py --check    self-check counts and that reference/ is up to date

Stdlib only; runs with any python3 (no pcbnew needed).
"""

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IPC = ROOT / "source/cadcam/single_phase_inverter_psu_v3 - CADCAM Netlist.IPC"
REF_DIR = ROOT / "reference"

# (truncated refdes, x_um, y_um) -> full refdes. Nets confirmed on the PDF:
# AFE_OUT on G3_SOURCE_HI (sheet 1), FILTER_IN on FILTER_INPUT and FILTER_OUT
# on LEMOUT (sheet 1), INU_OUT2 on Q5_S (sheet 5), DAB_PRI_1 on TR1 pin 1 =
# DAB_SOURCE_HI_PRI, DAB_PRI_2 on DAB_CAP_PRI, DAB_SEC_1 on TR1 pin 3 =
# DAB_SOURCE_HI_SEC, DAB_SEC_2 on DAB_CAP_SEC (sheet 6).
TRUNCATED_REFDES = {
    ("AFE_OU", 47500, -73600): "AFE_OUT",
    ("FILTER", -14400, -57300): "FILTER_IN",
    ("FILTER", -33000, -48500): "FILTER_OUT",
    ("INU_OU", 48500, 61500): "INU_OUT2",
    ("DAB_PR", 111250, -70300): "DAB_PRI_1",
    ("DAB_PR", 111250, -63200): "DAB_PRI_2",
    ("DAB_SE", 97900, 61700): "DAB_SEC_1",
    ("DAB_SE", 97900, 55400): "DAB_SEC_2",
}
# Expected net per fixed refdes, used by the self-check.
TRUNCATED_NETS = {
    "AFE_OUT": "G3_SOURCE_HI",
    "FILTER_IN": "FILTER_INPUT",
    "FILTER_OUT": "LEMOUT",
    "INU_OUT2": "Q5_S",
    "DAB_PRI_1": "DAB_SOURCE_HI_PRI",
    "DAB_PRI_2": "DAB_CAP_PRI",
    "DAB_SEC_1": "DAB_SOURCE_HI_SEC",
    "DAB_SEC_2": "DAB_CAP_SEC",
}

NET_ALIASES = {
    "GND=POWER": "GND",
    "VCC/VDD=POWER": "VCC",
}

# Expected raw counts in the Proteus file (PLAN.md section 1).
EXPECTED = {
    "nets": 208,          # NNAME declarations
    "refdes_raw": 265,    # distinct refdes fields, incl. the blank one of vias/holes
    "tht_records": 562,   # 317 records (component THT pads + vias + holes)
    "smd_records": 513,   # 327 records
    "nc_pads": 34,
    "vias": 173,
    "holes": 4,
    "parts": 267,         # named refdes after the truncation fix-up
}

FIELDS = ["kind", "net", "net_raw", "net_id", "refdes", "refdes_raw", "pin",
          "x_mm", "y_mm", "side", "pad_w", "pad_h", "rot", "is_tht", "drill",
          "plated", "mask"]

# Columns after the fixed 3/14/6/1/4 header part, e.g.
#   MD0558PA00X+019720Y-064800X0812          S0
#   M      A01X+089400Y-018000X1600Y2260R090 S0
DATA_RE = re.compile(
    r"M(?:D(?P<drill>\d{4})(?P<plated>[PU])|\s{6})"
    r"A(?P<access>\d\d)"
    r"X(?P<x>[+-]\d{6})Y(?P<y>[+-]\d{6})"
    r"X(?P<w>\d{4})(?:Y(?P<h>\d{4}))?(?:R(?P<rot>\d{3}))?"
    r"\s*S(?P<mask>\d)\s*$")

SIDES = {"00": "both", "01": "top", "16": "bottom"}


def natural_key(s):
    return [(0, int(t), "") if t.isdigit() else (1, 0, t)
            for t in re.findall(r"\d+|\D+", s)]


def parse(path):
    net_names = {}
    pads = []
    trunc_used = Counter()
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("P  NNAME"):
            nid, name = line[3:].split(None, 1)
            net_names[nid] = name.strip()
            continue
        op = line[:3]
        if op not in ("317", "327"):
            continue
        net_field = line[3:17].strip()
        refdes_raw = line[20:26].strip()
        pin = line[27:31].strip()
        m = DATA_RE.match(line[31:])
        if not m:
            raise ValueError(f"line {lineno}: cannot parse {line!r}")
        x_um, y_um = int(m["x"]), int(m["y"])

        if net_field == "N/C":
            net_id, net_raw = "", "N/C"
        elif net_field:
            net_id, net_raw = net_field, net_names[net_field]
        else:
            net_id, net_raw = "", ""
        net = NET_ALIASES.get(net_raw, net_raw)

        refdes = refdes_raw
        key = (refdes_raw, x_um, y_um)
        if key in TRUNCATED_REFDES:
            refdes = TRUNCATED_REFDES[key]
            trunc_used[key] += 1
        elif refdes_raw in {k[0] for k in TRUNCATED_REFDES}:
            raise ValueError(f"line {lineno}: truncated refdes {refdes_raw} at "
                             f"({x_um}, {y_um}) not in TRUNCATED_REFDES")

        if refdes:
            kind = "pad"
        elif net_raw:
            kind = "via"
        else:
            kind = "hole"
        w = int(m["w"]) / 1000
        pads.append({
            "kind": kind,
            "net": net,
            "net_raw": net_raw,
            "net_id": net_id,
            "refdes": refdes,
            "refdes_raw": refdes_raw,
            "pin": pin,
            "x_mm": x_um / 1000,
            "y_mm": y_um / 1000,
            "side": SIDES.get(m["access"], m["access"]),
            "pad_w": w,
            "pad_h": int(m["h"]) / 1000 if m["h"] else w,
            "rot": int(m["rot"]) if m["rot"] else 0,
            "is_tht": op == "317",
            "drill": int(m["drill"]) / 1000 if m["drill"] else 0.0,
            "plated": m["plated"] == "P" if m["drill"] else False,
            "mask": int(m["mask"]),
        })
    unused = set(TRUNCATED_REFDES) - set(trunc_used)
    if unused:
        raise ValueError(f"TRUNCATED_REFDES entries not found in IPC: {sorted(unused)}")
    return net_names, pads


def stats(net_names, pads):
    parts = {p["refdes"] for p in pads if p["kind"] == "pad"}
    return {
        "nets": len(net_names),
        "refdes_raw": len({p["refdes_raw"] for p in pads}),
        "tht_records": sum(p["is_tht"] for p in pads),
        "smd_records": sum(not p["is_tht"] for p in pads),
        "nc_pads": sum(p["net_raw"] == "N/C" for p in pads),
        "vias": sum(p["kind"] == "via" for p in pads),
        "holes": sum(p["kind"] == "hole" for p in pads),
        "parts": len(parts),
    }


def render_csv(pads):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(pads)
    return buf.getvalue()


def render_json(net_names, pads):
    doc = {
        "source": DEFAULT_IPC.name,
        "units": "mm, IPC coordinates (Y up)",
        "net_aliases": NET_ALIASES,
        "truncated_refdes": [
            {"raw": k[0], "x_mm": k[1] / 1000, "y_mm": k[2] / 1000, "refdes": v}
            for k, v in TRUNCATED_REFDES.items()],
        "nets": {nid: NET_ALIASES.get(n, n) for nid, n in net_names.items()},
        "pads": pads,
    }
    return json.dumps(doc, indent=1) + "\n"


def net_label(p):
    if p["net_raw"] == "N/C":
        return "N/C"
    if not p["net"]:
        return "(no net)"
    return p["net"]


def render_by_component(pads):
    by_ref = defaultdict(list)
    for p in pads:
        if p["kind"] == "pad":
            by_ref[p["refdes"]].append(p)
    out = ["# Pin → net by component",
           "",
           "Generated by `tools/ipc356.py` from the Proteus IPC-D-356A netlist. Do not edit.",
           "",
           "Net aliases: " + ", ".join(f"`{k}` → `{v}`" for k, v in NET_ALIASES.items()) + ".",
           "Refdes restored from 6-char truncation: "
           + ", ".join(f"`{v}`" for v in TRUNCATED_REFDES.values()) + ".",
           "`N/C` = explicitly unconnected in Proteus; `(no net)` = pad without any net record.",
           "Coordinates in mm, IPC orientation (Y up). Side: top/bottom for SMD, both for THT.",
           ""]
    groups = defaultdict(list)
    for ref in by_ref:
        groups[re.match(r"[A-Z_]*?(?=\d|$)", ref).group(0) or ref].append(ref)
    out.append("Index: " + ", ".join(
        f"{g} ({len(groups[g])})" for g in sorted(groups, key=natural_key)))
    out.append("")
    for ref in sorted(by_ref, key=natural_key):
        rows = sorted(by_ref[ref], key=lambda p: natural_key(p["pin"]))
        kinds = {"THT" if p["is_tht"] else "SMD" for p in rows}
        sides = {p["side"] for p in rows}
        out.append(f"## {ref}")
        out.append("")
        out.append(f"{len(rows)} pads, {'/'.join(sorted(kinds))}, side {'/'.join(sorted(sides))}")
        out.append("")
        out.append("| pin | net | x | y |")
        out.append("|---|---|---|---|")
        for p in rows:
            out.append(f"| {p['pin']} | {net_label(p)} | {p['x_mm']:.3f} | {p['y_mm']:.3f} |")
        out.append("")
    return "\n".join(out)


def render_by_net(pads):
    by_net = defaultdict(list)
    vias = Counter()
    for p in pads:
        if p["kind"] == "pad" and p["net"] and p["net"] != "N/C":
            by_net[p["net"]].append(f"{p['refdes']}-{p['pin']}")
        elif p["kind"] == "via":
            vias[p["net"]] += 1
    out = ["# Pins by net",
           "",
           "Generated by `tools/ipc356.py`. Do not edit. Nets with a single pin are",
           "usually test points or connections made through the ignored-by-IPC copper.",
           "",
           "| net | pins | vias | members |",
           "|---|---|---|---|"]
    for net in sorted(set(by_net) | set(vias), key=natural_key):
        members = sorted(by_net.get(net, []), key=natural_key)
        out.append(f"| {net} | {len(members)} | {vias.get(net, 0)} | {' '.join(members)} |")
    out.append("")
    return "\n".join(out)


def outputs(net_names, pads):
    return {
        "ipc356_pads.json": render_json(net_names, pads),
        "ipc356_pads.csv": render_csv(pads),
        "pin_nets_by_component.md": render_by_component(pads),
        "pins_by_net.md": render_by_net(pads),
    }


def self_check(net_names, pads, out_dir):
    errors = []
    st = stats(net_names, pads)
    for k, v in EXPECTED.items():
        if st[k] != v:
            errors.append(f"{k}: got {st[k]}, expected {v}")

    names = set(net_names.values())
    for raw, alias in NET_ALIASES.items():
        if raw not in names:
            errors.append(f"alias source net {raw!r} not in IPC")
        if alias in names:
            errors.append(f"alias target {alias!r} collides with an existing net")
    if len({NET_ALIASES.get(n, n) for n in names}) != len(names):
        errors.append("net names not unique after aliasing")
    used = {p["net_id"] for p in pads if p["net_id"]}
    unused = set(net_names) - used
    if unused:
        errors.append(f"declared nets without pads: {sorted(unused)}")

    # ACIN1/2 and ACOUT1/2 have two holes both numbered 1: fine if the net agrees.
    pin_nets = defaultdict(set)
    for p in pads:
        if p["kind"] == "pad":
            pin_nets[(p["refdes"], p["pin"])].add(p["net_raw"])
    conflicts = sorted(k for k, n in pin_nets.items() if len(n) > 1)
    if conflicts:
        errors.append(f"same refdes-pin on different nets: {conflicts}")
    for p in pads:
        exp = TRUNCATED_NETS.get(p["refdes"])
        if exp and p["net"] != exp:
            errors.append(f"{p['refdes']}: net {p['net']}, expected {exp}")

    for name, text in outputs(net_names, pads).items():
        f = out_dir / name
        if not f.exists() or f.read_text() != text:
            errors.append(f"{f.relative_to(ROOT)} is stale; run tools/ipc356.py")
    return st, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ipc", type=Path, default=DEFAULT_IPC)
    ap.add_argument("--out", type=Path, default=REF_DIR)
    ap.add_argument("--check", action="store_true",
                    help="verify counts and that the files in --out are up to date")
    args = ap.parse_args()

    net_names, pads = parse(args.ipc)
    if args.check:
        st, errors = self_check(net_names, pads, args.out)
        print("ipc356: " + ", ".join(f"{k}={v}" for k, v in st.items()))
        for e in errors:
            print("  FAIL " + e)
        print("ipc356: " + ("FAIL" if errors else "OK"))
        return 1 if errors else 0

    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in outputs(net_names, pads).items():
        (args.out / name).write_text(text)
    st = stats(net_names, pads)
    print("ipc356: " + ", ".join(f"{k}={v}" for k, v in st.items()))
    print(f"wrote {len(outputs(net_names, pads))} files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
