"""Intended deviations of the v4 design from the Proteus v3 original (stdlib only).

lib/v4_deviations.csv  netlist / parts / values (kinds merge, pin, part, add, value)
lib/v4_copper.csv      board copper (kinds via = via not in Proteus, area = rectangle where the
                       board copper may differ from the Proteus copper)
lib/v5_deviations.csv  v5 (aux flyback, CTRL isolation): the same kinds plus
                       remove = Proteus part deleted (its pins/pads leave the reference),
                       rename = whole IPC net renamed to a new net name,
                       refdes = Proteus refdes -> KiCad refdes (KiCad wants a trailing number);
                       the rows of the other kinds keep the Proteus refdes, rows() maps them
                       moved  = Proteus part placed elsewhere (v5 card-area layout): its pads are
                       not compared with the Proteus positions, pad numbers and nets still are
lib/v6_deviations.csv  v6 (baseboard for the half-bridge power cards, V6_PLAN.md): the same kinds
lib/v6_copper.csv      v6 board copper: the same kinds as lib/v5_copper.csv, plus
                       gone = a v4 via (kind via of lib/v4_copper.csv) at (x, y) deleted with its circuit
lib/v5_copper.csv      v5 board copper: area rows as above, and pending = rectangle where the
                       layout is left to the KiCad GUI (unrouted new parts, re-cut planes): DRC
                       clearance/unconnected items, opens and domain gaps there are reported as
                       pending, not as failures;
                       unrouted = rectangle that is placed but not routed yet: the copper may differ
                       from Proteus, and only DRC unconnected items, opens and missing Proteus vias
                       are excused there. Clearance and domain gaps are strict.
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
DEV_CSVS = [DEV_CSV, os.path.join(ROOT, "lib", "v5_deviations.csv"), os.path.join(ROOT, "lib", "v6_deviations.csv")]
COPPER_CSVS = [COPPER_CSV, os.path.join(ROOT, "lib", "v5_copper.csv"), os.path.join(ROOT, "lib", "v6_copper.csv")]
IPC_JSON = os.path.join(ROOT, "reference", "ipc356_pads.json")


def proteus_mode():
    return os.environ.get("AC_PSU_PROTEUS") == "1"


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def _read_all(paths):
    return [r for p in paths for r in _read(p)]


def refdes_map():
    """Proteus refdes -> KiCad refdes (kind refdes, v5)."""
    if proteus_mode():
        return {}
    return {r["from"]: r["to"] for r in _read_all(DEV_CSVS) if r["kind"] == "refdes"}


def kref(ref):
    """KiCad refdes of a Proteus refdes."""
    return refdes_map().get(ref, ref)


def rows():
    """Deviation rows, refdes in the KiCad naming. A part removed by a later revision (kind remove) takes the
    rows an earlier revision wrote for it along (a v4 part or value that v6 deletes again)."""
    if proteus_mode():
        return []
    m = refdes_map()
    out = []
    for r in _read_all(DEV_CSVS):
        if r.get("ref") in m:
            r = dict(r, ref=m[r["ref"]])
        out.append(r)
    gone = {r["ref"] for r in out if r["kind"] == "remove"}
    return [r for r in out if r["kind"] == "remove" or r.get("ref") not in gone]


def copper_rows():
    return [] if proteus_mode() else _read_all(COPPER_CSVS)


def gone_vias():
    """[(x, y)] of v4 vias (lib/v4_copper.csv kind via) that a later revision deleted with their circuit
    (kind gone in lib/v6_copper.csv)."""
    return [(float(r["x"]), float(r["y"])) for r in copper_rows() if r["kind"] == "gone"]


def removed():
    """Refdes of removed parts, in the KiCad naming and, for a renamed part (AFE_OUT -> AFE_OUT1), also in the
    Proteus naming, so that callers keyed by either find it (v6 deletes the renamed AFE_OUT1)."""
    gone = {r["ref"] for r in rows() if r["kind"] == "remove"}
    back = {k: p for p, k in refdes_map().items()}
    return gone | {back[g] for g in gone if g in back}


def renames():
    """IPC net -> new net name (kind rename, v5)."""
    return {r["from"]: r["to"] for r in rows() if r["kind"] == "rename"}


def pending_areas():
    """[(x0, y0, x1, y1, note)] where the v5 layout is left to the KiCad GUI."""
    out = []
    for r in copper_rows():
        if r["kind"] == "pending":
            x0, x1 = sorted((float(r["x"]), float(r["x1"])))
            y0, y1 = sorted((float(r["y"]), float(r["y1"])))
            out.append((x0, y0, x1, y1, r["note"]))
    return out


def in_pending(x, y, margin=0.0):
    return any(x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin
               for x0, y0, x1, y1, _ in pending_areas())


def wire_links():
    """[(net, (x, y), (x1, y1), note)] off-board wire links between two pads of one net (kind wire,
    lib/v5_copper.csv): the checks count the two pads as joined (v5 step 6: DC bus past J11)."""
    return [(r["net"], (float(r["x"]), float(r["y"])), (float(r["x1"]), float(r["y1"])), r["note"])
            for r in copper_rows() if r["kind"] == "wire"
            and not any(u["kind"] == "unwire" and (u["x"], u["y"], u["x1"], u["y1"]) == (r["x"], r["y"], r["x1"], r["y1"])
                        for u in copper_rows())]


def unrouted_areas():
    """[(x0, y0, x1, y1, note)] placed, not yet routed (kind unrouted)."""
    out = []
    for r in copper_rows():
        if r["kind"] == "unrouted":
            x0, x1 = sorted((float(r["x"]), float(r["x1"])))
            y0, y1 = sorted((float(r["y"]), float(r["y1"])))
            out.append((x0, y0, x1, y1, r["note"]))
    return out


def in_unrouted(x, y, margin=0.0):
    return any(x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin
               for x0, y0, x1, y1, _ in unrouted_areas())


def moved_parts():
    """refdes of Proteus parts placed elsewhere in v5 (kind moved)."""
    return {r["ref"] for r in rows() if r["kind"] == "moved"}


def v5_cut_nets():
    """IPC nets (after merges/renames) whose copper chain was cut off a v5-moved pad
    (tools/v5/v5_1_aux_ctrl.py step 3): their Proteus vias/copper may be gone outside the
    pending areas too (the ISO-side PWM bundle J11 -> J4/J6/J8 is re-routed in the GUI)."""
    return {new_net(r["from"]) for r in rows() if r["kind"] == "pin" and r.get("fix") in ("v5", "v6")}


def v5_parts():
    """refdes of parts added in v5 (part rows of lib/v5_deviations.csv)."""
    return {r["ref"] for p in DEV_CSVS[1:] for r in _read(p) if r["kind"] == "part"} if not proteus_mode() else set()


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


def footprint_changes():
    """ref -> (old footprint, new footprint, fix, note) for existing parts whose footprint is swapped.
    Their pads are not compared with the Proteus pads; instead every pad must lie in a terminal area
    (lib/v4_copper.csv: area on layer *, note starting with the refdes) on the net of the IPC pin."""
    return {r["ref"]: (r["from"], r["to"], r["fix"], r["note"]) for r in rows() if r["kind"] == "footprint"}


def terminal_area(ref):
    """(x0, y0, x1, y1) of the copper area of a swapped footprint (area row, layer *, note 'REF ...'). The last
    matching row wins: a later list (v6) may move the terminal (v6 step 3: INU_OUT2)."""
    found = None
    for r in copper_rows():
        if r["kind"] == "area" and r["layer"] == "*" and kref(r["note"].split(" ", 1)[0]) == kref(ref):
            x0, x1 = sorted((float(r["x"]), float(r["x1"])))
            y0, y1 = sorted((float(r["y"]), float(r["y1"])))
            found = (x0, y0, x1, y1)
    return found


def in_terminal_area(x, y, margin=0.0):
    """refdes of the swapped footprint whose terminal area holds (x, y), or None."""
    for ref in footprint_changes():
        a = terminal_area(ref)
        if a and a[0] - margin <= x <= a[2] + margin and a[1] - margin <= y <= a[3] + margin:
            return ref
    return None


def tie_anchors():
    """{lead ref: (x0, y0, x1, y1)} of the cable-tie anchors (area rows, layer *, note 'TIE <REF> ...').
    The board-only footprints TIE_<REF> (two NPTH holes) must lie inside; v4 fix 15."""
    out = {}
    for r in copper_rows():
        if r["kind"] == "area" and r["layer"] == "*" and r["note"].startswith("TIE "):
            x0, x1 = sorted((float(r["x"]), float(r["x1"])))
            y0, y1 = sorted((float(r["y"]), float(r["y1"])))
            out[kref(r["note"].split()[1])] = (x0, y0, x1, y1)
    return out


def value_changes():
    """ref -> (old, new) for existing parts"""
    return {r["ref"]: (r["from"], r["to"]) for r in rows() if r["kind"] == "value" and r["from"]}


def new_net(net):
    """IPC net -> v4/v5 net for whole-net merges and renames."""
    net = merges().get(net, net)
    return renames().get(net, net)


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
    gone = removed()
    m = refdes_map()
    for p in recs:
        if p["kind"] == "pad" and p.get("refdes") in gone:
            continue
        q = copy.copy(p)
        if q.get("refdes") in m:
            q["refdes"] = m[q["refdes"]]
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
    gone = removed()
    m = refdes_map()
    out = {(m.get(rp[0], rp[0]), rp[1]): (v4_net(m.get(rp[0], rp[0]), rp[1], n) if n not in ("N/C", "(no net)") else n)
           for rp, n in pin_net.items() if rp[0] not in gone}
    for ref, p in added_parts().items():
        for pin, net in p["pins"].items():
            out[(ref, pin)] = new_net(net)   # v5 renames apply to the v4 parts' rows too
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
    return in_pending(x, y, margin) or in_unrouted(x, y, margin)   # v5: changed copper too


def validate():
    """Errors where a deviation row does not match the Proteus reference (stale or wrong)."""
    with open(IPC_JSON) as f:
        recs = json.load(f)["pads"]
    nets = {p["net"] for p in recs if p.get("net")}
    pins = {(p["refdes"], p["pin"]): p["net"] for p in recs if p["kind"] == "pad"}
    refs = {p["refdes"] for p in recs if p["kind"] == "pad"}
    errs = []
    allrows = _read_all(DEV_CSVS)
    for r in allrows:
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
        elif k == "remove":
            if r["ref"] not in refs and not any(a["kind"] == "part" and a["ref"] == r["ref"] for a in allrows):
                errs.append(f"remove {r['ref']}: refdes is not in the IPC")
        elif k == "rename":
            if r["from"] not in nets:
                errs.append(f"rename {r['from']}->{r['to']}: {r['from']} is not an IPC net")
            if r["to"] in nets:
                errs.append(f"rename {r['from']}->{r['to']}: {r['to']} is already an IPC net (use merge)")
        elif k == "refdes":
            if r["from"] not in refs:
                errs.append(f"refdes {r['from']}->{r['to']}: {r['from']} is not an IPC refdes")
            if r["to"] in refs:
                errs.append(f"refdes {r['from']}->{r['to']}: {r['to']} is already an IPC refdes")
        elif k == "moved":
            if r["ref"] not in refs:
                errs.append(f"moved {r['ref']}: refdes is not in the IPC")
        elif k == "footprint":
            if r["ref"] not in refs:
                errs.append(f"footprint {r['ref']}: refdes is not in the IPC")
            if terminal_area(r["ref"]) is None:
                errs.append(f"footprint {r['ref']}: no terminal area (lib/v4_copper.csv, layer *, note '{r['ref']} ...')")
        else:
            errs.append(f"unknown kind {k!r}")
    newnets = {r["to"] for r in allrows if r["kind"] in ("pin", "rename")}
    gone = removed()
    for r in rows():
        if r["kind"] in ("pin", "value", "footprint", "moved") and r["ref"] in gone:
            errs.append(f"{r['kind']} {r['ref']}: the part is removed (kind remove)")
    v5new = v5_parts()
    for ref, p in added_parts().items():
        for pin, net in p["pins"].items():
            if ref in v5new:
                continue  # v5 parts bring their own new nets (checked against the schematic by compare)
            if net not in nets and net not in newnets:
                errs.append(f"add {ref}-{pin}: net {net} is neither an IPC net nor a new v4 net")
    return errs


def summary():
    r = rows()
    c = {}
    for x in r:
        c[x["kind"]] = c.get(x["kind"], 0) + 1
    cr = copper_rows()
    return (f"v4/v5 deviations: {c.get('merge', 0)} net merges, {c.get('rename', 0)} net renames, "
            f"{c.get('refdes', 0)} refdes renames, "
            f"{c.get('pin', 0)} pin moves, {c.get('remove', 0)} removed parts, "
            f"{c.get('part', 0)} new parts ({c.get('add', 0)} pins), {c.get('value', 0)} values, "
            f"{c.get('footprint', 0)} footprints, {c.get('moved', 0)} moved parts; "
            f"copper: {sum(1 for x in cr if x['kind'] == 'via')} new vias, "
            f"{sum(1 for x in cr if x['kind'] == 'area')} changed areas, "
            f"{sum(1 for x in cr if x['kind'] == 'pending')} pending-layout areas, "
            f"{sum(1 for x in cr if x['kind'] == 'unrouted')} unrouted areas")
