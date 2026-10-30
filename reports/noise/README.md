# Switching noise in the measurements – analysis (2026-10-30)

Symptom on the built v3 boards (user): spikes at the switching edges in **all** voltage and current
measurements, only while the power stages run; not a raised noise floor. The ADC samples
free-running, not synchronised to the PWM. Switching frequencies: AFE and VSI 30 kHz, DAB 66 kHz.

This is analysis only. Nothing in the schematic, board or BOM was changed. Sources: the netlist
(`kicad-cli sch export netlist`), the board copper (`export_polys.py` and `overlap2.py`, run with
`tools/p2k/bin/kipy`) and the renders `01`–`05` here (`plot.py`). Coordinates are mm in the IPC
frame (Y up), as in STATUS.md.

Assumptions: the board is 2.267 mm thick with 4 layers; the dielectric thicknesses are unknown, so
couplings are order-of-magnitude estimates. SiC C3M0065090D edges are 30–50 V/ns at 400–450 V,
and the gate-drive edges about 20 V in 10–20 ns.

## The measurement chains

| Chain | Path | Ground | Filtering today |
|---|---|---|---|
| ADA1: DC+ | DC+ → R41/R27/R35 (3 × 91k) → U14 (TLV316) diff amp, 10k legs; PGND side R42/R28/R36 | GND, via R37 | none at the amp; output R39 8.2k + C42 1 nF → **19 kHz** |
| ADA2: mains | AC_IN_1 / AC_IN2 → 3 × 91k chains → U1A (OPA2353), 10k legs, ref REF_1V65 | GND / REF_1V65 | none at the amp; R18 **100 Ω** + C88 1 nF (v4 fix 3) → **1.6 MHz** |
| ADA3: filter voltage | FILTER_INPUT / LEMOUT → 3 × 91k → U1B, ref leg **R7 = 1k** (!) | GND / REF_1V65 | none at the amp; R9 100 Ω + C89 1 nF → 1.6 MHz |
| ISOADA3: ISODC+ | ISODC+/ISOPGND → 3 × 91k → U2 (TLV316) | ISOGND | none at the amp; R77 8.2k + C2 1 nF → 19 kHz → J11.1 |
| ISOADA1: inverter filter | INU_FILTER_INPUT / INDUCTOR_OUTPUT → 3 × 91k → U7A, ref REF_1V65_ISO | ISOGND | none; R54 8.2k → J11.4, **no capacitor** |
| ISOADA2: AC out | AC_OUT_2 / AC_OUT_1 → 3 × 91k → U7B | ISOGND | none; R56 8.2k → J11.3, **no capacitor** |
| ADC | U11 mux (ADA1–3) → U12 TLV316 buffer → R86 10 Ω + C9 1 nF → AD1 ADS7056 | GND | anti-kickback only |
| AFE current | R48 (2 mΩ; force pin 4 on G1_SOURCE_HI = the Q1/Q2 switch node) → U5 | **GND1 = SHUNT1, on the switch node** | v3: 10 Ω + 220 pF per leg; v4: 12.4 Ω + 100 nF C0G differential (2.5 µs) |
| VSI current | R91 (force pin 3 on Q7_S = the Q7/Q8 switch node) → U4 | **GND1 = INU_SHUNT2, on the switch node** | as above (C90) |
| DAB current | R64 in the ISOPGND → DAB_GROUND return → U6 | GND1 = DAB_SHUNT2 ≈ ISOPGND | as above (C92) |

The 91k/10k taps give a signal gain of 10/273 = 0.0366. Charge injected **into a tap node**
reaches the output at a noise gain of 1 + 10k/273k ≈ 1.04. Node-coupled noise is therefore
amplified about 28 times more than the signal. That is why small couplings matter here.

## Findings, ranked by likely impact

### 1. The diff-amp input nodes have no capacitance and run 70–100 mm across the board (high confidence)

Each tap node (the 273k/10k junction at an amp input) is a ≈ 9.6 kΩ node with only trace and
op-amp input capacitance, about 5–10 pF.
- **The U7A/U7B/U2 nodes** run about 100 mm on In2, from the chains at x ≈ −10 to the amps at
  x ≈ 80 (render `02`).
  - Over x ≈ 0…50 they run 1.5–2 mm below the J8/J6 header row and the Q5–Q8 gate and source
    traces at y ≈ 50.6: Q5_G, Q7_G and Q5_S/Q7_S, which carry the full switch-node swing.
  - `overlap2.py` reports them within 2 mm of Q5_S, Q7_S, Q5_G and Q7_G on In1/In2/B.
  - Only x > 43 has an ISOGND/3V3_ISO plane next to them.
- **The U1A/U1B nodes** run about 70 mm from x ≈ −22 to U1 at (50.9, −3.3), with no plane under
  them for x < 42 (render `03`).

**Estimate:** 0.05 pF from a 400 V source node to a 8 pF tap node gives a 2.5 V step. 0.2 pF from
a 20 V gate edge gives 0.5 V. Each decays with 9.6 kΩ × 8 pF ≈ 80 ns. The + and − nodes of a
pair pick up different amounts (outer and inner trace), so a large part becomes differential and
reaches the output at about 1×, with no 0.0366 attenuation. That means spikes of tens of percent
of full scale, exactly at the edges, as observed.

**Fix:**
- **Board script (v4 pattern), new parts:** a 1 nF C0G 0402 across every 10k leg: the feedback
  resistor and the matching reference/ground resistor of all six amps.
  - U1A: R17, R21. U1B: R8, R7. U14: R38, R37. U2: R76, R1. U7A: R53, R52. U7B: R51, R46.
  - That is 12 caps; the corner is 15.9 kHz.
  - The injected step then becomes 400 V × 0.05 pF / 1 nF = 20 mV, smoothed over 10 µs.
  - The two caps of a pair must match (C0G 5 %) to keep the CMRR at high frequency.
- **Layout (v5):** put the 10k leg and its capacitor at the chain end, so the long run is the
  low-impedance side, or move the amps next to the chains. Route the pairs over a solid plane and
  at least 5 mm from the J1–J8 gate/source rows.

### 2. U1B: R7 = 1k breaks the difference amplifier (high confidence for the fact; the effect depends on the CM swing)

U1B has R7 = 1k in its + leg, against R8 = 10k in its feedback (sheet 1; the Proteus value, kept
1:1 in the conversion). Every other amp uses 10k/10k.

Result: V_out ≈ 1.705 V + 0.0038·V(LEMOUT) − 0.0366·V(FILTER_INPUT). The amp measures
FILTER_INPUT against GND (DC−), not the filter voltage, and its common-mode gain is about 0.033.
Correctly matched 1 % parts give at most 1.4 × 10⁻³.

Seen from DC−, the mains-side filter nodes carry the AFE's common-mode PWM voltage, up to Vdc/2
steps at 30 kHz before the CM chokes and Y capacitors. ADA3 can show about 24 × more switching
common mode than a matched amp: volts, so it clips.

**Fix (BOM value):** R7 1k → 10k (0402, the same part as R21). Check the firmware's ADA3 scaling
afterwards: the gain changes from the asymmetric value to 0.0366 differential.

### 3. The RC after the amps is far above the switching frequencies, or missing (high confidence)

- ADA2/ADA3 have 100 Ω + 1 nF (1.6 MHz). Fix 3 added the 1 nF but kept the 100 Ω.
- ADA1 and ISOADA3 have 8.2k + 1 nF (19 kHz), which is −1.7 dB at 30 kHz.
- ISOADA1/ISOADA2 have 8.2k and no capacitor on this board. Only the control card's ADC input
  filters them.

**Proposal: two poles**, the 15.9 kHz feedback capacitor from finding 1 plus an output RC.

| Chain | Output RC | Corner | At 50 Hz | At 30 kHz | At 66 kHz |
|---|---|---|---|---|---|
| AC: ADA2, ADA3, ISOADA1, ISOADA2 | 8.2k + 4.7 nF | 4.1 kHz | 0.87° lag (48 µs), < 0.01 % gain error | −24 dB | −37 dB |
| DC link: ADA1, ISOADA3 | 8.2k + 10 nF | 1.9 kHz | 1.7° + 2.95° at 100 Hz | −30 dB | −45 dB |

**Trade-off:**
- The AC chains keep a known 48 µs group delay at 50 Hz, which firmware can compensate.
- DC-link loops are usually 10–100 Hz, so they can take the harder filter.
- If a fast DAB/DC-link loop above 300 Hz uses these signals, use 4.7 nF there too (4.1 kHz).
  It adds about 14° at 1 kHz on top of the 15.9 kHz pole.

**Fix:**
- **BOM values, cheapest (existing footprints):**
  - R18, R9: 100 Ω → 8.2k
  - C88, C89: 1 nF → 4.7 nF C0G 0402 (v4 parts, free to change)
  - C42, C2: 1 nF → 10 nF
- **New parts:** ISOADA1/ISOADA2 need a 4.7 nF at R54/R56 (board script, 2 caps), or the
  capacitor on the control card at its ADC input. That is the easier place if the card is
  redesigned anyway; tell the efinix session.

### 4. Current measurements: v4 fix 4 explains and removes the edge spikes (medium-high confidence)

**Mechanism.** R48 and R91 sit between a switch node (G1_SOURCE_HI, Q7_S) and the filter
inductor. At every hard-switched edge, the inductor's winding and stray capacitance (20–100 pF)
and the off-board wiring charge at 30–50 V/ns. That puts 1–5 A for 5–10 ns through the shunt:
di/dt ≈ 1 A/ns.
- Across about 5 nH, L·di/dt ≈ 5 V. The I·R drop is about 8 mV.
- Against the ±250 mV range (±320 mV clip), the modulator is driven far over range at every edge.
- v3's 10 Ω + 220 pF per leg (τ ≈ 4 ns) passed these ns spikes almost unattenuated. An overloaded
  ΣΔ produces an invalid bit stream for a few clocks, and the sinc decimation turns that into a
  spike in the output word.

**v4 fix 4** (12.4 Ω per leg with 100 nF C0G differential; τ = 24.8 Ω × 100 nF = 2.48 µs = L/R
for 5 nH / 2 mΩ):
- It cancels the L·di/dt term of the real current.
- It low-passes a 10 ns spike by about 1/250, so 5 V becomes about 20 mV, inside the range.
- If L is really 10 nH, the remaining error is a 2× overshoot of fast current steps, not a spike.

**DAB (U6/R64)** is the most sensitive to the L match. The DAB current ramps for microseconds at
di/dt = V/L_leak. For example, 800 V / 10 µH = 80 A/µs, so 5 nH × 80 A/µs = 0.4 V for the whole
ramp, which is over range for microseconds.

**Still open:**
- **(a) Measure or tune L**, starting with R64: re-pick R73/R74 with the 2.5 Ω/nH rule.
- **(b) Common mode across the barrier.** U4/U5 have GND1 on the switch node. At 50 V/ns the
  ≈ 1–2 pF barrier capacitance injects 50–100 mA spikes into GND/ISOGND next to U4/U5. That is
  within CMTI: AMC1306M25 is ≥ 100 kV/µs, against 30–50 kV/µs here.
  - It flows through the logic ground near MCLK/MDAT.
  - U5's MDAT goes through U15, U4's straight to J11.34.
  - Planes under U4/U5 and short clock returns matter (layout, v5).
- **(c) Kelvin:** R64 and R91 are wired correctly; their sense nets reach only the sense pins.
  R48 was fixed in fix 5.
- **(d) Firmware:** set the sinc decimation window to the PWM period. 30 kHz = 33.3 µs, so for
  example OSR 666 at 20 MHz. That puts notches at the carrier and its harmonics. For U6 use the
  DAB period, 15.15 µs.

### 5. REF_1V65 and REF_1V65_ISO have no capacitor (high confidence for the fact, medium for the impact)

The reference node for four amps (U1A, U1B; U7A, U7B) is REF3025 → 422 Ω → node → 820 Ω to
ground: a 279 Ω source with no decoupling (renders `03`; REF_1V65_ISO is 8 mm² of copper on
B.Cu). Any current injected into one amp's reference leg moves the reference of the other.
Finding 1's capacitors return their HF current exactly there.

**Fix (board script):** 100 nF from REF_1V65 to GND and from REF_1V65_ISO to ISOGND (2 caps;
τ = 28 µs).

### 6. Sampling not synchronised, and 66 kHz aliases into the band (high confidence; firmware)

Free-running samples land at random phases of the 30 kHz and 66 kHz edges, so each edge's
residue appears as random spikes.
- Sampling synchronised to the 30 kHz carrier turns the 30 kHz residue into a constant offset.
- But a 66.67 kHz DAB component sampled at 30 kHz aliases to 66.67 − 60 = 6.67 kHz, which is
  inside the band.

**Options:**
- **(a) Sample in a common quiet window.** Mid-period of the AFE/VSI carrier, if both run on
  one time base, and only when no DAB edge falls within about 1 µs (the DAB has an edge about
  every 3.8 µs). This needs the DAB counter phase at sample time.
- **(b) Oversample and decimate.** Run the ADS7056 fast (up to 2.5 MSPS) and average over
  exactly one 33.33 µs carrier period. That nulls 30 kHz and its harmonics, and attenuates
  66.67 kHz by |sinc(66.67/30)| ≈ 0.09 (−21 dB). The analog filter of finding 3 does the rest.
- **(c) System choice.** Run the DAB at an integer multiple of the 30 kHz carrier (60 or 90 kHz)
  and synchronise it. Then a common quiet window exists every period, and nothing aliases.

Recommended: (b), plus the analog filters, unless (c) is easy in the FPGA.

### 7. J11 ground pins and the analog pins next to the clocks (medium confidence)

J11 (38 pins) has two ISOGND pins (2 and 5) for about 20 fast signals: the PWMs, the 5–21 MHz
ADC clocks and MDAT. J12 adds three ISOGND pins.
- The analog ISOADA3/ISOADA2/ISOADA1 are on pins 1/3/4, next to MDATA_ISO (6) and ADCLK_ISO (7).
- The clock and PWM return currents share the same two pins as the analog reference, so the
  ISOGND–card ground difference appears in series with ISOADA1–3 at the card ADC.

**Fix:**
- **Layout (v5) / card side:** more ground pins and ground between the analog and clock pins.
- **Now:** the capacitors of finding 3 at the card's ADC inputs.

Relevant for the efinix control-card connector.

### 8. GND/PGND star and the aux flyback return (medium confidence; not edge-related to the power stages)

R96 (0 Ω at (54.5, −12.0)) is the only link between GND and PGND; R97 at (96.9, 40.9) links
ISOGND and ISOPGND. The measurement ground is a star, which is good.
- **Aux flyback:** the IW1830 returns its primary current to GND, not PGND (PWM1.3, TR2.4 and
  R45/R47 on GND; C68 from DC+ to GND). Each flyback pulse (≈ 0.9 A peak) flows from the PGND
  bulk caps through R96 and the GND plane. That puts a ground voltage at the flyback frequency
  right at the R96 star point, next to U14 (61.3, −12.6).
  - It is there all the time, not only when the power stages run, so it is not the main symptom.
  - The v5 aux redesign should return the primary to PGND.
- **Question:** do the gate-driver boards on J1–J3 connect their logic GND (pin 46) to the power
  source/PGND (pins 15–20/29–34) anywhere? If yes, each is a second GND–PGND path, a ground loop
  carrying switching current through the GND plane.

### What v4 already fixes

| Fix | Effect on noise |
|---|---|
| 1 RET_ISO → ISOGND | The 20V_ISO_SEC return was floating against ISOGND; isolated-side references now share ISOGND (one of the bodges). |
| 2 U11 INH → GND | The mux enable was floating, so channels could switch off or glitch randomly. |
| 3 C88/C89 on ADA2/ADA3 | Mux kick-back only: 100 Ω + 1 nF is 1.6 MHz, no help at 30/66 kHz. Change the values (finding 3). |
| 4 RC on the ΣΔ inputs | The current-measurement edge spikes (finding 4). |
| 5 R48 Kelvin | The AFE current no longer includes the force-path copper drop. |

Still open: findings 1, 2, 3, 5, 7, the firmware part of 4 and 6, and the R64 L tuning.

## Proposed changes, by cost

| Class | Change | Findings |
|---|---|---|
| BOM value (existing footprints) | R7 1k → 10k; R18, R9 100 Ω → 8.2k; C88, C89 → 4.7 nF C0G; C42, C2 → 10 nF (or 4.7 nF for a fast DC loop) | 2, 3 |
| New parts, board script (v4 pattern) | 12 × 1 nF C0G 0402 across the 10k legs; 2 × 100 nF on REF_1V65/REF_1V65_ISO; 2 × 4.7 nF on ISOADA1/2 (or on the card). U1's area (R7/R8/R21 at x 50–54) is dense, so check the room first; the bottom side under the resistors may be needed. | 1, 3, 5 |
| Firmware | Sinc window = PWM period; synchronised or oversampled-and-averaged ADC sampling; DAB at a multiple of 30 kHz if possible; compensate the 48 µs AC filter delay | 4, 6 |
| Layout (v5) | Short low-impedance tap routing away from the J1–J8 gate/source rows, over planes; more ground pins and analog/clock separation on J11; aux primary return on PGND | 1, 7, 8 |

## Measurements to do on the v3 board

1. Trigger on one stage's PWM and run the stages one at a time (DAB only, AFE only, VSI only).
   Scope ADA2 (at U11.13) and ISOADA1 (at J11.4). This shows which edges cause which spikes.
2. **Finding 1:** solder a 1 nF 0402 across R17 and across R21 (U1A) and compare ADA2. Then
   repeat on U7A (R53/R52) and compare ISOADA1.
3. **Finding 2:** measure R7. Replace it with 10k and compare ADA3 (recalibrate the gain).
4. **Coupling vs common mode:** lift the top resistor of one chain (e.g. R13 and R16, U1A), so
   the tap sees only the 10k to its reference. If the spikes stay, they come from coupling along
   the trace, not from the divided common mode.
5. With a differential probe, measure across R96 (GND–PGND) and R97 (ISOGND–ISOPGND) with the
   stages switching: ground bounce at the star points.
6. **Currents:** solder 100 nF across the U4/U5/U6 inputs on the v3 board (fix 4 as a bodge) and
   compare the decimated current words. Then tune R73/R74 for the DAB shunt by minimising the
   overshoot at the DAB current reversal.

## Files

`01_overview_taps.png` (tap nodes vs switch nodes and gate drive), `02_inverter_U7_U2_In2.png`,
`03_afe_side_U1_U14.png`, `04_shunt_R48_U5.png`, `05_shunt_R91_U4.png`. Scripts:
- `export_polys.py` (kipy) writes the copper polygons to JSON; `plot.py` draws the renders.
- `overlap2.py` (kipy) measures the proximity and overlap between victim and aggressor nets.
