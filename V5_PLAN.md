# v5 plan – aux flyback redesign (INN3694C, EE25, 2 x 15 V)

Status: plan only (2026-10-24), no design change yet. The converter and transformer design are
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
   - Out2 replaces `20V_ISO_SEC`. Its barrier to the primary is DC ↔ ISO, whose rating is set by
     TR1 and the isolator ICs, not by the IEC 62368-1 reinforced figure.

   Re-run `transformer.py` with isolation sides [primary, primary, secondary, primary] and the
   DC ↔ ISO insulation class (decision D3). This may remove two of the three margin-tape
   barriers and free winding width.
2. **The InnoSwitch secondary side sits on Out1.** The secondary controller (SR FET drive, FB,
   VOUT pins) is referenced to Out1's return, which is `GND`, the same node as the primary
   `SOURCE`. That is allowed. The IC's internal FluxLink isolation is then simply unused between
   primary and Out1, so the "pending UL1577 / IEC 60747-17" note in the README no longer matters.
   An alternative is a primary-side-regulated part with the same transformer (decision D4).
3. **The relays are already overdriven.** R20 and R79 (SLA-12VDC-SL-A, 12 V coil) run from 20 V
   through a 2N7000 with no series resistor: 167 % of the rated coil voltage. At 15 V it is
   125 %. Check the relay's maximum allowable coil voltage, or add a series resistor (in v5 or a
   v4 fix).
4. **15 V instead of 20 V** at the HB GT connectors' pin 48 is only a problem if the gate-driver
   boards need more than 15 V (decision D2). U8/U9 (VXO78, 6.5–36 V input) are fine with 15 V.
5. **Stock.** INN3694C is JLC C567564, with 0 in stock on 2026-10-23. Neither the KiCad library nor
   JLC's basic parts have the InSOP-24D footprint or an EE25 10-pin bobbin footprint; both must be
   project footprints from the datasheets. The transformer is custom-wound, so JLC cannot assemble
   it: hand-fit it, like TR2 today.

## 3. Decisions for the user (answer before step 4)

- **D1 Output mapping:** Out1 (regulated) → `20V`, renamed `15V`, on `GND`; Out2 (cross-regulated)
  → `20V_ISO_SEC`, renamed `15V_ISO`, on `ISOGND`. Recommended. The alternative swaps them, so
  the isolated gate drivers get the regulated rail; FB and the SR controller then sit on ISOGND.
- **D2 15 V is enough** for the gate-driver boards on J1–J8 (pin 48). If not, choose 18 V or
  20 V outputs and redo the turns (NS/NB) in `params.py`.
- **D3 DC ↔ ISO insulation class** for the transformer (functional, basic or reinforced) and the
  working voltage across it (the ISO side carries the inverter's AC output). This sets margins,
  tape and the creepage on the board.
- **D4 Controller:** INN3694C (0 stock, buy elsewhere and hand-fit, or JLC global sourcing), or
  an alternative with stock (another InnoSwitch3-EP 900 V part, or a primary-side controller
  such as the existing iW1830 with the new EE25 transformer and a 900 V+ MOSFET).
- **D5 Where it goes:**
  - (a) in place on the main board: delete the sheet 7 copper and re-place and re-route the
    area in the KiCad GUI, with a slot under the transformer and IC;
  - (b) a separate small aux board on headers/wires, which keeps the frozen main board almost
    unchanged and lets the supply be tested on its own.

  Option (b) is recommended for a first prototype.
- **D6 Net names:** rename `20V` / `20V_ISO_SEC` to `15V` / `15V_ISO` (clear, but touches
  sheets 2, 3, 10 and every deviation file), or keep the names with a note.

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
   C93 / R98 / D11 / U18 / T3 (check that they are free).
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
5. **Board (D5).**
   - (a) In place: a `tools/v5/` script deletes the removed footprints and the copper inside the
     area and places the new footprints at agreed positions. Routing, pours and the slot are done
     in the KiCad GUI and recorded in STATUS.md, which ends the "frozen board edited only by
     scripts" rule for this area. A net class `HV_AUX` sets clearance for DC+, the drain node and
     the clamp (500 V working: ≥ 2.5 mm on external layers, and the creepage from D3 between the
     domains).
   - (b) Separate board: a new KiCad project `aux/` (2-layer), with a connector footprint on the
     main board placed by a v5 script in the freed area.
6. **Checks.** ERC, `tools/check_all.sh` (with the v5 deviations), DRC with the new net class,
   `tools/regen_check.sh`, renders of the area, and the JLC BOM/CPL refreshed.
7. **Bring-up** (README): measure Lp (MKF predicts +12 %), the drain peak at 500 V, the clamp
   temperature, and Out2 at light and full load.

## 5. Not part of v5

v4 clean-up and manufacturing items (C67, silk positions, pad decisions, JLC alternatives, CPL)
continue separately on the v4 board. Sheet 7 parts that v5 replaces (iW1830, EF20 TR2 and so on)
get no JLC alternatives.
