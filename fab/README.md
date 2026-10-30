# fab – JLCPCB manufacturing files (v4 board)

| File | |
|---|---|
| `jlc_bom.csv` | Assembly BOM in JLC's format (Comment, Designator, Footprint, JLCPCB Part #): 53 lines, 189 SMD parts that JLC places (no THT: the user fits relays, Y caps, modules and connectors) |
| `jlc_cpl.csv` | Assembly CPL (Designator, Mid X, Mid Y, Layer, Rotation) for exactly those parts, made by `make_fab.sh` |
| `hand_fit.csv` | Everything JLC does not assemble: source, JLC code where one exists, and why it is hand-fitted |
| `make_fab.sh` | Gerbers + Excellon drills → `out/ac_psu_gerber.zip`, position file → `jlc_cpl.csv`, BOM copy (`out/` is not committed) |
| `make_cpl.py` | KiCad position CSV → JLC CPL, with per-package rotation corrections |
| `jlc_bom_check.py` | Checks every JLC code (BOM and hand-fit list) for stock against the number of boards: `python3 fab/jlc_bom_check.py 5` |
| `jlc_stock_2026-10-30.json` | Result of the last stock check (all 53 BOM lines in stock for 5 boards; 2026-10-29 file: the check before the U16/U1/U7/AD1 changes) |
| `jlc_stock_search.py`, `jlc_stock_2026-10-22.json` | The first search (2026-10-22) that found the codes, kept for reference |

Order flow: `fab/make_fab.sh`, upload `fab/out/ac_psu_gerber.zip` (4 layers, 1.6 mm, see the board
stack-up), then `fab/jlc_bom.csv` and `fab/jlc_cpl.csv` for assembly. **Check every rotation in
JLC's placement preview**, both sides. The corrections in `make_cpl.py` are the usual KiCad →
JLC values, and the bottom-side sign is not verified against a real order.

Values: the series resistors on the sigma-delta inputs are 12.4R (C477607) for a 5 nH shunt
inductance (2.5 Ω per nH with the 100 nF C0G capacitors C90–C92). Re-pick them if the
inductance is measured.

## Substitutions (the schematic still names the original part)

| Ref | Design part | BOM part | Check |
|---|---|---|---|
| U4, U5, U6 | ADuM7701-8BRIZ (0 stock) | TI AMC1306M25DWVR (C471874), **accepted by the user** (start-up test pattern is fine for the firmware) | Same 8 pin functions (VDD1/AVDD, VIN±/AINP/N, GND1/AGND, GND2/DGND, MDAT/DOUT, MCLKIN/CLKIN, VDD2/DVDD), same 8-lead wide SOIC (11.5 mm span), ±250 mV linear (±320 mV clip), 5–21 MHz clock, data out after the rising clock edge (tD ≤ 15 ns), reinforced 7 kVpk. Differences: 32-clock test pattern after power-up; AVDD ≥ 3.0 V. The TI land pattern has 10.9 mm rows, this board has the Proteus 9.70 mm rows that the ADuM7701 was soldered on. |
| U13, U15 | Si8661BD-B-IS (2 in stock) | Chipanalog CA-IS3761LW (C528659) | Same 16-pin assignment (VDD 1/16, GND 8/9, 5 forward channels on pins 2–6 → 15–11, reverse channel 10 → 7), default output low (L = Si866x "B"), 5 kVrms wide body. U17 (spare, not fitted) is not in the BOM. |
| U16 | Si8660BD-B-IS (6 in stock) | TI ISO7760FDWR (C2878538) | Same 16-pin assignment (VCC1 1 / VCC2 16, GND1 8 / GND2 9, INA–INF 2–7 → OUTA–OUTF 15–10), "F" = default output low like Si8660 "B" (PWM gate signals stay off on power loss), 2.25–5.5 V, 5 kVrms reinforced, wide SOIC-16. |
| U1, U7 | OPA2353EA (16 in stock) | TI OPA2350EA/2K5 (C115876) | Same family and VSSOP-8 pinout, rail-to-rail in/out, 2.7–5.5 V (3.3 V here), 38 MHz vs 44 MHz GBW: plenty for the 50 Hz voltage measurements. Cheaper fallback: TLV9062IDGKR (C398356, 10 MHz). |
| AD1 | ADS7056IRUGR | bought by the user, not in the JLC BOM (`hand_fit.csv`) | Consign the parts to JLC (X2QFN-8, 0.5 mm pitch) rather than hand-solder. |
| R19, R32 | 420R | 422R (C67237) | v4 fix 9 changed the design value too: 1.6506 V instead of 1.6532 V. |
| R87 | RESISTOR_ARRAY (no value in the Proteus data) | 4 × 33R convex 4D02 (C25501) | 33R confirmed by the user (SPI series termination). |
| C67 | 100u (now drawn as a ceramic, v4 fix 7) | Murata GRM31CR61A107MEA8L 10 V X5R (C883598) | |
| C1, C35, C45–C50 | 2.2u 2220 | TDK C5750X6S2W225KT000N 450 V X6S (C445674) | Each sees half the DC link: 225 V at DC+ max 450 V (50 %); the earlier 250 V part had 90 %. |
| C68 | 100n 1206 (DC+ to GND; the built boards had a 630 V part) | TCC1206X7R104K501HT 500 V (C5448934) | No ≥ 630 V 1206 in stock; 500 V is the closest (90 % at 450 V). Hand-fit Samsung CL31B104KIHNNNE (1 kV) instead if wanted. |
| U8 | VXO7805-1000 | **Mornsun K7805-2000R3** (5 V / 2 A), hand-fit (`hand_fit.csv`) | v4 fix 10, for the isolated control card. C93 10 µF 50 V X7R 1210 (C138687; 22 µF 50 V is not stocked in 1206/1210) at the input, C94 22 µF 10 V 0805 (C29277) at the output. |
| C7… (14 × 2n2 disc) | 2n2 | TDK CS45-E2GA222M-NKA X1/Y2 (C96522), in `hand_fit.csv` (placed by the user) | Y2 is enough (user). |

Sheet 7 parts (IW1830 PWM1, TR2, D1/D2/D6, R23/R24/R33/R34/R43, C62, C65/C66 …) are ordered as
designed, but the v5 aux-flyback redesign (`V5_PLAN.md`) will replace them.

Voltage margins at DC+ max 450 V (user, 2026-10-29): 91k divider chains 3 × 91k → 150 V per 200 V
resistor (75 %); 2220 split capacitors 225 V on 450 V (50 %); C68 450 V on 500 V (90 %); the
snap-in DC link capacitors are 450 V parts (user: OK).

Sourced and soldered by the user (no order code): the common-mode chokes CM1–CM3 and the main
inductors (AliExpress), and the off-board parts (TR1, the inductor on J7/J9).
