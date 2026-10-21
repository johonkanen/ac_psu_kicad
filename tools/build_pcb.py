#!/usr/bin/env python3
"""Phase 3a: create kicad/ac_psu.kicad_pcb from the schematic, footprints placed where Proteus
put them (run under tools/p2k/bin/kipy). Re-runnable: the board is rebuilt from scratch.

There is no headless "Update PCB from schematic", so this does it in Python:
  - export the kicadxml netlist (kicad-cli) and create one footprint per symbol (TR1 and other
    "exclude from board" symbols are skipped) with reference, value, Datasheet/Description,
    the symbol link (path = sheet path + symbol UUID, sheet name/file) and every pad's net;
  - place each footprint with the recipe of tools/fpgeom.py from reports/footprint_fit.csv
    (SetPosition; bottom: Flip(LEFT_RIGHT); SetOrientationDegrees);
  - 4 copper layers, board outline on Edge.Cuts from the Mechanical 1 gerber (Proteus origin
    kept, KiCad y = -IPC y), drill/grid origin at the Proteus origin;
  - the 4 unnetted plated mounting holes (IPC 'hole' records) as board-only footprints H1..H4;
  - User.1..User.4 named for the Proteus pour outlines (filled in by gerber_to_tracks.py);
  - design rules from the Proteus data (tracks down to 0.1016 mm, vias 0.457/0.3 mm).

Tracks, vias and zones are added by the later steps (tools/make_pcb.sh runs them all).

Usage: tools/p2k/bin/kipy tools/build_pcb.py
"""
import csv
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
import board_common as bc  # noqa: E402
from p2k import gerber  # noqa: E402
from gen_footprints import footprint_path  # noqa: E402

FIT_CSV = os.path.join(bc.REPORTS, "footprint_fit.csv")


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    """IPC/gerber point (Y up) -> KiCad VECTOR2I (Y down)."""
    return pcbnew.VECTOR2I(mm(x), mm(-y))


def load_fit():
    with open(FIT_CSV) as f:
        rows = csv.DictReader(l for l in f if not l.startswith("# "))
        return {r["refdes"]: r for r in rows}


def load_fp(fpid):
    path = footprint_path(fpid)
    fp = pcbnew.FootprintLoad(os.path.dirname(path), os.path.basename(path)[:-len(".kicad_mod")])
    if fp is None:
        sys.exit(f"build_pcb: cannot load footprint {fpid} ({path})")
    lib, name = fpid.split(":", 1)
    fp.SetFPID(pcbnew.LIB_ID(pcbnew.UTF8(lib), pcbnew.UTF8(name)))
    return fp


def place(board, fp, x, y, side, orientation):
    board.Add(fp)  # must be on a board before Flip() (pcbnew 10 segfaults otherwise)
    pos = pcbnew.VECTOR2I(mm(x), mm(y))
    fp.SetPosition(pos)
    if side == "bottom":
        fp.Flip(pos, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(orientation)


def setup_board(board):
    board.SetCopperLayerCount(4)
    layers = board.GetEnabledLayers()
    for _, _, user in bc.COPPER:
        layers.AddLayer(getattr(pcbnew, user.replace(".", "_")))
    board.SetEnabledLayers(layers)
    for gname, cu, user in bc.COPPER:
        board.SetLayerName(getattr(pcbnew, user.replace(".", "_")), f"Proteus.{cu.split('.')[0]}.Pours")
    ds = board.GetDesignSettings()
    # Proteus stack: 4 x 0.036 Cu, 0.32 / 1.483 / 0.32 mm dielectric (CADCAM READ-ME)
    ds.SetBoardThickness(mm(2.267))
    # Rules from the Proteus data: thinnest conductor 0.1016 mm (D69), vias 0.4572 pad /
    # 0.3 drill (annular ring 0.0786 mm); clearance and edge clearance see STATUS.md.
    ds.m_TrackMinWidth = mm(0.1)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_ViasMinAnnularWidth = mm(0.075)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_MinClearance = mm(0.15)
    ds.m_HoleClearance = mm(0.15)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.25)
    ds.SetAuxOrigin(pcbnew.VECTOR2I(0, 0))
    ds.SetGridOrigin(pcbnew.VECTOR2I(0, 0))
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.15))
    nc.SetTrackWidth(mm(0.254))
    nc.SetViaDiameter(mm(0.4572))
    nc.SetViaDrill(mm(0.3))


def add_outline(board):
    g = gerber.parse(bc.gerber_path(bc.OUTLINE))
    n = 0
    for d in g.of(gerber.Draw):
        if d.ap.function != "Profile":
            continue
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pt(d.x1, d.y1))
        s.SetEnd(pt(d.x2, d.y2))
        s.SetWidth(mm(0.1))
        board.Add(s)
        n += 1
    return n


def main():
    pcbnew.KIID.SeedGenerator(3001)  # reproducible UUIDs (distinct seed per script)
    comps, nets = bc.export_netlist()
    fit = load_fit()
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = name

    board = pcbnew.NewBoard(bc.BOARD)
    setup_board(board)
    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    errors = []
    placed = skipped = 0
    for ref in sorted(comps):
        c = comps[ref]
        if c["excluded"]:
            skipped += 1
            continue
        if ref not in fit:
            errors.append(f"{ref}: not in {FIT_CSV}")
            continue
        row = fit[ref]
        if row["footprint"] != c["footprint"]:
            errors.append(f"{ref}: schematic footprint {c['footprint']} != fit {row['footprint']}")
            continue
        fp = load_fp(c["footprint"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
            fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
        fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
        fp.SetSheetname(c["sheetname"])
        fp.SetSheetfile(c["sheetfile"])
        if c["dnp"]:
            fp.SetDNP(True)
        place(board, fp, float(row["kicad_x"]), float(row["kicad_y"]), row["side"], float(row["kicad_orientation"]))
        for pad in fp.Pads():
            net = pin_net.get((ref, pad.GetNumber()))
            if net is not None:
                pad.SetNet(netinfo[net])
        placed += 1

    holes = [p for p in bc.ipc_records() if p["kind"] == "hole"]
    for i, h in enumerate(sorted(holes, key=lambda p: (-p["y_mm"], p["x_mm"])), 1):
        fp = load_fp(bc.HOLE_FOOTPRINT)
        fp.SetReference(f"H{i}")
        fp.SetValue("MountingHole_3.0mm")
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        place(board, fp, h["x_mm"], -h["y_mm"], "top", 0.0)

    edges = add_outline(board)
    if errors:
        for e in errors:
            print("build_pcb: ERROR " + e)
        sys.exit(1)
    pcbnew.SaveBoard(bc.BOARD, board)
    print(f"build_pcb: {placed} footprints placed ({skipped} excluded from board), {len(holes)} mounting holes, "
          f"{len(nets)} nets, {edges} outline segments -> {os.path.relpath(bc.BOARD, bc.ROOT)}")


if __name__ == "__main__":
    main()
