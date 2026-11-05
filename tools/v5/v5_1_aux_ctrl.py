#!/usr/bin/env python3
"""v5 step 1 (run once, kipy): bring the v5 schematic (aux flyback, CTRL isolation; V5_PLAN.md,
CTRL_ISOLATION_PLAN.md) onto the frozen board. Layout itself is GUI work (V5_PLAN.md D5 and
CTRL_ISOLATION_PLAN.md 4): this script only makes the board match the netlist and stages the parts.

  1. delete the removed Proteus parts (lib/v5_deviations.csv kind remove: the IW1830 supply),
     the tracks/vias/zones of nets that are left without any pad, and the track stubs this leaves
     dangling inside the aux area;
  2. rename the copper of 20V -> 15V and 20V_ISO_SEC -> 15V_ISO;
  3. moved pins (kind pin, fix v5: J11, J12, U13/U15/U16 and C82/C83/C86 to the CTRL nets): the pad
     takes its new net and the copper chain hanging off it (tracks, and vias that lead nowhere
     else) is deleted up to the first pad or branch, so no old-domain copper stays on a CTRL pad;
  4. place every new v5 part, unrouted, in a staging area below the board (IPC y < -85), grouped
     as aux flyback / CTRL island B / CTRL island A, nets from the schematic.
Everything left to do is inside the pending-layout areas of lib/v5_copper.csv.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v4"))
sys.path.insert(0, HERE)
from v4board import Board, F, T, load_fp  # noqa: E402
import v5_parts as V  # noqa: E402
import deviations  # noqa: E402

AUX = (65.0, -62.0, 110.0, -10.0)        # aux area (IPC frame) for the dangling-stub clean-up
STAGE_X0, STAGE_Y0 = -125.0, -92.0       # staging area top-left (IPC frame), rows grow downwards
STAGE_W = 240.0

b = Board(5001)
if b.fp("T1") is not None:
    raise SystemExit("v5 step 1 already applied (T1 is on the board)")


def inside(x, y, a):
    return a[0] <= x <= a[2] and a[1] <= y <= a[3]


def pt(v):
    return (T(v.x), -T(v.y))


# -- 1. removed parts and their copper -------------------------------------------------------
before = {}
for fp in b.b.GetFootprints():
    for pad in fp.Pads():
        before.setdefault(pad.GetNetname(), set()).add(fp.GetReference())
for ref in V.REMOVED:
    fp = b.fp(ref)
    if fp is None:
        raise SystemExit(f"v5: {ref} not on the board")
    b.b.Delete(fp)
b.log.append(f"deleted {len(V.REMOVED)} footprints: {' '.join(V.REMOVED)}")
after = {}
for fp in b.b.GetFootprints():
    for pad in fp.Pads():
        after.setdefault(pad.GetNetname(), set()).add(fp.GetReference())
dead = sorted(n for n in before if n and n not in after)
nt = sum(1 for t in b.b.GetTracks() if t.GetNetname() in dead)
nz = [z for z in b.b.Zones() if not z.GetIsRuleArea() and z.GetNetname() in dead]
for t in [t for t in b.b.GetTracks() if t.GetNetname() in dead]:
    b.b.Delete(t)
for z in nz:
    b.b.Delete(z)
b.log.append(f"{len(dead)} nets left without pads: {' '.join(dead)}; deleted {nt} tracks/vias, {len(nz)} zones")

# -- 2. renames ---------------------------------------------------------------------------------
for old, new in V.RENAMES.items():
    b.renet(old, new)

# -- 3. moved pins -------------------------------------------------------------------------------
EPS = F(0.002)


def chain_from(pad):
    """Tracks/vias hanging off `pad`: follow single chains, stop at pads and branches; a via joins
    the chain only when at most one other track meets it (it then leads on, or nowhere)."""
    net = pad.GetNetCode()
    items = [t for t in b.b.GetTracks() if t.GetNetCode() == net]
    tracks = [t for t in items if t.GetClass() != "PCB_VIA"]
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    pads = [p for fp in b.b.GetFootprints() for p in fp.Pads() if p.GetNetCode() == net]

    def at(p, layer):
        hits = [t for t in tracks if t.GetLayer() == layer and (abs(t.GetStart().x - p.x) <= EPS and abs(t.GetStart().y - p.y) <= EPS
                                                               or abs(t.GetEnd().x - p.x) <= EPS and abs(t.GetEnd().y - p.y) <= EPS)]
        return hits

    def on_pad(p, layer, skip):
        return any(q is not skip and q.IsOnLayer(layer) and q.HitTest(p) for q in pads)

    out, todo = [], []
    for t in tracks:
        for p in (t.GetStart(), t.GetEnd()):
            if pad.IsOnLayer(t.GetLayer()) and pad.HitTest(p):
                todo.append((t, p))
    seen = set()
    while todo:
        t, came = todo.pop()
        if id(t) in seen:
            continue
        seen.add(id(t))
        out.append(t)
        far = t.GetEnd() if (abs(t.GetStart().x - came.x) <= EPS and abs(t.GetStart().y - came.y) <= EPS) else t.GetStart()
        if on_pad(far, t.GetLayer(), None):
            continue
        via = next((v for v in vias if abs(v.GetPosition().x - far.x) <= EPS and abs(v.GetPosition().y - far.y) <= EPS), None)
        if via is not None:
            others = [u for lay in range(pcbnew.PCB_LAYER_ID_COUNT) if via.IsOnLayer(lay) and pcbnew.IsCopperLayer(lay)
                      for u in at(far, lay) if u is not t]
            if len(others) <= 1 and id(via) not in seen:
                seen.add(id(via))
                out.append(via)
                todo += [(u, far) for u in others]
            continue
        nxt = [u for u in at(far, t.GetLayer()) if u is not t]
        if len(nxt) == 1:
            todo.append((nxt[0], far))
    return out


moved = [(r["ref"], r["pin"], r["to"]) for r in deviations.rows() if r["kind"] == "pin" and r["fix"] == "v5"]
ncut = 0
for ref, pin, net in moved:
    pad = next(p for p in b.fp(ref).Pads() if p.GetNumber() == pin)
    cut = chain_from(pad)
    for t in cut:
        b.b.Delete(t)
    ncut += len(cut)
    b.log.append(f"{ref}-{pin}: {pad.GetNetname()} -> {net}; cut {len(cut)} tracks/vias")
    pad.SetNet(b.net(b.pin_net[(ref, pin)]))
for fp in b.b.GetFootprints():
    b.sync_pads(fp.GetReference())

# dangling stubs inside the aux area (left by the removed parts): repeat until none is left
def anchored(p, layer, me):
    for fp in b.b.GetFootprints():
        for q in fp.Pads():
            if q.IsOnLayer(layer) and q.HitTest(p):
                return True
    for t in b.b.GetTracks():
        if t is me:
            continue
        if t.GetClass() == "PCB_VIA":
            if t.IsOnLayer(layer) and abs(t.GetPosition().x - p.x) <= EPS and abs(t.GetPosition().y - p.y) <= EPS:
                return True
        elif t.GetLayer() == layer and (t.HitTest(p) or abs(t.GetStart().x - p.x) <= EPS and abs(t.GetStart().y - p.y) <= EPS
                                         or abs(t.GetEnd().x - p.x) <= EPS and abs(t.GetEnd().y - p.y) <= EPS):
            return True
    for z in b.b.Zones():
        if not z.GetIsRuleArea() and z.GetNetCode() == me.GetNetCode() and z.IsOnLayer(layer) and z.HitTestFilledArea(layer, p):
            return True
    return False


pcbnew.ZONE_FILLER(b.b).Fill(b.b.Zones())
nstub = 0
while True:
    stubs = []
    for t in b.b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = pt(t.GetPosition())
            if not inside(x, y, AUX):
                continue
            lays = [l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l) and t.IsOnLayer(l)]
            n = sum(1 for l in lays if anchored(t.GetPosition(), l, t))
            if n <= 1:
                stubs.append(t)
            continue
        ends = [t.GetStart(), t.GetEnd()]
        if not all(inside(*pt(e), AUX) for e in ends):
            continue
        if not all(anchored(e, t.GetLayer(), t) for e in ends):
            stubs.append(t)
    if not stubs:
        break
    for t in stubs:
        b.b.Delete(t)
    nstub += len(stubs)
b.log.append(f"cut {ncut} tracks/vias off the moved pads; removed {nstub} dangling stubs/vias in the aux area")

# -- 4. new parts in the staging area ----------------------------------------------------------
ISLAND_B = set("W1 J13 PEC2 U28 L2 D16 C137 C138 C139 C140 C141 C142 C143 C144 R131 R132 R133 R134 R135".split())
GROUPS = [("aux flyback", [p for p in V.PARTS if p[1] == 7 and p[0] not in ISLAND_B]),
          ("CTRL island B", [p for p in V.PARTS if p[0] in ISLAND_B]),
          ("CTRL island A", [p for p in V.PARTS if p[1] == 11])]
assert sum(len(g[1]) for g in GROUPS) == len(V.PARTS)
y = STAGE_Y0
for title, parts in GROUPS:
    x, rowh = STAGE_X0, 0.0
    b.log.append(f"staging: {title} from y {y:.1f}")
    for ref, sheet, sym, value, fpid, note in parts:
        c = b.comps[ref]
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
            fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
        fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
        fp.SetSheetname(c["sheetname"])
        fp.SetSheetfile(c["sheetfile"])
        b.b.Add(fp)
        fp.thisown = False
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False)
        w, h = T(bb.GetWidth()) + 1.0, T(bb.GetHeight()) + 1.0
        if x + w > STAGE_X0 + STAGE_W:
            x, y = STAGE_X0, y - rowh
            rowh = 0.0
        # put the courtyard's top-left corner at (x, y)
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False)
        fp.SetPosition(pcbnew.VECTOR2I(F(x + 0.5) - bb.GetLeft(), F(-(y - 0.5)) - bb.GetTop()))
        for pad in fp.Pads():
            net = b.pin_net.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(b.net(net))
        x += w
        rowh = max(rowh, h)
    y -= rowh + 4.0
b.log.append(f"placed {len(V.PARTS)} v5 parts in the staging area (IPC y {STAGE_Y0} .. {y:.1f})")
b.save("v5 step 1: v5 netlist on the board (parts removed/renamed/moved, new parts staged)")
