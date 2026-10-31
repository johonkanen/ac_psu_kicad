# Aux flyback (v5): UCC28710 PSR, 20 W, Out1 / Out2 / CTRL, EE25 with CTRL on TIW flying leads

Replacement for the sheet-7 auxiliary supply (today IW1830 + EF20 TR2), redesigned 2026-10-31 for
V5_PLAN.md sections 5–5.3 and CTRL_ISOLATION_PLAN.md. Computed with PyOpenMagnetics (OpenMagnetics MKF)
1.7.35. Not yet in the schematic.

History:
- **965a78b:** INN3694C, EE25, 2 × 15 V / 20 W, margin tape. Superseded: new controller, full power at
  100 V, the CTRL output, passive cooling.
- **3b4a33d:** UCC28710, 25 W, E30/15/7 on a 12-pin bobbin, all groups on pins. Kept below as the
  alternative.
- **This version:** 20 W on EE25 (user, 2026-10-31). CTRL leaves the bobbin as TIW flying leads,
  because the 10-pin bobbin cannot hold Out2 and CTRL on one 5-pin row ≥ 10 mm apart.

## Requirements

- **Input:** DC+ 100–450 V, full power at 100 V continuous.
- **Outputs:** design load **20 W** (user estimate 15–20 W):

  | Output | Domain | Voltage | Current | Power |
  |---|---|---|---|---|
  | Out1 `15V` | GND, primary group | 15 V | 0.37 A | 5.5 W |
  | Out2 `15V_ISO` | ISOGND | 15 V | 0.33 A | 5 W |
  | CTRL | control card | ≈ 9 V into a 5 V buck | 1.0 A | 9 W (card ≈ 7.5 W + buck loss) |
  | Bias | UCC28710 VDD | 24.4 V | 20 mA | 0.5 W |

- **Isolation:** three groups, reinforced from each other: {primary, bias, Out1}, Out2, CTRL. Working
  voltage taken as 500 V. Pollution degree 2, OVC II, CTI IIIa, ≤ 2000 m.
- **Cooling:** passive, closed chassis, **60 °C internal air assumed** (not measured).

## Controller: UCC28710 (TI SLUSB86C)

Primary-side regulation from the bias winding, DCM with valley switching.
- **fSW(max):** 100 kHz (92–106).
- **CC limit:** reached at a demagnetisation duty of 0.425.
- **CS thresholds:** VCST 780 mV (max; 738–810) / 195 mV (min).
- **VDD:** 9–35 V, UVLO 21 / 8.1 V, 25 V nominal recommended.
- **Timing:** LEB 235–280 ns; the TI design targets are tON(min) ≥ 300 ns and tDMAG(min) ≥ 1.2 µs.

Design (`params.py`; `python params.py` prints it, turn set A):

| Item | Value |
|---|---|
| VOR | 100.5 V (Np/Ns = 32/5). The 100 V input sets it: DCM at the CC point needs ton + tdemag + ½ ring ≤ T |
| Lp | **322 µH** (AL ≈ 314 nH at 32 turns) |
| Ipp(max) | 1.33 A at VCST(max); RCS = 0.588 Ω → **0.590 Ω 1 % (E96)**, 0.12 W |
| CC limit | 25.5 W typ (100 kHz, 780 mV); 23.5 W at fSW(max) 92 kHz; **21.0 W worst case** (92 kHz and 738 mV): above the 20 W design load |
| Full load | 20 W at **78 kHz** (FM region, peak current fixed) |
| 100 V full load | ton 4.27 µs + tdemag 4.25 µs + 1 µs ring = 0.75 of the period (0.95 at the CC point) |
| Primary RMS | 0.44 A at 100 V, 0.26 A at 300 V, 0.21 A at 450 V |
| Light load, 450 V | tON is LEB-limited at 280 ns → **tDMAG(min) 1.25 µs**, just above TI's 1.2 µs: check VS sampling on the sample at 450 V, no load |
| Drain peak | 450 V + 240 V clamp = **690 V** (73 % of the IPD95R450P7's 950 V) |

## Transformer (chosen: E25/13/7 N87, Norwe 10165-106, CTRL on flying leads)

| Item | Value |
|---|---|
| Core | E25/13/7 N87, centre-leg gap ≈ 0.22 mm for **AL ≈ 314 nH**. TDK B66317-series halves (ungapped B66317G0000X187 with a gapped B66317G…X187 half; the old design's B66317G0250X187 is ≈ 250 nH, too low: pick the gap for 314 nH or have the core ground), or Ferroxcube E25/13/7-3C95 gapped to the same AL |
| Bobbin | EE25 horizontal, longer creepage, 10 pins (5 + 5) at 5.08 mm: **Norwe 10165-106** (2-chamber 10166-106). Same family, standard creepage: Norwe 10220-024 / 10175-106. None are stocked at JLC/LCSC; confirm the drawing (row spacing, flange creepage) |
| Turns | Primary 32 (16 + 16 in series), Out1 5, Out2 5, CTRL 3, Bias 8 |
| Peak flux | 267 mT at Ipp(max) and VCST 810 mV (N87 Bsat ≈ 390 mT at 100 °C) |
| Losses (MKF) | 100 V: core 0.35 W + copper 0.25 W = **0.60 W**; 300 V: 0.72 W; 450 V: **0.76 W** |
| Temperature | ≈ 29 K/W free convection (rule of thumb) → **≈ 78–82 °C** at 60 °C air |
| Leakage (MKF, pairwise from the primary) | Out1 13.3 µH, Out2 5.8 µH, CTRL 3.0 µH, Bias 22.6 µH. Bias ↔ Out1 0.21 µH (tight coupling for PSR) |

Turn set B (38/6/4/10, CTRL ≈ 10 V) was also run: peak flux 223 mT and about the same total loss
(0.58–0.75 W), but ≈ 33 % more leakage (Out1 17.7 µH, Out2 7.8 µH), so more clamp loss. A is chosen.

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

**Construction: TIW on Out2 and CTRL, no margin tape.** TIW is solid reinforced insulation on the wire;
it must be a certified type (IEC 62368-1 Annex J / IEC 61558-1), e.g. Rubadue TCA3 or Furukawa TEX-E,
bought with its certificate. Enamelled leads (primary, Out1, bias) stay on the primary row.

### Pins and the CTRL flying leads

Horizontal bobbin: each flange carries one 5-pin row.
- **Primary row (pins 1–5):** 1 drain (P2 end), 2 DC+ (P1 start; the P1–P2 joint is inside the
  winding), 3 Bias, 4 GND (bias and Out1 return), 5 Out1. DC+ sits between the drain and the
  low-voltage pins; these are functional distances inside the primary group (5.08 mm pitch).
- **Secondary row (pins 6–10):** 6 Out2+, 7 ISOGND (Out2 return). Pins 8–10 are cut off.
- **CTRL:** the two CTRL ends (each 3 parallel TIW strands, twisted and tinned only at the very end)
  leave the winding over the secondary flange at the pin-10 end, away from pins 6–7, and run as
  free TIW to **two dedicated PCB holes** in the CTRL island.
  - **Holes:** Ø 1.6 mm (3 × TCA3 25 AWG, ≈ 0.66 mm OD each → ≈ 1.4 mm bundle), pads Ø 3.0 mm,
    5.08 mm apart.
  - **Position:** ≥ 10 mm (the board plan's reinforced spacing) from the Out2 pins 6–7, from the
    primary row and from the core outline, on the CTRL side of the slot. In practice that is about
    10–12 mm beyond the secondary flange, past the pin-10 end.
  - **Lead dress:** TIW is reinforced insulation along its whole length, so the free lead may cross
    above other groups' copper. Only the bare, soldered ends count for creepage. Fix the leads with
    adhesive or a lead clip so they cannot move toward pins 6–7 and the core.
- **The core is floating** and counts as a conductive part between the groups (IEC 62368-1 5.4).
  Inside the winding the TIW covers it. Outside, the path Out2 pin → core → primary pin, and the
  CTRL holes → core, must each meet the reinforced creepage over the bobbin flange and the PCB. Check
  the flange distances on the Norwe drawing (the longer-creepage version exists for this).

### Insulation figures (MKF `calculate_insulation`, 500 V working)

| Standard | Basic | Reinforced |
|---|---|---|
| IEC 62368-1 | creepage 1.6 mm, clearance 3.0 mm | **creepage 3.1 mm, clearance 5.5 mm**, DTI 0.4 mm, 5 kV withstand |
| IEC 60664-1 (insulating material IIIa, e.g. bobbin) | creepage 8.0 mm | **creepage 16 mm**, 2.7 kV |
| IEC 61558-1 | creepage 1.6 mm | creepage 2.8 mm |

- **IEC 62477-1** is not in MKF. It refers to IEC 60664-1, so take that column for the bobbin and pins.
- **On the PCB,** IEC 60664-1 printed-wiring values at PD2 are much lower: Table F.4 gives about
  2.5 mm basic at 500 V, so about 5 mm reinforced (verify against the table). The board plan keeps
  ≥ 10 mm with slots.
- **The standard is still to be decided.** Under IEC 62368-1 the EE25 flange and pin distances are
  enough. Under IEC 60664-1 / IEC 62477-1, 16 mm over the bobbin material is not reachable on an
  EE25. Options: varnish impregnation (lower pollution degree), or a potted transformer.

## Candidates (MKF at 20 W, turn set A)

| Core / bobbin | Ae | Bpk | Loss 100 V / 450 V | ≈ T at 60 °C | Pins | Footprint |
|---|---|---|---|---|---|---|
| **E25/13/7, Norwe 10165-106 (5 + 5)** | 52 mm² | 267 mT | **0.60 / 0.76 W** | **≈ 78–82 °C** | 10 + CTRL on TIW flying leads | ≈ 28 × 26 mm + CTRL hole pair (≈ 6 × 13 mm zone) |
| E30/15/7, Ferroxcube CSH-E30/15/7-1S-12P (alternative, design 3b4a33d) | 60 mm² | 231 mT | 0.52 / 0.63 W | ≈ 73–76 °C | 12 (6 + 6): all on pins | ≈ 35 × 31 mm |
| E32/16/9, Norwe 10750-024 (6 + 6) | 83 mm² | 167 mT | 0.47 / 0.57 W | ≈ 69–71 °C | 12 | ≈ 36 × 34 mm |

**Board area:**
- today's EF20: 22 × 14 mm body (≈ 310 mm²), 2 × 5 pins at 3.81 mm, rows 10.16 mm apart
- EE25 with the CTRL hole zone: ≈ 800 mm², ≈ 2.6 × the EF20
- E30: ≈ 1100 mm², ≈ 3.5 × the EF20

JLC/LCSC stocks none of these cores, bobbins or TIW. The transformer is hand-wound and hand-fitted,
like TR2 today.

## Around the transformer (100 V full load)

| Part | Stress | Choice (class) |
|---|---|---|
| MOSFET | 690 V peak, 0.44 A rms | IPD95R450P7 (DPAK). ≈ 0.2 W conduction (hot Rds ≈ 1 Ω) + ≈ 0.2 W switching ≈ **0.4 W** |
| Clamp | ≈ **0.8 W** at full load (6.7 µH effective leakage, conservative) | TVS P6SMB200A / SMBJ170A class (≈ 240 V at 1.3 A) + 1000 V fast diode (US1M / RS1M). Give the TVS copper; measure the leakage on the sample |
| RCS | 1.33 A peak | 0.590 Ω 1 %, 0.25 W (1206) |
| Out1 diode | 85 V reverse, 2.4 A peak, 0.37 A avg | 200 V ultrafast 1–2 A (ES2D / STTH202 class) |
| Out2 diode | 85 V, 2.1 A peak, 0.33 A avg | same |
| CTRL diode | 51 V reverse, 6.5 A peak, 1.0 A avg | 100 V Schottky 3 A (SS310 / SS510 class), ≈ 0.45 W: copper |
| Bias diode | 137 V | 300–400 V ultrafast 1 A (ES1G / US1G) |
| Output capacitor RMS | Out1 0.69 A, Out2 0.62 A, CTRL 1.86 A | low-ESR polymer or MLCC + electrolytic; 105 °C, long life (passive chassis) |
| VS divider | bias winding 25.1 V during demag → VS 4.05 V | RS1/RS2 per TI equation 1 (line compensation via RS1) |

**Heat in the aux area at 100 V full load:** transformer 0.6 W + clamp 0.8 W + MOSFET 0.4 W + diodes
≈ 0.9 W ≈ **2.7 W**.

**Cross-regulation:** PSR regulates the bias winding (24.4 V) and sets Out1 = 15.0 V through the tight
bias ↔ Out1 coupling.
- **Out2:** leakage to the bias ≈ 0.58 µH (referred to Out2) gives ≈ 0.3 V droop at full load, so
  expect 14.6–15.3 V. It rises toward 16–17 V when Out2 is light and the others are heavy. Preload
  ≈ 3 mA (5.1 kΩ).
- **CTRL:** ≈ 0.25 µH gives ≈ 0.35 V droop, so 8.5–9.3 V with load and up to ≈ 11–12 V at no load.
  Use a 5 V buck rated ≥ 17 V input; preload ≈ 10 mA (≈ 1 kΩ).
- **Out1:** ≈ 0.1 V.

## Open items

1. **Enclosure temperature:** measure the real internal air temperature (60 °C assumed). The
   transformer at ≈ 80 °C leaves margin up to about 75 °C air.
2. **Sample measurements:**
   - Lp, target 322 µH: set the gap for AL ≈ 314 nH
   - the leakage from the primary with all secondaries shorted (→ clamp loss)
   - the VS waveform at 450 V no load: tDMAG ≥ 1.2 µs, ringing ≤ 100 mVpp in the last 200 ns
3. **TIW:** buy a certified reinforced type (Rubadue TCA3 24/25 AWG, Furukawa TEX-E); not stocked
   at JLC/LCSC.
4. **Core and bobbin:**
   - the gapped E25 half for AL ≈ 314 nH (or a ground core)
   - the Norwe 10165-106 drawing: row spacing, flange creepage from the pins to the core, where
     the CTRL leads can leave
5. **Working voltage:** 500 V is assumed between all three groups. Recompute if the ISO side can
   reach more relative to the primary (450 V DC link plus the AC output).
6. **Standard:** IEC 62368-1 (met) or IEC 62477-1 / IEC 60664-1 (16 mm over the bobbin: needs
   impregnation or potting).
7. **CC limit tolerance:** the worst case is 21 W against the 20 W load. If the real load
   approaches 20 W, lower RCS to 0.562 Ω (+5 % power; flux ≈ 280 mT) or use the E30 alternative.

## Files

| File | |
|---|---|
| `params.py` | all design parameters and the analytical design summary (`python params.py`) |
| `inputs.py` | MKF converter model → `inputs.json` (operating points at 100 / 300 / 450 V) |
| `transformer.py` | winds and evaluates the candidates → `report.txt`; `magnetic.json` and `winding.svg` for the chosen EE25 (`TURNSET=B` for the alternative turns) |
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
