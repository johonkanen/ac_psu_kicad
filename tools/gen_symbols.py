#!/usr/bin/env python3
"""Generate lib/ac_psu.kicad_sym, the project symbol library.

Pin numbers equal the Proteus/IPC pin ids. Simple symbols are copied from the
KiCad 10 standard library (flattened, pins renumbered); ICs and other parts are
drawn as boxes with the pin names of the Proteus symbols (pin names follow the
Proteus drawing, which for REF3025 differs from the KiCad library pinout).
Power symbols carry the IPC net names.

Run:  tools/gen_symbols.py           (needs the AppImage mount for the std libs)
      tools/gen_symbols.py --check   (fail if lib/ac_psu.kicad_sym is not up to date)
"""
import copy
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import Sym, dump, find, find_all, load, parse, save, walk  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_PATH = os.path.join(ROOT, "lib", "ac_psu.kicad_sym")
LIB = "ac_psu"


def std_lib_dir():
    mount = subprocess.run(["bash", "-c", f"source {ROOT}/tools/kicad_env.sh >/dev/null && echo $KICAD_MOUNT"],
                           capture_output=True, text=True, check=True).stdout.strip()
    return os.path.join(mount, "share", "kicad", "symbols")


STD = None


def std_symbol(lib, name):
    """Return the flattened std symbol node `lib:name` (extends resolved)."""
    path = os.path.join(STD, f"{lib}.kicad_symdir", f"{name}.kicad_sym")
    sym = copy.deepcopy(find(load(path), "symbol"))
    ext = find(sym, "extends")
    if ext:
        parent = std_symbol(lib, ext[1])
        props = {p[1]: p for p in find_all(sym, "property")}
        for i, c in enumerate(parent):
            if isinstance(c, list) and c[0] == "property" and c[1] in props:
                parent[i] = props[c[1]]
        sym = parent
    return sym


def rename(sym, new):
    old = sym[1]
    sym[1] = new
    for sub in find_all(sym, "symbol"):
        sub[1] = new + sub[1][len(old):]
    return sym


def set_prop(sym, key, value, hide=None):
    for p in find_all(sym, "property"):
        if p[1] == key:
            p[2] = value
            if hide is not None:
                p[:] = [c for c in p if not (isinstance(c, list) and c[0] == "hide")]
                if hide:
                    p.insert(4, [Sym("hide"), Sym("yes")])
            return
    node = [Sym("property"), key, value, [Sym("at"), 0, 0, 0]]
    if hide is not False:
        node.append([Sym("hide"), Sym("yes")])
    node.append([Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]])
    sym.insert(len([c for c in sym if not isinstance(c, list) or c[0] != "symbol"]), node)


def set_flag(sym, key, value):
    node = find(sym, key)
    if node:
        node[1] = Sym("yes" if value else "no")


def remap_pins(sym, mapping, names=None):
    seen = set()
    for pin in walk(sym, "pin"):
        num = find(pin, "number")
        if num[1] in mapping:
            new = mapping[num[1]]
            num[1] = new
            seen.add(new)
            if names and new in names:
                find(pin, "name")[1] = names[new]
    missing = set(mapping.values()) - seen
    assert not missing, (sym[1], missing)
    return sym


def from_std(lib, name, new, ref, value=None, desc=None, pins=None, names=None):
    sym = rename(std_symbol(lib, name), new)
    if pins:
        remap_pins(sym, pins, names)
    set_prop(sym, "Reference", ref)
    set_prop(sym, "Value", value or new)
    set_prop(sym, "Footprint", "")
    set_prop(sym, "Datasheet", "")
    if desc:
        set_prop(sym, "Description", desc)
    # drop sim models: pin numbers no longer match them
    sym[:] = [c for c in sym if not (isinstance(c, list) and c[0] == "property" and str(c[1]).startswith("Sim."))]
    return sym


# ---------------------------------------------------------------- box symbols

def _font():
    return [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]


def _prop(key, value, x, y, hide=False, justify=None):
    p = [Sym("property"), key, value, [Sym("at"), x, y, 0]]
    if hide:
        p.append([Sym("hide"), Sym("yes")])
    eff = _font()
    if justify:
        eff.append([Sym("justify"), Sym(justify)])
    p.append(eff)
    return p


def _pin(num, name, etype, x, y, rot, length=2.54, hidden_name=False):
    return [Sym("pin"), Sym(etype), Sym("line"), [Sym("at"), x, y, rot], [Sym("length"), length],
            [Sym("name"), name, _font()], [Sym("number"), str(num), _font()]]


def box(name, ref, left, right, top=(), bottom=(), value=None, desc="", show_pin_names=True,
        min_width=7.62, on_board=True):
    """left/right/top/bottom: lists of (number, name, electrical_type); None = gap."""
    g = 2.54
    def maxlen(plist):
        return max([len(p[1].replace("~{", "").replace("}", "")) for p in plist if p] + [0])
    ml, mr = (maxlen(left), maxlen(right)) if show_pin_names else (0, 0)
    width = max(min_width, (ml + mr) * 1.2 + 4.5, (max(len(top), len(bottom)) + 1) * 2 * g)
    hw = -(-width / 2 // g) * g
    rows = max(len(left), len(right), 1)
    ytop = -(-(rows - 1) // 2) * g          # pins on the 2.54 grid, first row at ytop
    pad = lambda plist: -(-(maxlen(plist) * 1.2 + 1.5) // g) * g if plist else 0
    top_y, bot_y = ytop + g + pad(top), ytop - rows * g - pad(bottom)
    pins = []
    for side, plist in (("L", left), ("R", right)):
        for i, p in enumerate(plist):
            if not p:
                continue
            x = -hw - g if side == "L" else hw + g
            pins.append(_pin(p[0], p[1], p[2], x, ytop - i * g, 0 if side == "L" else 180))
    for side, plist in (("T", top), ("B", bottom)):
        n = len(plist)
        for i, p in enumerate(plist):
            if not p:
                continue
            x = (i - (n - 1) / 2) * g * 2
            x = round(x / g) * g
            y = top_y + g if side == "T" else bot_y - g
            pins.append(_pin(p[0], p[1], p[2], x, y, 270 if side == "T" else 90))
    sym = [Sym("symbol"), name]
    if not show_pin_names:
        sym.append([Sym("pin_names"), [Sym("offset"), 1.016], [Sym("hide"), Sym("yes")]])
    else:
        sym.append([Sym("pin_names"), [Sym("offset"), 1.016]])
    sym += [[Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
            [Sym("on_board"), Sym("yes" if on_board else "no")],
            _prop("Reference", ref, -hw, top_y + 1.27 + (g if top else 0), justify="left"),
            _prop("Value", value or name, -hw, bot_y - 1.27 - (g if bottom else 0), justify="left"),
            _prop("Footprint", "", 0, 0, hide=True),
            _prop("Datasheet", "", 0, 0, hide=True),
            _prop("Description", desc, 0, 0, hide=True),
            [Sym("symbol"), f"{name}_0_1",
             [Sym("rectangle"), [Sym("start"), -hw, top_y], [Sym("end"), hw, bot_y],
              [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
              [Sym("fill"), [Sym("type"), Sym("background")]]]],
            [Sym("symbol"), f"{name}_1_1", *pins],
            [Sym("embedded_fonts"), Sym("no")]]
    return sym


def header(pins):
    """Dual-row connector box: odd pins left, even pins right, absent pins leave gaps."""
    nums = sorted(int(p) for p in pins)
    lo, hi = nums[0] - (nums[0] % 2 == 0), nums[-1] + (nums[-1] % 2)
    left, right = [], []
    for odd in range(lo, hi, 2):
        left.append((odd, str(odd), "passive") if odd in nums else None)
        right.append((odd + 1, str(odd + 1), "passive") if odd + 1 in nums else None)
    return left, right


# ---------------------------------------------------------------- power symbols

def power(net, ground):
    sym = rename(std_symbol("power", "GND" if ground else "+3V3"), net)
    set_prop(sym, "Value", net)
    set_prop(sym, "Description", f'Power symbol for net "{net}" (IPC net name)')
    return sym


GROUNDS = ["GND", "PGND", "ISOGND", "ISOPGND", "DGND", "DAB_GROUND", "RET_ISO"]
SUPPLIES = ["VCC", "3V3_ISO", "5V", "5V_ISOL", "20V", "20V_ISO_SEC", "DC+", "ISODC+"]

PI, PO, IN, OUT, PAS = "power_in", "power_out", "input", "output", "passive"


def build():
    D_PINS = {"1": "C", "2": "A"}
    syms = [
        from_std("Device", "R", "R", "R", "R"),
        from_std("Device", "C", "C", "C", "C"),
        from_std("Device", "C_Polarized", "C_Polarized", "C", "C", desc="Polarized capacitor, pin 1 = +"),
        from_std("Device", "L", "L", "L", "L"),
        from_std("Device", "R_Pack04_Split", "RESISTOR_ARRAY_4", "R", "RESISTOR_ARRAY",
                 desc="4-resistor array, units A..D = 1-8, 2-7, 3-6, 4-5"),
        from_std("Device", "D", "D", "D", desc="Diode, pins A/C as in Proteus", pins=D_PINS),
        from_std("Device", "D_Schottky", "D_Schottky", "D", desc="Schottky diode, pins A/C", pins=D_PINS),
        from_std("Device", "D_Zener", "D_Zener", "D", desc="Zener diode, pins A/C", pins=D_PINS),
        from_std("Device", "Q_NMOS", "C3M0065090D", "Q", desc="SiC MOSFET TO-247-3, 1=G 2=D 3=S",
                 pins={"G": "1", "D": "2", "S": "3"}, names={"1": "G", "2": "D", "3": "S"}),
        from_std("Device", "Q_NMOS", "2N7000", "Q", desc="N-MOSFET, Proteus pin ids 1=D 2=G 3=S",
                 pins={"D": "1", "G": "2", "S": "3"}, names={"1": "D", "2": "G", "3": "S"}),
        from_std("Device", "R_Shunt", "FKK5R0020FE-TR", "R",
                 desc="4-terminal shunt; 1/3 one end, 2/4 other end (Proteus ids)",
                 pins={"1": "1", "2": "3", "3": "4", "4": "2"}),
        from_std("Device", "Filter_EMI_LL_1423", "WE-CMBNC", "CM",
                 desc="Common-mode choke, windings 1-4 and 2-3"),
        from_std("Device", "Transformer_1P_1S", "ETD34_TRAN_1P1S", "TR",
                 desc="DAB transformer, off-board (connected via DAB_PRI/DAB_SEC terminals)"),
        from_std("Connector", "TestPoint", "PIN", "TP", "PIN",
                 desc="Proteus PIN terminal (single pad; ACIN/ACOUT footprints have two pads numbered 1)"),
        from_std("Amplifier_Operational", "LM2904", "OPA2353UA", "U", desc="Dual op-amp, SOIC-8"),
        from_std("Amplifier_Operational", "MCP6L91T-EOT", "TLV316IDBVR", "U", desc="Op-amp, SOT-23-5"),
    ]
    tr1 = syms[12]
    set_flag(tr1, "on_board", False)

    syms += [
        box("TPS73033DBVT", "U", [(1, "IN", PI), (2, "GND", PI), (3, "EN", IN)],
            [(4, "NR", PAS), (5, "OUT", PO), None], desc="LDO 3.3 V, SOT-23-5"),
        box("REF3025", "REF", [(2, "VIN", PI)], [(3, "VOUT", PO)], bottom=[(1, "GND", PI)],
            desc="2.5 V reference; Proteus pin ids 1=GND 2=VIN 3=VOUT (KiCad lib: 1=IN 2=OUT 3=GND)"),
        box("VXO7805-500", "U", [(1, "+VIN", PI), (2, "GND/-VOUT", PI), (3, "+VOUT/GND", PO)], [],
            desc="DC/DC 5 V 0.5 A"),
        box("VXO7805-1000", "U", [(1, "+VIN", PI), (2, "GND", PI), (3, "+VOUT", PO)], [],
            desc="DC/DC 5 V 1 A"),
        box("ADUM7701-8BRIZ", "U",
            [(1, "VDD1", PI), (2, "VIN+", IN), (3, "VIN-", IN), (4, "GND1", PI)],
            [(8, "VDD2", PI), (7, "MCLKIN", IN), (6, "MDAT", OUT), (5, "GND2", PI)],
            desc="Isolated sigma-delta modulator, SOIC-8 wide"),
        box("ADS7056", "U",
            [(8, "AINM", IN), (7, "AINP", IN), (6, "AVDD", PI), (5, "GND", PI)],
            [(1, "~{CS}", IN), (2, "SDO", OUT), (3, "SCLK", IN), (4, "DVDD", PI)],
            desc="14-bit 2.5 MSPS ADC, X2QFN-8"),
        box("SN74LV4051", "U",
            [(13, "X0", PAS), (14, "X1", PAS), (15, "X2", PAS), (12, "X3", PAS), (1, "X4", PAS),
             (5, "X5", PAS), (2, "X6", PAS), (4, "X7", PAS), None, (11, "A", IN), (10, "B", IN),
             (9, "C", IN), (6, "INH", IN)],
            [(3, "X", PAS)], top=[(16, "VDD", PI)], bottom=[(7, "VEE", PI), (8, "VSS", PI)],
            desc="8:1 analog mux (Proteus hides VDD/VEE/VSS; shown here)"),
        box("IW1830", "PWM",
            [(1, "Vcc", PI), (2, "Vsense", IN), (3, "GND", PI)],
            [(8, "D", PAS), (7, "D", PAS), (5, "S", PAS), (4, "I_sense", IN)],
            desc="Flyback controller with integrated switch, SOIC-8 (no pin 6)"),
        box("SLA-12VDC-SL-A", "K",
            [(6, "COIL_2", PAS), (5, "COM_2", PAS)],
            [(3, "NO", PAS), (2, "COIL_1", PAS), (1, "COM_1", PAS)],
            desc="Power relay (Proteus refdes R20/R79; no pin 4)"),
        box("EF20_AUX_TRANS", "TR",
            [(i, str(i), PAS) for i in (1, 2, 3, 4, 5)],
            [(i, str(i), PAS) for i in (10, 9, 8, 7, 6)],
            desc="EF20 auxiliary flyback transformer, 10 pins"),
    ]
    for name, rev in (("Si8660BD-B-IS", False), ("Si8661BD-B-IS", True)):
        a = [(1, "VDD1", PI)] + [(i + 1, f"A{i}", OUT if rev and i == 6 else IN) for i in range(1, 7)] + [(8, "GND1", PI)]
        b = [(16, "VDD2", PI)] + [(16 - i, f"B{i}", IN if rev and i == 6 else OUT) for i in range(1, 7)] + [(9, "GND2", PI)]
        syms.append(box(name, "U", b, a, desc="6-channel digital isolator, SOIC-16 wide"
                        + (" (5 fwd / 1 rev)" if rev else " (6 fwd)")))

    l, r = header([*range(15, 27), *range(29, 41), *range(43, 49)])
    syms.append(box("HB_GT_CONNECTOR", "J", l, r, show_pin_names=False,
                    desc="Gate-driver connector, pins 15..48 without 27,28,41,42 (as on the PCB)"))
    l, r = header(range(1, 39))
    syms.append(box("HEADER_38_50MIL", "J", l, r, show_pin_names=False, desc="38-pin header, 50 mil"))
    l, r = header(range(43, 49))
    syms.append(box("HEADER_2X3_43_48", "J", l, r, show_pin_names=False,
                    desc="2x3 50 mil connector numbered 43..48"))

    syms.append(rename(std_symbol("power", "PWR_FLAG"), "PWR_FLAG"))
    syms += [power(n, True) for n in GROUNDS] + [power(n, False) for n in SUPPLIES]
    return syms


def main():
    global STD
    STD = std_lib_dir()
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), Sym("20251024")], [Sym("generator"), "ac_psu_gen_symbols"],
           [Sym("generator_version"), "10.0"], *build()]
    if "--check" in sys.argv:
        current = load(LIB_PATH) if os.path.exists(LIB_PATH) else None
        if current != parse(dump(lib)):
            print(f"gen_symbols: {os.path.relpath(LIB_PATH, ROOT)} is out of date, run tools/gen_symbols.py")
            return 1
        print(f"gen_symbols: {os.path.relpath(LIB_PATH, ROOT)} up to date ({len(lib) - 4} symbols)")
        return 0
    save(LIB_PATH, lib)
    print(f"wrote {os.path.relpath(LIB_PATH, ROOT)}: {len(lib) - 4} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(main())
