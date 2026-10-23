"""Board settings of the Phase 3 tools, which are shared now (proteus2kicad p2k.pcb,
p2k.build_pcb, ...; the wrappers tools/build_pcb.py etc. import this module first).

Paths: tools/make_pcb.sh builds the Proteus board from the tagged schematic into
build/proteus/ (AC_PSU_BOARD / AC_PSU_SCHEMATIC / AC_PSU_REPORTS); by default the tools work on
the v4 design in kicad/. IPC records go through the v4 deviations (tools/deviations.py; raw
Proteus data when AC_PSU_PROTEUS=1, as tools/make_pcb.sh sets it). Design rules, thickness,
mounting-hole footprint and accepted DRC types are in p2k_config.py.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "p2k"))  # proteus2kicad
import deviations  # noqa: E402
from p2k import pcb  # noqa: E402

ROOT = os.path.dirname(TOOLS)
BOARD = os.environ.get("AC_PSU_BOARD") or os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
SCHEMATIC = os.environ.get("AC_PSU_SCHEMATIC") or os.path.join(ROOT, "kicad", "ac_psu.kicad_sch")
REPORTS = os.environ.get("AC_PSU_REPORTS") or os.path.join(ROOT, "reports")
os.environ.setdefault("P2K_BOARD", ROOT)
pcb.configure(board=BOARD, schematic=SCHEMATIC, reports=REPORTS, records=deviations.apply_records)

TOL = pcb.TOL
ipc_records = pcb.ipc_records
export_netlist = pcb.export_netlist
is_unconnected_net = pcb.is_unconnected_net
ipc_to_kicad_nets = pcb.ipc_to_kicad_nets
gerber_path = pcb.gerber_path
