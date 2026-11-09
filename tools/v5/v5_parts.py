"""v5 part list (stdlib only): the aux flyback that replaces the sheet 7 IW1830/EF20 supply
(V5_PLAN.md: UCC28710 + IPD95R450P7, EE25 vertical, 15V / 15V_ISO / CTRL winding) and the
control-card isolation (CTRL_ISOLATION_PLAN.md: CTRL islands A at J11 and B at J12).

One place for refdes, sheet, symbol, value and footprint: tools/v5/make_v5_lists.py writes the
part_map rows and the part/value rows of lib/v5_deviations.csv from it, and the sheet scripts
(sheet07.py, sheet11.py) take the values from here.
"""

# Proteus parts deleted in v5 (V5_PLAN.md step 2: the IW1830 flyback and its parts)
REMOVED = ("PWM1 TR2 R43 R34 R33 D7 C65 C66 R24 C62 R23 D6 R44 R25 C63 R26 R29 R31 R45 R47 D2 D1 R49").split()

# whole-net renames (V5_PLAN.md D6)
RENAMES = {"20V": "15V", "20V_ISO_SEC": "15V_ISO"}
# Proteus refdes without a trailing number: KiCad counts such a reference as unannotated and refuses
# "Update PCB from Schematic", so the KiCad design uses these names (kind refdes).
REFDES = {"AFE_OUT": "AFE_OUT1", "FILTER_IN": "FILTER_IN1", "FILTER_OUT": "FILTER_OUT1"}

R0402, R0603, R0805, R1206, R2512 = ("Resistor_SMD:R_0402_1005Metric", "Resistor_SMD:R_0603_1608Metric",
                                     "Resistor_SMD:R_0805_2012Metric", "Resistor_SMD:R_1206_3216Metric",
                                     "Resistor_SMD:R_2512_6332Metric")
C0402, C0603, C0805, C1206, C1210 = ("Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric",
                                     "Capacitor_SMD:C_0805_2012Metric", "Capacitor_SMD:C_1206_3216Metric",
                                     "Capacitor_SMD:C_1210_3225Metric")
CP8 = "Capacitor_SMD:CP_Elec_8x10"
SMA, SMB, SOD323 = "ac_psu:D_SMA_AC", "ac_psu:D_SMB_AC", "ac_psu:D_SOD-323_AC"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOIC16W = "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm"
TERM = "ac_psu:Terminal_D4.0mm_Drill3.0mm"

# (ref, sheet, symbol, value, footprint, note)
PARTS = [
    # ---- sheet 7: aux flyback (primary side, Out1 = 15V on GND) ----
    ("R98", 7, "R", "10R 2512", R2512, "aux input damping resistor DC+ -> AUX_VIN"),
    ("C111", 7, "C", "47n 1kV", C1210, "aux input filter"),
    ("C112", 7, "C", "47n 1kV", C1210, "aux input filter"),
    ("U18", 7, "UCC28710", "UCC28710DR", "ac_psu:SOIC-7_3.9x4.9mm_P1.27mm_UCC28710", "PSR flyback controller (JLC C80866)"),
    ("C113", 7, "C", "15u 50V", C1210, "UCC28710 VDD capacitor CDD"),
    ("C114", 7, "C", "100n", C0603, "UCC28710 VDD decoupling"),
    ("R100", 7, "R", "47R", R0603, "VDD feed from 15V"),
    ("D11", 7, "D", "BAS16WS", SOD323, "VDD feed diode"),
    ("R101", 7, "R", "59.0k", R0603, "VS divider RS1 (Out1 winding node)"),
    ("R102", 7, "R", "21.0k", R0603, "VS divider RS2"),
    ("R103", 7, "R", "118k", R0603, "cable compensation RCBC"),
    ("R104", 7, "R", "1k", R0603, "CS line-compensation resistor RLC (tune on the prototype)"),
    ("R105", 7, "R", "0.562R", R1206, "current-sense resistor RCS"),
    ("Q15", 7, "MMBT3904", "MMBT3904", SOT23, "gate buffer, source"),
    ("Q16", 7, "MMBT3906", "MMBT3906", SOT23, "gate buffer, sink"),
    ("R106", 7, "R", "10R", R0603, "gate resistor"),
    ("R107", 7, "R", "10k", R0603, "gate-source pull-down"),
    ("Q17", 7, "IPD95R450P7", "IPD95R450P7", "Package_TO_SOT_SMD:TO-252-2", "950 V MOSFET (JLC C3289115)"),
    ("D12", 7, "D", "US1M", SMA, "clamp diode 1000 V"),
    ("D13", 7, "D_TVS", "SMBJ170A", SMB, "clamp TVS (~230 V at 1.4 A): drain peak ~450 + 240 V"),
    ("T1", 7, "EE25_AUX_TRANS", "EE25 aux flyback", "ac_psu:Transformer_EE25_Ferroxcube_CPV-E25-13-7-1S-10P_Vertical",
     "E25/13/7 N87, Lp 322 uH, P1 16 / CTRL 3 TIW / Out1 5 / P2 16 / Out2 5 TIW (reports/aux_flyback)"),
    ("D14", 7, "D", "ES2D", SMA, "Out1 rectifier 200 V 2 A"),
    ("C115", 7, "C_Polarized", "470u 25V", CP8, "Out1 (15V) output capacitor"),
    ("R108", 7, "R", "4.7k", R0805, "Out1 preload"),
    ("D15", 7, "D", "ES2D", SMA, "Out2 rectifier 200 V 2 A"),
    ("C116", 7, "C_Polarized", "470u 25V", CP8, "Out2 (15V_ISO) output capacitor"),
    ("R109", 7, "R", "4.7k", R0805, "Out2 preload"),
    # ---- sheet 7: CTRL winding -> 5V_CTRL (island B at J12) ----
    ("W1", 7, "CTRL_WINDING", "CTRL winding (T1, TIW)", "ac_psu:CTRL_Winding_Leads_2x1.6mm_P5.08mm",
     "CTRL winding flying leads of T1 (3 x TIW 25 AWG)"),
    ("D16", 7, "D_Schottky", "SS310", SMA, "CTRL rectifier 100 V 3 A"),
    ("C137", 7, "C_Polarized", "470u 16V", CP8, "CTRL_RAW capacitor"),
    ("C138", 7, "C_Polarized", "470u 16V", CP8, "CTRL_RAW capacitor"),
    ("R131", 7, "R", "910R", R1206, "CTRL preload ~10 mA"),
    ("U28", 7, "TPS54202", "TPS54202DDCR", "Package_TO_SOT_SMD:SOT-23-6", "5V_CTRL buck for the control card"),
    ("C139", 7, "C", "10u 25V", C1206, "buck input"),
    ("C140", 7, "C", "100n", C0603, "buck input HF"),
    ("R132", 7, "R", "511k", R0603, "EN divider (start ~7 V)"),
    ("R133", 7, "R", "105k", R0603, "EN divider"),
    ("C141", 7, "C", "100n", C0603, "bootstrap"),
    ("L2", 7, "L", "15u", "Inductor_SMD:L_Sunlord_SWPA6045S", "buck inductor 15 uH (SWPA6045S150MT)"),
    ("C142", 7, "C", "22u 10V", C1206, "buck output"),
    ("C143", 7, "C", "22u 10V", C1206, "buck output"),
    ("R134", 7, "R", "100k", R0603, "FB divider top"),
    ("R135", 7, "R", "13.3k", R0603, "FB divider bottom (5.0 V)"),
    ("C144", 7, "C", "75p", C0603, "FB feed-forward"),
    ("J13", 7, "CONN_2", "CTRL 5V link B", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "5V_CTRL/CTRLGND to island A (double-insulated wire to J14)"),
    ("PEC2", 7, "PIN", "PIN", TERM, "PE bond of CTRL island B (CTRLGND)"),
    # ---- sheet 11: CTRL island A at J11 ----
    ("J14", 11, "CONN_2", "CTRL 5V link A", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "5V_CTRL_A/CTRLGND_A from island B (J13)"),
    ("PEC1", 11, "PIN", "PIN", TERM, "PE bond of CTRL island A (CTRLGND_A)"),
    ("U27", 11, "TPS73033DBVT", "TPS73033DBVT", "Package_TO_SOT_SMD:SOT-23-5", "3V3_CTRL LDO"),
    ("C134", 11, "C", "10n", C0402, "LDO NR"),
    ("C135", 11, "C", "2.2u", C0603, "LDO output"),
    ("C136", 11, "C", "1u", C0603, "LDO input"),
    ("U19", 11, "ISO7760F", "ISO7760FDWR", SOIC16W, "ISO-side PWMs Q5-Q8, TRANS4/5 (JLC C2878538)"),
    ("U20", 11, "ISO7760F", "ISO7760FDWR", SOIC16W, "ISO-side PWMs TRANS6, DAB_SEC, relay (JLC C2878538)"),
    ("C117", 11, "C", "100n", C0402, "U19 CTRL side"),
    ("C118", 11, "C", "100n", C0402, "U19 ISO side"),
    ("C119", 11, "C", "100n", C0402, "U20 CTRL side"),
    ("C120", 11, "C", "100n", C0402, "U20 ISO side"),
    ("U21", 11, "CA-IS3742", "CA-IS3742LW", SOIC16W, "U4/U6 sigma-delta clock and data (JLC C4944981)"),
    ("C121", 11, "C", "100n", C0402, "U21 CTRL side"),
    ("C122", 11, "C", "100n", C0402, "U21 ISO side"),
] + [
    p for n, ch, cap in ((22, 1, "4.7n"), (23, 2, "4.7n"), (24, 3, "10n")) for p in (
        (f"U{n}", 11, "AMC1311", "AMC1311BDWVR", "Package_SO:SOIC-8_7.5x5.85mm_P1.27mm", f"ISOADA{ch} isolated amplifier (JLC C783598)"),
        (f"C{123 + 2 * (ch - 1)}", 11, "C", "100n", C0402, f"U{n} VDD1 (ISO)"),
        (f"C{124 + 2 * (ch - 1)}", 11, "C", "100n", C0402, f"U{n} VDD2 (CTRL)"),
        (f"R{110 + 2 * (ch - 1)}", 11, "R", "6.8k 0.1%", R0603, f"ISOADA{ch} divider top (x0.4 with the 8.2k source)"),
        (f"R{111 + 2 * (ch - 1)}", 11, "R", "10k 0.1%", R0603, f"ISOADA{ch} divider bottom"),
        (f"R{116 + 4 * (ch - 1)}", 11, "R", "10k 0.1%", R0603, f"ch{ch} diff amp input (OUTN)"),
        (f"R{117 + 4 * (ch - 1)}", 11, "R", "24.9k 0.1%", R0603, f"ch{ch} diff amp feedback (gain 2.49)"),
        (f"R{118 + 4 * (ch - 1)}", 11, "R", "10k 0.1%", R0603, f"ch{ch} diff amp input (OUTP)"),
        (f"R{119 + 4 * (ch - 1)}", 11, "R", "24.9k 0.1%", R0603, f"ch{ch} diff amp reference leg"),
        (f"R{127 + ch}", 11, "R", "8.2k", R0402, f"ISOADA{ch}_CTRL output filter R (as before at J11)"),
        (f"C{128 + ch}", 11, "C", f"{cap} C0G", C0402, f"ISOADA{ch}_CTRL output filter C"),
    )
] + [
    ("U25", 11, "OPA2350EA", "OPA2350EA", "Package_SO:VSSOP-8_3x3mm_P0.65mm", "CTRL diff amps ch1/ch2"),
    ("U26", 11, "OPA2350EA", "OPA2350EA", "Package_SO:VSSOP-8_3x3mm_P0.65mm", "CTRL diff amp ch3 (B spare)"),
    ("C132", 11, "C", "100n", C0402, "U25 decoupling"),
    ("C133", 11, "C", "100n", C0402, "U26 decoupling"),
]

VALUE = {p[0]: p[3] for p in PARTS}
