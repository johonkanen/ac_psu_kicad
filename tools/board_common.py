"""Shared bits of the Phase 3 board scripts (build_pcb, gerber_to_tracks, assign_nets,
pours_to_zones, check_board). Run under tools/bin/kipy (needs pcbnew) except where noted.

Coordinates: the IPC file and the gerbers use mm with Y up; the KiCad board uses the same
origin with Y down, so KiCad (x, y) = (x, -y) of the IPC/gerber point (PLAN.md 3a).
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.environ.get("AC_PSU_BOARD") or os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")  # env: tests
SCHEMATIC = os.path.join(ROOT, "kicad", "ac_psu.kicad_sch")
REPORTS = os.path.join(ROOT, "reports")
CADCAM = os.path.join(ROOT, "source", "cadcam")
IPC_JSON = os.path.join(ROOT, "reference", "ipc356_pads.json")
TOL = 0.05  # mm, pad position tolerance against the IPC file

# Proteus copper gerbers -> KiCad copper layer name, and the User layer that keeps the
# Proteus pour outlines as a reference underlay.
COPPER = [
    ("Top Copper", "F.Cu", "User.1"),
    ("Inner  1", "In1.Cu", "User.2"),
    ("Inner  2", "In2.Cu", "User.3"),
    ("Bottom Copper", "B.Cu", "User.4"),
]
DRILL = "Drill TOP-BOT Plated"
OUTLINE = "Mechanical 1"

# Unnetted plated mounting holes (IPC 'hole' records): board-only footprints H1..H4.
HOLE_FOOTPRINT = "ac_psu:Terminal_D4.0mm_Drill3.0mm"


def gerber_path(name):
    paths = glob.glob(os.path.join(CADCAM, f"* - CADCAM {name}.GBR"))
    if len(paths) != 1:
        sys.exit(f"gerber {name!r} not found in {CADCAM}")
    return paths[0]


def ipc_records():
    with open(IPC_JSON) as f:
        return json.load(f)["pads"]


def export_netlist():
    """kicadxml netlist of the schematic -> (comps, nets).
    comps: {ref: dict(value, footprint, fields, sheet_tstamps, tstamps, sheetname,
                      sheetfile, excluded)}
    nets:  {name: [(ref, pin), ...]}"""
    cli = os.path.join(ROOT, "tools", "bin", "kicad-cli")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "netlist.xml")
        r = subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCHEMATIC],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"netlist export failed:\n{r.stdout}{r.stderr}")
        root = ET.parse(out).getroot()
    comps = {}
    for c in root.iter("comp"):
        props = {p.get("name"): p.get("value") for p in c.findall("property")}
        fields = {f.get("name"): (f.text or "") for f in c.iter("field")}
        sp = c.find("sheetpath")
        comps[c.get("ref")] = dict(
            value=c.findtext("value", ""), footprint=c.findtext("footprint", ""), fields=fields,
            sheet_tstamps=sp.get("tstamps"), tstamps=c.findtext("tstamps", "").split(),
            sheetname=props.get("Sheetname", ""), sheetfile=props.get("Sheetfile", ""),
            excluded="exclude_from_board" in props, dnp="dnp" in props)
    nets = {}
    for n in root.iter("net"):
        nets[n.get("name")] = [(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")]
    return comps, nets


def is_unconnected_net(name):
    """KiCad's per-pin nets of unconnected symbol pins (no-connect flags)."""
    return not name or name.startswith("unconnected-(")


def ipc_to_kicad_nets(board):
    """Map IPC net -> KiCad net name through the footprint pads (pad-set equivalence).
    Returns (mapping, problems). An IPC net maps to exactly one KiCad net, or it is a problem."""
    ipc = {}
    for p in ipc_records():
        if p["kind"] == "pad" and p["net"] and p["net_raw"] != "N/C":
            ipc[(p["refdes"], p["pin"])] = p["net"]
    seen = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in ipc:
                seen.setdefault(ipc[key], set()).add(pad.GetNetname())
    mapping, problems = {}, []
    for net, kn in sorted(seen.items()):
        if len(kn) == 1:
            mapping[net] = next(iter(kn))
        else:
            problems.append(f"IPC net {net} spans KiCad nets {sorted(kn)}")
    back = {}
    for net, kn in mapping.items():
        back.setdefault(kn, []).append(net)
    for kn, nets in back.items():
        if len(nets) > 1:
            problems.append(f"KiCad net {kn} spans IPC nets {sorted(nets)}")
    return mapping, problems


def layer_id(board, name):
    return board.GetLayerID(name)
