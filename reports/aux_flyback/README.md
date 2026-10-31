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
  because the 10-pin bobbin cannot hold Out2 and CTRL on one 5-pin row ≥ 10 mm apart. **No separate
  bias winding** (user, 2026-10-31): Out1 is the PSR sense winding and supplies VDD.

## Requirements

- **Input:** DC+ 100–450 V, full power at 100 V continuous.
- **Outputs:** design load **≈ 20 W** (19.8 W; user estimate 15–20 W):

  | Output | Domain | Voltage | Current | Power |
  |---|---|---|---|---|
  | Out1 `15V` | GND, primary group; PSR sense + VDD | 15 V | 0.39 A (0.37 A load + ≈ 20 mA VDD) | 5.85 W |
  | Out2 `15V_ISO` | ISOGND | 15 V | 0.33 A | 5 W |
  | CTRL | control card | ≈ 9 V into a 5 V buck | 1.0 A | 9 W (card ≈ 7.5 W + buck loss) |

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
| Ipp(max) | 1.39 A at VCST(max); **RCS 0.562 Ω 1 % (E96)**, 0.12 W (user 2026-10-31; the 20 W design gives 0.588 Ω, lowered for CC-limit margin) |
| CC limit | 27.9 W typ (100 kHz, 780 mV); 25.7 W at fSW(max) 92 kHz; **23.0 W worst case** (92 kHz and 738 mV): 15 % above the 20 W design load. DCM at the CC point at 100 V uses 0.99 of the period (overload only) |
| Full load | 19.8 W at **71 kHz** (FM region, peak current fixed); 0.70 of the period at 100 V |
| 100 V full load | ton 4.27 µs + tdemag 4.25 µs + 1 µs ring = 0.75 of the period (0.95 at the CC point) |
| Primary RMS | 0.44 A at 100 V, 0.26 A at 300 V, 0.21 A at 450 V |
| Light load, 450 V | tON is LEB-limited at 280 ns → **tDMAG(min) 1.25 µs**, just above TI's 1.2 µs: check VS sampling on the sample at 450 V, no load |
| Drain peak | 450 V + 240 V clamp = **690 V** (73 % of the IPD95R450P7's 950 V) |

## Transformer (chosen: E25/13/7 N87, Norwe 10165-106, CTRL on flying leads)

| Item | Value |
|---|---|
| Core | E25/13/7 N87, centre-leg gap ≈ 0.22 mm for **AL ≈ 314 nH**. TDK B66317-series halves (ungapped B66317G0000X187 with a gapped B66317G…X187 half; the old design's B66317G0250X187 is ≈ 250 nH, too low: pick the gap for 314 nH or have the core ground), or Ferroxcube E25/13/7-3C95 gapped to the same AL |
| Bobbin | EE25 horizontal, longer creepage, 10 pins (5 + 5) at 5.08 mm: **Norwe 10165-106** (2-chamber 10166-106). Same family, standard creepage: Norwe 10220-024 / 10175-106. None are stocked at JLC/LCSC; confirm the drawing (row spacing, flange creepage) |
| Turns | Primary 32 (16 + 16 in series), Out1 5, Out2 5, CTRL 3; no bias winding |
| Peak flux | 280 mT at Ipp(max) and VCST 810 mV (N87 Bsat ≈ 390 mT at 100 °C) |
| Losses (MKF) | 100 V: core 0.36 W + copper 0.26 W = **0.61 W**; 300 V: 0.71 W; 450 V: **0.87 W** |
| Temperature | ≈ 29 K/W free convection (rule of thumb) → **≈ 78–86 °C** at 60 °C air |
| Leakage (MKF, pairwise from the primary) | Out1 6.1 µH, Out2 11.2 µH, CTRL 2.9 µH; clamp-effective ≈ 5.9 µH. Referred to Out2 with Out1 shorted 0.32 µH, CTRL 0.06 µH (cross-regulation against Out1) |

Turn set B (38/6/4, CTRL ≈ 10 V) was run in the bias-winding version: peak flux 223 mT, about the same
loss, but ≈ 33 % more leakage, so more clamp loss. A is kept.

Winding orders compared (MKF, no bias winding; `WINDING=O1..O4 python transformer.py EE25`):

| Order | P→Out1 / Out2 / CTRL leakage | Clamp-effective | Loss 100 / 450 V |
|---|---|---|---|
| O1 P1, Out1, P2, CTRL, Out2 | 4.5 / 15.0 / 5.7 µH | 7.6 µH | 0.86 / 1.07 W |
| **O2 P1, CTRL, Out1, P2, Out2** | **6.1 / 11.2 / 2.9 µH** | **5.9 µH** | **0.61 / 0.80 W** |
| O3 P1, Out1, CTRL, P2, Out2 | 6.0 / 11.2 / 2.9 µH | 5.9 µH | 0.69 / 0.92 W |
| O4 P1, CTRL, Out2, P2, Out1 (old order) | 11.7 / 5.8 / 3.0 µH | 6.2 µH | 0.59 / 0.76 W |

O2 is chosen: the lowest clamp-effective leakage, Out1 sandwiched between the primary halves for clean
VS sensing (6.1 µH, half of O4's), CTRL tightly coupled to Out1 (0.06 µH), and about the lowest loss.

Winding order, inside to outside (`winding.svg`):

| # | Winding | Wire | Turns |
|---|---|---|---|
| 1 | P1 | 0.40 mm Grade 2 | 16 |
| 2 | CTRL | 3 × TIW 25 AWG (Rubadue TCA3) in parallel | 3 |
| 3 | Out1 | 0.63 mm Grade 2 (heavier: the bias winding's space) | 5 |
| 4 | P2 | 0.40 mm Grade 2 | 16 |
| 5 | Out2 | TIW 24 AWG (TCA3) | 5 |

1 × 25 µm tape between layers, plus an outer wrap.

**Construction: TIW on Out2 and CTRL, no margin tape.** TIW is solid reinforced insulation on the wire;
it must be a certified type (IEC 62368-1 Annex J / IEC 61558-1), e.g. Rubadue TCA3 or Furukawa TEX-E,
bought with its certificate. Enamelled leads (primary, Out1) stay on the primary row.

### Out1 as the PSR sense and VDD winding

- **VS:** the UCC28710 VS divider is taken from the Out1 winding node before its rectifier diode,
  on GND (the controller ground). NPA = 32/5, NAS = 1.
  - RS1 = 59.0 kΩ (eq. 25, DC input: run at ≈ 85 V, stop at ≈ 30 V).
  - RS2 = 21.0 kΩ (eq. 26 with VVSR 4.05 V and VF ≈ 0.45 V near zero current).
  - Cable compensation RCBC ≈ 118 kΩ (eq. 28) gives +0.25 V at full load for the diode VF rise and
    the winding IR drop. The sample is taken near zero secondary current, so the IR drop is in the
    output, not in the sample; trim RCBC on the prototype.
  - **The controller now regulates Out1 directly**; Out2 and CTRL cross-regulate against Out1.
- **VDD:** from the 15 V rail through a small-signal diode (BAS16/1N4148W) + 47 Ω: VDD ≈ 14.3 V
  (run range 8.1–35 V). The HV start-up switch (100–500 µA, ≈ 300 µA typ) charges CDD to the 21 V
  UVLO-on first.
  - **CDD (eq. 24):** run current ≈ 6.2 mA (IRUN 2.65 mA max + Qg 35 nC × 100 kHz). VDD must hold
    from 21 V (19 V worst) down to above 8.1 V (8.5 V worst) + 1 V margin until Out1 is high enough
    to feed it (≈ 10 V).
  - **Start-up time:** charging ≈ 0.08 J into the outputs (≈ 600 µF on Out1 incl. the gate-driver
    boards and U9, ≈ 600 µF on Out2, ≈ 1000 µF on CTRL) at the 21 W worst-case CC limit, with half
    of it taken by loads that start early, takes ≈ 8 ms. Design for 20 ms → CDD ≥ 12.9 µF →
    **15 µF / 50 V**.
  - **Start delay** with 15 µF: ≈ 1.3 s typ, ≈ 4.9 s worst case (IHV 100 µA min at 100 V input).
- **Short circuit:** a short on Out1 collapses VDD (as does a short on Out2 or CTRL, which clamps all
  windings). The controller drops out at 8.1 V, the HV switch recharges CDD (≈ 1–5 s), and it
  restarts for one CDD discharge (≈ 15 µF × 12 V / 6 mA ≈ 30 ms). The result is a low-duty hiccup
  (≈ 1–3 %), thermally safe. An open VS divider or output overvoltage (VS > 4.6 V, +15 %) is a fault
  with UVLO reset too.
- **Gate drive:** with VDD ≈ 14.3 V the DRV output reaches ≈ 13 V (below its 14–16 V clamp). That is
  above the IPD95R450P7's 10 V Rds(on) rating, so the FET is fully on.
  - **Speed:** DRV sources only 20–25 mA, so Qg 35 nC takes ≈ 1.4–1.8 µs. That is fine at 100 V full
    load (ton 4.3 µs) and at 450 V full load (0.95 µs; the current starts at zero in DCM). At 450 V
    light load (ton ≈ 280 ns, LEB-limited) the gate barely passes the plateau.
  - **Decision (user, 2026-10-31):** a small NPN/PNP emitter-follower buffer (MMBT3904/MMBT3906) from
    VDD; the IPD95R450P7 stays (the IPD95R750P7 would add ≈ 0.2 W).
  - Turn-off: 6–12 Ω sink.
- **VS waveform at the knee:**
  - **Leakage reset:** with ≈ 5.9 µH clamp-effective leakage the reset pedestal is ≈ 5.9 µH × 1.33 A /
    (240 − 100.5 V) ≈ 60 ns at Ipp(max) and ≈ 15 ns at Ipp(min). TI's limits are 2.2 µs and 600 ns.
  - **Ringing:** the Out1-side leakage (≈ 0.15–0.32 µH) with the diode and winding capacitance
    (≈ 100 pF) rings at ≈ 30–40 MHz and dies out in ≲ 200 ns.
  - **Timing:** at 450 V no load, tDMAG(min) ≈ 1.25 µs, so the ringing must be below 100 mVpp at VS
    (≈ 0.38 Vpp at the winding with RS1/RS2) by ≈ 1.05 µs.
  - If it is not, add an RC snubber across the Out1 diode and check on the sample.

### Pins and the CTRL flying leads

Horizontal bobbin: each flange carries one 5-pin row.
- **Primary row (pins 1–5):** 1 drain (P2 end), 2 DC+ (P1 start; the P1–P2 joint is inside the
  winding), 3 **empty** (the freed bias pin: 10.16 mm between DC+ and the low-voltage pins),
  4 GND (Out1 return), 5 Out1. These are functional distances inside the primary group.
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

## Candidates (MKF at 20 W, turn set A, winding order O2)

| Core / bobbin | Ae | Bpk | Loss 100 V / 450 V | ≈ T at 60 °C | Pins | Footprint |
|---|---|---|---|---|---|---|
| **E25/13/7, Norwe 10165-106 (5 + 5)** | 52 mm² | 280 mT | **0.61 / 0.87 W** | **≈ 78–86 °C** | 10 + CTRL on TIW flying leads | ≈ 28 × 26 mm + CTRL hole pair (≈ 6 × 13 mm zone) |
| E30/15/7, Ferroxcube CSH-E30/15/7-1S-12P (alternative, design 3b4a33d) | 60 mm² | 241 mT | 0.52 / 0.71 W | ≈ 73–78 °C | 12 (6 + 6): all on pins | ≈ 35 × 31 mm |
| E32/16/9, Norwe 10750-024 (6 + 6) | 83 mm² | 167 mT | 0.49 / 0.61 W | ≈ 70–72 °C | 12 | ≈ 36 × 34 mm |

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
| Clamp | ≈ **0.7 W** at full load (5.9 µH effective leakage, conservative) | TVS P6SMB200A / SMBJ170A class (≈ 240 V at 1.3 A) + 1000 V fast diode (US1M / RS1M). Give the TVS copper; measure the leakage on the sample |
| RCS | 1.39 A peak | 0.562 Ω 1 %, 0.25 W (1206) |
| Out1 diode | 85 V reverse, 2.5 A peak, 0.39 A avg | 200 V ultrafast 1–2 A (ES2D / STTH202 class) |
| Out2 diode | 85 V, 2.1 A peak, 0.33 A avg | same |
| CTRL diode | 51 V reverse, 6.5 A peak, 1.0 A avg | 100 V Schottky 3 A (SS310 / SS510 class), ≈ 0.45 W: copper |
| VDD feed | Out1 → VDD, ≈ 6 mA | BAS16 / 1N4148W + 47 Ω; CDD 15 µF / 50 V (X7R 1210 or electrolytic) + 100 nF at the pin |
| Gate buffer | Qg 35 nC from 20–25 mA DRV | **MMBT3904 / MMBT3906 emitter follower from VDD** (user 2026-10-31) |
| Output capacitor RMS | Out1 0.71 A, Out2 0.62 A, CTRL 1.86 A | low-ESR polymer or MLCC + electrolytic; 105 °C, long life (passive chassis) |
| VS divider | Out1 winding 15.45 V at the knee → VS 4.05 V | RS1 59.0 k, RS2 21.0 k, RCBC ≈ 118 k (see above); RLC per TI eq. 27 |

**Heat in the aux area at 100 V full load:** transformer 0.6 W + clamp 0.7 W + MOSFET 0.4 W + diodes
≈ 0.9 W ≈ **2.6 W**.

**Cross-regulation:** PSR regulates Out1 directly (VS from the Out1 winding): ±1 % VVSR plus the
diode tolerance, with cable compensation for the VF rise. Out2 and CTRL follow Out1 through their
leakage to it (ΔV ≈ Llk × Ipk / tdemag):
- **Out2:** 0.32 µH × 2.1 A / 4.25 µs ≈ 0.16 V droop, so expect 14.7–15.3 V. It rises toward ≈ 16 V
  when Out2 is light and Out1 heavy. Preload ≈ 3 mA (5.1 kΩ).
- **CTRL:** 0.06 µH × 6.5 A / 4.25 µs ≈ 0.1 V, so ≈ 8.9–9.3 V with load and ≈ 10.5–11.5 V at no load.
  Use a 5 V buck rated ≥ 17 V input; preload ≈ 10 mA (≈ 1 kΩ).

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
7. **Gate drive:** decided – MMBT3904/3906 buffer (user, 2026-10-31). Check the light-load
   LEB-limited on-time at 450 V on the prototype.
8. **VS divider and cable compensation:** trim RS2 / RCBC on the prototype. Check the VS ringing at
   450 V no load (≤ 100 mVpp at VS from ≈ 1.05 µs) and the start-up into the real output capacitance
   (CDD 15 µF).
9. **CC limit tolerance:** decided – RCS 0.562 Ω (user, 2026-10-31): worst case 23.0 W against the
   20 W load (was 21.0 W with 0.590 Ω); flux 280 mT at Ipp(max).

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
