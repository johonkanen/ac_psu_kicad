"""Prep / finish of the routing-pass board copy (run under tools/p2k/bin/kipy). Coordinates: IPC frame (y up).

  kipy prep.py prep IN OUT      lock every existing track and via, add the temporary keep-outs that tell the router
                                the rules of routing_brief.md it cannot read from the board, draw the J11 west-row
                                escape stubs
  kipy prep.py unfence IN OUT   remove the two west fences (x < 0 and x 0..22, y < 36): the old copper of the divider
                                taps and of the relay line lies there, and the router fails those nets when its
                                target point is fenced (seen in run 2)
  kipy prep.py finish IN OUT    remove the temporary keep-outs, unlock

Temporary keep-outs (rule areas named "tmp route ...", tracks and vias not allowed, pours untouched):
  - the DC bus band x 58.9..118.1, y 43.2..48.8 on F.Cu / B.Cu (rule 2)
  - the passage north of J11 x 40..59, y 51.1..55 on F.Cu / B.Cu (rule 3: In3 / In4 only)
  - 2.5 mm around the bus wire pads BUSP1 / BUSN1 / BUSP2 / BUSN2 on F.Cu / B.Cu (rule 3a)
  - fences on all layers around the `unrouted` rectangles of lib/v5_copper.csv (widened to y 55.3 north of J8 /
    J11 and to y -25.5 at x 22..65, see prep()); check_pass.py reports new copper outside the rectangles.

J11 (2 x 19, 1.27 mm, pads 0.81 mm): the west row (even pins, x 44.90) is 0.1 mm from the west edge of the CTRL
area, so its only way out is east, between the pads of the east row: a 0.46 mm gap, which holds exactly one
0.152 mm track at 0.154 mm clearance. The router's grid cannot hit that, so the stubs are drawn here: from the
pad 45 degrees north-east into the gap above the pin (y + 0.635), then east to x 47.0. Pins 4..22 (to U15/U13/U16
and the filters, top side) on F.Cu, pins 24..36 (to U21/U19/U20, bottom side) on B.Cu.
"""
import math
import sys

import pcbnew

F = pcbnew.FromMM
TMP = "tmp route "


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


def keepout(b, name, pts, layers, vias=True):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(TMP + name)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(b.GetLayerID(l))
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(F(x), F(-y))
    b.Add(z)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def prep(b):
    n = 0
    for t in b.GetTracks():
        t.SetLocked(True)
        n += 1
    print(f"prep: {n} existing tracks and vias locked")
    fb = ["F.Cu", "B.Cu"]
    keepout(b, "bus band", rect(58.9, 43.2, 118.1, 48.8), fb)
    keepout(b, "passage north of J11", rect(40.0, 51.1, 59.0, 55.0), fb)
    for ref in ("BUSP1", "BUSN1", "BUSP2", "BUSN2"):
        fp = b.FindFootprintByReference(ref)
        pad = list(fp.Pads())[0]
        c = pad.GetPosition()
        r = pcbnew.ToMM(max(pad.GetSize(pcbnew.F_Cu).x, pad.GetSize(pcbnew.F_Cu).y)) / 2 + 2.5
        cx, cy = pcbnew.ToMM(c.x), -pcbnew.ToMM(c.y)
        ro = r / math.cos(math.pi / 16)
        keepout(b, f"bus wire pad {ref}", [(cx + ro * math.cos(a * math.pi / 8), cy + ro * math.sin(a * math.pi / 8))
                                           for a in range(16)], fb)
    # fences on all layers: the router stays in the `unrouted` rectangles of lib/v5_copper.csv, widened to the
    # passage height of the brief (y 55.3, the INU_OUT2 pads) and to y -25.5 at x 22..65 (the In2 track ends of
    # PWM_G2 / PWM_G4 / PWM_TRANS1 lie at y -24.5 .. -24.8, outside the rectangle)
    al = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
    for name, r in (("north", (-130, 55.3, 125, 80)), ("west", (-130, -90, 0, 55.3)), ("west 2", (0, -90, 22, 36)),
                    ("south 1", (22, -90, 65, -25.5)), ("south 2", (65, -90, 125, -62))):
        keepout(b, "fence " + name, rect(*r), al)
    # no track on the ground layers inside the card planes (pass 1 put a tap through the In4 ISOGND plane); vias allowed
    for i, r in enumerate(((44.4, 10.8, 95.1, 33.0), (58.9, -9.4, 118.1, 48.8), (102.5, -34.5, 118.1, 3.0), (42.5, -20.7, 85.5, 5.8))):
        keepout(b, f"planes {i}", rect(*r), ["In1.Cu", "In2.Cu", "In4.Cu"], vias=False)   # pass 3: In2 too
    # north-row pins of J6 / J4 that are reached from the south (under the bus band, In3): a 0.152 mm stub through
    # the 0.46 mm gap of the south row, like the J11 stubs
    m = 0
    for ref, num, dx, yend in (("J6", "43", -0.635, 49.9), ("J6", "47", 0.635, 50.0), ("J4", "43", -0.635, 48.7),
                               ("J4", "47", 0.635, 48.7)):
        pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
        x, y = pcbnew.ToMM(pad.GetPosition().x), -pcbnew.ToMM(pad.GetPosition().y)
        pts = [(x, y), (x + dx, y - 0.635), (x + dx, yend)]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(*a))
            t.SetEnd(P(*c))
            t.SetWidth(F(0.152))
            t.SetLayer(b.GetLayerID("In3.Cu"))
            t.SetNet(pad.GetNet())
            t.SetLocked(True)
            b.Add(t)
        m += 1
    print(f"prep: {m} J6 / J4 north-row escape stubs (In3)")
    j11 = b.FindFootprintByReference("J11")
    m = 0
    for pad in j11.Pads():
        num = int(pad.GetNumber())
        net = pad.GetNetname()
        if num % 2 or num < 4 or num > 36 or net.startswith("unconnected") or net in ("CTRLGND_A", "3V3_CTRL"):
            continue
        x, y = pcbnew.ToMM(pad.GetPosition().x), -pcbnew.ToMM(pad.GetPosition().y)
        lay = b.GetLayerID("F.Cu" if num <= 22 else "B.Cu")
        pts = [(x, y), (x + 0.635, y + 0.635), (47.0, y + 0.635)]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(*a))
            t.SetEnd(P(*c))
            t.SetWidth(F(0.152))
            t.SetLayer(lay)
            t.SetNet(pad.GetNet())
            t.SetLocked(True)
            b.Add(t)
        m += 1
    print(f"prep: {m} J11 west-row escape stubs")


def finish(b):
    zs = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith(TMP)]
    for z in zs:
        b.Delete(z)
    n = 0
    for t in b.GetTracks():
        n += t.IsLocked()
        t.SetLocked(False)
    print(f"finish: {len(zs)} temporary keep-outs removed, {n} tracks and vias unlocked")


def unfence(b):
    zs = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith(TMP + "fence west")]
    for z in zs:
        b.Delete(z)
    print(f"unfence: {len(zs)} west fences removed")


# The router does not know the 5 mm rules between the net classes; the barrier strips (rule areas) stop it only
# where they are drawn. Where two domains meet without a strip (south of the ISO aux area at y < -53, around the
# primary area, west of the card) it walked an ISO net through the primary and aux areas (pass 2, first try). So
# each router step gets the fence of its domain: everything that belongs to the other side.
DOMAIN_FENCES = {
    "I": [(-130, -90, 88.0, 8.3), (88.0, -90, 125, -48.0)],           # primary area, aux primary side, south of IA
    "P": [(-130, 8.3, 125, 80), (88.0, -53.0, 125, 8.3)],             # north of the C|P line; the ISO side down to
                                                                      # y -53 (IA ends at -48: 5 mm)
    "C": [],                                                          # both CTRL pieces are ringed by strips
}


def domain(b, dom):
    zs = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith(TMP + "domain")]
    for z in zs:
        b.Delete(z)
    al = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
    for i, r in enumerate(DOMAIN_FENCES[dom]):
        keepout(b, f"domain {dom} {i}", rect(*r), al)
    print(f"domain: fences for {dom} ({len(DOMAIN_FENCES[dom])})")


def prune(b, ref):
    """Delete new copper (not in the placed board `ref`) that lies in a fence (the router laid a 15V track through
    the west fence in pass 2: its power-net passes do not honour keep-outs). Reports what it deletes."""
    def key(t):
        if t.Type() == pcbnew.PCB_VIA_T:
            return ("via", t.GetPosition().x, t.GetPosition().y, t.GetNetname())
        a, c = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        return ("trk", t.GetLayer(), min(a, c), max(a, c), t.GetWidth(), t.GetNetname())
    old = {key(t) for t in pcbnew.LoadBoard(ref).GetTracks()}
    fences = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith(TMP + "fence")]
    dead = []
    for t in b.GetTracks():
        if key(t) in old:
            continue
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if any(z.Outline().Contains(q) for z in fences for q in pts):
            dead.append(t)
    for t in dead:
        q = t.GetPosition() if t.Type() == pcbnew.PCB_VIA_T else t.GetStart()
        print(f"prune: {t.GetNetname()} {b.GetLayerName(t.GetLayer())} at ({pcbnew.ToMM(q.x):.1f}, {-pcbnew.ToMM(q.y):.1f}) deleted (inside a fence)")
        b.Delete(t)
    print(f"prune: {len(dead)} new tracks / vias inside the fences deleted")


def main():
    mode, src, dst = sys.argv[1:4]
    if mode == "prune":
        b = pcbnew.LoadBoard(src)
        prune(b, sys.argv[4])
        b.Save(dst)
        return
    b = pcbnew.LoadBoard(src)
    if mode == "domain":
        domain(b, sys.argv[4])
    else:
        {"prep": prep, "finish": finish, "unfence": unfence}[mode](b)
    b.Save(dst)


main()
