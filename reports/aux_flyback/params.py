"""Design parameters of the v5 aux flyback (20 W, EE25, CTRL on TIW flying leads): Infineon ICE5AR0680BZS (fixed
100 kHz, integrated 800 V / 0.71 ohm CoolMOS and error amplifier; v5 step 7, 2026-11-18, before that UCC28710 +
IPD95R450P7), 100-450 V DC in (DC+ limited to 450 V), Out1 15 V (GND, regulated through VERR, feeds VCC),
Out2 15 V (ISOGND), CTRL ~9 V (control card, buck to 5 V).
Three reinforced-separated groups: {primary, Out1}, Out2, CTRL. See README.md and V5_PLAN.md 5.4 / 5.5. All values SI.
v5 step 8: EEL19 core and bobbin (TURNSETS A) and the SMD package ICE5AR0680AG; the MKF scripts still describe the EE25."""
import math

# ---- input / controller (ICE5ARxxxxBZS datasheet V2.3, 2020-02-03) -----------------------------------
VIN_MIN, VIN_MID, VIN_MAX = 100.0, 300.0, 450.0   # V DC, full power at VIN_MIN continuous; 450 V is a hard limit now
FSW = 100e3             # fixed oscillator frequency (94..106 kHz at 25 C, +-4 % jitter)
FSW_MIN = 92e3          # over temperature
VCS_N = (0.72, 0.80, 0.88)       # peak current limit threshold at CS: min, typ, max
RDS_HOT = 1.271         # ohm at Tj 125 C, ID 2 A (0.71 typ / 0.80 max at 25 C), incl. the low-side MOSFET
CO_ER = 24e-12          # effective output capacitance, energy related, 0..500 V
RTH_JA = (94.0, 65.0)   # K/W: ICE5AR0680AG data sheet with the minimum drain-pin copper; estimate with ~230 mm2 on the drain pins
                        # (Infineon's 24 W demo board: 61..66 K rise of a 2.2 ohm part at about 1 W)
K_OFF = 0.4             # turn-off loss as a share of 0.5 V I tf f: the drain capacitance takes over part of the
                        # current while the channel closes. ESTIMATE; 1.0 is the upper bound. Measure on the board.
ID_PULSE = 5.82         # A
VCC_ON, VCC_OFF, VCC_OVP = 16.0, 10.0, 25.5   # typ (VCC_OFF max 10.4)
IVCC_CH1, IVCC_CH3 = 0.20e-3, 3.0e-3   # VCC charge currents typ (below / above VCC_SCP 1.1 V)
IVCC_RUN = 2.5e-3       # estimate: IC supply current with the gate charge of the 0.71 ohm switch at 100 kHz
VERR_REF = 1.80         # error amplifier reference (1.76 .. 1.84)
IERR_BIAS_MIN, VERR_SEL_MAX = 9.5e-6, 0.24    # VERR bias current min, non-isolated selection threshold max
T_SS = 12e-3            # digital soft start

# ---- turn set (Np, Ns, Nctrl, Nbias); TURNSET env var for the comparison run ---------------------
import os as _os
TURNSETS = {"A": (70, 11, 7, 0), "EE25": (32, 5, 3, 0)}   # A: EEL19 (v5 step 8); EE25: the first design   # (Np, Ns, Nctrl, Nbias): no bias winding since 2026-10-31
TURNSET = TURNSETS[_os.environ.get("TURNSET", "A")]
CTRL_V = TURNSET[2] * TURNSET[0] / TURNSET[1] * 15.7 / TURNSET[0] - 0.45   # CTRL winding minus Schottky drop
CTRL_I = 9.0 / CTRL_V                                                       # 9 W into the buck

# ---- outputs (design load 20 W total, user decision 2026-10-31; was 25 W in 3b4a33d) -------------
#          name    V     I     diode VF  isolation side (MKF)
OUTPUTS = [("Out1", 15.0, 0.39, 0.70, "primary"),     # 15V on GND (primary group): 5.5 W + VCC; regulated through VERR
           ("Out2", 15.0, 0.33, 0.70, "secondary"),   # 15V_ISO on ISOGND, 5 W
           ("CTRL",  CTRL_V, CTRL_I, 0.45, "tertiary")]  # control card: winding into a 5 V buck, 9 W
# No separate bias winding (user, 2026-10-31): the 15V rail (Out1) is regulated directly through the VERR
# divider and supplies VCC through a diode + resistor (~14.3 V).
ETA = 0.86              # converter efficiency estimate at 100 V full load (for the input power)
ETA_XFMR = 0.90         # transformer efficiency term (leakage, losses)

# ---- transformer (unchanged from the UCC28710 design: same core, turns and inductance) --------------
NP, NS, NC, NB = TURNSET      # primary, 15 V windings, CTRL, (bias: none, NB = 0)
VOR = NP / NS * (15.0 + 0.70)  # reflected voltage (~100 V: set by DCM at 100 V input)
LP = 322e-6             # primary inductance, as designed for the UCC28710 at its CC point; kept
RCS = 0.562             # current-sense resistor (E96), kept
POUT = sum(v * i for _, v, i, _, _ in OUTPUTS)
IPP_FULL = math.sqrt(2 * POUT / (LP * FSW * ETA_XFMR))   # peak current at the design load, 100 kHz, DCM
IPP = VCS_N[1] / RCS                                      # typical peak current limit (flux and wire checks use it)
LP_IPP = LP * IPP

# ---- switch / clamp ------------------------------------------------------------------------------
VDS_RATING = 800.0      # ICE5AR0680BZS
V_CLAMP = 205.0         # SMBJ150A: Vbr 167..185 V, Vc 243 V at 2.5 A -> ~190 V typ, ~205 V worst at 1.2..1.4 A
LK_EFF = 5.9e-6         # effective primary leakage at full load: MKF pairwise P->Out1/Out2/CTRL (6.1/11.2/2.9 uH,
                        # winding order O2) weighted by each output's power share (conservative; measure on the sample)
VDS_PK = VIN_MAX + V_CLAMP

# ---- thermal ----------------------------------------------------------------------------------
T_AMB = 55.0            # internal air: 30 C rated ambient (user 2026-10-31) + an assumed 20-30 K rise of the passively
                        # cooled closed chassis (no dissipation figure for the whole unit yet; must be measured)

# ---- MKF modelling ----------------------------------------------------------------------------
MATERIAL = "N87"
TAPE = 25e-6            # one layer of polyester tape between sections (mechanical; TIW carries the insulation)

CANDIDATES = {
    # name: (core shape, bobbin, catalogue gap or None, primary wire, Out1 wire, Out2 TIW, CTRL TIW (n parallel), bias wire)
    "EE25": ("E 25/13/7", "Bobbin EE 25 horizontal longer-creepage 10-pin 5.08mm (Norwe 10165-106)"),  # chosen
    "E30":  ("E 30/15/7", "Bobbin E 30/15/7 (Ferroxcube CP-E30/15/7-1S)"),
    "EE32": ("E 32/16/9", "Bobbin EE 32 horizontal 12-pin 5.08mm (Norwe 10750-024)"),
}
WIRES = {"Primary": ("Round 0.4 - Grade 2", 1),
         "Out1": ("Round 0.63 - Grade 2", 1),
         "Out2": ("Round TCA3 24 AWG", 1),
         "CTRL": ("Round TCA3 25 AWG", 3),
         }
TURNS = {"Primary": NP, "Out1": NS, "Out2": NS, "CTRL": NC}


def summary():
    rows = [f"VOR {VOR:.1f} V, Lp {LP*1e6:.0f} uH, RCS {RCS:.3f} ohm, fsw {FSW/1e3:.0f} kHz fixed"]
    rows.append(f"design load {POUT:.1f} W -> peak current {IPP_FULL:.3f} A at 100 kHz (DCM)")
    lim = [v / RCS for v in VCS_N]
    rows.append("peak current limit VCS_N / RCS: " + " / ".join(f"{i:.2f}" for i in lim) + " A (min / typ / max) -> output power at "
                "the limit " + " / ".join(f"{0.5*LP*i**2*f*ETA_XFMR:.1f}" for i, f in zip(lim, (FSW_MIN, FSW, 106e3)))
                + f" W; margin over the load at the minimum {0.5*LP*lim[0]**2*FSW_MIN*ETA_XFMR/POUT:.2f}x; ID,pulse {ID_PULSE} A")
    for vin in (VIN_MIN, VIN_MID, VIN_MAX):
        ton = LP * IPP_FULL / vin
        tdm = LP * IPP_FULL / VOR
        d = ton * FSW
        irms = IPP_FULL * math.sqrt(d / 3)
        p_cond = irms ** 2 * RDS_HOT
        p_coss = 0.5 * CO_ER * vin ** 2 * FSW          # DCM, hard turn-on at about Vin (no valley switching)
        p_off = K_OFF * 0.5 * vin * IPP_FULL * 30e-9 * FSW      # turn-off overlap, 30 ns fall time
        p_hi = p_cond + p_coss + p_off / K_OFF + 15 * IVCC_RUN
        p = p_cond + p_coss + p_off + 15 * IVCC_RUN
        rows.append(f"  Vin {vin:3.0f} V: ton {ton*1e6:.2f} us, tdemag {tdm*1e6:.2f} us, D {d:.3f}, period use {(ton+tdm)*FSW:.2f}, "
                    f"Ipri rms {irms:.3f} A; U18 loss {p_cond:.2f} cond + {p_coss:.2f} Coss + {p_off:.2f} turn-off + "
                    f"{15*IVCC_RUN:.2f} supply = {p:.2f} W (upper bound {p_hi:.2f} W) -> Tj ~{T_AMB + p*RTH_JA[1]:.0f} C at {T_AMB:.0f} C air "
                    f"with drain copper ({RTH_JA[1]:.0f} K/W), ~{T_AMB + p*RTH_JA[0]:.0f} C without ({RTH_JA[0]:.0f} K/W); upper bound "
                    f"{T_AMB + p_hi*RTH_JA[1]:.0f} C with copper")
    ton_l, tdm_l = LP * lim[2] / VIN_MIN, LP * lim[2] / VOR
    rows.append(f"at the maximum current limit, 100 V: ton {ton_l*1e6:.2f} + tdemag {tdm_l*1e6:.2f} us = {(ton_l+tdm_l)*FSW:.2f} of the "
                f"period (above 1.0 = CCM, which the controller supports with slope compensation)")
    rows.append(f"drain peak at 450 V: {VIN_MAX:.0f} + clamp {V_CLAMP:.0f} = {VDS_PK:.0f} V ({VDS_PK/VDS_RATING*100:.0f} % of {VDS_RATING:.0f} V)")
    for name, ipk in (("design load", IPP_FULL), ("typical limit", lim[1])):
        rows.append(f"clamp loss at the {name} (leakage {LK_EFF*1e6:.1f} uH, {ipk:.2f} A, Vclamp {V_CLAMP:.0f} V): "
                    f"{0.5*LK_EFF*ipk**2*FSW*V_CLAMP/(V_CLAMP-VOR):.2f} W")
    rows.append(f"RCS {RCS:.3f} ohm 1 %: {(IPP_FULL*math.sqrt(LP*IPP_FULL/VIN_MIN*FSW/3))**2*RCS:.2f} W at 100 V")
    for name, v, i, vf, _ in OUTPUTS:
        n = {"Out1": NS, "Out2": NS, "CTRL": NC}[name]
        vrev = VIN_MAX * n / NP + v
        rows.append(f"  {name}: N {n}, winding {n*VOR/NP:.2f} V -> out {n*VOR/NP - vf:.2f} V; diode reverse {vrev:.0f} V")
    rows += control()
    rows += eel19()
    return "\n".join(rows)


# ---- EEL19 (v5 step 8): hand calculation, not an MKF run -------------------------------------------------
EEL19 = dict(Ae=23.4e-6, Ve=1.45e-6, win_w=21.2e-3, win_h=3.975e-3, mlt=(30e-3, 34e-3, 38e-3, 42e-3), surface=19.6e-4)
#   core data and window from ~/dev/tube_psu_kicad simulation/flyback/EEL19_DESIGN.md (seller's table; window assumed)
EEL19_WIND = [   # layer (inner -> outer): name, turns, strands, copper d, outer d, Irms at 100 V
    ("P1", NP // 2, 1, 0.35e-3, 0.39e-3, None), ("CTRL (TIW) + Out1", None, None, None, 0.66e-3, None),
    ("P2", NP - NP // 2, 1, 0.35e-3, 0.39e-3, None), ("Out2 (TIW)", NS, 1, 0.40e-3, 0.60e-3, None)]


def eel19():
    e = EEL19
    lim = [v / RCS for v in VCS_N]
    r = [f"EEL19 PC40 (Ae {e['Ae']*1e6:.1f} mm2), turns {NP} / {NS} / {NS} / {NC}: HAND CALCULATION, to confirm by a winding design run"]
    r.append(f"  peak flux {LP*IPP_FULL/(NP*e['Ae'])*1e3:.0f} mT at the design load, " + " / ".join(f"{LP*i/(NP*e['Ae'])*1e3:.0f}" for i in lim)
             + " mT at the current limit (min / typ / max); PC40 saturates at about 390 mT at 100 C")
    r.append(f"  gap for {LP*1e6:.0f} uH: {4e-7*math.pi*NP**2*e['Ae']/LP*1e3:.2f} mm in total")
    build = 0.39e-3 * 2 + 0.66e-3 + 0.60e-3 + 4 * 0.05e-3
    r.append(f"  window {e['win_w']*1e3:.1f} x {e['win_h']*1e3:.2f} mm: P1 {NP//2} T (0.35 mm, {NP//2*0.39:.1f} mm wide) | CTRL {NC} T x 3 TIW 25 AWG "
             f"({NC*3*0.66:.1f} mm) beside Out1 {NS} T 0.5 mm ({NS*0.55:.1f} mm) | P2 {NP-NP//2} T | Out2 {NS} T TIW 0.4 mm ({NS*0.6:.1f} mm); "
             f"build {build*1e3:.2f} mm = {build/e['win_h']*100:.0f} % of the window height")
    d2 = LP * IPP_FULL / VOR * FSW                     # demagnetisation duty
    k = math.sqrt(4 / (3 * d2))                        # secondary rms / average
    irms_p = IPP_FULL * math.sqrt(LP * IPP_FULL / VIN_MIN * FSW / 3)
    rho = 0.0172e-6 * 1.3                              # copper at about 100 C
    def loss(n, strands, dcu, mlt, irms): return irms ** 2 * rho * n * mlt / (strands * math.pi * dcu ** 2 / 4)
    out = {o[0]: o[2] for o in OUTPUTS}
    pw = (loss(NP // 2, 1, 0.35e-3, e["mlt"][0], irms_p) + loss(NP - NP // 2, 1, 0.35e-3, e["mlt"][2], irms_p)
          + loss(NS, 1, 0.5e-3, e["mlt"][1], out["Out1"] * k) + loss(NC, 3, 0.455e-3, e["mlt"][1], out["CTRL"] * k)
          + loss(NS, 1, 0.40e-3, e["mlt"][3], out["Out2"] * k))
    bac = LP * IPP_FULL / (NP * e["Ae"]) / 2
    pc = 410e3 * (bac / 0.2) ** 2.5 * e["Ve"]          # PC40: about 410 kW/m3 at 100 kHz, 200 mT, 100 C
    for name, f in (("DC resistance only", 1.0), ("with a factor 3 for skin, proximity and gap fringing", 3.0)):
        p = pw * f + pc
        r.append(f"  losses at 100 V input, {name}: windings {pw*f:.2f} W + core {pc:.2f} W = {p:.2f} W -> rise about "
                 f"{(p*1e3/(e['surface']*1e4))**0.833:.0f} K (surface {e['surface']*1e4:.1f} cm2)")
    return r


def control():
    """VERR divider, VCC supply and start-up of the ICE5AR0680BZS (datasheet 3.1, 3.6)."""
    r = []
    rt, rb = 365e3, 49.9e3
    vo = [v * (1 + rt / rb) for v in (1.76, VERR_REF, 1.84)]
    rpar = rt * rb / (rt + rb)
    r.append(f"VERR divider R101 365k / R102 49.9k from 15V: {vo[1]:.2f} V ({vo[0]:.2f} .. {vo[2]:.2f} V from the reference, plus 1 % "
             f"resistors); {15/(rt+rb)*1e6:.0f} uA")
    r.append(f"  non-isolated mode needs VERR > {VERR_SEL_MAX} V from the {IERR_BIAS_MIN*1e6:.1f} uA bias before the start: "
             f"R101 || R102 = {rpar/1e3:.1f} k -> {IERR_BIAS_MIN*rpar:.2f} V (minimum {VERR_SEL_MAX/IERR_BIAS_MIN/1e3:.1f} k)")
    c_vcc = 47e-6 * 0.8 + 0.5e-6        # C113 47 uF electrolytic (-20 %) + C114 1 uF X5R at 15 V
    t_start = 1.1 * c_vcc / IVCC_CH1 + (VCC_ON - 1.1) * c_vcc / IVCC_CH3
    t_hold = c_vcc * (VCC_ON - 10.4) / IVCC_RUN
    c_out = (220e-6, 690e-6, 940e-6)    # 15V (C28; C115 dropped in v5 step 8), 15V_ISO, CTRL_RAW capacitance on the board
    e_out = 0.5 * (c_out[0] * 15 ** 2 + c_out[1] * 15 ** 2 + c_out[2] * 9 ** 2)
    p_lim = 0.5 * LP * (VCS_N[0] / RCS) ** 2 * FSW_MIN * ETA_XFMR
    t_rise = T_SS + e_out / (p_lim / 2)          # soft start, then about half the limit power into the capacitors
    r.append(f"VCC from 15V via R100 10R + D11: ~{15.0-0.7:.1f} V in operation (off below {VCC_OFF} V, over-voltage at {VCC_OVP} V)")
    r.append(f"start: the cascode charges C113 + C114 ({c_vcc*1e6:.0f} uF effective) to {VCC_ON:.0f} V in ~{t_start:.2f} s typ; hold-up "
             f"16 -> 10.4 V at {IVCC_RUN*1e3:.1f} mA: {t_hold*1e3:.0f} ms, against ~{t_rise*1e3:.0f} ms until 15V carries VCC "
             f"(soft start {T_SS*1e3:.0f} ms + {e_out:.2f} J in the output capacitors)")
    r.append(f"start-up chain R136-R138 3 x 10M from AUX_VIN to GATE: {VIN_MAX/30e6*1e6:.0f} uA and {VIN_MAX/3:.0f} V per resistor at "
             f"{VIN_MAX:.0f} V ({VIN_MAX**2/30e6*1e3:.0f} mW)")
    r.append("FB: R140 4.7k + C145 10n, C146 2.2n, RSel R139 750k (burst option 2): start values from the tube PSU design "
             "(~/dev/tube_psu_kicad kicad_next/CHANGES_5_2.md 1.5); loop to be confirmed by a load step on the first board")
    return r


if __name__ == "__main__":
    print(summary())
