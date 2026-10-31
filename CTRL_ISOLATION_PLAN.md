# Control-card isolation on the baseboard (branch `ctrl-isolation`)

Status: plan only (2026-10-31), no design change yet. Based on main 2104b5b (v4 with fixes 1–12).
User decisions 2026-10-31: **done together with v5** (this branch is the v5 branch; see V5_PLAN.md),
**CTRL power from a dedicated winding on the v5 aux flyback** (option B). Total aux power about
15–20 W (user estimate). Decisions 2 (two islands) and 3 (CTRL bonded to PE) taken 2026-10-31; all decisions are taken.

Goal (user): the control card's domain becomes its own SELV domain **CTRL**, isolated by reinforced
barriers from the primary (GND/PGND: DC+ up to 450 V, mains) and from the isolated DC side
(ISOGND/ISOPGND: ISODC+ up to 450 V, AC output). The card's Ethernet and touchscreen are user
accessible. The **J11/J12 pinout, logic levels and analog scaling stay as they are**, so the existing
control card works unchanged. Coordinates: mm, IPC frame (Y up).

## 1. What changes today's design

`ISOGND` is the isolated DC link's negative rail: R97 (0 R) joins it to `ISOPGND`. Everything on
ISOGND, 3V3_ISO and 5V_ISOL is therefore at the potential of a 450 V power circuit, and today the card
plugs straight into it. The signals in J11 fall into three groups:

| Group | J11 pins | Today | With CTRL |
|---|---|---|---|
| Primary PWMs PWM_G1–G4, DAB_PWM_PRI_HI/LO, PWM_TRANS1–3 | 15–23 | U13/U16 (reinforced), A side on 3V3_ISO/ISOGND | **A side to 3V3_CTRL/CTRLGND** – no new isolator |
| Primary ADC/mux/relay SDATA1, CS1, CLK1, ADASEL0–2, ADCLK_ISO, MDATA_ISO, GPIO_BYPASS_RLY_ISOLATED | 6–14 | U13/U15, A side on ISO | **A side to CTRL** – no new isolator |
| ISO-side PWMs PWM_Q5–Q8, DAB_PWM_HI/LO_SEC, PWM_TRANS4–6, relay GPIO_BYPASS_RLY_ISO | 25, 27–31, 33, 35–37 | direct J11 → J4/J6/J8, R78/R88 | **new isolators**, 10 forward channels |
| ISO sigma-delta INU_ADCLK, MDATA_INU (U4), ADCLK_DAB, MDATA_DAB (U6) | 24, 26, 32, 34 | direct to U4/U6 digital side (ISOGND) | **new isolator** 2 forward + 2 reverse (see 1.2) |
| ISO analog ISOADA1–3 (U7A/U7B/U2 outputs, 8.2k + 4.7n/10n filters) | 1, 3, 4 | analog, ISOGND-referenced | **isolated amplifiers** |
| Grounds | 2, 5; J12 43/45/47 | ISOGND | **CTRLGND** |
| Card power | J12 44/46/48 | 5V_ISOL from U8 | **5V_CTRL** from a reinforced isolated supply |

### 1.1 Every part on ISOGND / 3V3_ISO / 5V_ISOL today, and where it goes

| Part(s) | Function | Domain after |
|---|---|---|
| J11, J12 | card connectors | **CTRL** |
| U13, U15, U16 (A side, pins 1–8), C82/C83/C86 | primary-side digital isolators | A side **CTRL**, B side primary as now |
| U4 (INU SDM, at (18.6, 41.8), bottom), U6 (DAB SDM, at (109.9, 27.4)) | AMC1306M05 modulators | digital side stays **ISO**, isolated through a new isolator (1.2) |
| U7 (OPA2353 → OPA2350 in the BOM), U2 (TLV316), their dividers R46/R51–R53/R56/R67/R68/R71/R256/R1/R76/R77/R82/R85, C95–C108, C101, C2 | ISO DC-link and VSI voltage measurement | **ISO** |
| REF2, R32, R40, C6, C110 (REF_1V65_ISO) | 1.65 V mid reference for U7/U2 | **ISO** |
| U10 (TPS73033), C3/C5 (3V3_ISO) | 3.3 V for the ISO analog parts and isolator ISO sides | **ISO** |
| U8 (K7805-2000R3), C4, C93, C94 (5V_ISOL) | 5 V for J4/J6/J8 pin 45 and U10 | **ISO**. It no longer feeds the card, so the 2 A upgrade is not needed for the card; 1 A is enough again |
| J4/J6/J8 pins 45/46 | gate-driver logic supply | **ISO** |
| Q13, R78, R88, C43 (relay R79 driver, at (−73, 14)) | relay drive | **ISO**, gate driven by a new isolator output |
| C15, C36, R49, TR2-6 (20V_ISO_SEC return), R97 | aux supply secondary, ISOGND–ISOPGND link | **ISO** |
| C37, C38, C56, C80, C87 | decoupling of U4/U7/U6/U2 | **ISO** |

### 1.2 Sigma-delta modulators U4/U6

The modulators are isolators themselves, so the cleanest option is to put their digital side
(DGND/DVDD/CLKIN/DOUT) on CTRL. The layout rules that out:
- U4 sits at (18.6, 41.8) inside the ISODC+ pour, about 30 mm from J11. CTRL traces cannot reach it
  with reinforced spacing.
- U6 sits next to the DAB shunt R64.

**So both stay ISO-referenced, and their clock and data cross a new 2 + 2 channel isolator.** This
adds about 2 × 12 ns to the clock-to-data round trip, the same as the primary modulator U5 already
has through U15. The firmware has to sample MDATA_INU/MDATA_DAB with the same phase offset it uses
for MDATA_ISO.

### 1.3 New parts (JLC stock 2026-10-31)

| Function | Part | JLC | Stock | Notes |
|---|---|---|---|---|
| ISO-side PWMs + relay (10 forward) | 2 × TI ISO7760FDWR | C2878538 | 3270 | 6 forward each, default output low, reinforced 5 kVrms, wide SOIC-16. 2 spare channels |
| U4/U6 clock + data (2 fwd + 2 rev) | Chipanalog CA-IS3742LW | C4944981 | 2115 | 2/2 channels, default low, reinforced. Alt.: TI ISO7742FDWR (C2862403, 78) |
| ISOADA1–3 | 3 × TI AMC1311BDWVR | C783598 | 7828 | isolated amplifier, 0–2 V input, gain 1, differential output, reinforced. Alt.: Chipanalog CA-IS1311BG (C42370078, 2817) |
| CTRL-side difference amplifiers | 2 × OPA2350EA (as U1/U7 in the BOM) or TLV9062 | C115876 / C398356 | 1114 / 55 014 | gain 2 back to 0–3.3 V around 1.65 V |
| 3V3_CTRL | TPS73033 (as U3/U10) | – | – | for the isolator CTRL sides, AMC1311 VDD2, op amps |
| 5V_CTRL for the card | see section 3 | | | |

**ISOADA scaling.** Today the J11 voltage is U7/U2's output (0–3.3 V around REF_1V65_ISO =
1.65 V) through 8.2k with 4.7n (ISOADA1/2) or 10n (ISOADA3).
- **ISO side:** keep U7/U2 and the filter, then divide by 2 (e.g. 10k/10k 0.1 %) into AMC1311 VIN.
  The 0–1.65 V input sits within its 0–2 V linear range. The divider changes the filter corner: set
  the series R to 4.1k so that 4.1k‖10k ≈ 2.9k with 4.7n/10n stays near today's 4.1/1.9 kHz, or keep
  8.2k and accept lower corners.
- **CTRL side:** a difference amplifier with gain 2 (0.1 % resistors), output referenced to CTRLGND,
  then the same 8.2k + 4.7n/10n output filter, so the card sees today's source.
- **Error budget:** AMC1311B gain error ±0.2 %, offset ±1.5 mV max (datasheet values to confirm),
  ×2 → about ±0.3 % ± 3 mV at J11, plus 0.1 % resistors. Calibratable.
- **Bandwidth:** AMC1311 ≈ 220–275 kHz, well above the 4.1 kHz filters.
- **Clipping:** the ×2 op amp on a 3.3 V supply clips the last ~50 mV at each rail with a
  rail-to-rail part. Today U7/U2 on 3V3_ISO have the same limit, so the usable range is unchanged.

## 2. Working voltages and creepage (IEC 61010-1, 2026-10-31)

**Standard: IEC 61010-1 (3rd ed. + A1), user decision 2026-10-31** (bench-top laboratory power
supply). The values below use the **IEC 60664-1 basis** that IEC 61010-1 Annex K builds on
(Table F.2 clearance, Table F.4 creepage, reinforced = 2 × basic). The standard text was not
available here, so **every number must be verified against IEC 61010-1 Annex K (K.1 mains circuits,
K.2 secondary circuits) before layout sign-off.** Assumptions: mains 230 V, OVC II (2.5 kV impulse),
PD2, ≤ 2000 m; bobbin plastic material group IIIa; FR4 CTI ≥ 175 (IIIa).

**Working voltages** (user 2026-10-31: the isolated DC link is ≤ 410 V, so the AC output peak is
≤ 410 V (≈ 290 Vrms sine); the primary DC+ stays ≤ 450 V for the 100–450 V input range. CTRL is
bonded to PE; both power domains move against PE). **User 2026-10-31: the output is always floating AC**, so the DC/earthed case below does not apply and B2 stays in the 500 V row. Whether an output terminal can be earthed was not
known yet, so both cases are given:

| Barrier | Floating output (only the output Y caps C29–C32 to PE) | Output earthed (through the Y caps' leakage path, the user or the load) | IEC 60664-1 row (RMS / DC working voltage) |
|---|---|---|---|
| B2 primary ↔ ISO | ISO domain centred on PE: ISOGND ≈ −205 V average, −410…0 V extremes; DC+ ≤ +450 V to PE. Peak ≈ 860 V, RMS ≈ 430–500 V | ISOGND = −(earthed pole voltage): −410…0 V. Same peak ≈ 860 V, RMS ≈ 430–500 V | **500 V row** (was 630 V); medium confidence, the RMS sits near the 500 V boundary. (The DC-output/earthed case, 1000 V row, does not apply: the output is always floating AC, user 2026-10-31.) |
| B3 primary ↔ CTRL (PE) | DC+ ≤ 450 V peak to PE, RMS < 450 V | same | **500 V row** (unchanged) |
| B4 ISO ↔ CTRL (PE) | ≤ 410 V peak (switching common mode included), RMS ≈ 205–290 V | ≤ 410 V peak, RMS ≤ 410 V (DC output) | **500 V row** (just above the 400 V row; unchanged) |
| B1 mains/primary ↔ accessible parts | mains 230 Vrms OVC II; DC+ ≤ 450 V | same | mains OVC II 300 V |
| B5 CTRL ↔ user parts (Ethernet, touchscreen) | same domain, PE-bonded, SELV | same | functional |

Insulation type: reinforced everywhere (user D3 for B2; for B3/B4, basic + PE bonding would satisfy
class I). IEC 61010-1 may only require basic between two hazardous-live circuits (B2); to confirm.

**Required distances** (IEC 60664-1 basis; confidence in brackets):

| Barrier | Clearance, reinforced | Creepage, reinforced: PCB (printed-wiring column, CTI ≥ 175) | Creepage, reinforced: other insulating material IIIa (bobbin, connector bodies) | Solid insulation, reinforced |
|---|---|---|---|---|
| B2, B3, B4 (500 V row) | ≥ 3.0 mm (2.5 kV OVC II impulse → 4 kV step; the ≈ 860 V recurring peak needs less) (medium-high; K.1.2 may add for working voltages above mains, so lay out ≥ 4 mm) | 2 × 2.5 = **5.0 mm** (medium) | 2 × 5.0 = **10.0 mm** (medium) | ≥ 0.4 mm single layer, or ≥ 2 thin layers each passing the full test voltage (3 layers: any 2) (medium) |
| ~~B2 if the output could be DC and earthed (1000 V row)~~ not applicable (floating AC output) | ≥ 3.0 mm | 2 × 5.0 = **10.0 mm** (medium-low) | 2 × 10.0 = **20 mm** (medium-low) | same |

- **Test voltage** (dielectric strength, reinforced, 1 min AC): ≈ 3 kVrms for mains OVC II 300 V,
  higher for the 500 V row working voltages (≈ 3.5–4 kVrms). Low confidence: verify in IEC 61010-1 6.8 and Annex K
  MKF's IEC 60664-1 figure is 2.7 kV; its IEC 62368-1 figure is 5 kV.
- **If IEC 61010-1 does not accept the printed-wiring column** for these working voltages, use the
  material-group column on the PCB too (10.0 mm for all three barriers). The board plan's ≥ 10 mm with
  slots covers that (the 20 mm DC-output/earthed case does not apply: floating AC output).
- **Slots** count as an interruption of the creepage path when ≥ 1.0 mm wide (IEC 60664-1, PD2).
- **MKF numbers** (reports/aux_flyback/insulation.py → insulation.txt): its IEC 60664-1 creepage is
  16 mm at 450–500 V and 25 mm at 630–800 V reinforced (IIIa, PD2). That is far above Table F.4 because
  MKF applies the high-frequency (> 30 kHz) creepage rules to the converter's 71 kHz waveform. Between
  the groups the voltage is mostly DC/50 Hz plus a ≈ 100 V switching swing, so Table F.4 governs.
  The HF rule must be checked for the swing amplitude only (small). Keep the MKF figure as an upper
  bound.
- **Digital isolators and AMC1306/AMC1311:** IEC 61010-1 ed. 3 asks for ≥ 0.4 mm internal distance
  through insulation, with relief for components certified to IEC 60747-17 / VDE 0884-11 (ADI note).
  Use parts with that certification (ISO7760F, CA-IS3742, AMC1311, AMC1306 are listed as reinforced
  per DIN EN IEC 60747-17; confirm each datasheet). Their 8 mm package creepage on CTI ≥ 600 mold
  compound covers 5.0 mm (group I at 500 V); the slot under each package is still needed for the FR4.

**PCB verdict:**
- **B3/B4 (CTRL islands):** the plan's ≥ 10 mm with slots meets the IEC 60664-1 basis in both cases:
  printed-wiring column 5.0 mm, material-group column 10.0 mm. **OK** (unchanged by the 410 V limit). Clearance ≥ 4 mm is met
  automatically.
- **B2 (primary ↔ ISO on the PCB):** the aux transformer's P/Out1 pads ↔ Out2 pads and the TR1
  terminals (DAB_PRI_x ↔ DAB_SEC_x) need **5.0 mm (printed-wiring column) to 10.0 mm (material-group
  column)** at the 500 V row; ≥ 10 mm (PCB) / 20 mm (other material) if the output can be DC and
  earthed. Lay out ≥ 10 mm, or slot. Check today's DAB terminal spacing on the v4 board as well.
- **Inner layers:** keep the same gap on In1/In2 unless the PCB is qualified for cemented joints. A
  domain on L1 must not overlap another domain on L2: the L1–L2 prepreg (≈ 0.2 mm) is below the
  0.4 mm reinforced solid-insulation thickness and is not two separately tested layers.
- **Slots:** ≥ 1.0 mm wide under every isolator and across each barrier where the copper gap is
  tight. The plan already says ≥ 1 mm.

**IEC 61010-1 checklist (beyond distances):**
- **Output terminals:** the AC output and the DC link are hazardous live (> 30 Vrms / 60 V DC).
  Use shrouded, finger-safe output terminals, with markings and a warning symbol.
- **Protective bonding:** PE bond resistance test (≤ 0.1 Ω at 25 A or 2 × rated current, per 6.5.2)
  covering the chassis, the CTRL island PE terminals and the Ethernet shield.
- **Touch current / protective-conductor current:** limits in 6.3. The Y capacitors and all barrier
  capacitances to PE add up; check the total.
- **Temperature limits (10.1):** surfaces, windings (insulation class) and components in the passively
  cooled chassis at the rated ambient (to define, e.g. 40 °C) and full load.
- **Fire enclosure, mains switch / fuse, X/Y capacitor ratings, marking and documentation.**
- **EMC:** IEC 61326-1.

The aux transformer verdict is in V5_PLAN.md 5.3 (core insulation needed). Rated ambient 30 °C (user
2026-10-31), internal air ≈ 50–60 °C assumed; the thermal notes are in V5_PLAN.md 5.1.

## 3. Power for CTRL

Load: the card up to ≈ 1.15 A at 5 V (efinix POWER_BUDGET.md high case; the existing Ti60 card
less), plus about 50 mA at 3.3 V for the isolator CTRL sides and the AMC1311/op amps. That is
**≈ 6–7 W**.

| Option | For | Against |
|---|---|---|
| **A. Reinforced DC/DC module** from 20V_ISO_SEC (or 20V), e.g. TRACO THM 10-2411WI (C5960531, 10 in stock: 9–36 V in, 5 V 2 A, 5 kVAC, medical 2 × MOPP) | drop-in, 31.8 × 20.3 × 10.2 mm DIP | medical modules are usually rated **reinforced for 250 VAC working voltage only**; check the THM 10 datasheet. That is below the ≈ 450–500 V needed here, so it is not compliant for this product. It is fine for bench work. RECOM REM10 is out of stock |
| **B. Dedicated CTRL winding on the v5 aux flyback** (V5_PLAN.md) | designed for the real working voltage. Three isolation groups: {primary, Out1, bias}, Out2 (ISO), CTRL | v5 work. The EE25 must now carry three reinforced groups (margins/TIW), so a bigger core may be needed |
| C. Reinforced module rated for ≥ 500 V working (industrial gate-drive-class DC/DCs with high VIOWM) | compliant, if found | none found in stock at JLC; needs a distributor search |

**Recommendation: B for the product, A for the first boards and bench tests.** The v4 aux supply
(IW1830/EF20) would carry another ≈ 7–8 W on 20V_ISO_SEC in option A, the same load concern as for
the U8 upgrade. U8 itself drops back to the gate-driver logic and U10 only.

## 4. Board feasibility

The control card covers x 42.6 … 118.6, y −18.8 … 46.4 (efinix MECHANICAL.md). On the board that
area is:
- In1 = **ISOGND plane** and In2 = **3V3_ISO plane** over most of it.
- The primary logic area (GND on In1, VCC on In2) in its lower-left part, x 42.5 … 85.5,
  y −20.7 … 15: U11, AD1, U12, U14, U1, REF1.
- ISO analog parts inside it: U7 (79.5, 38.2), U2 (91.8, 35.9), REF2 (111.2, 10.3), U10 (112.1, −4.4),
  U6 (109.9, 27.4), R64.

Renders: `reports/ctrliso/card_area_{F,B,In1,In2}.png`.

**Two CTRL islands,** because J11 and J12 are ≈ 70 mm apart with ISO and primary copper between them.
A CTRL corridor with 9–10 mm clearance on each side across all four layers is not practical.
- **Island A around J11** (46.2, 22.6): J11, the A sides of U15 (56.0, 18.3), U13 (68.0, 18.3) and
  U16 (81.8, 14.0), the two new ISO7760F, the CA-IS3742LW, the three AMC1311 low sides, two op amps
  and a 3V3_CTRL LDO. About 45 × 35 mm.
  - It needs its own 3.3 V supply, because J11 has no power pin: a small reinforced DC/DC
    (≈ 0.5 W), or the 3.3 V from the island B supply if a corridor turns out possible.
  - CTRLGND of island A connects to island B only through the card (J11 pins 2/5 and J12 pins
    43/45/47 are the same ground on the card). That is one domain with a single connection, so no
    loop through the baseboard.
- **Island B around J12** (114.1, −15.7): J12 and the CTRL DC/DC output. The module has to sit
  outside the card outline (y < −18.8, near U8) because of its height.

**Moves and re-cuts:**
- U7/U2 and their dividers/filters, REF2, U6's digital side and U10 move out of island A, or
  island A is shaped around them with 9–10 mm spacing.
- The In1/In2 planes are re-cut on all four layers: CTRL planes under islands A/B, ISO planes for the
  ISO analog, the existing primary GND/VCC area kept.
- Slots go under every isolator.
- The existing GND ↔ ISOGND gap under U13/U15/U16 (≈ 6–7 mm on In1) must grow to the reinforced
  distance.
- The ISODC+ pour on F.Cu/B.Cu reaches x ≈ 43 next to J11 and must be pulled back ≥ 9–10 mm from
  island A.
- The ISO-side PWM bundle (today J11 → J4/J6/J8) is re-routed from the ISO7760F outputs at island A's
  top edge to J4/J6/J8 at y ≈ 50–52.

**Verdict:** the schematic change is moderate: about 10 new ICs, ~30 passives and re-domained nets
on sheets 2, 3, 4, 5, 8, 10 and 11. The board is a **full re-layout of the ≈ 76 × 65 mm logic area
on all four layers in the KiCad GUI**: the copper of fixes 2/3/11/12 there, the ISO measurement
placement and both planes. It is v5-sized work and best done together with v5, which brings the
CTRL winding (option B) and also changes the area around U8/J12. The frozen-board script approach
(tools/v4) does not fit this; record it as a GUI re-layout.

## 5. Steps

1. **User decisions** (section 7).
2. **Schematic on this branch:**
   - new nets CTRLGND/3V3_CTRL/5V_CTRL
   - re-domain J11/J12 and the U13/U15/U16 A sides
   - new isolators, AMC1311 chains, LDO and DC/DC
   - a `ctrliso` deviation list (net renames and new parts) so that compare/check_board/ipc356_diff
     keep checking the rest against Proteus
   - ERC 0 errors
3. **Footprints:** all the new parts are in the KiCad library (SOIC-16W, SOIC-8W, VSSOP-8, SOT-23-5);
   the DC/DC module needs a project footprint. Add slots (Edge.Cuts or a board-level NPTH slot
   footprint) under each isolator.
4. **Board (GUI):** islands, plane re-cuts, slots, the new placement and routing. Net classes for
   the reinforced gaps (DRC: custom rules `(condition "A.NetClass != B.NetClass")` per domain pair).
   Record it in STATUS.md.
5. **Checks:** ERC, check_all with the deviations, DRC including the new domain-clearance rules,
   renders, and a creepage review of every boundary, inner layers included.

## 6. Risks

- **Timing:** the sigma-delta round trip for U4/U6 becomes +2 × ≈ 12 ns (like U5 today). The PWM
  edges get ≈ 11 ns common delay and a few ns channel skew, negligible for dead time at 30/66 kHz.
- **Fail-safe:** all new isolators default low. With the CTRL side unpowered the PWMs are off, which
  matches today's U13/U15/U16 behaviour.
- **ISOADA accuracy:** ≈ ±0.3 % ± 3 mV added. Recalibrate.
- **Card ground:** CTRLGND floats unless the user ties it to PE through the chassis. Decide (section 7).
- **Power:** option A is not compliant at this working voltage (250 VAC-class modules); the v4 aux
  load grows by ≈ 7–8 W.

## 7. Decisions for the user

1. **CTRL power – B, the v5 winding** (user, 2026-10-31). The THM 10-2411WI stays an option for bench
   boards only.
2. **Islands – two CTRL islands** (user, 2026-10-31): island A around J11 with the isolators and its
   own small 3.3 V supply, island B at J12 with the card supply. They are joined through the card's
   ground.
3. **CTRL earthing – bonded to protective earth** (user, 2026-10-31). Consequences for the design:
   - **Bonding:** a PE terminal (or a PE pad bolted to the chassis) on **each** island, so neither
     relies on the card's ground for its bond. Size the bond as a protective bonding conductor:
     trace width and the fault current from the barrier side, per IEC 62368-1 5.6 / IEC 62477-1.
     The existing PE terminals (PE1–PE8) are on the power side; add new ones at the islands.
   - **Barriers stay reinforced,** as decided. Earthing adds a further safeguard. The standards
     could accept basic insulation plus protective earthing, but the plan keeps reinforced, so the
     card stays safe even if the PE bond is missing.
   - **Leakage current:** the barrier capacitances (isolators, AMC1311, transformer interwinding)
     now return the switching common-mode current of ISOGND and GND to PE. Check the touch-current
     limit (≈ 3.5 mA for pluggable type A equipment), and keep any Y capacitors from the power
     domains to PE within it.
   - **EMC benefit:** the card's ground and the Ethernet shield are at earth potential, not jumping
     with the inverter's switching.
4. **Schedule – together with v5** (user, 2026-10-31).
