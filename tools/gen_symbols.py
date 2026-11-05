#!/usr/bin/env python3
"""Generate lib/ac_psu.kicad_sym, the project symbol library (helpers: p2k.symgen).

Pin numbers equal the Proteus/IPC pin ids. Simple symbols are copied from the
KiCad 10 standard library (flattened, pins renumbered); ICs and other parts are
drawn as boxes with the pin names of the Proteus symbols (pin names follow the
Proteus drawing, which for REF3025 differs from the KiCad library pinout).
Power symbols carry the IPC net names.

Run:  tools/gen_symbols.py           (needs the AppImage mount for the std libs)
      tools/gen_symbols.py --check   (fail if lib/ac_psu.kicad_sym is not up to date)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k.symgen import *  # noqa: E402,F401,F403
from p2k.symgen import run  # noqa: E402


GROUNDS = ["GND", "PGND", "ISOGND", "ISOPGND", "DAB_GROUND",  # v4: DGND, RET_ISO merged into GND / ISOGND
           "CTRLGND", "CTRLGND_A"]  # v5: control-card domain, islands B (J12) and A (J11)
# v5: 20V / 20V_ISO_SEC renamed 15V / 15V_ISO (aux flyback outputs), CTRL rails added
SUPPLIES = ["VCC", "3V3_ISO", "5V", "5V_ISOL", "15V", "15V_ISO", "DC+", "ISODC+",
            "3V3_CTRL", "5V_CTRL", "5V_CTRL_A"]


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
        box("SLA-12VDC-SL-A", "K",
            [(6, "COIL_2", PAS), (5, "COM_2", PAS)],
            [(3, "NO", PAS), (2, "COIL_1", PAS), (1, "COM_1", PAS)],
            desc="Power relay (Proteus refdes R20/R79; no pin 4)"),
    ]
    # v5: aux flyback (UCC28710 + 950 V MOSFET, EE25) and control-card isolation (CTRL domain)
    syms += [
        from_std("Device", "Q_NMOS", "IPD95R450P7", "Q", desc="950 V N-MOSFET, DPAK (TO-252-2), 1=G 2=D (tab) 3=S",
                 pins={"G": "1", "D": "2", "S": "3"}, names={"1": "G", "2": "D", "3": "S"}),
        from_std("Device", "Q_NPN", "MMBT3904", "Q", desc="NPN, SOT-23, 1=B 2=E 3=C",
                 pins={"B": "1", "E": "2", "C": "3"}, names={"1": "B", "2": "E", "3": "C"}),
        from_std("Device", "Q_PNP", "MMBT3906", "Q", desc="PNP, SOT-23, 1=B 2=E 3=C",
                 pins={"B": "1", "E": "2", "C": "3"}, names={"1": "B", "2": "E", "3": "C"}),
        from_std("Device", "D_Zener", "D_TVS", "D", desc="Unidirectional TVS diode, pins A/C", pins=D_PINS),
        from_std("Connector_Generic", "Conn_01x02", "CONN_2", "J", desc="2-pin connector"),
        from_std("Amplifier_Operational", "LM2904", "OPA2350EA", "U", desc="Dual rail-to-rail op-amp, VSSOP-8"),
        box("UCC28710", "U", [(7, "HV", PAS), (1, "VDD", PI), (2, "VS", IN), (3, "CBC", PAS)],
            [(6, "DRV", OUT), (5, "CS", IN), None, (4, "GND", PI)],
            desc="PSR flyback controller, SOIC-7 (D): pin 7 = HV at the pin-8 position"),
        box("EE25_AUX_TRANS", "T", [(i, str(i), PAS) for i in (1, 2, 3, 4, 5)],
            [(i, str(i), PAS) for i in (10, 9, 8, 7, 6)],
            desc="EE25 aux flyback transformer, Ferroxcube CPV-E25/13/7-1S-10P-Z (1 drain, 2 DC+, 3 P1/P2 joint, "
                 "4 GND, 5 Out1, 6 Out2, 7 ISOGND, 8-10 cut)"),
        box("CTRL_WINDING", "W", [(1, "CTRL+", PAS)], [(2, "CTRL-", PAS)],
            desc="CTRL winding of the aux transformer T1: TIW flying leads soldered into two holes (no pins on T1)"),
        box("ISO7760F", "U", [(1, "VCC1", PI)] + [(i + 2, f"IN{c}", IN) for i, c in enumerate("ABCDEF")] + [(8, "GND1", PI)],
            [(16, "VCC2", PI)] + [(15 - i, f"OUT{c}", OUT) for i, c in enumerate("ABCDEF")] + [(9, "GND2", PI)],
            desc="6-channel reinforced digital isolator (6 forward, default low), SOIC-16 wide"),
        box("CA-IS3742", "U",
            [(1, "VDDA", PI), (3, "A1", IN), (4, "A2", IN), (5, "A3", OUT), (6, "A4", OUT), (7, "ENA", IN),
             (2, "GNDA", PI), (8, "GNDA", PI)],
            [(16, "VDDB", PI), (14, "B1", OUT), (13, "B2", OUT), (12, "B3", IN), (11, "B4", IN), (10, "ENB", IN),
             (9, "GNDB", PI), (15, "GNDB", PI)],
            desc="4-channel reinforced digital isolator (2 forward, 2 reverse), SOIC-16 wide"),
        box("AMC1311", "U", [(1, "VDD1", PI), (2, "IN", IN), (3, "SHTDN", IN), (4, "GND1", PI)],
            [(8, "VDD2", PI), (7, "OUTP", OUT), (6, "OUTN", OUT), (5, "GND2", PI)],
            desc="Reinforced isolated amplifier, 0-2 V input, gain 1, SOIC-8 wide (DWV)"),
        box("TPS54202", "U", [(3, "VIN", PI), (5, "EN", IN), None, (1, "GND", PI)],
            [(6, "BOOT", PAS), (2, "SW", PAS), None, (4, "FB", IN)],
            desc="28 V 2 A synchronous buck, 500 kHz, SOT-23-6"),
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


if __name__ == "__main__":
    sys.exit(run(build))
