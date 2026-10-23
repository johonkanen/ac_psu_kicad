"""Helpers for the one-shot v4 board edit scripts tools/v4/fix_*.py (run under tools/p2k/bin/kipy).

The design board kicad/ac_psu.kicad_pcb is frozen (no longer generated from the Proteus
gerbers); each fix script loads it, makes its change and saves it. They are kept for
traceability and are not meant to be re-run (each one checks that it has not been applied yet).
Coordinates are mm in the IPC frame (Y up), as everywhere in STATUS.md; KiCad y = -y.
Afterwards: tools/check_all.sh.
"""
import math
import os
import sys

import pcbnew

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "p2k"))
import board_common as bc  # noqa: E402
from build_pcb import load_fp  # noqa: E402

F = pcbnew.FromMM
T = pcbnew.ToMM
VIA_PAD, VIA_DRILL = 0.4572, 0.3  # the Proteus via


def P(x, y):
    return pcbnew.VECTOR2I(F(x), F(-y))


class Board:
    def __init__(self, seed):
        pcbnew.KIID.SeedGenerator(seed)  # reproducible UUIDs (one seed per script)
        self.b = pcbnew.LoadBoard(bc.BOARD)
        self.comps, nets = bc.export_netlist()
        self.pin_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes}
        self.log = []

    # -- nets ------------------------------------------------------------------------
    def net(self, name):
        ni = self.b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(ni)
            ni = self.b.FindNet(name)
            self.log.append(f"new net {name}")
        return ni

    def fp(self, ref):
        return self.b.FindFootprintByReference(ref)

    def sync_pads(self, ref):
        """Pad nets of an existing footprint from the schematic netlist; returns changes."""
        out = []
        for pad in self.fp(ref).Pads():
            want = self.pin_net.get((ref, pad.GetNumber()))
            if want and pad.GetNetname() != want:
                out.append(f"{ref}-{pad.GetNumber()}: {pad.GetNetname()} -> {want}")
                pad.SetNet(self.net(want))
        self.log += out
        return out

    def renet(self, old, new, kinds=("track", "via", "zone")):
        """Move every track / via / zone on net `old` to `new`."""
        n = 0
        ni = self.net(new)
        if "track" in kinds or "via" in kinds:
            for t in self.b.GetTracks():
                if t.GetNetname() == old:
                    t.SetNet(ni)
                    n += 1
        if "zone" in kinds:
            for z in self.b.Zones():
                if z.GetNetname() == old and not z.GetIsRuleArea():
                    z.SetNet(ni)
                    n += 1
        self.log.append(f"{n} tracks/vias/zones {old} -> {new}")
        return n

    # -- copper ----------------------------------------------------------------------
    def track(self, layer, pts, width, net):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(x1, y1))
            t.SetEnd(P(x2, y2))
            t.SetWidth(F(width))
            t.SetLayer(self.b.GetLayerID(layer))
            t.SetNet(self.net(net))
            self.b.Add(t)
            t.thisown = False
            self.log.append(f"track {layer} {net} w{width}: ({x1:.3f},{y1:.3f})-({x2:.3f},{y2:.3f})")

    def via(self, x, y, net):
        v = pcbnew.PCB_VIA(self.b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(P(x, y))
        v.SetWidth(F(VIA_PAD))
        v.SetDrill(F(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(self.net(net))
        self.b.Add(v)
        v.thisown = False
        self.log.append(f"via {net} at ({x:.3f},{y:.3f}) {VIA_PAD}/{VIA_DRILL}")

    def delete_tracks(self, pred):
        dead = [t for t in self.b.GetTracks() if t.GetClass() != "PCB_VIA" and pred(t)]
        for t in dead:
            s, e = t.GetStart(), t.GetEnd()
            self.log.append(f"deleted track {self.b.GetLayerName(t.GetLayer())} {t.GetNetname()} "
                            f"({T(s.x):.3f},{-T(s.y):.3f})-({T(e.x):.3f},{-T(e.y):.3f}) w{T(t.GetWidth()):.3f}")
            self.b.Delete(t)
        return len(dead)

    def zone(self, layer, pts, net, name, priority, clearance=0.15):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(self.b.GetLayerID(layer))
        z.SetNet(self.net(net))
        ch = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in pts:
            ch.Append(F(x), F(-y))
        ch.SetClosed(True)
        z.Outline().AddOutline(ch)
        z.SetZoneName(name)
        z.SetAssignedPriority(priority)
        z.SetMinThickness(F(0.1))
        z.SetLocalClearance(F(clearance))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
        self.b.Add(z)
        z.thisown = False
        self.log.append(f"zone {name} {layer} {net} prio {priority}: " + " ".join(f"({x},{y})" for x, y in pts))
        return z

    def pour_keepout(self, layer, x, y, r, name, n=32):
        """Rule area that keeps zone fills (pours) out of a circle (no effect on tracks/vias)."""
        z = pcbnew.ZONE(self.b)
        z.SetIsRuleArea(True)
        z.SetLayer(self.b.GetLayerID(layer))
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ch = pcbnew.SHAPE_LINE_CHAIN()
        for k in range(n):
            a = 2 * math.pi * k / n
            ch.Append(F(x + r * math.cos(a)), F(-(y + r * math.sin(a))))
        ch.SetClosed(True)
        z.Outline().AddOutline(ch)
        z.SetZoneName(name)
        self.b.Add(z)
        z.thisown = False
        self.log.append(f"pour keep-out {name} {layer} circle r{r} at ({x:.3f},{y:.3f})")

    # -- parts -----------------------------------------------------------------------
    def add_part(self, ref, side, pad1, pad2):
        """New 2-pad footprint from the schematic, placed so that pad 1 / pad 2 centres land on
        pad1 / pad2 (IPC frame); pad nets from the netlist, symbol link like build_pcb.py."""
        if self.fp(ref) is not None:
            sys.exit(f"{ref} is already on the board (fix applied?)")
        c = self.comps[ref]
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
            fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
        fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
        fp.SetSheetname(c["sheetname"])
        fp.SetSheetfile(c["sheetfile"])
        cx, cy = (pad1[0] + pad2[0]) / 2, (pad1[1] + pad2[1]) / 2
        self.b.Add(fp)
        fp.thisown = False
        pos = P(cx, cy)
        fp.SetPosition(pos)
        if side == "bottom":
            fp.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        best = None
        for ang in (0, 90, 180, 270):
            fp.SetOrientationDegrees(ang)
            p1 = next(p for p in fp.Pads() if p.GetNumber() == "1").GetPosition()
            d = math.hypot(T(p1.x) - pad1[0], -T(p1.y) - pad1[1])
            if best is None or d < best[0]:
                best = (d, ang)
        fp.SetOrientationDegrees(best[1])
        for pad in fp.Pads():
            pad.SetNet(self.net(self.pin_net[(ref, pad.GetNumber())]))
            q = pad.GetPosition()
            want = pad1 if pad.GetNumber() == "1" else pad2
            if math.hypot(T(q.x) - want[0], -T(q.y) - want[1]) > 0.01:
                sys.exit(f"{ref}: pad {pad.GetNumber()} at ({T(q.x):.3f},{-T(q.y):.3f}), wanted {want}")
        self.log.append(f"{ref} {c['value']} {c['footprint']} {side} at ({cx:.3f},{cy:.3f}) "
                        f"rot {best[1]}: pad1 {self.pin_net[(ref, '1')]} {pad1}, pad2 {self.pin_net[(ref, '2')]} {pad2}")
        return fp

    def set_value(self, ref, value):
        fp = self.fp(ref)
        self.log.append(f"{ref} value {fp.GetValue()} -> {value}")
        fp.SetValue(value)

    # -- save ------------------------------------------------------------------------
    def save(self, title):
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        pcbnew.SaveBoard(bc.BOARD, self.b)
        print(f"== {title}")
        for line in self.log:
            print("  " + line)
