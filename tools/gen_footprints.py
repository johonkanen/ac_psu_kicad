"""Footprint assignment and the project footprint library (stdlib only).

Writes
  lib/footprint_map.csv  refdes -> footprint (every IPC part; TR1 has none, it is not on the board)
  lib/ac_psu.pretty/     project footprints (derived from KiCad library footprints, or built
                         from the IPC-D-356A pad geometry where KiCad has nothing that fits)

Usage: python3 tools/gen_footprints.py [--check]

Assignment: every IPC refdes is classified by its symbol (lib/part_map.csv) and its IPC pad
pattern (pad count, largest pad-to-pad distance = "span", pad size, drill). RULES maps that to
a footprint; the first matching rule wins and every refdes must match one.

Pad numbers always equal the IPC pin ids. Policy (PLAN.md 4.3): use the KiCad library
footprint unchanged when its pads land within 0.045 mm of the IPC pads; otherwise derive a
project footprint from it with the pad centres moved onto the Proteus positions (KiCad pad
sizes kept unless `ipc_sizes`), or build one from the IPC pads when KiCad has no such package.
tools/check_footprints.py verifies the result (residual < 0.05 mm per pad).
"""
import copy
import csv
import io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import fpgeom  # noqa: E402
from p2k import sexpr  # noqa: E402
from p2k.sexpr import Sym  # noqa: E402
import deviations  # noqa: E402  (v4 added parts)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRETTY = os.path.join(ROOT, "lib", "ac_psu.pretty")
MAP_CSV = os.path.join(ROOT, "lib", "footprint_map.csv")
PART_MAP = os.path.join(ROOT, "lib", "part_map.csv")

# (symbol, conditions, footprint, note). Conditions: n = pad count, tht, span (mm, +-0.02),
# pad = (w, h) of the IPC pads (sorted), drill.
RULES = [
    ("R", dict(tht=False, span=1.00, pad=(0.558, 0.609)), "Resistor_SMD:R_0402_1005Metric", "0402"),
    ("R", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Resistor_SMD:R_0603_1608Metric", "0603"),
    ("R", dict(tht=False, span=1.73, pad=(0.889, 0.889)), "Resistor_SMD:R_0603_1608Metric", "0603 (Proteus pads 1.73 mm apart)"),
    ("R", dict(tht=False, span=2.00, pad=(0.939, 1.447)), "Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "0805"),
    ("R", dict(tht=False, span=2.90, pad=(1.143, 1.803)), "Resistor_SMD:R_1206_3216Metric", "1206"),
    ("R", dict(tht=False, span=3.15, pad=(1.016, 1.524)), "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder", "1206 (Proteus pads 3.15 mm apart)"),
    ("R", dict(tht=True, span=5.00), "Resistor_THT:R_Radial_Power_L13.0mm_W9.0mm_P5.00mm", "TWW10J15RE 10 W wirewound, vertical"),
    ("C", dict(tht=False, span=0.90, pad=(0.609, 0.609)), "Capacitor_SMD:C_0402_1005Metric", "0402"),
    ("C", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Capacitor_SMD:C_0603_1608Metric", "0603"),
    ("C", dict(tht=False, span=3.15, pad=(1.016, 1.524)), "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "1206"),
    ("C", dict(tht=False, span=5.20, pad=(1.397, 5.257)), "Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder", "2220"),
    ("C", dict(tht=True, span=7.50), "Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P7.50mm", "2n2 Y cap, P7.5 (Proteus silk ~13 x 6 mm)"),
    ("C", dict(tht=True, span=27.50, drill=1.27), "ac_psu:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus",
     "7u film, P27.5, Proteus 1.27 mm drill"),
    ("C", dict(tht=True, span=27.50), "Capacitor_THT:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4", "7u film, P27.5"),
    ("C_Polarized", dict(tht=True, span=10.00), "ac_psu:CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus", "SNAP_IN_35MM, Proteus pads/drills"),
    ("C_Polarized", dict(tht=False, span=4.50), "ac_psu:CP_Elec_6.3x7.7_EEEFTE221XAP", "EEEFTE221XAP SMD electrolytic"),
    ("D", dict(), "ac_psu:D_SMA_AC", "SMA (ES1A, S1M)"),
    ("D_Schottky", dict(), "ac_psu:D_SOD-323_AC", "SOD-323 (ZLLS400TA)"),
    ("D_Zener", dict(), "ac_psu:D_SOD-323_AC", "SOD-323 (MM3Z5V1T1)"),
    ("L", dict(), "Inductor_SMD:L_0805_2012Metric", "0805"),
    ("2N7000", dict(), "ac_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering"),
    ("REF3025", dict(), "ac_psu:SOT-23_Proteus", "SOT-23, Proteus pad numbering"),
    ("TLV316IDBVR", dict(), "ac_psu:SOT-23-5_TLV316", "SOT-23-5 (DBV), Proteus pad rows 2.39 mm apart"),
    ("TPS73033DBVT", dict(), "ac_psu:SOT-23-5_TPS73033", "SOT-23-5 (DBV), Proteus pad rows 2.50 mm apart"),
    ("OPA2353UA", dict(), "ac_psu:TSSOP-8_3x3mm_P0.65mm_Proteus", "pads are MSOP/TSSOP-8 (not the SO-8 of the UA suffix)"),
    ("SN74LV4051", dict(), "ac_psu:TSSOP-16_4.4x5mm_P0.65mm_Proteus", "TSSOP-16"),
    ("Si8660BD-B-IS", dict(), "ac_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus", "SOIC-16W"),
    ("Si8661BD-B-IS", dict(), "ac_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus", "SOIC-16W"),
    ("ADUM7701-8BRIZ", dict(), "ac_psu:SOIC-8W_7.5x5.85mm_P1.27mm_ADuM7701", "SOIC127P1031X265-8N"),
    ("ADS7056", dict(), "ac_psu:X2QFN-8_1.5x1.5mm_P0.5mm_ADS7056", "X2QFN-8 (RUG)"),
    ("RESISTOR_ARRAY_4", dict(), "ac_psu:R_Array_Convex_4x0402_Proteus", "4x0402 array"),
    ("IW1830", dict(), "Package_DIP:DIP-8-N6_W7.62mm", "DIP-8 without pin 6"),
    ("C3M0065090D", dict(), "ac_psu:TO-247-3_Vertical_Proteus", "TO-247-3, 1=G 2=D 3=S"),
    ("HB_GT_CONNECTOR", dict(), "ac_psu:PinHeader_2x24_P1.27mm_Vertical_Pins15-48", "2x24 1.27 mm, pins 15-26/29-40/43-48 only"),
    ("HEADER_38_50MIL", dict(), "ac_psu:PinHeader_2x19_P1.27mm_Vertical_Proteus", "2x19 1.27 mm"),
    ("HEADER_2X3_43_48", dict(), "ac_psu:PinHeader_2x03_P1.27mm_Vertical_Pins43-48", "2x3 1.27 mm, pads 43-48"),
    ("VXO7805-1000", dict(), "ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus", "SIP-3 P2.54 (1 Vin, 2 GND, 3 Vout)"),
    ("VXO7805-500", dict(), "ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus", "SIP-3 P2.54 (1 Vin, 2 GND, 3 Vout)"),
    ("EF20_AUX_TRANS", dict(), "ac_psu:Transformer_EF20_2x5_P3.81mm", "EF20, pads 1-10"),
    ("WE-CMBNC", dict(), "ac_psu:L_CommonMode_WE-CMBNC", "WE-CMBNC 4-pin choke"),
    ("FKK5R0020FE-TR", dict(), "ac_psu:R_Shunt_FKK5R0020FE", "4-terminal shunt"),
    ("SLA-12VDC-SL-A", dict(), "ac_psu:Relay_SLA-12VDC-SL-A", "SLA relay, pads 1,2,3,5,6"),
    ("PIN", dict(n=2), "ac_psu:Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm", "two holes, both pad 1"),
    ("PIN", dict(pad=(3.048, 3.048), drill=1.524), "ac_psu:Terminal_D3.05mm_Drill1.52mm", "PIN terminal"),
    ("PIN", dict(pad=(4.0, 4.0), drill=2.0), "ac_psu:Terminal_D4.0mm_Drill2.0mm", "PIN terminal"),
    ("PIN", dict(pad=(4.0, 4.0), drill=2.55), "ac_psu:Terminal_D4.0mm_Drill2.55mm", "PIN terminal"),
    ("PIN", dict(pad=(4.0, 4.0), drill=3.0), "ac_psu:Terminal_D4.0mm_Drill3.0mm", "PIN terminal"),
]

# Project footprints.
#   base      KiCad library footprint to start from (graphics, 3D model, pad shapes)
#   renumber  base pad number -> IPC pin id
#   drop      remove base pads whose (renumbered) number the IPC part does not have
#   ipc       refdes whose IPC pads give the pad centres (moved into the base frame)
#   ipc_sizes also take pad size (and drill) from the IPC pads
#   body      (w, h) body outline for footprints built from the IPC pads only
PROJECT = {
    "CP_Elec_6.3x7.7_EEEFTE221XAP": dict(base="Capacitor_SMD:CP_Elec_6.3x7.7", ipc="C28", ipc_sizes=True,
                                         descr="Panasonic EEE-FTE221XAP, Proteus land pattern"),
    "D_SMA_AC": dict(base="Diode_SMD:D_SMA", renumber={"1": "C", "2": "A"}, ipc="D1",
                     descr="SMA diode, pads C/A, Proteus pad positions"),
    "D_SOD-323_AC": dict(base="Diode_SMD:D_SOD-323_HandSoldering", renumber={"1": "C", "2": "A"}, ipc="D3",
                         descr="SOD-323 diode, pads C/A, Proteus pad positions"),
    "SOT-23_Proteus": dict(base="Package_TO_SOT_SMD:SOT-23", renumber={"3": "1", "1": "2", "2": "3"},
                           ipc="REF1", ipc_sizes=True,
                           descr="SOT-23 with Proteus pad numbering: pad 1 = JEDEC pin 3 (single side), "
                                 "pad 2 = JEDEC pin 1, pad 3 = JEDEC pin 2; Proteus pad sizes"),
    "SOT-23-5_TLV316": dict(base="Package_TO_SOT_SMD:SOT-23-5", ipc="U2", ipc_sizes=True,
                            descr="SOT-23-5, Proteus land pattern (rows 2.39 mm apart)"),
    "SOT-23-5_TPS73033": dict(base="Package_TO_SOT_SMD:SOT-23-5", ipc="U3",
                              descr="SOT-23-5, Proteus pad positions (rows 2.50 mm apart)"),
    "SOIC-8W_7.5x5.85mm_P1.27mm_ADuM7701": dict(base="Package_SO:SOIC-8_7.5x5.85mm_P1.27mm", ipc="U6",
                                               descr="ADuM7701 8-lead wide SOIC, Proteus pad positions (rows 9.70 mm apart)"),
    "X2QFN-8_1.5x1.5mm_P0.5mm_ADS7056": dict(base="Package_DFN_QFN:Texas_UQFN-8_1.5x1.5mm_P0.5mm", ipc="AD1",
                                            ipc_sizes=True, descr="TI X2QFN-8 (RUG), Proteus land pattern"),
    "R_Array_Convex_4x0402_Proteus": dict(base="Resistor_SMD:R_Array_Convex_4x0402", ipc="R87",
                                          descr="4x0402 resistor array, Proteus pad positions"),
    "PinHeader_2x24_P1.27mm_Vertical_Pins15-48": dict(
        base="Connector_PinHeader_1.27mm:PinHeader_2x24_P1.27mm_Vertical", drop="J1", ipc="J1", ipc_sizes=True,
        descr="2x24 1.27 mm header position, only pins 15-26, 29-40, 43-48 fitted (HB GT CONNECTOR), "
              "Proteus pads (0.812 mm)"),
    "PinHeader_2x19_P1.27mm_Vertical_Proteus": dict(
        base="Connector_PinHeader_1.27mm:PinHeader_2x19_P1.27mm_Vertical", ipc="J11", ipc_sizes=True,
        descr="2x19 1.27 mm header, Proteus pads (0.812 mm)"),
    # Proteus pad sizes where the KiCad pads reach Proteus tracks (Phase 3 DRC, user decision
    # 2026-10-19), Proteus pads and drills where the KiCad drill is smaller than Proteus'
    "TSSOP-8_3x3mm_P0.65mm_Proteus": dict(base="Package_SO:TSSOP-8_3x3mm_P0.65mm", ipc="U1", ipc_sizes=True,
                                          descr="TSSOP/MSOP-8, Proteus land pattern"),
    "TSSOP-16_4.4x5mm_P0.65mm_Proteus": dict(base="Package_SO:TSSOP-16_4.4x5mm_P0.65mm", ipc="U11", ipc_sizes=True,
                                             descr="TSSOP-16, Proteus land pattern"),
    "SOIC-16W_7.5x10.3mm_P1.27mm_Proteus": dict(base="Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", ipc="U13",
                                                ipc_sizes=True, descr="SOIC-16W, Proteus land pattern"),
    "TO-247-3_Vertical_Proteus": dict(base="Package_TO_SOT_THT:TO-247-3_Vertical", ipc="Q1", ipc_sizes=True,
                                      descr="TO-247-3, Proteus pads (3.048 mm) and drills (1.651 mm)"),
    "Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus": dict(
        base="Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT", ipc="U8", ipc_sizes=True,
        flip_body=2.54, descr="SIP-3 P2.54, Proteus pads (1.8 mm) and drills (1.2 mm); body on the "
                               "component-face side of the pin row like the Proteus silk (photo of the built "
                               "board, 2026-10-23), R-78E graphics mirrored"),
    "C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus": dict(
        base="Capacitor_THT:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4", ipc="C21", ipc_sizes=True,
        descr="Film capacitor P27.5, Proteus pads (2.286 mm) and drills (1.27 mm)"),
    "CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus": dict(
        base="Capacitor_THT:CP_Radial_D35.0mm_P10.00mm_SnapIn", ipc="C11", ipc_sizes=True,
        descr="35 mm snap-in electrolytic, Proteus pads (5.08 mm) and drills (2.032 mm)"),
    "PinHeader_2x03_P1.27mm_Vertical_Pins43-48": dict(
        base="Connector_PinHeader_1.27mm:PinHeader_2x03_P1.27mm_Vertical",
        renumber={str(i): str(42 + i) for i in range(1, 7)}, descr="2x3 1.27 mm header, pads numbered 43-48"),
    "Transformer_EF20_2x5_P3.81mm": dict(ipc="TR2", body=(22.0, 14.0), descr="EF20 auxiliary transformer, Proteus land pattern"),
    "L_CommonMode_WE-CMBNC": dict(ipc="CM1", descr="Wurth WE-CMBNC common mode choke, Proteus land pattern"),
    "R_Shunt_FKK5R0020FE": dict(ipc="R48", descr="FKK5R0020FE 4-terminal current shunt, Proteus land pattern"),
    "Relay_SLA-12VDC-SL-A": dict(ipc="R20", descr="Songle SLA-12VDC-SL-A relay, Proteus land pattern (pads 1,2,3,5,6)"),
    "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm": dict(ipc="ACIN1", descr="Two-hole wire terminal, both holes pad 1"),
    "Terminal_D3.05mm_Drill1.52mm": dict(ipc="PE8", descr="Single PIN terminal"),
    "Terminal_D4.0mm_Drill2.0mm": dict(ipc="PE2", descr="Single PIN terminal"),
    "Terminal_D4.0mm_Drill2.55mm": dict(ipc="J5", descr="Single PIN terminal"),
    "Terminal_D4.0mm_Drill3.0mm": dict(ipc="PE1", descr="Single PIN terminal"),
}

TOL_KICAD = 0.045   # use a KiCad footprint unchanged up to this residual


def kicad_footprint_dir():
    state = f"{os.environ.get('TMPDIR', '/tmp')}/p2k_kicad_mount.{os.getuid()}"
    mount = os.environ.get("KICAD_MOUNT") or (open(state).read().strip() if os.path.exists(state) else "")
    d = os.path.join(mount, "share", "kicad", "footprints")
    if not mount or not os.path.isdir(d):
        sys.exit("gen_footprints: KiCad AppImage not mounted - run `source tools/p2k/bin/kicad_env.sh` "
                 "(or any tools/p2k/bin wrapper) first")
    return d


def footprint_path(fpid):
    nick, _, name = fpid.partition(":")
    if nick == "ac_psu":
        return os.path.join(PRETTY, name + ".kicad_mod")
    return os.path.join(kicad_footprint_dir(), nick + ".pretty", name + ".kicad_mod")


def part_map():
    with open(PART_MAP) as f:
        return {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("# "))}


def features(pads):
    span = max((math.hypot(a["x_mm"] - b["x_mm"], a["y_mm"] - b["y_mm"])
                for a in pads for b in pads), default=0.0)
    return {"n": len(pads), "tht": pads[0]["is_tht"], "span": span,
            "pads": {tuple(sorted((p["pad_w"], p["pad_h"]))) for p in pads},
            "drills": {p["drill"] for p in pads}}


def match(sym, cond, f):
    for key, want in cond.items():
        if key == "n" and f["n"] != want:
            return False
        if key == "tht" and f["tht"] != want:
            return False
        if key == "span" and abs(f["span"] - want) > 0.02:
            return False
        if key == "pad" and f["pads"] != {tuple(sorted(want))}:
            return False
        if key == "drill" and f["drills"] != {want}:
            return False
    return True


def assign():
    """refdes -> (footprint, note) for every IPC part."""
    pm = part_map()
    ipc = fpgeom.ipc_pads_by_refdes()
    out, errors = {}, []
    for ref in sorted(ipc):
        sym = pm[ref]["lib_id"].split(":", 1)[1]
        f = features(ipc[ref])
        hits = [(fp, note) for s, cond, fp, note in RULES if s == sym and match(sym, cond, f)]
        if not hits:
            errors.append(f"{ref}: no footprint rule for {sym} (n={f['n']} span={f['span']:.2f} pads={f['pads']})")
            continue
        out[ref] = hits[0]
    # v4: parts added to the Proteus design (lib/v4_deviations.csv, no IPC pads)
    for ref, p in deviations.added_parts().items():
        if ref not in pm:
            errors.append(f"{ref}: v4 part missing from lib/part_map.csv")
        out[ref] = (p["footprint"], f"v4 fix {p['fix']}: {p['note']}")
    return out, errors


# ---------------------------------------------------------------- footprint building

def _side_mirror(pads, fp_pads=None):
    """Mirror flag for building from a refdes: bottom SMD parts are mirrored; THT parts
    are taken as top side unless only the mirrored fit works."""
    side = pads[0]["side"]
    if side == "bottom":
        return [True]
    if side == "top":
        return [False]
    return [False, True]


def _to_fp(fitres, qx, qy):
    """Board (IPC, Y up) point -> footprint frame (Y up) for a fit result."""
    a = math.radians(fitres["angle"])
    dx, dy = qx - fitres["tx"], qy - fitres["ty"]
    x = math.cos(a) * dx + math.sin(a) * dy
    y = -math.sin(a) * dx + math.cos(a) * dy
    return (-x if fitres["mirror"] else x), y


def _fp_rot(fitres, qrot):
    r = qrot - fitres["angle"]
    return (-r if fitres["mirror"] else r) % 180.0


def _r4(v):
    v = round(v, 4)
    return 0 if v == 0 else v


def derive(name, spec, ipc):
    base = sexpr.load(footprint_path(spec["base"]))
    base[1] = name
    ren = spec.get("renumber", {})
    for pad in sexpr.find_all(base, "pad"):
        pad[1] = ren.get(str(pad[1]), str(pad[1]))
    keep_ref = spec.get("drop")
    if keep_ref:
        pins = {p["pin"] for p in ipc[keep_ref]}
        base[:] = [c for c in base if not (isinstance(c, list) and c and c[0] == "pad" and str(c[1]) not in pins)]
    if spec.get("ipc"):
        ref = spec["ipc"]
        pads = ipc[ref]
        fp_pads = []
        nodes = {}
        for pad in sexpr.find_all(base, "pad"):
            if str(pad[2]) == "np_thru_hole":
                continue
            at, size = sexpr.find(pad, "at"), sexpr.find(pad, "size")
            d = {"num": str(pad[1]), "kind": str(pad[2]), "x": float(at[1]), "y": -float(at[2]),
                 "rot": float(at[3]) if len(at) > 3 else 0.0, "w": float(size[1]), "h": float(size[2]), "drill": 0.0}
            nodes[id(d)] = pad
            fp_pads.append(d)
        fits = [fpgeom.fit(fp_pads, pads, m) for m in _side_mirror(pads)]
        fr = min(fits, key=lambda r: r["max_res"])
        if fr["missing"] or fr["extra"] or fr["count_diff"]:
            raise SystemExit(f"{name}: pad numbers of {spec['base']} do not match {ref}: {fr}")
        for num, f, q, _ in fr["pads"]:
            pad = nodes[id(f)]
            x, y = _to_fp(fr, q["x_mm"], q["y_mm"])
            at = sexpr.find(pad, "at")
            rot = float(at[3]) if len(at) > 3 else 0.0
            if spec.get("ipc_sizes"):
                rot = _fp_rot(fr, q["rot"])
                size = sexpr.find(pad, "size")
                size[1:] = [q["pad_w"], q["pad_h"]]
                if q["is_tht"]:
                    drill = sexpr.find(pad, "drill")
                    drill[1:] = [q["drill"]]
            at[1:] = [_r4(x), _r4(-y)] + ([_r4(rot)] if abs(rot) > 1e-9 else [])
    if spec.get("flip_body") is not None:
        _flip_body(base, spec["flip_body"])
    if spec.get("ipc_sizes"):
        # Proteus land pattern -> the board's Proteus clearance rule, not a library override
        # (KiCad's TSSOP-8 carries a footprint clearance of 0.2 mm)
        base[:] = [c for c in base if not (isinstance(c, list) and c and c[0] == "clearance")]
    for prop in sexpr.find_all(base, "property"):
        if prop[1] == "Value":
            prop[2] = name
    descr = sexpr.find(base, "descr")
    text = f"{spec['descr']} (ac_psu, derived from {spec['base']})"
    if descr is None:
        base.insert(4, [Sym("descr"), text])
    else:
        descr[1] = text
    gen = sexpr.find(base, "generator")
    if gen is not None:
        gen[1] = "ac_psu_gen_footprints"
    return base


def _flip_body(base, xc):
    """Mirror the graphics (lines, texts, courtyard, 3D model) across the pin row y = 0, pads
    unchanged: the body ends up on the other side of the pins. The 3D model is turned 180 deg
    about the pin row centre x = xc (the pin order of a symmetric SIP body is kept)."""
    for item in base:
        if not (isinstance(item, list) and item):
            continue
        if item[0] in ("fp_line", "fp_rect", "fp_circle", "fp_arc"):
            for key in ("start", "end", "center", "mid"):
                pt = sexpr.find(item, key)
                if pt is not None:
                    pt[2] = _r4(-float(pt[2]))
        elif item[0] == "fp_poly":
            for pt in sexpr.find_all(sexpr.find(item, "pts"), "xy"):
                pt[2] = _r4(-float(pt[2]))
        elif item[0] in ("property", "fp_text"):
            at = sexpr.find(item, "at")
            if at is not None:
                at[2] = _r4(-float(at[2]))
        elif item[0] == "model":
            sexpr.find(sexpr.find(item, "offset"), "xyz")[1] = _r4(2 * xc)
            sexpr.find(sexpr.find(item, "rotate"), "xyz")[3] = 180


def _eff(size=1.0, thick=0.15):
    return [Sym("effects"), [Sym("font"), [Sym("size"), size, size], [Sym("thickness"), thick]]]


def _rect(x0, y0, x1, y1, layer, width):
    return [Sym("fp_rect"), [Sym("start"), _r4(x0), _r4(y0)], [Sym("end"), _r4(x1), _r4(y1)],
            [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
            [Sym("layer"), "F." + layer]]


def _circle(r, layer, width):
    return [Sym("fp_circle"), [Sym("center"), 0, 0], [Sym("end"), _r4(r), 0],
            [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
            [Sym("layer"), "F." + layer]]


def from_ipc(name, spec, ipc):
    pads = ipc[spec["ipc"]]
    mirror = pads[0]["side"] == "bottom"
    m = -1.0 if mirror else 1.0
    xs = [m * p["x_mm"] for p in pads]
    ys = [p["y_mm"] for p in pads]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    tht = pads[0]["is_tht"]
    # pad extents (axis-aligned bounding box of each pad, Y up, centred)
    ext = []
    for p, x, y in zip(pads, xs, ys):
        a = math.radians(p["rot"])
        hw = abs(math.cos(a)) * p["pad_w"] / 2 + abs(math.sin(a)) * p["pad_h"] / 2
        hh = abs(math.sin(a)) * p["pad_w"] / 2 + abs(math.cos(a)) * p["pad_h"] / 2
        ext.append((x - cx - hw, y - cy - hh, x - cx + hw, y - cy + hh))
    bx0, by0 = min(e[0] for e in ext), min(e[1] for e in ext)
    bx1, by1 = max(e[2] for e in ext), max(e[3] for e in ext)
    # body = spec["body"] or the pad extents; courtyard 0.25 mm around body and pads (KLC),
    # a circle for single round pins (PIN terminals) so neighbours are not blocked diagonally
    if spec.get("body"):
        w, h = spec["body"]
        fx0, fy0, fx1, fy1 = -w / 2, -h / 2, w / 2, h / 2
    else:
        fx0, fy0, fx1, fy1 = bx0, by0, bx1, by1
    cx0, cy0 = min(fx0, bx0) - 0.25, min(fy0, by0) - 0.25
    cx1, cy1 = max(fx1, bx1) + 0.25, max(fy1, by1) + 0.25
    sx0, sy0, sx1, sy1 = fx0 - 0.12, fy0 - 0.12, fx1 + 0.12, fy1 + 0.12
    round_pin = len(pads) == 1 and abs(pads[0]["pad_w"] - pads[0]["pad_h"]) < 1e-6 and not spec.get("body")
    # file coordinates are Y down
    node = [Sym("footprint"), name, [Sym("version"), 20260206], [Sym("generator"), "ac_psu_gen_footprints"],
            [Sym("layer"), "F.Cu"], [Sym("descr"), f"{spec['descr']} (ac_psu, pads from IPC-D-356A {spec['ipc']})"],
            [Sym("property"), "Reference", "REF**", [Sym("at"), 0, _r4(-sy1 - 1.2), 0], [Sym("layer"), "F.SilkS"], _eff()],
            [Sym("property"), "Value", name, [Sym("at"), 0, _r4(-sy0 + 1.2), 0], [Sym("layer"), "F.Fab"], _eff()],
            [Sym("attr"), Sym("through_hole" if tht else "smd")],
            *([_circle(fx1, "Fab", 0.1), _circle(sx1, "SilkS", 0.12), _circle(cx1, "CrtYd", 0.05)] if round_pin else
              [_rect(fx0, -fy1, fx1, -fy0, "Fab", 0.1), _rect(sx0, -sy1, sx1, -sy0, "SilkS", 0.12),
               _rect(cx0, -cy1, cx1, -cy0, "CrtYd", 0.05)]),
            [Sym("fp_text"), Sym("user"), "${REFERENCE}", [Sym("at"), 0, 0, 0], [Sym("layer"), "F.Fab"], _eff()]]
    for p, x, y in zip(pads, xs, ys):
        px, py = _r4(x - cx), _r4(-(y - cy))
        rot = (-p["rot"] if mirror else p["rot"]) % 180.0
        at = [Sym("at"), px, py] + ([_r4(rot)] if rot else [])
        if tht:
            shape = "circle" if abs(p["pad_w"] - p["pad_h"]) < 1e-6 else "oval"
            node.append([Sym("pad"), p["pin"], Sym("thru_hole"), Sym(shape), at,
                         [Sym("size"), p["pad_w"], p["pad_h"]], [Sym("drill"), p["drill"]],
                         [Sym("layers"), "*.Cu", "*.Mask"]])
        else:
            node.append([Sym("pad"), p["pin"], Sym("smd"), Sym("rect"), at,
                         [Sym("size"), p["pad_w"], p["pad_h"]], [Sym("layers"), "F.Cu", "F.Paste", "F.Mask"]])
    node.append([Sym("embedded_fonts"), Sym("no")])
    return node


def build_library():
    ipc = fpgeom.ipc_pads_by_refdes()
    out = {}
    for name, spec in PROJECT.items():
        node = derive(name, spec, ipc) if spec.get("base") else from_ipc(name, spec, ipc)
        out[name + ".kicad_mod"] = sexpr.dump(node) + "\n"
    return out


def map_csv(assignment):
    pm = part_map()
    buf = io.StringIO()
    buf.write("# refdes -> footprint, generated by tools/gen_footprints.py (do not edit)\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["refdes", "lib_id", "footprint", "note"])
    for ref in sorted(pm, key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):] or 0), r)):
        fp, note = assignment.get(ref, ("", "not on the board" if pm[ref]["lib_id"].endswith("ETD34_TRAN_1P1S") else ""))
        w.writerow([ref, pm[ref]["lib_id"], fp, note])
    return buf.getvalue()


def main():
    check = "--check" in sys.argv
    assignment, errors = assign()
    used = {fp.split(":", 1)[1] for fp, _ in assignment.values() if fp.startswith("ac_psu:")}
    unused = sorted(set(PROJECT) - used)
    undefined = sorted(used - set(PROJECT))
    for n in unused:
        errors.append(f"project footprint {n} is not used")
    for n in undefined:
        errors.append(f"project footprint {n} is not defined")
    files = build_library()
    files_map = map_csv(assignment)
    stale = []
    want = {os.path.join(PRETTY, k): v for k, v in files.items()}
    want[MAP_CSV] = files_map
    have = set()
    if os.path.isdir(PRETTY):
        have = {os.path.join(PRETTY, f) for f in os.listdir(PRETTY) if f.endswith(".kicad_mod")}
    for path, text in want.items():
        cur = open(path).read() if os.path.exists(path) else None
        if cur != text:
            stale.append(path)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(text)
    extra = sorted(have - set(want))
    for path in extra:
        stale.append(path)
        if not check:
            os.remove(path)
    rel = [os.path.relpath(p, ROOT) for p in stale]
    for e in errors:
        print("gen_footprints: " + e)
    nfp = len({fp for fp, _ in assignment.values()})
    if check:
        if rel:
            print("gen_footprints: out of date: " + ", ".join(rel))
        print(f"gen_footprints: {len(assignment)} parts, {nfp} footprints ({len(files)} project)"
              + ("" if rel else ", up to date"))
        sys.exit(1 if rel or errors else 0)
    print(f"gen_footprints: {len(assignment)} parts, {nfp} footprints ({len(files)} project); "
          f"wrote {len(rel)} file(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
