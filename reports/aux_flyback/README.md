# Aux flyback (v5): UCC28710 PSR, 25 W, Out1 / Out2 / CTRL, E30/15/7

Replacement for the sheet-7 auxiliary supply (today IW1830 + EF20 TR2), redesigned 2026-10-31 for
V5_PLAN.md sections 5–5.2 and CTRL_ISOLATION_PLAN.md. Computed with PyOpenMagnetics (OpenMagnetics MKF)
1.7.35. Not yet in the schematic.

Previous design (commit 965a78b, superseded): INN3694C, EE25, 2 × 15 V / 20 W, margin-tape construction.
The design changed for four reasons:
- the controller is now a UCC28710 with an external MOSFET
- full power is needed at 100 V
- the control card gets its own reinforced CTRL output
- the cooling is passive

## Requirements

- **Input:** DC+ 100–450 V, full power at 100 V continuous.
- **Outputs:** design load 25 W, which is the user's 15–20 W estimate plus margin.

  | Output | Domain | Voltage | Current | Power |
  |---|---|---|---|---|
  | Out1 `15V` | GND, primary group | 15 V | 0.5 A | 7.5 W |
  | Out2 `15V_ISO` | ISOGND | 15 V | 0.4 A | 6 W |
  | CTRL | control card | ≈ 9 V into a 5 V buck | 1.2 A | 10.8 W |
  | Bias | UCC28710 VDD | 24.4 V | 20 mA | 0.5 W |

- **Isolation:** three groups, reinforced from each other: {primary, bias, Out1}, Out2, CTRL. Working
  voltage taken as 500 V. Pollution degree 2, OVC II, CTI IIIa, ≤ 2000 m.
- **Cooling:** passive, closed chassis, **60 °C internal air assumed** (not measured).

## Controller: UCC28710 (TI SLUSB86C)

Primary-side regulation from the bias winding, DCM with valley switching.
- **fSW(max):** 100 kHz (92–106).
- **CC limit:** reached at a demagnetisation duty of 0.425.
- **CS thresholds:** VCST 780 mV (max) / 195 mV (min).
- **VDD:** 9–35 V, UVLO 21 / 8.1 V, 25 V nominal recommended.
- **Timing:** LEB 235–280 ns; the TI design targets are tON(min) ≥ 300 ns and tDMAG(min) ≥ 1.2 µs.

Design (`params.py`, `python params.py` prints it):

| Item | Value |
|---|---|
| VOR | 100.5 V (Np/Ns = 32/5). Limited by 100 V input: DCM at the CC point needs ton + tdemag + ½ ring ≤ T |
| Lp | **265 µH** (AL ≈ 259 nH at 32 turns) |
| Ipp(max) | 1.61 A at VCST(max); RCS = 0.484 Ω → **0.47 Ω 1 %** (0.14 W) |
| CC limit | 31 W at 100 kHz, **28.5 W at the minimum fSW(max) of 92 kHz**: above the 25 W design load |
| Full load | 24.8 W at **80 kHz** (FM region, peak current fixed) |
| 100 V full load | ton 4.27 µs + tdemag 4.25 µs + 1 µs ring = 0.76 of the period (0.95 at the CC point) |
| Primary RMS | 0.54 A at 100 V, 0.31 A at 300 V, 0.26 A at 450 V |
| Light load, 450 V | tON is LEB-limited at 280 ns → **tDMAG(min) 1.25 µs**. Just above TI's 1.2 µs: check VS sampling on the sample at 450 V, no load |
| Drain peak | 450 V + 240 V clamp = **690 V** (73 % of the IPD95R450P7's 950 V) |

## Transformer (chosen: E30/15/7, N87)

| Item | Value |
|---|---|
| Core | E30/15/7 N87, centre-leg gap ≈ 0.265 mm for AL ≈ 259 nH. TDK B66319G0250X187 (0.25 mm; check the AL in the datasheet; B66319G0500X187 is 145 nH) + B66319G0000X187, or Ferroxcube E30/15/7-3C95 gapped to the same AL |
| Bobbin | 12-pin horizontal (6 + 6): Ferroxcube CSH-E30/15/7-1S-12P(-C) or the TDK/EPCOS horizontal E30/15/7 coil former (about 35.4 × 31.4 × 22.6 mm). Confirm pin pitch and row spacing from the drawing before the footprint |
| Turns | Primary 32 (16 + 16 in series), Out1 5, Out2 5, CTRL 3, Bias 8 |
| Peak flux | 231 mT at Ipp(max) and VCST 810 mV (N87 Bsat ≈ 390 mT at 100 °C) |
| Losses (MKF) | 100 V: core 0.31 W + copper 0.34 W = **0.65 W**; 300 V: 0.71 W; 450 V: **0.74 W** |
| Temperature | ≈ 25 K/W free convection (rule of thumb) → **≈ 80 °C** at 60 °C air |
| Leakage (MKF, pairwise from the primary) | Out1 12.8 µH, Out2 5.8 µH, CTRL 3.0 µH, Bias 21.6 µH. Bias ↔ Out1 0.52 µH, which is the tight coupling the PSR regulation relies on |

Winding order, inside to outside (`winding.svg`):

| # | Winding | Wire | Turns |
|---|---|---|---|
| 1 | P1 | 0.40 mm Grade 2 | 16 |
| 2 | CTRL | 3 × TIW 25 AWG (Rubadue TCA3) in parallel | 3 |
| 3 | Out2 | TIW 24 AWG (TCA3) | 5 |
| 4 | P2 | 0.40 mm Grade 2 | 16 |
| 5 | Out1 | 0.50 mm Grade 2 | 5 |
| 6 | Bias | 0.20 mm Grade 2 | 8 |

1 × 25 µm tape between layers, plus an outer wrap.

**Construction: TIW on Out2 and CTRL; no margin tape.** Out2 and CTRL each need reinforced insulation to the primary group and to each other. Margin tape would need two separate reinforced barriers in a 17 mm window, which doesn't fit. TIW is solid insulation on the wire itself: TCA3 is three coats, 6 kV. Requirements:
- **Certified wire:** the TIW must be certified for reinforced insulation (IEC 62368-1 Annex J / IEC 61558-1). Buy a certified type such as Rubadue TCA3 or Furukawa TEX-E, with its certificate.
- **Lead dress:** the TIW leads go straight to their pins, never through primary-side pins.
- **No sleeving needed** on TIW. Enamelled leads (primary, Out1, bias) that cross the TIW layers stay on the primary row.

Insulation figures (MKF `calculate_insulation`, 500 V working):

| Standard | Basic | Reinforced |
|---|---|---|
| IEC 62368-1 | creepage 1.6 mm, clearance 3.0 mm | **creepage 3.1 mm, clearance 5.5 mm**, DTI 0.4 mm, 5 kV withstand |
| IEC 60664-1 | creepage 8.0 mm | **creepage 16 mm**, 2.7 kV |
| IEC 61558-1 | creepage 1.6 mm | creepage 2.8 mm |

IEC 62477-1 is not in MKF. It refers to IEC 60664-1, so take the 60664-1 column as its creepage. MKF's IEC 60664-1 numbers apply to the bobbin and pins (non-PCB insulating material). On the PCB, the board plan keeps **≥ 10 mm** between groups, with slots (CTRL_ISOLATION_PLAN.md).

Pin assignment proposal (12 pins, 6 per row):
- **Primary row:** 1 DC+ (P1 start), 2 drain (P2 end), 3 empty, 4 Bias, 5 GND (bias and Out1 return), 6 Out1.
- **Secondary row:** 7 Out2+, 8 ISOGND, 9 and 10 removed, 11 CTRL+, 12 CTRL return. Pins 8 and 11 are 15.24 mm apart centre to centre, about 13.5 mm edge to edge.
- **Board:** a slot under the bobbin between the rows, and a slot between pins 8 and 11.

## Candidates (MKF, same turns, wires and order)

| Core / bobbin | Ae | Bpk | Loss 100 V / 450 V | ≈ T at 60 °C | Pins | Footprint |
|---|---|---|---|---|---|---|
| E25/13/7, Norwe 10165-106 (5 + 5) | 52 mm² | 267 mT | 0.76 / 0.91 W | ≈ 87 °C | 10: Out2 and CTRL can't both sit on a 5-pin row ≥ 10 mm apart → CTRL on TIW flying leads | ≈ 28 × 26 mm |
| **E30/15/7, Ferroxcube CSH-E30/15/7-1S-12P** | 60 mm² | 231 mT | **0.65 / 0.74 W** | **≈ 80 °C** | 12 (6 + 6): all on pins | ≈ 35 × 31 mm |
| E32/16/9, Norwe 10750-024 (6 + 6) | 83 mm² | 167 mT | 0.65 / 0.75 W | ≈ 75 °C | 12 | ≈ 36 × 34 mm |

E30/15/7 is the smallest core that puts all three groups on pins with reinforced spacing. EE32 is no cooler in total loss; its copper is longer. EF25 and EFD30 are not in the MKF bobbin database: EF25 has 10-pin bobbins, and the EFD30 bobbins (4 + 4, 2.5 mm pitch) have too few pins and too little creepage. JLC/LCSC stocks none of these cores, bobbins or TIW (only CSH-E30/15/7-1S-12P-C is listed, with 0 stock). The transformer is hand-wound and hand-fitted, like TR2 today.

**Board area:** today's EF20 is a 22 × 14 mm body, 2 × 5 pins at 3.81 mm, rows 10.16 mm apart. The E30 bobbin is about 35 × 31 mm, roughly 3.5 × the area, plus the slots.

## Around the transformer (100 V full load)

| Part | Stress | Choice (class) |
|---|---|---|
| MOSFET | 690 V peak, 0.54 A rms | IPD95R450P7 (DPAK, V5_PLAN 5.1) |
| Clamp | ≈ 1.2 W at the full-load 80 kHz (6.7 µH effective leakage, conservative) | TVS P6SMB200A / SMBJ170A class (≈ 240 V at 1.6 A) + 1000 V fast diode (US1M / RS1M). Give the TVS copper. Measure the leakage on the sample; a lower value cuts the loss |
| RCS | 1.61 A peak | 0.47 Ω 1 %, 0.25–0.5 W (1206 / 2010) |
| Out1 diode | 85 V reverse, 3.2 A peak, 0.5 A avg | 200 V ultrafast 2 A (ES2D / STTH202 class) |
| Out2 diode | 85 V, 2.6 A peak, 0.4 A avg | same |
| CTRL diode | 51 V reverse, 7.6 A peak, 1.2 A avg | 100 V Schottky 3–5 A (SS510 / V8PAM10 class), ≈ 0.5 W: copper |
| Bias diode | 137 V | 300–400 V ultrafast 1 A (ES1G / US1G) |
| Output capacitor RMS | Out1 0.91 A, Out2 0.73 A, CTRL 2.19 A | low-ESR polymer or MLCC + electrolytic; 105 °C, long life (passive chassis) |
| VS divider | bias winding 25.1 V during demag → VS 4.05 V | RS1/RS2 per TI equation 1 (line compensation via RS1) |

**Cross-regulation:** PSR regulates the bias winding (24.4 V) and sets Out1 = 15.0 V through the tight bias ↔ Out1 coupling.
- **Out2:** leakage to the bias ≈ 0.57 µH (referred to Out2) gives ≈ 0.34 V droop at full load, so expect 14.5–15.3 V. It rises toward 16–17 V when Out2 is light and the others are heavy. Preload ≈ 3 mA (5.1 kΩ).
- **CTRL:** ≈ 0.24 µH gives ≈ 0.4 V droop, so 8.4–9.3 V with load and up to ≈ 11–12 V at no load. Use a buck rated ≥ 17 V input, and a preload ≈ 10 mA (≈ 1 kΩ).
- **Out1:** ≈ 0.15 V.

## Open items

1. **Enclosure temperature:** measure the real internal air temperature (60 °C assumed). The transformer at ≈ 80 °C leaves margin up to about 75 °C air.
2. **Sample measurements:** Lp (target 265 µH; set the gap), the leakage from the primary with all secondaries shorted (→ clamp loss), and the VS waveform at 450 V no load (tDMAG ≥ 1.2 µs, ringing ≤ 100 mVpp in the last 200 ns).
3. **TIW:** buy a certified reinforced type (Rubadue TCA3 24/25 AWG, Furukawa TEX-E 0.4–0.5 mm); not stocked at JLC/LCSC.
4. **Core and bobbin part numbers:** confirm the TDK B66319G0250X187 AL value and the 12-pin E30/15/7 bobbin drawing (pin pitch, row spacing) before drawing the footprint.
5. **Working voltage:** 500 V is assumed between all three groups. If the ISO side can reach more relative to the primary (450 V DC link plus AC output), recompute.
6. **CC limit tolerance:** with both fSW(max) (92 kHz) and VCST(max) (738 mV) at their datasheet minimum, the CC limit is ≈ 25.5 W. That just covers the 25 W design load, which itself has margin over the 15–20 W estimate. If the real load approaches 25 W, lower RCS by about 5 % (0.45 Ω) and re-check the flux (≈ 245 mT).

## Files

| File | |
|---|---|
| `params.py` | all design parameters and the analytical design summary (`python params.py`) |
| `inputs.py` | MKF converter model → `inputs.json` (operating points at 100 / 300 / 450 V) |
| `transformer.py` | winds and evaluates the candidates → `report.txt`; `magnetic.json` and `winding.svg` for the chosen E30 |
| `report.txt` | output of the last `transformer.py` run |

Run:

```
python3 -m venv venv && venv/bin/pip install PyOpenMagnetics==1.7.35
cd reports/aux_flyback && ../../venv/bin/python inputs.py && ../../venv/bin/python transformer.py
```

MKF quirks worked around in the scripts:
- `calculate_gapping_from_number_turns_and_inductance` fails ("bad optional access"), so the gap is bisected on MKF's inductance model.
- `wind()` margin pairs apply per pattern section, and only with `coilEqualizeMargins` off. Not used here: TIW needs no margins.
- The thermal estimate is a rule of thumb (R ≈ 53 · Ve^-0.54 K/W). MKF 1.7.35 has no temperature model in the Python API.
