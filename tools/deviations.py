"""Intended deviations of the v4 design from the Proteus v3 original (stdlib only).

lib/v4_deviations.csv  netlist / parts / values (kinds merge, pin, part, add, value)
lib/v4_copper.csv      board copper (kinds via = via not in Proteus, area = rectangle where the
                       board copper may differ from the Proteus copper)
Coordinates in mm, IPC frame (Y up).

Every check that compares the design with the Proteus CADCAM files applies exactly these
deviations to the Proteus reference and nothing else, so any other difference still fails.
`validate()` checks that each row still matches the Proteus data (no stale deviations).
Set AC_PSU_PROTEUS=1 to get the raw Proteus reference (tools/make_pcb.sh does).
"""
import copy
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_CSV = os.path.join(ROOT, "lib", "v4_deviations.csv")
COPPER_CSV = os.path.join(ROOT, "lib", "v4_copper.csv")
IPC_JSON = os.path.join(ROOT, "reference", "ipc356_pads.json")


def proteus_mode():
    return os.environ.get("AC_PSU_PROTEUS") == "1"


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def rows():
    return [] if proteus_mode() else _read(DEV_CSV)


def copper_rows():
    return [] if proteus_mode() else _read(COPPER_CSV)


def merges():
    return {r["from"]: r["to"] for r in rows() if r["kind"] == "merge"}


def pin_moves():
    return {(r["ref"], r["pin"]): (r["from"], r["to"]) for r in rows() if r["kind"] == "pin"}


def added_parts():
    """ref -> {'footprint', 'value', 'pins': {pin: net}, 'fix'}"""
    out = {}
    for r in rows():
        if r["kind"] == "part":
            out.setdefault(r["ref"], {"pins": {}, "value": None})
            out[r["ref"]].update(footprint=r["to"], fix=r["fix"], note=r["note"])
    for r in rows():
        if r["kind"] == "add":
            out[r["ref"]]["pins"][r["pin"]] = r["to"]
        elif r["kind"] == "value" and r["ref"] in out:
            out[r["ref"]]["value"] = r["to"]
    return out


def value_changes():
    """ref -> (old, new) for existing parts"""
    return {r["ref"]: (r["from"], r["to"]) for r in rows() if r["kind"] == "value" and r["from"]}


def new_net(net):
    """IPC net -> v4 net for whole-net merges."""
    return merges().get(net, net)


def v4_net(ref, pin, net):
    mv = pin_moves().get((ref, pin))
    if mv:
        return mv[1]
    return new_net(net)


def apply_records(recs):
    """IPC records (reference/ipc356_pads.json 'pads') with the v4 nets (copies)."""
    if proteus_mode():
        return recs
    out = []
    for p in recs:
        q = copy.copy(p)
        if q.get("net") and q.get("net_raw") != "N/C":
            n = v4_net(q.get("refdes", ""), q.get("pin", ""), q["net"]) if q["kind"] == "pad" else new_net(q["net"])
            if n != q["net"]:
                q["net"] = n
                q["net_raw"] = n
                q["v4_deviation"] = True
        out.append(q)
    return out


def apply_pin_nets(pin_net):
    """{(ref, pin): net} of the IPC -> v4 (net moves and added parts' pins)."""
    if proteus_mode():
        return pin_net
    out = {rp: (v4_net(rp[0], rp[1], n) if n not in ("N/C", "(no net)") else n) for rp, n in pin_net.items()}
    for ref, p in added_parts().items():
        for pin, net in p["pins"].items():
            out[(ref, pin)] = net
    return out


def vias():
    """[(x, y, net, note)] vias that are not in Proteus."""
    return [(float(r["x"]), float(r["y"]), r["net"], r["note"]) for r in copper_rows() if r["kind"] == "via"]


def areas():
    """[(layer, x0, y0, x1, y1, note)] where the copper may differ from Proteus ('*' = all layers)."""
    out = []
    for r in copper_rows():
        if r["kind"] == "area":
            x0, x1 = sorted((float(r["x"]), float(r["x1"])))
            y0, y1 = sorted((float(r["y"]), float(r["y1"])))
            out.append((r["layer"], x0, y0, x1, y1, r["note"]))
    return out


def in_area(layer, x, y, margin=0.0):
    for l, x0, y0, x1, y1, _ in areas():
        if (l in ("*", layer)) and x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
            return True
    return False


def validate():
    """Errors where a deviation row does not match the Proteus reference (stale or wrong)."""
    with open(IPC_JSON) as f:
        recs = json.load(f)["pads"]
    nets = {p["net"] for p in recs if p.get("net")}
    pins = {(p["refdes"], p["pin"]): p["net"] for p in recs if p["kind"] == "pad"}
    refs = {p["refdes"] for p in recs if p["kind"] == "pad"}
    errs = []
    for r in _read(DEV_CSV):
        k = r["kind"]
        if k == "merge":
            for n in (r["from"], r["to"]):
                if n not in nets:
                    errs.append(f"merge {r['from']}->{r['to']}: {n} is not an IPC net")
        elif k == "pin":
            if pins.get((r["ref"], r["pin"])) != r["from"]:
                errs.append(f"pin {r['ref']}-{r['pin']}: IPC net {pins.get((r['ref'], r['pin']))}, row says {r['from']}")
        elif k in ("part", "add"):
            if r["ref"] in refs:
                errs.append(f"{k} {r['ref']}: refdes exists in the IPC")
        elif k == "value":
            pass
        else:
            errs.append(f"unknown kind {k!r}")
    newnets = {r["to"] for r in _read(DEV_CSV) if r["kind"] == "pin"}
    for ref, p in added_parts().items():
        for pin, net in p["pins"].items():
            if net not in nets and net not in newnets:
                errs.append(f"add {ref}-{pin}: net {net} is neither an IPC net nor a new v4 net")
    return errs


def summary():
    r = rows()
    c = {}
    for x in r:
        c[x["kind"]] = c.get(x["kind"], 0) + 1
    cr = copper_rows()
    return (f"v4 deviations: {c.get('merge', 0)} net merges, {c.get('pin', 0)} pin moves, "
            f"{c.get('part', 0)} new parts ({c.get('add', 0)} pins), {c.get('value', 0)} values; "
            f"copper: {sum(1 for x in cr if x['kind'] == 'via')} new vias, "
            f"{sum(1 for x in cr if x['kind'] == 'area')} changed areas")
