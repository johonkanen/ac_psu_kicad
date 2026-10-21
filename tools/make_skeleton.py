#!/usr/bin/env python3
"""Create the KiCad project skeleton (one-shot; refuses to overwrite).

kicad/ac_psu.kicad_pro, sym-lib-table, root sheet ac_psu.kicad_sch with one
hierarchical sheet per Proteus PDF page, and empty sub-sheet files.
"""
import json
import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k.sexpr import Sym, save  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(ROOT, "kicad")
PROJECT = "ac_psu"

# (Proteus page, sheet name, file) - names as in the PDF title blocks
SHEETS = [
    (1, "afe", "01_afe.kicad_sch"),
    (2, "fpga connector", "02_fpga_connector.kicad_sch"),
    (3, "regulators", "03_regulators.kicad_sch"),
    (4, "DC links", "04_dc_links.kicad_sch"),
    (5, "VSI", "05_vsi.kicad_sch"),
    (6, "Dual Active Bridge", "06_dual_active_bridge.kicad_sch"),
    (7, "Auxiliary supply", "07_auxiliary_supply.kicad_sch"),
    (8, "SDM current measurements", "08_sdm_current_measurements.kicad_sch"),
    (9, "primary side ADC", "09_primary_side_adc.kicad_sch"),
    (10, "INU SDM and relay drive", "10_inu_sdm_relay_drive.kicad_sch"),  # untitled in the PDF
    (11, "signal isolators", "11_signal_isolators.kicad_sch"),
]


def uid():
    return str(uuid.uuid4())


def font(size=1.27):
    return [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]


def title_block(title):
    return [Sym("title_block"), [Sym("title"), title], [Sym("company"), "Inverter PSU"],
            [Sym("rev"), "v3"], [Sym("comment"), 1, "Redrawn from Proteus single_phase_inverter_psu_v3"]]


def schematic(file_uuid, title, body=(), root=False):
    node = [Sym("kicad_sch"), [Sym("version"), Sym("20260101")], [Sym("generator"), "eeschema"],
            [Sym("generator_version"), "10.0"], [Sym("uuid"), file_uuid], [Sym("paper"), "A3"],
            title_block(title), [Sym("lib_symbols")], *body]
    if root:
        node.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
    node.append([Sym("embedded_fonts"), Sym("no")])
    return node


def sheet_block(root_uuid, i, page, name, fname):
    w, h = 76.2, 20.32
    x = 25.4 + (i % 3) * 127.0
    y = 38.1 + (i // 3) * 50.8
    return [Sym("sheet"), [Sym("at"), x, y], [Sym("size"), w, h],
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            [Sym("dnp"), Sym("no")],
            [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
            [Sym("fill"), [Sym("color"), 0, 0, 0, 0]],
            [Sym("uuid"), uid()],
            [Sym("property"), "Sheetname", f"{page:02d} {name}", [Sym("at"), x, y - 0.7, 0],
             [Sym("effects"), [Sym("font"), [Sym("size"), 1.524, 1.524]], [Sym("justify"), Sym("left"), Sym("bottom")]]],
            [Sym("property"), "Sheetfile", fname, [Sym("at"), x, y + h + 0.6, 0],
             [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]], [Sym("justify"), Sym("left"), Sym("top")]]],
            [Sym("instances"), [Sym("project"), PROJECT, [Sym("path"), f"/{root_uuid}", [Sym("page"), str(page + 1)]]]]]


def main():
    force = "--force" in sys.argv
    os.makedirs(KDIR, exist_ok=True)
    targets = [f"{PROJECT}.kicad_pro", f"{PROJECT}.kicad_sch", "sym-lib-table"] + [s[2] for s in SHEETS]
    existing = [t for t in targets if os.path.exists(os.path.join(KDIR, t))]
    if existing and not force:
        sys.exit(f"make_skeleton: refusing to overwrite {existing} (use --force)")

    mount = subprocess.run(["bash", "-c", f"source {ROOT}/tools/p2k/bin/kicad_env.sh >/dev/null && echo $KICAD_MOUNT"],
                           capture_output=True, text=True, check=True).stdout.strip()
    pro = json.load(open(os.path.join(mount, "share", "kicad", "template", "kicad.kicad_pro")))
    pro["meta"]["filename"] = f"{PROJECT}.kicad_pro"
    root_uuid = uid()
    pro["sheets"] = [[root_uuid, "Root"]]
    with open(os.path.join(KDIR, f"{PROJECT}.kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")

    with open(os.path.join(KDIR, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "ac_psu")(type "KiCad")'
                '(uri "${KIPRJMOD}/../lib/ac_psu.kicad_sym")(options "")(descr "Project symbols, pin ids = IPC"))\n)\n')

    blocks = [sheet_block(root_uuid, i, *s) for i, s in enumerate(SHEETS)]
    note = [Sym("text"), "Inverter PSU v3 - redrawn from Proteus. One sheet per Proteus PDF page.\n"
            "Net names follow the IPC-D-356A netlist (reference/pins_by_net.md).",
            [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), 25.4, 22.86, 0],
            [Sym("effects"), [Sym("font"), [Sym("size"), 2.0, 2.0]], [Sym("justify"), Sym("left"), Sym("bottom")]],
            [Sym("uuid"), uid()]]
    save(os.path.join(KDIR, f"{PROJECT}.kicad_sch"), schematic(root_uuid, "Inverter PSU", [note, *blocks], root=True))
    for page, name, fname in SHEETS:
        save(os.path.join(KDIR, fname), schematic(uid(), f"Inverter PSU - {name}"))
    print(f"make_skeleton: wrote {len(targets)} files in kicad/")


if __name__ == "__main__":
    main()
