"""Design parameters of the v5 aux flyback: UCC28710 (PSR) + IPD95R450P7, 100-450 V DC in,
Out1 15 V (GND), Out2 15 V (ISOGND), CTRL ~9 V (control card, buck to 5 V), bias for VDD.
Three reinforced-separated groups: {primary, bias, Out1}, Out2, CTRL. See README.md and
V5_PLAN.md 5.3. All values SI."""
import math

# ---- input / controller (UCC28710, TI SLUSB86C) ------------------------------------------------
VIN_MIN, VIN_MID, VIN_MAX = 100.0, 300.0, 450.0   # V DC, full power at VIN_MIN continuous
FMAX = 100e3            # fSW(max) typ (92..106 kHz); full-load point sits below it (FM region at VCST(max))
FMAX_MIN = 92e3         # datasheet minimum of fSW(max): CC power is checked with this
VCST_MAX, VCST_MIN = 0.780, 0.195   # CS thresholds (typ); VCST(max) 0.738..0.810
DMAGCC = 0.425          # demag duty at the CC limit (internal)
T_RES_HALF = 1.0e-6     # end of demag -> first valley (TI default estimate 500 kHz ring)
TLEB = 0.280e-6         # leading-edge blanking max = practical minimum on time
VDD_NOM = 25.0          # TI recommendation; run 9..35 V, UVLO 21/8.1 V
VVSR = 4.05             # VS regulation level

# ---- outputs (design load = user's 15-20 W estimate + margin, 25 W total) -----------------------
#          name    V     I     diode VF  isolation side (MKF)
OUTPUTS = [("Out1", 15.0, 0.50, 0.70, "primary"),     # 15V on GND (primary group), ultrafast diode
           ("Out2", 15.0, 0.40, 0.70, "secondary"),   # 15V_ISO on ISOGND
           ("CTRL",  9.0, 1.20, 0.45, "tertiary"),    # control card: ~9 V into a 5 V buck (8 W card + buck loss + margin)
           ("Bias", 24.4, 0.020, 0.70, "primary")]    # UCC28710 VDD
ETA = 0.86              # converter efficiency estimate at 100 V full load (for the input power)
ETA_XFMR = 0.90         # TI's transformer efficiency term (leakage, losses, bias)

# ---- transformer ------------------------------------------------------------------------------
NP, NS, NC, NB = 32, 5, 3, 8   # primary, 15 V windings, CTRL, bias
VOR = NP / NS * (15.0 + 0.70)  # reflected voltage = 100.5 V
P_CC = 31.0             # output power at the CC limit (typ fSW(max)); full load 25 W stays below
LP_IPP = DMAGCC * VOR / FMAX                    # V*s at the CC point (demag duty 0.425 at fmax)
IPP = P_CC / (0.5 * LP_IPP * FMAX * ETA_XFMR)  # primary peak current at VCST(max)
LP = LP_IPP / IPP                               # primary inductance
RCS = VCST_MAX / IPP                            # current-sense resistor

# ---- MOSFET / clamp --------------------------------------------------------------------------
VDS_RATING = 950.0      # IPD95R450P7
V_CLAMP = 240.0         # TVS clamp voltage at ~1.6 A (P6SMB200A / SMBJ170A class: Vbr 190-210 V, Vc 274 V at 2.2 A)
LK_EFF = 6.7e-6         # effective primary leakage at full load: MKF pairwise P->Out1/Out2/CTRL (12.8/5.8/3.0 uH)
                        # weighted by each output's share of the ampere-turns (conservative; measure on the sample)
VDS_PK = VIN_MAX + V_CLAMP

# ---- thermal ----------------------------------------------------------------------------------
T_AMB = 60.0            # assumed internal air of the passively cooled chassis (not measured)

# ---- MKF modelling ----------------------------------------------------------------------------
MATERIAL = "N87"
TAPE = 25e-6            # one layer of polyester tape between sections (mechanical; TIW carries the insulation)

CANDIDATES = {
    # name: (core shape, bobbin, catalogue gap or None, primary wire, Out1 wire, Out2 TIW, CTRL TIW (n parallel), bias wire)
    "EE25": ("E 25/13/7", "Bobbin EE 25 horizontal longer-creepage 10-pin 5.08mm (Norwe 10165-106)"),
    "E30":  ("E 30/15/7", "Bobbin E 30/15/7 (Ferroxcube CP-E30/15/7-1S)"),
    "EE32": ("E 32/16/9", "Bobbin EE 32 horizontal 12-pin 5.08mm (Norwe 10750-024)"),
}
WIRES = {"Primary": ("Round 0.4 - Grade 2", 1),
         "Out1": ("Round 0.5 - Grade 2", 1),
         "Out2": ("Round TCA3 24 AWG", 1),
         "CTRL": ("Round TCA3 25 AWG", 3),
         "Bias": ("Round 0.2 - Grade 2", 1)}
TURNS = {"Primary": NP, "Out1": NS, "Out2": NS, "CTRL": NC, "Bias": NB}


def summary():
    rows = [f"VOR {VOR:.1f} V, Lp*Ipp {LP_IPP*1e6:.0f} uVs, Ipp(max) {IPP:.3f} A, Lp {LP*1e6:.0f} uH, RCS {RCS:.3f} ohm"]
    pout = sum(v * i for _, v, i, _, _ in OUTPUTS)
    f_full = pout / (0.5 * LP * IPP ** 2 * ETA_XFMR)
    rows.append(f"design load {pout:.1f} W -> full-load fsw {f_full/1e3:.1f} kHz at Ipp(max) (FM region)")
    for vin in (VIN_MIN, VIN_MID, VIN_MAX):
        ton = LP * IPP / vin
        tdm = LP * IPP / VOR
        d = ton * f_full
        rows.append(f"  Vin {vin:3.0f} V: ton {ton*1e6:.2f} us, tdemag {tdm*1e6:.2f} us, D {d:.3f}, demag duty {tdm*f_full:.3f}, "
                    f"period use {(ton+tdm+T_RES_HALF)*f_full:.2f}, Ipri rms {IPP*math.sqrt(d/3):.3f} A")
    # CC limit with the minimum fSW(max)
    p_cc_min = 0.5 * LP * IPP ** 2 * FMAX_MIN * ETA_XFMR
    rows.append(f"CC limit: {P_CC:.1f} W at 100 kHz, {p_cc_min:.1f} W at fSW(max) min 92 kHz")
    # DCM check at the CC point, 100 V
    ton_cc = LP_IPP / VIN_MIN
    rows.append(f"DCM at the CC point, 100 V: ton {ton_cc*1e6:.2f} + tdemag {LP_IPP/VOR*1e6:.2f} + {T_RES_HALF*1e6:.1f} us "
                f"= {(ton_cc+LP_IPP/VOR+T_RES_HALF)*FMAX:.2f} of the 10 us period")
    # light load / high line
    ton_min = LP * IPP * (VCST_MIN / VCST_MAX) / VIN_MAX
    rows.append(f"min on time at 450 V, VCST(min): {ton_min*1e9:.0f} ns (LEB max {TLEB*1e9:.0f} ns -> effective "
                f"{max(ton_min, TLEB)*1e9:.0f} ns); tDMAG(min) {max(ton_min, TLEB)*VIN_MAX/VOR*1e6:.2f} us (TI target >= 1.2 us)")
    rows.append(f"drain peak at 450 V: {VIN_MAX:.0f} + clamp {V_CLAMP:.0f} = {VDS_PK:.0f} V ({VDS_PK/VDS_RATING*100:.0f} % of {VDS_RATING:.0f} V)")
    p_clamp = 0.5 * LK_EFF * IPP ** 2 * f_full * V_CLAMP / (V_CLAMP - VOR)
    rows.append(f"clamp loss (leakage {LK_EFF*1e6:.1f} uH, Vclamp {V_CLAMP:.0f} V): {p_clamp:.2f} W at full load "
                f"(any Vin; Ipp is fixed by VCST(max) in the FM region)")
    rows.append(f"RCS {RCS:.3f} ohm (use 0.47 ohm 1 %): {IPP**2*0.341/3*RCS:.2f} W at 100 V")
    for name, v, i, vf, _ in OUTPUTS:
        n = {"Out1": NS, "Out2": NS, "CTRL": NC, "Bias": NB}[name]
        vrev = VIN_MAX * n / NP + v
        rows.append(f"  {name}: N {n}, winding {n*VOR/NP:.2f} V -> out {n*VOR/NP - vf:.2f} V; diode reverse {vrev:.0f} V")
    return "\n".join(rows)


if __name__ == "__main__":
    print(summary())
