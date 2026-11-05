#!/usr/bin/env python3
"""Sheet 7 - Auxiliary supply, v5 (V5_PLAN.md; the v4 IW1830/EF20 flyback of PDF page 7 is in git
history before v5): UCC28710 primary-side-regulated flyback with the external 950 V MOSFET Q17,
EE25 transformer T1 (vertical Ferroxcube former), outputs Out1 = 15V on GND (also the PSR sense and
VDD winding), Out2 = 15V_ISO on ISOGND (reinforced, TIW), and the CTRL winding W1 (TIW flying
leads) -> CTRL_RAW -> TPS54202 buck -> 5V_CTRL for the control card at J12 (CTRL island B, bonded
to PE by PEC2, linked to island A by J13). Kept from v4: C28/C41 (15V), C36/C15 (15V_ISO),
C67/C58/C57 (5V), C68 (DC+)."""
import os
import sys

from _common import *  # noqa: F401,F403

sys.path.insert(0, os.path.join(TOOLS, "v5"))
from v5_parts import VALUE as V  # noqa: E402

sh = sheet("07_auxiliary_supply.kicad_sch")


def flag_net(net, x, y):
    """PWR_FLAG on a global-label net (a power input fed only through passives)."""
    sh.glabel(net, x, y, 180)
    sh.wire((x, y), right((x, y), 2))
    sh.pwr_flag(*right((x, y), 2), 270)


def row(y, x0, parts, step=10):
    """Vertical two-pin parts side by side: (sym, ref, value, top net, bottom net, top pin)."""
    for i, (sym, ref, val, na, nb, a) in enumerate(parts):
        part2(sh, sym, ref, x0 + g(step * i), y, val, na, nb, a=a)


# ---- kept rail capacitors (v4 refdes) ------------------------------------------------------
sh.text("Rails kept from v4: 15V (was 20V) C28/C41, 5V C67/C58/C57, 15V_ISO (was 20V_ISO_SEC) C36/C15, DC+ C68.",
        g(16), g(12))
row(g(22), g(20), [
    ("C_Polarized", "C28", "220u", "15V", "GND", 1),
    ("C", "C41", "4.7u", "15V", "GND", 1),
    ("C", "C67", "100u", "GND", "5V", 1),
    ("C", "C58", "22u", "GND", "5V", 1),
    ("C", "C57", "22u", "GND", "5V", 1),
    ("C", "C68", "100n", "DC+", "GND", 2),
    ("C", "C36", "4.7u", "15V_ISO", "ISOGND", 1),
    ("C_Polarized", "C15", "220u", "15V_ISO", "ISOGND", 1),
])
sh.text("C67: 100 uF ceramic (X5R 1206; v4 clean-up, was drawn polarized).", g(20), g(34))
for i, net in enumerate(("15V", "15V_ISO", "GND")):
    flagged_power(sh, net, g(110 + 8 * i), g(22))

# ---- input, controller, MOSFET, clamp --------------------------------------------------------
sh.text("Primary: DC+ (100-450 V) -> R98 -> AUX_VIN (C111/C112) -> T1 pin 2; UCC28710 HV start-up from AUX_VIN.",
        g(16), g(44))
row(g(54), g(20), [
    ("R", "R98", V["R98"], "DC+", "AUX_VIN", 1),
    ("C", "C111", V["C111"], "AUX_VIN", "GND", 1),
    ("C", "C112", V["C112"], "AUX_VIN", "GND", 1),
    ("D", "D12", V["D12"], "AUX_DRAIN", "AUX_CLAMP", "A"),
    ("D_TVS", "D13", V["D13"], "AUX_CLAMP", "AUX_VIN", "C"),
])
sh.text("Clamp: drain -> D12 (1000 V) -> AUX_CLAMP -> D13 TVS -> AUX_VIN (drain peak ~450 + 240 V < 950 V).",
        g(16), g(71))
ic(sh, "UCC28710", "U18", g(90), g(84), {7: "AUX_VIN", 1: "AUX_VDD", 2: "AUX_VS", 3: "AUX_CBC",
                                         6: "AUX_DRV", 5: "AUX_CSP", 4: "GND"}, value=V["U18"])
flag_net("AUX_VDD", g(40), g(84))
row(g(110), g(20), [
    ("C", "C113", V["C113"], "AUX_VDD", "GND", 1),
    ("C", "C114", V["C114"], "AUX_VDD", "GND", 1),
    ("R", "R100", V["R100"], "15V", "AUX_VDDR", 1),
    ("D", "D11", V["D11"], "AUX_VDDR", "AUX_VDD", "A"),
    ("R", "R101", V["R101"], "AUX_W1", "AUX_VS", 1),
    ("R", "R102", V["R102"], "AUX_VS", "GND", 1),
    ("R", "R103", V["R103"], "AUX_CBC", "GND", 1),
    ("R", "R104", V["R104"], "AUX_CS", "AUX_CSP", 1),
    ("R", "R105", V["R105"], "AUX_CS", "GND", 1),
    ("R", "R106", V["R106"], "AUX_GATED", "AUX_GATE", 1),
    ("R", "R107", V["R107"], "AUX_GATE", "AUX_CS", 1),
])
sh.text("VDD from 15V (Out1) via R100 + D11; CDD 15 uF. VS divider RS1/RS2 from the Out1 winding node AUX_W1, "
        "RCBC 118k, RLC 1k, RCS 0.562R (V5_PLAN.md 5.3).", g(16), g(127))
ic(sh, "MMBT3904", "Q15", g(150), g(82), {1: "AUX_DRV", 3: "AUX_VDD", 2: "AUX_GATED"}, value=V["Q15"])
ic(sh, "MMBT3906", "Q16", g(180), g(82), {1: "AUX_DRV", 3: "GND", 2: "AUX_GATED"}, value=V["Q16"])
ic(sh, "IPD95R450P7", "Q17", g(210), g(82), {1: "AUX_GATE", 2: "AUX_DRAIN", 3: "AUX_CS"}, value=V["Q17"])
sh.text("Gate buffer Q15/Q16 (DRV sources only 20-25 mA; Q17 Qg 35 nC).", g(140), g(96))

# ---- transformer and outputs ---------------------------------------------------------------------
ic(sh, "EE25_AUX_TRANS", "T1", g(270), g(40), {1: "AUX_DRAIN", 2: "AUX_VIN", 3: None, 4: "GND", 5: "AUX_W1",
                                               6: "AUX_W2", 7: "ISOGND", 8: None, 9: None, 10: None},
   value=V["T1"], n=4)
for i, t in enumerate(("T1: E25/13/7 N87 on Ferroxcube CPV-E25/13/7-1S-10P-Z (vertical), Lp 322 uH, gap ~0.22 mm.",
                       "Primary row: 1 drain, 2 DC+ (AUX_VIN), 3 P1/P2 joint (no net), 4 GND, 5 Out1.",
                       "Secondary row: 6 Out2+, 7 ISOGND, 8-10 cut. CTRL winding = W1 (TIW flying leads).",
                       "Reinforced: {primary, Out1} | Out2 | CTRL. Core floating: insulate it (tape/caps).")):
    sh.text(t, g(240), g(56 + 3 * i))
row(g(84), g(240), [
    ("D", "D14", V["D14"], "AUX_W1", "15V", "A"),
    ("C_Polarized", "C115", V["C115"], "15V", "GND", 1),
    ("R", "R108", V["R108"], "15V", "GND", 1),
    ("D", "D15", V["D15"], "AUX_W2", "15V_ISO", "A"),
    ("C_Polarized", "C116", V["C116"], "15V_ISO", "ISOGND", 1),
    ("R", "R109", V["R109"], "15V_ISO", "ISOGND", 1),
])

# ---- CTRL winding -> 5V_CTRL (island B) ----------------------------------------------------------
sh.text("CTRL island B (at J12): W1 -> D16 -> CTRL_RAW (~9 V, 11.5 V at no load) -> U28 buck -> 5V_CTRL; "
        "PEC2 bonds CTRLGND to PE; J13 feeds island A.", g(16), g(134))
part2(sh, "CTRL_WINDING", "W1", g(34), g(148), V["W1"], "CTRL_W", "CTRLGND", horizontal=True)
row(g(160), g(50), [
    ("D_Schottky", "D16", V["D16"], "CTRL_W", "CTRL_RAW", "A"),
    ("C_Polarized", "C137", V["C137"], "CTRL_RAW", "CTRLGND", 1),
    ("C_Polarized", "C138", V["C138"], "CTRL_RAW", "CTRLGND", 1),
    ("R", "R131", V["R131"], "CTRL_RAW", "CTRLGND", 1),
    ("C", "C139", V["C139"], "CTRL_RAW", "CTRLGND", 1),
    ("C", "C140", V["C140"], "CTRL_RAW", "CTRLGND", 1),
    ("R", "R132", V["R132"], "CTRL_RAW", "CTRL_EN", 1),
    ("R", "R133", V["R133"], "CTRL_EN", "CTRLGND", 1),
])
ic(sh, "TPS54202", "U28", g(170), g(160), {3: "CTRL_RAW", 5: "CTRL_EN", 1: "CTRLGND", 6: "CTRL_BOOT",
                                           2: "CTRL_SW", 4: "CTRL_FB"}, value=V["U28"])
flag_net("CTRL_RAW", g(150), g(176))
row(g(160), g(210), [
    ("C", "C141", V["C141"], "CTRL_BOOT", "CTRL_SW", 1),
    ("L", "L2", V["L2"], "CTRL_SW", "5V_CTRL", 1),
    ("C", "C142", V["C142"], "5V_CTRL", "CTRLGND", 1),
    ("C", "C143", V["C143"], "5V_CTRL", "CTRLGND", 1),
    ("R", "R134", V["R134"], "5V_CTRL", "CTRL_FB", 1),
    ("C", "C144", V["C144"], "5V_CTRL", "CTRL_FB", 1),
    ("R", "R135", V["R135"], "CTRL_FB", "CTRLGND", 1),
])
j = ic(sh, "CONN_2", "J13", g(300), g(160), {1: "5V_CTRL", 2: "CTRLGND"}, value=V["J13"])
terminal(sh, "PEC2", g(316), g(156), "up")
net_at(sh, (g(316), g(156)), "CTRLGND", "down")
flagged_power(sh, "5V_CTRL", g(290), g(180))
flagged_power(sh, "CTRLGND", g(300), g(180))
sh.text("J13 -> J14 (sheet 11): double-insulated two-wire link 5V_CTRL/CTRLGND to CTRL island A.", g(240), g(192))
sh.save()
print("sheet07: written")
