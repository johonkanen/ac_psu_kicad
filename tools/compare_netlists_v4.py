#!/usr/bin/env python3
"""p2k compare_netlists against the Proteus IPC netlist with the v4 deviations applied
(lib/v4_deviations.csv, tools/deviations.py). Thin wrapper: replaces the IPC loader of
p2k.compare_netlists by the deviated one, and also checks the values of the `value` rows
against the schematic. Any difference that is not a listed deviation is still an error.

Usage: python3 tools/compare_netlists_v4.py [compare_netlists options]
"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "p2k"))
import deviations  # noqa: E402
from p2k import board, compare_netlists as cn  # noqa: E402


def main():
    errs = deviations.validate()
    orig = cn.load_ipc
    cn.load_ipc = lambda: deviations.apply_pin_nets(orig())
    print(deviations.summary())
    with tempfile.TemporaryDirectory() as td:
        xml = os.path.join(td, "netlist.xml")
        if "--netlist" not in sys.argv:
            cn.export_netlist(board.path("kicad", f"{board.config().PROJECT}.kicad_sch"), xml)
            sys.argv += ["--netlist", xml]
        else:
            xml = sys.argv[sys.argv.index("--netlist") + 1]
        vals = {c.get("ref"): c.findtext("value", "") for c in ET.parse(xml).getroot().iter("comp")}
        want = dict((r, n) for r, (o, n) in deviations.value_changes().items())
        want.update({r: p["value"] for r, p in deviations.added_parts().items()})
        for ref, v in sorted(want.items()):
            if vals.get(ref) != v:
                errs.append(f"value of {ref} is {vals.get(ref)!r}, deviation list says {v!r}")
        print(f"compare_v4: {len(want)} deviation values checked against the schematic")
        rc = cn.main()
    for e in errs:
        print("ERROR (v4 deviations):", e)
    sys.exit(1 if errs or rc else 0)


if __name__ == "__main__":
    main()
