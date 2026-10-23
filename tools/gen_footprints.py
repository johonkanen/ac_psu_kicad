"""Footprint assignment and the project footprint library of ac_psu (stdlib only).

Writes (through the shared generator p2k.footprints)
  lib/footprint_map.csv  refdes -> footprint (every IPC part; TR1 has none, it is not on the board:
                         OFF_BOARD_PARTS in p2k_config.py)
  lib/ac_psu.pretty/     project footprints (derived from KiCad library footprints, or built
                         from the IPC-D-356A pad geometry where KiCad has nothing that fits)

Usage: python3 tools/gen_footprints.py [--check]

This file holds what is decided for this board: RULES (symbol + IPC pad pattern -> footprint)
and PROJECT (the project footprint specs); the rule syntax and the spec keys are documented in
tools/p2k/p2k/footprints.py. Pad numbers always equal the IPC pin ids. Policy (PLAN.md 4.3): use
the KiCad library footprint unchanged when its pads land within 0.045 mm of the IPC pads;
otherwise derive a project footprint from it with the pad centres moved onto the Proteus
positions (KiCad pad sizes kept unless `ipc_sizes`), or build one from the IPC pads when KiCad
has no such package. tools/check_footprints.py verifies the result (residual < 0.05 mm per pad).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import footprints  # noqa: E402
from p2k.footprints import footprint_path  # noqa: E402,F401  (used by build_pcb.py)
import deviations  # noqa: E402  (v4 added parts)

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
        descr="SIP-3 P2.54, Proteus pads (1.8 mm) and drills (1.2 mm)"),
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


def main():
    # v4: parts added to the Proteus design (lib/v4_deviations.csv, no IPC pads)
    added = {ref: {"footprint": p["footprint"], "note": f"v4 fix {p['fix']}: {p['note']}"}
             for ref, p in deviations.added_parts().items()}
    footprints.run(RULES, PROJECT, added=added)


if __name__ == "__main__":
    main()
