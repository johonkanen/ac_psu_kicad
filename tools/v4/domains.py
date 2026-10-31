"""Insulation domains of the nets (stdlib only): P = primary (mains, DC link, GND/PGND side),
I = isolated DC/AC output side (ISOGND/ISOPGND), E = protective earth (PE terminals).

Nets are joined through every part except the barrier parts, which are split into their sides:
TR1 (DAB transformer, off-board: PRI/SEC nets), TR2 (aux transformer: pins 1-5 / 6-10),
U13/U15/U16/U17 (digital isolators: 1-8 / 9-16), U4/U5/U6 (isolated modulators: 1-4 / 5-8) and
the Y capacitors (each pin on its own). A group is P if it holds GND, PGND or DC+, I if it holds
ISOGND, ISOPGND or ISODC+, and E if it holds a pin of a PE terminal; anything else is None
(unconnected pins of the spare U17).

Used by tools/v4/fix_14_insulation_gaps.py and tools/v4/domain_gaps.py (IEC 61010-1 spacing:
P <-> I reinforced, P/I <-> E basic; see STATUS.md "v4 fix 13/14").
"""
YCAPS = set("C7 C10 C13 C14 C19 C20 C22 C23 C29 C30 C31 C32 C59 C60".split())
P_SEEDS = {"GND", "PGND", "DC+"}
I_SEEDS = {"ISOGND", "ISOPGND", "ISODC+"}
# required copper gap (mm) between domains on one layer: reinforced P-I, basic to PE
GAP = {frozenset("PI"): 5.0, frozenset("PE"): 2.5, frozenset("IE"): 2.5}


def short(net):
    return net.split("/")[-1]


def _side(ref, pin, net):
    if ref == "TR1":
        return "PRI" in net
    if ref == "TR2":
        return int(pin) <= 5
    if ref in ("U13", "U15", "U16", "U17"):
        return int(pin) <= 8
    if ref in ("U4", "U5", "U6"):
        return int(pin) <= 4
    if ref in YCAPS:
        return pin
    return 0


def classify(nets):
    """nets: {net name: [(ref, pin), ...]} (board_common.export_netlist) -> {net name: 'P'|'I'|'E'|None}"""
    parent = {n: n for n in nets}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    groups = {}
    for net, nodes in nets.items():
        for ref, pin in nodes:
            groups.setdefault((ref, _side(ref, pin, net)), []).append(net)
    for members in groups.values():
        for n in members[1:]:
            parent[find(n)] = find(members[0])
    seeds = {}
    for net, nodes in nets.items():
        s = seeds.setdefault(find(net), set())
        if short(net) in P_SEEDS:
            s.add("P")
        if short(net) in I_SEEDS:
            s.add("I")
        if any(ref.startswith("PE") and ref[2:].isdigit() for ref, _ in nodes):
            s.add("E")
    out = {}
    for net in nets:
        s = seeds.get(find(net), set())
        if len(s) > 1:
            raise ValueError(f"net {net} joins domains {sorted(s)}: a barrier part is missing from tools/v4/domains.py")
        out[net] = next(iter(s)) if s else None
    return out


def gap(a, b):
    """Required gap between two domains (None = same domain or unclassified)."""
    if not a or not b or a == b:
        return None
    return GAP[frozenset((a, b))]
