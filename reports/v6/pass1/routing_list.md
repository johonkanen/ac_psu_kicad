# v6 routing pass 1 – routing list and lane budget

Board: chain step 03 (`7981425`, 404 unconnected). Open connections from `kicad-cli pcb drc` grouped by
`tools/v6/route/groups_v6.py`; lane counts by `tools/v6/route/lanes.py` over the cuts in
`tools/v6/route/cuts.json` (+ `P7..P9`, `A12`), raw output in `lanes.txt` beside this file.

Lane model: track 0.2 mm, gap 0.15 mm (pitch 0.35 mm). A track centre is free where it keeps from every object of
another net max(0.15, the object's own clearance, 2.5 mm if either net is high-voltage (`tools/v6/route/hv.py`),
the domain gap 5.0 / 2.5 mm), lies outside every track keep-out (barrier strips) and 0.25 mm inside the edge.
**Pours count as obstacles** (a lane may not cut a pour), so the In1 / In2 / In4 planes of the card areas and the
In4 ISOGND strip show as 0 lanes: they are usable for a via or a short stub only.

## 1. Open connections by net group (step 03 board)

| Group | Open | Nets |
|---|---|---|
| DC buses and pour stitching | 5 | ISOPGND 3 (J38 pad and the F pour 8 part 2 not joined to the bus), DC+ 1 (In1 bus to F pour 5), PGND 1 |
| Current-sense groups, U29 / U30, D17 / R257 | 54 | SHUNT1 9, INU_SHUNT2 9, D8-K / D9-K / D17-K 4 each, U4 / U5 VIN± 3 each, SDM_RAW / ISO_AFE_SDM_RAW 2, the force nets AFE_CHOKE1, LEMOUT, INU_CHOKE, INDUCTOR_OUTPUT 1 each, MDAT stubs |
| Sigma-delta links (drawn by script) | 6 | MDATA 2, ADCLK 2, MDATA_INU 1, INU_ADCLK 1 |
| Primary supplies (J21..J23, U29, U5) | 51 | GND 25, 5V 9, VCC 9, 15V 8 |
| ISO supplies (J24..J26, U30, U4, relay) | 73 | ISOGND 36, 3V3_ISO 15, 15V_ISO 11, 5V_ISOL 11 |
| Card PWM, primary | 10 | PWM_G1..G4, PWM_TRANS1..3, DAB_PWM_PRI_HI / LO |
| Card PWM, ISO | 9 | PWM_Q5..Q8, PWM_TRANS4..6, DAB_PWM_HI / LO_SEC |
| ISO runs west of J11 | 7 | the six divider taps Net-(U7A±), (U7B±), (U2±), GPIO_BYPASS_RLY_ISO |
| Primary logic | 14 | REF_1V65 4, ADASEL0..2, CLK1, CS1, SDATA1, ADA3, U11-X, U15-B5, GPIO_BYPASS_RLY |
| ISO logic | 17 | REF_1V65_ISO 3, ISOADA1..3 / _AIN, MDATA_DAB, ADCLK_DAB, DAB_SHUNT2, SHUNT2 |
| CTRL area under the control card | 158 | CTRLGND_A 36, 3V3_CTRL 24, CTRLGND 10, buck (CTRL_*) 18, 5V_CTRL(_A) 8, J11 fan-out 33 single links, analog chain ISOADA*_N/P/M/PL/OUT 20 |
| **Total** | **404** | |

## 2. Long runs and where they go

| Run | From -> to | Length (direct) | Domain | Narrow places on the way |
|---|---|---|---|---|
| MDATA_INU / INU_ADCLK + 3V3_ISO (U4 VDD2) | U21-12 / -14 (75, 40) -> U4 (-94, 64) | 172 mm | I | A2, A1, A3 or A4+A12, A10 |
| 5V_ISOL to J24 and U30 | J25 / C157 (64, 45) -> J24 (13, 44) -> U30 (-97, 46) | 160 mm | I | A2, A1, A3 / A12 |
| 15V_ISO to J24 and the relay R79 | C156 (59, 45) -> J24 -> track end (10.3, 19.2) | 75 mm | I | same |
| PWM_Q7 / Q8 / TRANS6 | U20 / U19 (62..84, 40) -> J24 (13, 45) | 50..70 mm | I | same |
| GPIO_BYPASS_RLY_ISO | U19-15 (67, 40) -> track end (25.3, 40.7) | 42 mm | I | same |
| six divider taps | U7 / U2 (95..103, 2..13) -> track ends (-11..17, 27..48) | 90..108 mm | I | B3 (east column), B2, A2, A1, A3 / A12 |
| MDATA / ADCLK + VCC, 5V, GND to the U5 group | U15-10 / R22 (49..56, 1..4) -> U5 / R55 (-38..-27, -76..-81) | 115 mm | P | P6, S3, P1, S1 / S2 |
| primary card PWM | U13 / U15 / U16 P side (47..80, 3.6) -> J21 (4, -50.5), J22 (54, -59.5), J23 (90, -58.8) | 55..90 mm | P | P6, S3 / P1 (J21), P2 (J22), P3 + P7 / P8 (J23) |
| J11 fan-out to U19..U21 (14) and U13 / U15 / U16 (16) | J11 (45..46, 23..45) -> (49..90, 13 / 31) | 15..43 mm | C | C1, C2 |

## 3. Narrow places: nets that must cross, lanes per layer

Lanes per layer at the narrowest cut of each place (F / In1 / In2 / In3 / In4 / B); "pour" = filled by a plane or
DC pour of that place (via or short stub only).

| Place | Cut | F | In1 | In2 | In3 | In4 | B | Nets to cross (lane equivalents, 0.4 mm supply = 1.6) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **North of J11**, tower corridor x 43..57, y 51.1 (barrier strip) .. 58.8 (2.5 mm from the ISO lane) | A1 x 48 | 22 | 22 | 22 | 22 | 2 (strip) | 22 | 15 west-going I nets: 2 SDM + 3 PWM (J24) + relay + 6 taps + 3V3_ISO, 5V_ISOL, 15V_ISO = 12 + 4.8 = **16.8** | ample (110) |
| NW corner of the ISO region (strip curve, C156, J25) | A2 x 58.6 | 43 | pour | pour | 45 | pour | 45 | same 15 | ample |
| **Past J37 / J38** (the real pinch west of the corridor; both pads and tongues carry 2.5 mm, J37 tongue on B/In1/In3, J38 tongue on F/In2/In4, ISO DC pours F pour 8 / B pour 5 south of y 49) | A3 J37 east pinch y 46.5 (0.64 mm) | pour | 2 | 2 | 2 | 2 | pour | same 15 = **16.8** | **19**: A3 8 lanes (In1..In4) + In2 down the J37 / J38 gap (A5, 2 lanes from the north) + a via column at x 28.75 between the two tongues (A12: 9.0 mm free, about 14 vias at 0.61 mm pitch) from F / In2 north of J37 (A4: 17 lanes each) to In1 / In3 north of J38 (A6: 18 lanes each). **Tight, not short.** |
|  | A4 north of J37 x 33 | 17 | 0 | 17 | 0 | 0 | 0 | | |
|  | A6 north of J38 x 20 | 0 | 18 | 0 | 18 | 0 | 18 | | |
|  | A7 south of the terminals x 30 | pour | 68 | 68 | 68 | 68 | pour | | |
| West run to U4 | A9 x -45 / A10 x -72 (J9 / J7) / A11 x -85 | 91 / 26 / 40 | 91 / 26 / 84 | 91 / 26 / 84 | 91 / 26 / 84 | 91 / 26 / 84 | 72 / 26 / 2 | SDM pair + ISOGND track + 3V3_ISO + 5V_ISOL (U30) | ample; A10 passes between J9 (INU_CHOKE, 2.5 mm) and J7 (switch-node landing) in a 7.1 mm band: a crossing, not a run |
| **Control card edge (y 46.36) to the ISO lane (y 61.3)**, under J39 / J40 / J26 | B1 x 70 / B2 x 88 | 15 / 21 | pour | pour | 38 / 36 | pour | 31 / 32 | the 15 west-going nets + J25 / J26 headers (12) | ample on In3 / B |
| ISO east column (taps from U7 / U2 north) | B3 y 30 | 45 | pour | pour | 53 | pour | 41 | 6 taps + MDATA_DAB / ADCLK_DAB + ISOADA* | ample |
| **CTRL barrier crossings**: J11 tower channel x 46.7..53.45 (C side, between J11 and the C\|I strip) | C1 y 40 | 21 | 21 | 21 | 21 | 21 | 21 | J11 pins 19..38: 18 signals + CTRLGND_A / 3V3_CTRL stubs | ample (126) |
|  | C2 x 57 over the U19..U21 CTRL pads | 57 | pour | pour | 63 | pour | 63 | 14 signals to U19..U21 (bottom), 16 to U13 / U15 / U16 (top) | ample. The isolator channels themselves are fixed (V6_PLAN section 4) |
| **Primary header area**: J21 approach | P1 y -46 | 5 | 103 | 99 | 103 | 103 | pour | 3 PWM + 15V, 5V, GND + the U5 bundle (MDATA, ADCLK, VCC, 5V, GND) | ample |
| J22 approach | P2 y -50 | pour | 69 | 69 | 69 | 69 | 21 | 3 PWM + 15V, 5V, GND | ample |
| J23 through the aux area PX | P3 y -30 | 32 | 80 | 33 | 75 | 79 | 23 | 3 PWM (DAB_PWM_PRI_HI / LO, PWM_TRANS3); 15V / 5V / GND come from the east (U9, pour 19) | ample |
| J23: under the end of the aux barrier strip, between the AUX_DRAIN In1 / In4 zones (2.0 mm) and the J33 DC+ tongue (2.5 mm, F/In1/In3) | P7 x 78 / P8 x 83.5 | 0 / 6 | 3 / 3 | 0 / 34 | 5 (y -54.1..-52.2) / 7 | 5 / 9 | 0 / 21 | 3 PWM | **tight**: one band of 3..5 lanes on In3 / In4 at y -52.2 .. -54.7; enough for 3 |
| AFE sigma-delta run to U5 (FILTER_IN1, FILTER_OUT1, J5, AFE_OUT1, J32) | S1 y -60 / S2 x -10 / S3 x 20 | 7 / 60 / 17 | 84 / 120 / 124 | 78 / 118 / 116 | 84 / 124 / 125 | 84 / 124 / 126 | 30 / 92 / 59 | the U5 bundle (5 nets) | ample |

**Verdict: no place is short.** The two tight places are the passage past J37 / J38 (16.8 lane equivalents
against about 19, a third of them through a single via column between the two terminal tongues) and the J23
approach under the end of the aux barrier strip (3 nets, 3..5 lanes). Both get drawn copper (script) rather than
the router.

## 4. Order (planning session rule 3)

1. Bus stitching (ISOPGND at J38 / F pour 8 part 2, DC+ In1, PGND) and supplies and grounds to J21..J26, the
   header capacitors, U29 / U30, the sense groups (15V / 15V_ISO / 5V / 5V_ISOL to the headers 0.4 mm or wider).
2. The two sigma-delta pairs drawn by script, each pair side by side on In3; over the In4 GND / ISOGND planes where
   they exist, elsewhere with a ground track (GND / ISOGND) beside them; series resistors R55 / R50 (data, at the
   modulator) and R22 39R (ADCLK, at U15 B5) / R258 33R (INU_ADCLK, baseboard step 4c, at U21-14).
3. PWM_HI / PWM_LO / PWM_TRANS per card as one group (primary: P side of U13 / U15 / U16; ISO: U19 / U20).
4. The card area under the control card (J11 / J12 fan-outs, analog chain, buck, CTRL / ISO / primary logic).
5. The rest (divider taps, relay, leftovers).
