# fab – JLCPCB manufacturing files (v4 board, v5 BOM in progress)

| File | |
|---|---|
| `jlc_bom.csv` | Assembly BOM in JLC's format (Comment, Designator, Footprint, JLCPCB Part #): 70 lines, 257 SMD parts that JLC places (no THT: the user fits relays, Y caps, modules and connectors). v5 (2026-11-12): the 23 deleted sheet-7 parts are out and the 71 v5 passives are in; the v5 ICs, diodes, transistors and T1 are not yet |
| `jlc_cpl.csv` | Assembly CPL (Designator, Mid X, Mid Y, Layer, Rotation) for exactly those parts, made by `make_fab.sh` |
| `hand_fit.csv` | Everything JLC does not assemble: source, JLC code where one exists, and why it is hand-fitted |
| `make_fab.sh` | Gerbers + Excellon drills → `out/ac_psu_gerber.zip`, position file → `jlc_cpl.csv`, BOM copy (`out/` is not committed) |
| `make_cpl.py` | KiCad position CSV → JLC CPL, with per-package rotation corrections |
| `jlc_bom_check.py` | Checks every JLC code (BOM and hand-fit list) for stock against the number of boards: `python3 fab/jlc_bom_check.py 5` |
| `jlc_stock_2026-11-12.json` | Result of the last stock check for 5 boards: every BOM line in stock except AMC1306M05 (2 for 15; the user buys the rest from Mouser/Digikey) and REF3025AIDBZR (0, was in stock on 10-31); hand-fit codes incl. the snap-in and X2 capacitors. Older files: the checks before later BOM changes |
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
| U4, U5, U6 | ADuM7701-8BRIZ (0 stock) | **TI AMC1306M05DWVR (C701717)**: ±50 mV version (user, 2026-10-30), JLC had 5 in stock on 2026-10-30, enough for one board (3 per board). If JLC runs out, the user buys from Mouser/Digikey and hand-solders. | Same pins and package as the M25 (VDD1/AVDD, VIN±/AINP/N, GND1/AGND, GND2/DGND, MDAT/DOUT, MCLKIN/CLKIN, VDD2/DVDD; 8-lead wide SOIC). SBAS734D: ±50 mV linear (VFSR), ±64 mV clip, R_IND 4.9 kΩ (M25: ±250/±320 mV, 22 kΩ), CMTI 50 kV/µs min / 100 typ. With the 2 mΩ shunts: ±25 A full scale, about ±32 A clip, 5× more counts per amp than the M25 (firmware scale). The fix 4 series resistors (2 × 12.4 Ω = 24.8 Ω) against 4.9 kΩ give ≈ 0.5 % gain error: calibrate it out, do not make the resistors larger. The L/R compensation does not depend on the range. Start-up test pattern accepted (firmware). TI's land pattern has 10.9 mm rows; this board has the Proteus 9.70 mm rows the ADuM7701 used. |
| U13, U15 | Si8661BD-B-IS (2 in stock) | Chipanalog CA-IS3761LW (C528659) | Same 16-pin assignment (VDD 1/16, GND 8/9, 5 forward channels on pins 2–6 → 15–11, reverse channel 10 → 7), default output low (L = Si866x "B"), 5 kVrms wide body. U17 (spare, not fitted) is not in the BOM. |
| U16 | Si8660BD-B-IS (6 in stock) | TI ISO7760FDWR (C2878538) | Same 16-pin assignment (VCC1 1 / VCC2 16, GND1 8 / GND2 9, INA–INF 2–7 → OUTA–OUTF 15–10), "F" = default output low like Si8660 "B" (PWM gate signals stay off on power loss), 2.25–5.5 V, 5 kVrms reinforced, wide SOIC-16. |
| U1, U7 | OPA2353EA (16 in stock) | TI OPA2350EA/2K5 (C115876) | Same family and VSSOP-8 pinout, rail-to-rail in/out, 2.7–5.5 V (3.3 V here), 38 MHz vs 44 MHz GBW: plenty for the 50 Hz voltage measurements. Cheaper fallback: TLV9062IDGKR (C398356, 10 MHz). |
| AD1 | ADS7056IRUGR | bought by the user, not in the JLC BOM (`hand_fit.csv`) | Consign the parts to JLC (X2QFN-8, 0.5 mm pitch) rather than hand-solder. |
| R7 | 1k | **10k** (C25744), v4 fix 11 | U1B's + leg is now matched to its 10k feedback. With 1k, ADA3 measured about 0.0366·V(FILTER_INPUT) − 0.0038·V(LEMOUT) against GND: a common-mode gain of ≈ 0.033. Now it measures 0.0366 × (LEMOUT − FILTER_INPUT) around 1.65 V, so **the firmware scaling of ADA3 changes**. |
| R18, R9 | 100R | 8.2k (C25924), v4 fix 11 | With C88/C89 4.7 nF C0G (C1518204): 4.1 kHz output filter on ADA2/ADA3. |
| C42, C2 | 1n | 10 nF C0G (C22400107), v4 fix 11 | With R39/R77 8.2k: 1.9 kHz DC-link filters (ADA1 = DC+, ISOADA3 = ISODC+). |
| C95–C106 | (new, v4 fix 11) | 1 nF C0G 0402 (C307441) | Across every 10k leg of the six difference amplifiers (15.9 kHz): tap-node filter (reports/noise finding 1). |
| C107, C108 | (new, v4 fix 11) | 4.7 nF C0G 0402 (C1518204) | ISOADA1/ISOADA2 at R54/R56 8.2k: 4.1 kHz. The control card's ADC sees an 8.2 kΩ ∥ 4.7 nF source on ISOADA1–3 (ISOADA3: 8.2k ∥ 10 nF). |
| C109, C110 | (new, v4 fix 11) | 100 nF 0402 (C1525) | Decoupling REF_1V65 / REF_1V65_ISO (279 Ω source, 28 µs). |
| R19, R32 | 420R | 422R (C67237) | v4 fix 9 changed the design value too: 1.6506 V instead of 1.6532 V. |
| R87 | RESISTOR_ARRAY (no value in the Proteus data) | 4 × 33R convex 4D02 (C25501) | 33R confirmed by the user (SPI series termination). |
| C67 | 100u (now drawn as a ceramic, v4 fix 7) | Murata GRM31CR61A107MEA8L 10 V X5R (C883598) | |
| C1, C35, C45–C50 | 2.2u 2220 | TDK C5750X6S2W225KT000N 450 V X6S (C445674) | Each sees half the DC link: 225 V at DC+ max 450 V (50 %); the earlier 250 V part had 90 %. |
| C68 | 100n 1206 (DC+ to GND; the built boards had a 630 V part) | TCC1206X7R104K501HT 500 V (C5448934) | No ≥ 630 V 1206 in stock; 500 V is the closest (90 % at 450 V). Hand-fit Samsung CL31B104KIHNNNE (1 kV) instead if wanted. |
| U8 | VXO7805-1000 | **Mornsun K7805-2000R3** (5 V / 2 A), hand-fit (`hand_fit.csv`) | v4 fix 10, for the isolated control card. C93 10 µF 50 V X7R 1210 (C138687; 22 µF 50 V is not stocked in 1206/1210) at the input, C94 22 µF 10 V 0805 (C29277) at the output. |
| C7… (14 × 2n2 disc) | 2n2 | TDK CS45-E2GA222M-NKA X1/Y2 (C96522), in `hand_fit.csv` (placed by the user) | Y2 is enough (user). |

## v5 passives (picked 2026-11-12, all in stock for 5 boards)

Codes reused where the BOM already had the value and package (100n 0402/0603, 8.2k 0402, 4.7n / 10n
C0G 0402, 22u 1206, 1k 0603); otherwise JLC basic parts first, then the highest stock. Choices that
are not just "value + package":

| Ref | Design | BOM part | Why |
|---|---|---|---|
| R105 (RCS) | 0.562R 1206 | **0.56R** 1 % FOJAN FRL1206FR560TS (C2907358) | No 0.562R 1206 in stock anywhere at JLC. 0.4 % lower: CC limit ≈ +0.4 % (23.1 W worst instead of 23.0 W). ≈ 0.12 W at 100 V full load (0.25 W part). |
| C113 (CDD) | 15u 50V 1210 | **22uF 35V X5R** Taiyo Yuden GMK325BJ226MM-P (C778721) | No 15 µF and no 22 µF 50 V 1210 at JLC. VDD ≈ 14.3 V. **Check:** TI eq. 24 needs ≥ 12.9 µF *effective*; an X5R 35 V part typically keeps only about half its value at 14 V (check Taiyo Yuden's DC-bias curve), so this is near the limit. Verify the start-up into the full output capacitance on the prototype (or fit a second capacitor). |
| R98 | 10R 2512 | 10R **2 W** FOJAN FRP2512J100 (C3013385) | Carries the flyback input current: ≈ 0.2 W at 325–450 V, up to ≈ 1–2 W at 100 V full load (low-line start). |
| C111, C112 | 47n 1kV 1210 | TORCH CV1210X7R1KV473KN (C54916903) | The only 47 nF 1 kV 1210 at JLC (1690 in stock). Known-brand fallback: Murata GRM32DR72J473KW01L 630 V (C97970), 71 % at 450 V. |
| C115, C116 / C137, C138 | 470u 25V / 470u 16V, 8x10 | **polymer** jieerrui MA25V470M8x10 (C46550466) / MA16V470M8x10 (C46550462), 4.1 A ripple, 18–25 mΩ | DCM flyback outputs: ripple ≈ 1.7 × DC, about 0.65 A (Out1), 0.55 A (Out2), 1.7 A over the two CTRL capacitors. Ordinary 8x10 electrolytics are rated 0.3–0.45 A. No known-brand 470 µF polymer of this size is in stock. |
| R110–R127 | 0.1 % | Yageo RT0603BRD (thin film, 25 ppm/K): 6.8k C861539, 10k C95204, 24.9k C136967 | Diff-amp matching; the same series for all three values. |
| L2 | 15u SWPA6045S150MT | Sunlord SWPA6045S150MT (C83374) | As designed. |

Not yet in the BOM (not passives): U18 UCC28710 (C80866), Q17 IPD95R450P7 (C3289115), U19/U20
ISO7760FDWR (C2878538), U21 CA-IS3742LW (C4944981), U22–U24 AMC1311BDWVR (C783598), U25/U26
OPA2350EA (C115876), U27 TPS73033 (the BOM's TPS73033DBVR C57424 fits), U28 TPS54202, Q15/Q16,
D11–D16 still to pick. T1, W1, J13/J14 and PEC1/PEC2 will be hand-fit (not yet in `hand_fit.csv`).

Voltage margins at DC+ max 450 V (user, 2026-10-29): 91k divider chains 3 × 91k → 150 V per 200 V
resistor (75 %); 2220 split capacitors 225 V on 450 V (50 %); C68 450 V on 500 V (90 %); the
snap-in DC link capacitors are 450 V parts (user: OK).

M4 ring-lug terminals (v4 fix 13): Würth REDCUBE THR 74650074R on FILTER_IN, FILTER_OUT,
INU_OUT2, J5, J7, J9, J10 (hand-soldered; Mouser/Digikey), each with an M4 × 6 screw, a lock washer
and an insulated M4 ring lug for 2.5–6 mm² (`hand_fit.csv`). The other lead connections (DAB, ACIN,
ACOUT, AFE_OUT, PE) are still soldered pins until they are re-laid out.

Sourced and soldered by the user (no order code): the common-mode chokes CM1–CM3 and the main
inductors (AliExpress), and the off-board parts (TR1, the inductor on J7/J9).
