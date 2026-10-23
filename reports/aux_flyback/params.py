"""Design parameters of the 20 W, 2 x 15 V aux flyback (INN3694C, EE25). See README.md."""

# converter (InnoSwitch3-EP INN3694C, 900 V MOSFET; datasheet Rev. W 06/24)
VIN_MIN, VIN_NOM, VIN_MAX = 100.0, 400.0, 500.0   # V DC
VOUT, IOUT = 15.0, 20.0 / 2 / 15.0                  # 2 x 15 V, 10 W each; Out1 regulated (FB), Out2 cross-regulated
VBIAS, IBIAS = 12.0, 0.010                          # BPP bias winding (primary side)
FSW = 70e3                                          # datasheet full-load target for INN369x
ETA = 0.88
ILIM_TYP, ILIM_MAX = 0.750, 0.806                   # standard ILIM (BPP = 0.47 uF)
VDS_TARGET = 725                                    # datasheet peak-drain limit for normal operation (900 V part)

# transformer: TDK B66317G0250X187 (E25/13/7 N87, 0.25 mm centre-leg gap, AL ~250 nH)
CORE_SHAPE, CORE_MATERIAL = "E 25/13/7", "N87"
CATALOGUE_GAP = 0.25e-3
AL_DATASHEET = 250e-9
NP, NS, NB = 69, 10, 9                              # primary split 35 + 34 around the secondaries
LP = AL_DATASHEET * NP ** 2                         # 1.19 mH from the datasheet AL
BOBBIN = "Bobbin EE 25 horizontal longer-creepage 10-pin 5.08mm (Norwe 10165-106)"
W_PRI = "Round 0.28 - Grade 2"
W_SEC = "Round 0.56 - Grade 2"
W_BIAS = "Round 0.25 - Grade 2"

# insulation: enamelled wire + margin tape (no TIW), reinforced per IEC 62368-1, 500 V, PD2, CTI IIIa
MARGIN = 2.0e-3                                     # each side of every primary/secondary layer -> 4 mm creepage (needs 3.9)
TAPE = 75e-6                                        # 3 x 25 um polyester at each pri/sec barrier, modelled as one layer
