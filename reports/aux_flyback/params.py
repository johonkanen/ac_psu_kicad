"""Design parameters of the v5 aux flyback (20 W, EE25, CTRL on TIW flying leads): UCC28710 (PSR) + IPD95R450P7, 100-450 V DC in,
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
VDD_ON, VDD_OFF = 21.0, 8.1      # UVLO on/off typ (19..23 / 7.7..8.5 V); VDD runs from the 15 V Out1 rail
IRUN_MAX = 2.65e-3      # run supply current max
IHV_MIN = 100e-6        # HV start-up current min at VHV = 100 V (typ 250 uA; TI: "typically 300 uA available")
IDRS = 0.020            # DRV source current min (25 typ) at VDRV 8 V
QG = 35e-9              # IPD95R450P7 total gate charge at 10 V
VVSR = 4.05             # VS regulation level

# ---- turn set (Np, Ns, Nctrl, Nbias); TURNSET env var for the comparison run ---------------------
import os as _os
TURNSETS = {"A": (32, 5, 3, 0), "B": (38, 6, 4, 0)}   # (Np, Ns, Nctrl, Nbias): no bias winding since 2026-10-31
TURNSET = TURNSETS[_os.environ.get("TURNSET", "A")]   # A chosen: lower leakage (clamp), 9 V CTRL; B: 216 mT, more leakage
CTRL_V = TURNSET[2] * TURNSET[0] / TURNSET[1] * 15.7 / TURNSET[0] - 0.45   # CTRL winding minus Schottky drop
CTRL_I = 9.0 / CTRL_V                                                       # 9 W into the buck

# ---- outputs (design load 20 W total, user decision 2026-10-31; was 25 W in 3b4a33d) -------------
#          name    V     I     diode VF  isolation side (MKF)
OUTPUTS = [("Out1", 15.0, 0.39, 0.70, "primary"),     # 15V on GND (primary group): 5.5 W + VDD ~20 mA; PSR sense winding
           ("Out2", 15.0, 0.33, 0.70, "secondary"),   # 15V_ISO on ISOGND, 5 W
           ("CTRL",  CTRL_V, CTRL_I, 0.45, "tertiary")]  # control card: winding into a 5 V buck, 9 W
# No separate bias winding (user, 2026-10-31): Out1 is the PSR sense winding (VS divider from the
# Out1 winding node before its rectifier) and supplies VDD through a diode + resistor (VDD ~14.3 V).
ETA = 0.86              # converter efficiency estimate at 100 V full load (for the input power)
ETA_XFMR = 0.90         # TI's transformer efficiency term (leakage, losses, bias)

# ---- transformer ------------------------------------------------------------------------------
NP, NS, NC, NB = TURNSET      # primary, 15 V windings, CTRL, (bias: none, NB = 0)
VOR = NP / NS * (15.0 + 0.70)  # reflected voltage (~100 V: set by DCM at 100 V input)
P_CC = 25.5             # output power at the CC limit (typ fSW(max), typ VCST(max)); the worst case
                        # (fSW(max) 92 kHz, VCST(max) 738 mV) is 0.824 x = 21.0 W, above the 20 W design load
LP_IPP = DMAGCC * VOR / FMAX                    # V*s at the CC point (demag duty 0.425 at fmax)
IPP = P_CC / (0.5 * LP_IPP * FMAX * ETA_XFMR)  # primary peak current at VCST(max)
LP = LP_IPP / IPP                               # primary inductance
RCS = VCST_MAX / IPP                            # current-sense resistor
# user decision 2026-10-31: RCS 0.562 ohm (E96) instead of 0.590 for more CC-limit margin over the
# 20 W load; Lp stays as designed above, the peak current and CC power rise by 5 %
RCS = 0.562
IPP = VCST_MAX / RCS
LP_IPP = LP * IPP
P_CC = 0.5 * LP * IPP ** 2 * FMAX * ETA_XFMR

# ---- MOSFET / clamp --------------------------------------------------------------------------
VDS_RATING = 950.0      # IPD95R450P7
V_CLAMP = 240.0         # TVS clamp voltage at ~1.6 A (P6SMB200A / SMBJ170A class: Vbr 190-210 V, Vc 274 V at 2.2 A)
LK_EFF = 5.9e-6         # effective primary leakage at full load: MKF pairwise P->Out1/Out2/CTRL (6.1/11.2/2.9 uH,
                        # winding order O2) weighted by each output's power share (conservative; measure on the sample)
VDS_PK = VIN_MAX + V_CLAMP

# ---- thermal ----------------------------------------------------------------------------------
T_AMB = 60.0            # assumed internal air of the passively cooled chassis (not measured)

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
    rows.append(f"CC limit: {P_CC:.1f} W at 100 kHz, {p_cc_min:.1f} W at fSW(max) min 92 kHz, "
                f"{p_cc_min*(0.738/VCST_MAX)**2:.1f} W with VCST(max) 738 mV too (worst case)")
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
    rows.append(f"RCS {RCS:.3f} ohm 1 % (E96): {IPP**2*0.335/3*RCS:.2f} W at 100 V")
    for name, v, i, vf, _ in OUTPUTS:
        n = {"Out1": NS, "Out2": NS, "CTRL": NC}[name]
        vrev = VIN_MAX * n / NP + v
        rows.append(f"  {name}: N {n}, winding {n*VOR/NP:.2f} V -> out {n*VOR/NP - vf:.2f} V; diode reverse {vrev:.0f} V")
    rows += out1_sense_vdd(f_full)
    return "\n".join(rows)


def out1_sense_vdd(f_full):
    """Out1 as the PSR sense and VDD winding (TI SLUSB86C eq. 24-26, 28)."""
    r = []
    npa = NP / NS                       # primary to 'auxiliary' (= Out1) turns ratio
    vin_run = 85.0                      # DC input at which DRV is enabled
    rs1 = vin_run / (npa * 225e-6)      # IVSL(run) typ 225 uA (DC input: no sqrt(2))
    rs2 = rs1 * VVSR / (1.0 * (15.0 + 0.45) - VVSR)   # NAS = 1; VF ~0.45 V near zero current (ultrafast); use 21.0 k E96
    r.append(f"VS divider from the Out1 winding: RS1 {rs1/1e3:.1f} k (run at {vin_run:.0f} V DC, stop at "
             f"{rs1*npa*80e-6:.0f} V), RS2 {rs2/1e3:.2f} k")
    vocbc = 0.25                        # cable compensation at the output at full load (diode VF + winding IR)
    rcbc = 3.2 * 3e3 * (15.0 + 0.45) / (VVSR * vocbc) - 28e3
    r.append(f"cable compensation {vocbc:.2f} V at full load: RCBC {rcbc/1e3:.0f} k")
    vdd = 15.0 - 0.7
    idd = IRUN_MAX + QG * FMAX          # run current + gate charge at fSW(max)
    vocc = 10.0                         # Out1 level at which VDD (diode from Out1) holds >= VDD_OFF + margin
    c_out1 = 600e-6                     # Out1 capacitance incl. gate-driver boards and U9 (estimate)
    p_cc_worst = 0.5 * LP * IPP ** 2 * FMAX_MIN * ETA_XFMR * (0.738 / VCST_MAX) ** 2
    t_occ = 0.020                       # design start-up time to Out1 = 10 V (estimate x2.5 margin, see README)
    cdd = idd * t_occ / (19.0 - 8.5 - 1.0)   # worst-case UVLO window 19 V on / 8.5 V off, 1 V margin
    t_start_typ = 15e-6 * VDD_ON / 250e-6
    t_start_max = 15e-6 * 23.0 / (IHV_MIN - 30e-6)
    r.append(f"VDD from Out1 via diode + 47 ohm: ~{vdd:.1f} V; run current {idd*1e3:.1f} mA (IRUN max + Qg x 100 kHz)")
    r.append(f"CDD >= {cdd*1e6:.1f} uF for {t_occ*1e3:.0f} ms to Out1 {vocc:.0f} V (worst UVLO window 9.5 V) -> 15 uF; "
             f"start delay with 15 uF: {t_start_typ:.1f} s typ, {t_start_max:.1f} s worst (IHV 100 uA at 100 V)")
    r.append(f"gate drive: VDD {vdd:.1f} V, DRV ~{vdd-1:.0f} V (clamp 14-16 V only at high VDD); Qg {QG*1e9:.0f} nC at "
             f"{IDRS*1e3:.0f} mA min source -> {QG/IDRS*1e6:.1f} us to full charge")
    return r


if __name__ == "__main__":
    print(summary())
