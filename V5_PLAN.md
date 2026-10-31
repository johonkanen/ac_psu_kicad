# v5 plan – aux flyback redesign (INN3694C, EE25, 2 x 15 V)

Status: plan only (2026-10-24), no design change yet; to be acted on later. User decisions taken
2026-10-24: D1 yes, D2 15 V is fine, D3 reinforced, D5 in place on the main board, D6 rename. D4
(controller sourcing) is still open. The converter and transformer design are
in `reports/aux_flyback/README.md` (commit 965a78b). This file says how to bring that design
into the KiCad project, and which questions need answers first. Coordinates: mm, IPC frame (Y up).

## 1. What sheet 7 does today (v4)

| Rail | Made by | Return | Loads |
|---|---|---|---|
| `20V` | IW1830 PWM1, aux winding TR2-3 → D2, C28/C41; regulates through `AUX_FB` (primary-side sensing) | `GND` | J1/J2/J3 pin 48 (primary gate drivers), U9 → `5V`, relay R20 coil via Q14, D10 |
| `20V_ISO_SEC` | TR2-7 → D1, C36/C15, R49 preload (cross-regulated) | `ISOGND` | J4/J6/J8 pin 48 (isolated-side gate drivers), U8 → `5V_ISOL`, relay R79 coil via Q13, D4 |
| `5V` | U9 (VXO7805), C67/C58/C57 | `GND` | J1–J3 pin 45, U3, … |

`GND` is the DC-link negative: R96 (0 R, sheet 4) joins `GND` and `PGND`. The flyback primary
(PWM1, TR2-4) and the 20 V output therefore already share one reference. Only `20V_ISO_SEC`
crosses the DC ↔ ISO barrier, the same barrier as the DAB transformer TR1 and the
ADuM7701 / Si866x isolators.

The sheet 7 parts take up about x 70…107, y −60…−13. TR2 (EF20, 2 × 5 pins, P 3.81) is at
(87.5, −28.4) and PWM1 (DIP-8) at (75.8, −37.8). DC+ (up to 500 V) runs through the area.

## 2. Findings that change the README design

1. **Isolation sides.** The README models the transformer as primary | Out1 | Out2 | bias, with
   reinforced insulation from the primary to both outputs. On this board:
   - Out1 replaces `20V` (return `GND` = DC−), so it is in the primary domain. Primary ↔ Out1
     needs no insulation at all.
   - Out2 replaces `20V_ISO_SEC` on `ISOGND`. The barrier that matters is
     {primary, Out1, bias} ↔ Out2, and it must be reinforced (D3).

   Re-run `transformer.py` with isolation sides [primary, primary, secondary, primary]. Out2 then
   needs reinforced margins and 3-layer tape on both of its faces. The primary ↔ Out1 barrier
   becomes functional, so P1 → Out1 can be wound without margins. That frees winding width,
   which may allow wider margins on Out2 for the IEC 60664-1 caveat in the README. The
   reinforced barrier on the board, through the transformer and the slot, must match the
   ADuM7701 / Si866x / TR1 barrier around it.
2. **The InnoSwitch secondary side sits on Out1.** The secondary controller (SR FET drive, FB,
   VOUT pins) is referenced to Out1's return, which is `GND`, the same node as the primary
   `SOURCE`. That is allowed. The IC's internal FluxLink isolation is then simply unused between
   primary and Out1, so the "pending UL1577 / IEC 60747-17" note in the README no longer matters.
   An alternative is a primary-side-regulated part with the same transformer (decision D4).
3. **Relay coils.** R20 and R79 (SLA-12VDC-SL-A, 12 V coil) run from the rails through a
   2N7000 with no series resistor. With the two 15 V rails that is 125 % of the rated coil
   voltage (v4: 167 % at 20 V). The user considers this acceptable; check the relay's maximum
   coil voltage once.
4. **15 V instead of 20 V** at the HB GT connectors' pin 48 is only a problem if the gate-driver
   boards need more than 15 V (decision D2). U8/U9 (VXO78, 6.5–36 V input) are fine with 15 V.
5. **Stock.** INN3694C is JLC C567564, with 0 in stock on 2026-10-23. Neither the KiCad library nor
   JLC's basic parts have the InSOP-24D footprint or an EE25 10-pin bobbin footprint; both must be
   project footprints from the datasheets. The transformer is custom-wound, so JLC cannot assemble
   it: hand-fit it, like TR2 today.

6. **Out2 power is too small for the new control card.** The efinix-soc-board session asks for
   U8 (5V_ISOL) to be upgraded to 1.5–2 A for the Ti135 control card (0.72 A typical, 1.15 A
   high at 5 V; `~/dev/efinix_soc_board/POWER_BUDGET.md`). On Out2 (`15V_ISO`) that is U8 at
   up to about 7–8 W (1.45 A at 5 V with the gate-driver logic and U10, at 89–92 % efficiency),
   plus the J4/J6/J8 gate-driver supplies and the R79 coil (≈ 0.5 W). That exceeds the README's
   10 W per output. Re-balance the outputs before step 1 (for example Out2 13–14 W, Out1 6–7 W,
   or a larger total), and re-check the INN3694C's power rating, ILIM and the core.

## 3. Decisions (D1–D3, D5, D6 answered 2026-10-24; D4 2026-10-30)

- **D1 Output mapping – yes:** Out1 (regulated) → `20V`, renamed `15V`, on `GND`; Out2
  (cross-regulated) → `20V_ISO_SEC`, renamed `15V_ISO`, on `ISOGND`.
- **D2 – 15 V is fine** for the gate-driver boards on J1–J8 (pin 48), so `params.py` keeps
  VOUT = 15 V.
- **D3 – reinforced** between {primary, Out1, bias} and Out2 (finding 1), in the transformer and
  on the board.
- **D4 Controller – TI UCC28710 with an external 950 V MOSFET** (user, 2026-10-30), instead of the
  INN3694C (0 stock at JLC). Details in section 5. The iW1830 has 0 stock at JLC, and its 700 V
  switch is too close to 450 V DC plus VOR plus the leakage spike.
- **D5 – in place on the main board:** it replaces the aux supply. Delete the sheet 7 copper,
  then re-place and re-route the area in the KiCad GUI, with a slot under the transformer and IC.
- **D6 – rename** `20V` / `20V_ISO_SEC` to `15V` / `15V_ISO`. This touches sheets 1, 2, 3, 5, 7
  and 10, the deviation files and the checks; the renamed nets go into the v5 deviation list.

## 4. Steps (after the decisions)

1. **Transformer re-check.** Update `params.py` and `inputs.py` for D1–D3 (isolation sides,
   insulation class, output voltages), re-run `inputs.py` and `transformer.py`, and update the
   README tables. Check Out2 cross-regulation at the real load split. Out2 feeds the U8 module
   and the relay coil: keep a preload, or accept 16–17 V at light load if both are fine with it.
2. **Circuit.** Base it on PI's INN3694C datasheet application circuit and the README "Around
   the transformer" section:
   - input: DC+ → small RC/π filter, bulk capacitor rated ≥ 630 V (stacked 1206 parts at 500 V
     need a voltage rating to match)
   - clamp: 180–200 V TVS plus a 1000 V fast diode
   - BPP 0.47 µF; bias winding → 200 V diode → BPP resistor
   - Out1: SR MOSFET ≥ 150 V, FB divider 100 k / 9.09 k, low-ESR output capacitors ≥ 25 V
   - Out2: 150–200 V Schottky/ultrafast diode, output capacitors, preload
   - a Y1 capacitor across the DC ↔ ISO barrier only if D3 allows it (it bridges the barrier
     the ADuM7701s isolate; check the measurement noise effect)

   Write it as a new `tools/sheets/sheet07.py` (the v4 one stays in git history). Keep the 5 V
   capacitors C67/C58/C57, C68 and the rail flags. Remove PWM1, TR2, R43/R34/R33, D7, C65/C66,
   R24/C62/R23/D6, R44/R25/C63/R26/R29/R31, R45/R47, D2, D1, R49. New refdes continue from
   C111 / R98 / D11 / U18 / T3 (check that they are free; C95–C110 are fix 11).
3. **Library.**
   - Symbols in `tools/gen_symbols.py`: INN3694C with all InSOP-24D pins, and the EE25 transformer
     (10 pins, winding dots, one unit, pin numbers as on the bobbin).
   - Project footprints in `tools/gen_footprints.py` (`from_ipc`-style builder from datasheet
     coordinates): `InSOP-24D` (PI package drawing, with its creepage slot) and
     `Transformer_EE25_Norwe_10165-106` (pin pitch, row spacing, holes and body from the Norwe
     drawing; slot between the rows if D3 needs it).
   - Part map rows and `fab/jlc_bom.csv` codes.
4. **Deviation framework.** v5 replaces a whole block, so per-pin deviation rows are the wrong
   tool. Add `lib/v5_deviations.csv` with `removed_part` rows (the v4 parts above) and a
   `replaced_block` area (the aux copper area, every layer). Teach `tools/deviations.py`,
   `compare_netlists_v4.py`, `check_board.py`, `ipc356_diff.py` and `gerber_roundtrip.py` to skip
   removed parts and their pins, nets that exist only inside the block, and copper clusters
   inside the area. Everything outside the block keeps the Proteus parity checks. Negative-test
   it: a part outside the block that is removed or renetted must still fail.
5. **Board (D5: in place).** A `tools/v5/` script deletes the removed footprints and the copper
   inside the area, then places the new footprints at agreed positions. Routing, pours and the
   slot are done in the KiCad GUI and recorded in STATUS.md, which ends the "frozen board edited
   only by scripts" rule for this area.

   A net class `HV_AUX` sets the clearance for DC+, the drain node and the clamp (500 V working:
   ≥ 2.5 mm on external layers). The reinforced creepage between the GND and ISOGND domains is
   kept across the transformer, the slot and the Out2 copper, including on the inner layers.
   Check the space first: the EE25 bobbin is larger than the EF20, and the InSOP-24D needs
   its own slot.
6. **Checks.** ERC, `tools/check_all.sh` (with the v5 deviations), DRC with the new net class,
   `tools/regen_check.sh`, renders of the area, and the JLC BOM/CPL refreshed.
7. **Bring-up** (README): measure Lp (MKF predicts +12 %), the drain peak at 500 V, the clamp
   temperature, and Out2 at light and full load.

## 5. Controller: UCC28710 + external MOSFET (D4)

Why: primary-side regulation (PSR) like the present iW1830 design: the output is sensed through
the bias winding, so there is no optocoupler across the reinforced barrier. The external MOSFET
removes the 700–725 V switch limit of the integrated parts, and the 700 V high-voltage start-up
switch (DC+ ≤ 450 V) replaces the R43/R34/R33 start-up chain. ±5 % CV/CC regulation, up to
100 kHz, clamped MOSFET gate drive, SOIC-7. JLC C80866 (UCC28710DR), 381 in stock on 2026-10-30.
The UCC28712 is pin-compatible (fixed cable compensation) and could serve as a second source.

MOSFET (primary peak current ≈ 0.8–1 A at 20–25 W; RMS ≈ 0.2 A at 400 V, ≈ 0.45 A at 100 V;
drain peak ≈ 450 V + VOR ≈ 104 V + clamp overshoot, so ≈ 700–750 V with a 180–200 V TVS clamp,
which needs ≥ 950 V parts):

| Part | Package | Rds(on) at 10 V | JLC / stock 2026-10-30 | Note |
|---|---|---|---|---|
| Infineon IPN95R2K0P7 (only if the input stays ≥ 300 V; see 5.1) | SOT-223 | 2.0 Ω | C3278575 / 75 | Smallest; CoolMOS P7, 330 pF Ciss, 10 nC. ≈ 0.1 W conduction at 400 V, ≈ 0.4–0.8 W at 100 V hot: needs a copper area of ≈ 1–2 cm² on the drain tab, which is the switch node (keep it small for EMI; use the source side and a thermal pad). |
| Infineon IPN95R3K7P7 | SOT-223 | 3.7 Ω | C3278582 / 172 | More stock, twice the conduction loss. |
| ST STD6N95K5 | DPAK (TO-252) | 1.25 Ω | C455168 / 112 254 | Large stock and lower loss, with a bigger tab (≈ 6.6 × 6.1 mm). The fallback if the SOT-223 parts run out. |
| Infineon IPD95R1K2P7 | DPAK | 1.2 Ω | C536916 / 1528 | Same class as STD6N95K5. |

Check in the datasheets before the circuit step:
- the UCC28710 DRV drive against the MOSFET Qg (10–15 nC is fine at ≤ 100 kHz)
- the minimum demagnetisation time for its PSR sampling against the EE25 leakage (20.6 µH)
- the bias-winding voltage range (VDD), then pick NB to suit
- the maximum power the TI design calculator gives at VIN 100–450 V

With PSR, Out1 is no longer the regulated rail. Both 15 V outputs are cross-regulated through the
bias winding, as 20V/20V_ISO_SEC are today, so the transformer coupling (MKF leakage) sets the
accuracy. Keep a preload on both outputs.

Step changes for this choice: step 2 follows the UCC28710 application circuit (no SR MOSFET and no
FB divider on Out1; a VS divider from the bias winding, a CS resistor, a 950 V MOSFET, and diodes on
both outputs). Step 3 drops the InSOP-24D footprint (SOIC-7 and SOT-223 are KiCad library
footprints).

### 5.1 Full power at 100 V, passive cooling (user, 2026-10-30)

DC+ is rated 100–450 V, and the aux supply must deliver full power at 100 V: the control card
(FPGA, Ethernet, LCD), the 5 V logic and all the gate-drive supplies. The supply is passively
cooled inside a closed chassis.

**Power budget (estimate, to confirm).** Output side:

| Load | Estimate |
|---|---|
| Out2: U8 (card 5.8 W high case + gate-driver logic + U10) / 0.9 | ≈ 7–8 W |
| Out2: J4/J6/J8 gate-drive supplies | ≈ 3 W |
| Out2: R79 coil | 0.5 W |
| Out1: J1–J3 gate drives | ≈ 3 W |
| Out1: U9 5 V logic | ≈ 1–2 W |
| Out1: R20 coil | 0.5 W |

Each gate-driver board is assumed at about 1 W. The SiC gate charge itself is only ≈ 20–40 mW per
switch at 30/66 kHz; the drivers' isolated DC/DCs dominate. The total is **≈ 15–20 W, so design for
25 W output (≈ 29 W input) at 100 V.**

**The README transformer cannot do that.** The UCC28710 is primary-side regulated and needs DCM:
on-time plus demagnetisation time must fit in the switching period.
- With VOR ≈ 104 V at 100 V input, the DCM boundary is D ≈ 0.51.
- The maximum input power is then (Vin·D)² / (2·Lp·fsw) = 51² / (2 · 1.19 mH · 70 kHz) ≈ 15.6 W.

Redesign for:
- **Lp ≈ 0.5–0.6 mH** at 70 kHz (≤ 0.64 mH at the boundary, with margin for the PSR sampling
  window).
- **Or a higher VOR** (≈ 130–150 V gives D ≈ 0.57–0.6 and allows ≈ 0.7–0.9 mH). The drain peak then
  rises to ≈ 450 + 150 + overshoot ≈ 780 V, still under 950 V. Choose by the transformer losses.
- Primary at 0.5 mH: Ipk ≈ 1.46 A, Irms ≈ 0.6 A, stored energy ≈ 0.53 mJ per cycle.
- On EE25 (Ae ≈ 52 mm²) at 0.3 T that is ≈ 47 primary turns and a gap of ≈ 0.3 mm. It is feasible,
  but re-run MKF for copper and core loss at 100 V in a hot enclosure.
- If the losses come out over ≈ 1.5 W, step up to E30/EF25.

**MOSFET for continuous 100 V operation.** Hot Rds(on) is about 2.2 × the 25 °C value; the
switching loss is ≈ 0.25 W turn-off at 250 V / 1.46 A.

| Part | Package | Rds(on) 25 °C | Conduction loss hot at 100 V | JLC / stock 2026-10-30 |
|---|---|---|---|---|
| **Infineon IPD95R450P7** | DPAK | 0.45 Ω | ≈ 0.36 W | C3289115 / 112 |
| Infineon IPD95R750P7 | DPAK | 0.75 Ω | ≈ 0.6 W | C536918 / 97 |
| ST STD6N95K5 | DPAK | 1.25 Ω | ≈ 1.0 W | C455168 / 112 254 (fallback) |
| ST STB20N95K5 | D2PAK | 0.275 Ω | ≈ 0.2 W | C500935 / 895 (if DPAK runs hot) |
| ~~IPN95R2K0P7~~ | SOT-223 | 2.0 Ω | ≈ 1.6 W | too hot for 100 V continuous; dropped |

Choose the IPD95R450P7, about 0.6 W in total. Its tab is the drain, i.e. the switch node, so
keep that copper small: cool it through a source-side and inner-layer copper spread with thermal
vias, not a large drain pour. Check the 35 nC Qg against the UCC28710 DRV current.

**Thermal budget in the closed chassis:**
- FET ≈ 0.6 W, clamp ≈ 1–1.3 W (more at the higher Ipk), transformer ≈ 1–1.5 W, output diodes
  ≈ 0.5–0.8 W: ≈ 3.5–4 W in the aux area.
- Give the clamp TVS and the diodes copper too.
- Measure the internal air temperature on the v3 build, then check the N87 core loss, the
  electrolytic capacitor life and the U8 K7805-2000R3 derating (the 5 V version derates from
  ≈ 55–71 °C ambient).

### 5.2 CTRL winding and control-card isolation (user, 2026-10-31)

v5 includes the control-card isolation in `CTRL_ISOLATION_PLAN.md`. The card domain (J11/J12)
becomes CTRL, isolated by reinforced barriers from both power sides, so the card's Ethernet and
touchscreen are SELV. The card's 5 V comes from a **dedicated CTRL winding** on this flyback. The
transformer now has **three reinforced-separated groups**:
- {primary, Out1 (`15V`, GND; also the PSR sense and VDD winding since 5.3)}
- Out2 (`15V_ISO`, ISOGND)
- CTRL (5 V, card ≈ 6–7 W)

Margins or TIW are needed on both of the last two. Re-run MKF with isolation sides
[primary, primary, secondary, tertiary, primary], and expect the EE25 to become too small: check
E30 / EF25 / EFD30 with the 100 V full-power design point of 5.1.

**Power (user estimate):** about 15–20 W in total; the 25 W design point of 5.1 covers it. With
CTRL taking the card, Out2 drops back to the gate-driver supplies, U8 (now only the gate-driver
logic and U10) and the R79 coil, ≈ 4–5 W. Rebalance the outputs: Out1 ≈ 5–6 W, Out2 ≈ 4–5 W, CTRL
≈ 7 W, with margin.

**Regulation:** PSR regulates the bias winding (since 5.3: Out1 itself, no separate bias winding). CTRL is cross-regulated like the others, so put a
local regulator (buck or LDO) after the CTRL winding if the card needs a tight 5 V. Choose the
CTRL winding voltage to suit, e.g. ≈ 7–8 V into a buck.

**Why not the iW1830** (user question 2026-10-31): Renesas rates it at 12–15 W maximum, for AC input
(85–264 VAC, ≈ 120–375 V DC). Its integrated MOSFET is 700 V, but here the drain peak at 450 V DC is
≈ 700–780 V. And JLC has 0 in stock. The UCC28710 (section 5) is the same kind of controller
(primary-side regulation from the bias winding, no optocoupler), but drives an external 950 V
MOSFET, so the power is set by the transformer and the MOSFET.

### 5.3 Transformer (run 2026-10-31, revised to 20 W on EE25, no bias winding)

Details, candidates and scripts: `reports/aux_flyback/` (README.md, params.py, inputs.py,
transformer.py, report.txt, winding.svg). This supersedes the INN3694C/EE25 numbers above. The
25 W / E30/15/7 design (commit 3b4a33d) is kept in the README as the alternative.

**Electrical design** (UCC28710, 100–450 V, full power at 100 V; user: 20 W):
- **Design load ≈ 20 W:** Out1 15 V 0.39 A (load + ≈ 20 mA VDD), Out2 15 V 0.33 A, CTRL ≈ 9 V 1.0 A
  (into a 5 V buck). **No separate bias winding** (user, 2026-10-31).
- **VOR 100.5 V:** the 100 V DCM limit sets it.
- **Lp 322 µH, Ipp(max) 1.39 A, RCS 0.562 Ω** (user 2026-10-31: lowered from 0.590 Ω for CC margin).
- **Full load (19.8 W) at 71 kHz:** at 100 V, the on-time, demagnetisation and ring take 0.70 of the
  period.
- **CC limit:** 27.9 W typ; **23.0 W worst case** (fSW(max) 92 kHz and VCST 738 mV).
- **Drain peak:** 450 + 240 V clamp = 690 V (73 % of 950 V).
- **Light load at 450 V:** tDMAG(min) ≈ 1.25 µs (TI target 1.2 µs).

**Core:** E25/13/7 N87, gap ≈ 0.22 mm for AL ≈ 314 nH (choose the TDK B66317 gapped half or grind).
**Bobbin:** Norwe 10165-106 (EE25 horizontal, longer creepage, 5 + 5 pins at 5.08 mm); alternatives
Norwe 10220-024 / 10175-106. Confirm the drawing.

| Winding (inside → out) | Turns | Wire |
|---|---|---|
| P1 | 16 | 0.40 mm Grade 2 |
| CTRL | 3 | 3 × TIW 25 AWG (Rubadue TCA3) in parallel, **flying leads** |
| Out1 | 5 | 0.63 mm Grade 2 (PSR sense + VDD) |
| P2 | 16 | 0.40 mm Grade 2 |
| Out2 | 5 | TIW 24 AWG |

Order O2 out of four compared: the lowest clamp-effective leakage (5.9 µH), Out1 between the
primary halves (P→Out1 6.1 µH), and CTRL tightly coupled to Out1 (0.06 µH).

**Out1 as the PSR sense and VDD winding** (user, 2026-10-31; details in the README):
- **VS divider** from the Out1 winding node before its diode: RS1 59.0 k, RS2 21.0 k, cable
  compensation RCBC ≈ 118 k (+0.25 V at full load). The controller regulates Out1 directly; Out2 and
  CTRL cross-regulate against it.
- **VDD** from the 15 V rail via BAS16 + 47 Ω, ≈ 14.3 V. CDD 15 µF (TI eq. 24: ≥ 12.9 µF for a 20 ms
  start into ≈ 2200 µF total output capacitance). Start delay ≈ 1.3 s typ, 4.9 s worst at 100 V.
- **An output short** collapses VDD: hiccup (≈ 30 ms on per 1–5 s), thermally safe.
- **Gate drive:** DRV ≈ 13 V, so the FET is fully on (its Rds(on) is rated at 10 V). DRV sources only
  20–25 mA, so add an MMBT3904/3906 buffer for the 35 nC gate (or use the IPD95R750P7, 23 nC).
- **VS knee:** the leakage reset is ≈ 60 ns (TI limit 2.2 µs). The ringing must be < 100 mVpp at VS by
  ≈ 1.05 µs at 450 V no load (tDMAG(min) 1.25 µs); add an RC snubber on the Out1 diode if needed.

**Pins:**
- **Primary row:** drain, DC+, empty (the freed bias pin), GND, Out1.
- **Secondary row:** Out2+, ISOGND; pins 8–10 cut.
- **CTRL:** TIW flying leads from the pin-10 end of the secondary flange to two Ø 1.6 mm holes
  (pads Ø 3.0 mm, 5.08 mm apart) in the CTRL island, ≥ 10 mm from the Out2 pins, the primary row and
  the core.
- **The core is floating:** the flange distances from the pins to the core count (IEC 62368-1 5.4).

**Insulation (MKF, 500 V working):**
- IEC 62368-1 reinforced: creepage 3.1 mm, clearance 5.5 mm (met).
- IEC 60664-1 / IEC 62477-1 reinforced: 16 mm over the bobbin material. Not reachable on an EE25
  without impregnation or potting.
- PCB: ≥ 10 mm with slots, per the board plan.

**Losses (MKF):** 0.61 W at 100 V, 0.87 W at 450 V. Peak flux 280 mT. ≈ 78–86 °C at the assumed
60 °C chassis air. Aux area total at 100 V full load ≈ 2.6 W (clamp 0.7 W, MOSFET 0.4 W, diodes
≈ 0.9 W).

**Board footprint:** ≈ 28 × 26 mm plus the CTRL hole zone (≈ 800 mm² in total). That is ≈ 2.6 ×
today's EF20 and ≈ 25 % less than the E30 alternative (≈ 35 × 31 mm).

**Rest of the stage:**
- clamp TVS ≈ 200 V class + 1000 V fast diode
- Out1/Out2: 200 V ultrafast 1–2 A
- CTRL: 100 V Schottky 3 A
- VDD feed: BAS16 + 47 Ω, CDD 15 µF / 50 V; gate buffer MMBT3904/3906
- output capacitor RMS: Out1 0.71 A, Out2 0.62 A, CTRL 1.86 A
- preloads: Out2 ≈ 3 mA, CTRL ≈ 10 mA
- cross-regulation against Out1: Out2 14.7–15.3 V; CTRL ≈ 8.9–9.3 V loaded, ≈ 10.5–11.5 V at no load;
  CTRL buck ≥ 17 V input

**Open items:**
1. measure the chassis air temperature
2. wind a sample and measure Lp, the leakage, and the VS waveform at 450 V no load
3. source certified TIW
4. confirm the E25 gap (AL 314 nH) and the Norwe 10165-106 drawing (flange creepage, CTRL lead exit)
5. confirm the 500 V working voltage
6. decide the standard (IEC 62368-1 vs IEC 62477-1)
7. trim RS2 / RCBC and check the VS ringing, the start-up and the gate buffer on the prototype
   (decided 2026-10-31: MMBT3904/3906 buffer, RCS 0.562 Ω → CC worst case 23.0 W)

## 6. Not part of v5

v4 clean-up and manufacturing items (C67, silk positions, pad decisions, JLC alternatives, CPL)
continue separately on the v4 board. Sheet 7 parts that v5 replaces (iW1830, EF20 TR2 and so on)
get no JLC alternatives.
