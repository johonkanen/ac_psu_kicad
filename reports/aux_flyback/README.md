# Aux flyback: 20 W, 2 x 15 V, INN3694C, EE25

Replacement design for the sheet-7 auxiliary supply (currently IW1830 + EF20 TR2).
Not yet in the schematic. Designed 2026-10-23 with PyOpenMagnetics (OpenMagnetics MKF) 1.7.35.

## Requirements

- Input 100–500 V DC (DC+ bus).
- Outputs 2 x 15 V, 0.67 A each (20 W total). Out1 is regulated (InnoSwitch FB), Out2 is cross-regulated.
- Reinforced isolation primary to outputs. Out1 to Out2 functional only.
- EE25 core, no triple-insulated wire (enamelled wire + margin tape + sleeving).

## Controller: INN3694C (InnoSwitch3-EP, 900 V MOSFET)

The INN3165C (650 V) was the first choice but cannot take 500 V: Vbus + VOR + clamp would be ≈ 660 V.
INN3694C limits used (datasheet Rev. W 06/24): peak drain ≤ 725 V in normal operation,
ILIM standard 693/750/806 mA (BPP = 0.47 µF), full-load fSW ≈ 70 kHz, 20 W rating at 85–440 VAC.
JLC C567564 (0 stock 2026-10-23). The datasheet lists UL1577/TUV/IEC 60747-17 for INN369xC as *pending*; check
before relying on the IC package for reinforced isolation.

## Transformer

| Item | Value |
|---|---|
| Core | TDK B66317G0250X187: E25/13/7, N87, 0.25 mm gap in one half (centre leg), AL ≈ 250 nH |
| Bobbin | Norwe 10165-106, EE25 horizontal 10-pin, longer creepage |
| Lp | 1.19 mH (from the datasheet AL), ±10 % |
| Turns | primary 69 (35 + 34), Out1 10, Out2 10, bias 9 |
| VOR | ≈ 104 V |
| Peak flux | 268 mT at ILIM max |
| Losses (MKF) | core 0.23–0.43 W, copper 0.33–0.37 W |
| Leakage (MKF) | 20.6 µH from the primary; Out1–Out2 0.35 µH |

Winding order, inside to outside (2.0 mm margin tape on both sides of every primary and secondary layer):

| # | Winding | Wire | Turns | Notes |
|---|---|---|---|---|
| 1 | P1 | 0.28 mm Grade 2 | 35, 1 layer (11.2 mm) | start at the DRAIN pin |
| – | tape | 3 x 25 µm polyester | | reinforced barrier |
| 2 | Out1 | 0.56 mm Grade 2 | 10, spread across the width | |
| – | tape | 1 x 25 µm | | functional (Out1–Out2) |
| 3 | Out2 | 0.56 mm Grade 2 | 10, spread across the width | |
| – | tape | 3 x 25 µm | | reinforced barrier |
| 4 | P2 | 0.28 mm Grade 2 | 34, 1 layer (10.9 mm) | finish at DC+ |
| – | tape | 1 x 25 µm | | |
| 5 | Bias | 0.25 mm Grade 2 | 9, spread | no margins needed |
| – | tape | 3 x 25 µm | | outer wrap |

- Margins: 2 x 2.0 mm gives 4 mm creepage. The MKF IEC 62368-1 reinforced requirement is 3.9 mm
  (500 V, PD2, CTI IIIa). Thin-sheet reinforced insulation needs at least 3 tape layers.
- Sleeving: sleeve every lead that crosses a margin or another isolation group (Out1/Out2 starts and finishes,
  the P1→P2 link) from inside the margin to the pin. Use sleeving rated for reinforced insulation (5 kV test).
- Secondaries go out on the opposite pin row (pins 6–10). Leave a pin empty between Out1 and Out2.
- Measure Lp on the first sample. At the same gap, MKF predicts ≈ 12 % more than the TDK AL (1.34 vs 1.19 mH).
  If it reads high, remove a primary turn or two.

## Around the transformer

- Primary clamp: 180–200 V TVS plus a 1000 V fast diode. Peak drain ≈ 700 V at 500 V input. Clamp loss ≈ 0.9 W.
- Out1: SR MOSFET rated 150 V (sees ≈ 85 V plus ringing). FB divider ≈ 100 k / 9.09 k (1.265 V reference).
- Out2: 150–200 V Schottky or ultrafast diode. Expect ≈ 14.6 V at full load and up to ≈ 16–17 V with Out1 heavily
  and Out2 lightly loaded. Add a 2–3 mA preload or a post-regulator if Out2 must be tight.
- Bias: ≈ 12–13 V at full load, 200 V diode.
- PCB: 10 mm creepage primary to outputs (conservative), slot under the IC and transformer, Y1 capacitor per
  isolated return. InSOP-24D package creepage is 11.4 mm.

## Standard caveat

The insulation design uses IEC 62368-1. Under IEC 60664-1 tables (IEC 62477-1 / 61800-5-1, typical for inverters),
MKF asks for 16 mm creepage at PD2. A margin-tape construction can't meet that on EE25 (15.8 mm winding width).
The options are vacuum varnish impregnation (PD1 → 4.8 mm, 2.4 mm margins) or triple-insulated secondaries.

## Files

| File | |
|---|---|
| `params.py` | all design parameters |
| `inputs.py` | converter model → `inputs.json` (MAS operating points at 100 / 400 / 500 V) |
| `transformer.py` | winds and evaluates the transformer → `magnetic.json`, `winding.svg`, printed report |
| `report.txt` | output of the last `transformer.py` run |

Run:

```
python3 -m venv venv && venv/bin/pip install PyOpenMagnetics==1.7.35
cd reports/aux_flyback && ../../venv/bin/python inputs.py && ../../venv/bin/python transformer.py
```

MKF quirks worked around in the scripts:
- `calculate_gapping_from_number_turns_and_inductance` fails ("bad optional access"), so the gap is bisected on
  MKF's inductance model.
- `wind()` margin pairs apply per pattern section, and only with `coilEqualizeMargins` off.
- `wind()` keeps one intersection-insulation layer, so 3 x 25 µm is modelled as one 75 µm layer.
- `simulate_flyback_with_magnetic` does not accept a finished magnetic, so cross-regulation is estimated, not simulated.
