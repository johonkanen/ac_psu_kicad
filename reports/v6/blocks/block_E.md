# Block E (control-card area): replay script, 2026-11-27

Branch `block-E`, cut from `v6-baseboard` 6226a75. Nothing was pushed. The replay was tested on a fresh 6226a75 board.

**Verdict.** E is routed down to 7 real open connections inside the block, each listed below with its reason. All 29
ports are drawn to the block edge. The replayed board is legal:

- DRC: 0 copper errors, schematic parity 0.
- domain_gaps: OK.
- Pour islands: 66 before, 66 after.
- Open connections on the whole board: 102 before, 85 after.

The target of 0 open inside E is not reached. I made more than three full tries (the try table is below).

## How to replay

```
tools/p2k/bin/kipy tools/v6/route/block_E.py [--board IN] [--out OUT]   # default: kicad/ac_psu.kicad_pcb in place
kicad-cli pcb drc --refill-zones --save-board ...                       # the zones are added unfilled
```

`block_E.py` has a fixed seed of 6300. Its data is `block_E_copper.csv`. It runs these steps:

1. **Pad check.** It checks the 353 pads it connects to: reference, pad, net and position within 0.01 mm. If any pad
   differs, it saves nothing. I tested this by moving R128 by 0.1 mm; the run refused.
2. **Clean start.** It deletes 1434 pass-1 tracks and 209 pass-1 vias inside E (E minus block G). It cuts 22 pass-1
   tracks that cross the E edge back to the edge. It deletes one dead pass-1 PWM_G1 piece that the cut left inside G.
   If any listed item is missing, it saves nothing.
3. **Rule area.** It shrinks the In3 rule area "v6 route reserve sdm U21 to the corridor In3" from y 40..47 to
   y 46..47, which is its part north of E. The INV sigma-delta pair now leaves E on B.Cu, and the reserve had
   forbidden vias in the isolator I-side band.
4. **Copper.** It adds 2079 tracks and 290 vias, all locked. There are no zones and no part moves.

`build/blockE/` is rebuilt by `tools/v6/route/block_E_chain.sh` (steps 00-43, then 90 / 91 write the CSV and
replay). Step 91 confirms that the replay equals the chain board: 5382 of 5382 items, no footprint moved.

## Numbers (replayed board, refilled, DRC with the project rules)

| | 6226a75 | clean start | replayed E |
|---|---|---|---|
| Open, both ends in E (E minus G) | 29 | 262 | **10** (7 real, see below) |
| Open, one end in E (the trunks outside) | 18 | 24 | 20 |
| Open, whole board | 102 | — | **85** |
| DRC errors in E / copper errors on the board | 0 / 0 | 0 / 0 | **0 / 0** (the 35 accepted courtyard overlaps remain) |
| Schematic parity | 0 | 0 | 0 |
| domain_gaps | — | — | **OK** (0 violations) |
| Pour islands (`islands.py`, 62 pour layers) | 66 | — | **66** (none worse) |
| Dangling items, whole board | 47 | 69 | 74 (the 29 port stubs end on the edge) |

**Real open connections inside E (7):**

| Net | Between | Why it stays open |
|---|---|---|
| GPIO_BYPASS_RLY_ISO | U19-15 (B.Cu) and its port at (65.0, 46) | The B.Cu band between the U19 pins and the edge is full. F.Cu there is the ISOPGND pour and In1/In2/In4 are planes. |
| GND | two old stubs at (60.4, -0.8) B.Cu and (60.6, -0.2) F.Cu, near U13 / AD1 | Kept v4 copper. The P supply router step times out on GND (its pours run outside E). |
| CTRLGND_A | U19-3 | No via spot between the bottom-fan lanes around the U19 C-side row. |
| CLK1 | R87-3 (B.Cu) to U13-12 (F.Cu) | The P logic around U13 / R87 / AD1 is full. |
| ADA3 | two kept F.Cu pieces, at (55.8, -0.6) and (51.3, 1.6) | Same area. |
| GPIO_BYPASS_RLY | U15-12 to the kept v4 run at (45.5, -22.0) | This net and ADCLK should leave on that kept v4 copper; the router does not reach it. |
| ADCLK | R22-2 to the kept v4 In2 run at (42.0, -18.0) | Same. |

**The other 3 "inside" items are not E work:**
- The GND pieces of "Proteus F.Cu pour 19" at x 102..110, y -40..-46 are joined in block C. The P fence of
  `fence.py` covers them.
- PWM_Q7 and 15V_ISO: the E side reaches its port, but D's pass-1 run ends at a different point on the edge
  (71.9 and 92.2).

**One more port does not reach its window:** PWM_TRANS3. Its route stops at (56.95, -38.25) on In3, before the
port at (45.5, -46).

## Ports (net, point on the E edge, layer)

**South edge, y -46 (window E-C, x 41..66), to J21 / J22 / J23.**
- West to east, 0.5 mm pitch:
  - PWM_G1 41.5 In3, PWM_G2 42.0 In2, PWM_TRANS1 42.5 In3 (to J21)
  - PWM_G3 43.0 In3, PWM_G4 43.5 In3, PWM_TRANS2 44.0 In2 (to J22)
  - DAB_PWM_PRI_HI 44.5 In2, DAB_PWM_PRI_LO 45.0 In2, PWM_TRANS3 45.5 In3 (to J23)
- In this order the trunks need not cross: the J21 trunks turn west, the J23 trunks east, and the J22 trunks go
  straight south between them.
- Why these layers: F.Cu there is the DC+ pour and B.Cu the PGND pour. The In3 channel past R41 / C12 (both DC+,
  2.5 mm) holds six lanes. So four nets come on In2, which has no plane south of y -20.7; their vias stand at
  x 40..42.5, west of the P planes.

**West edge, x 40 (window E-A).**
- MDATA: (40, -22.0) on In3.
- On kept v4 copper:
  - Net-(R2-Pad1): -11.3 In2
  - Net-(R5-Pad1): -13.6 In2
  - Net-(U1A-+): -15.7 In2
  - Net-(U1A--): -18.21 In2
  - ADCLK: -19.98 In2 (open inside E, see above)
  - GPIO_BYPASS_RLY: -27.56 In1 (open inside E, see above)
- R2 and R5 lie outside the window range (-45..-15).

**North edge, y 46 (window E-D).** All ISO nets leave here. "p1" means the port is the end of D's pass-1 copper,
which stays.

| Group | Ports (x, layer) |
|---|---|
| Above U19 | PWM_TRANS5 60.5 B (p1), PWM_Q8 61.3 B, PWM_Q6 63.0 F (p1), PWM_Q5 63.6 B (p1), GPIO_BYPASS_RLY_ISO 65.0 B (not reached) |
| | PWM_TRANS6 71.2 B (p1), MDATA_INU 73.5 B, INU_ADCLK 74.0 B |
| Above U20 | PWM_Q7 83.64 B, PWM_TRANS4 86.19 B, DAB_PWM_LO_SEC 87.45 B, DAB_PWM_HI_SEC 88.72 B |
| Divider taps (p1) | Net-(U7B--) 90.9, Net-(U7B-+) 91.5, Net-(U7A--) 92.1, Net-(U7A-+) 92.7, Net-(U2--) 93.3, Net-(U2-+) 93.9, all In3 |
| Supplies | 15V_ISO 95.0 B, 5V_ISOL 96.15 B (p1, 0.28 mm stub) |

Notes on the north ports:
- **Order:** the band under this edge (y 40..46) has only B.Cu, so most ports stand straight above their isolator
  pin. The trunks in D sort the order. D has inner layers there, and J24 / J25 / J26 are through-hole, so crossings
  at the headers need no via.
- **Spacing:** points are at least 0.5 mm apart on any layer. The narrowest pair, Q6 / Q5, is 0.6 mm.
- **D's dangling pass-1 copper:** where my port differs from pass 1, D's pass-1 run now dangles at its old point.
  These are GPIO_BYPASS_RLY_ISO 62.2, PWM_Q7 71.9, DAB_PWM_HI_SEC 92.85, PWM_TRANS4 93.7, the 15V_ISO run at 58.89 F,
  and the 5V_ISOL run at 64.2 F. The trunk step joins or removes them.

## Part moves and other changes

- **No part moved.**
- **Kept copper:** a pass-1 15V B.Cu track that grazes E's south-west corner, (39.1, -44.2) to (48.9, -54.0), is left
  whole.
- **C4 at the E / G corner:** C4's ISOGND pad lies in G (x 97.07). One 0.15 mm pad-entry piece of E's ISOGND reaches
  0.45 mm into G. It appears twice in the CSV; the duplicate is harmless.
- **Via-in-pad (decision for the user):** the router placed 48 vias inside SMD pads. They include several SOIC pins of
  U13, U15, U16, U19, U20, U21 and U28. JLC can make them filled and capped, at extra cost; otherwise they need a
  rework pass.

## How the chain got here (tries)

| Try | Change | Open inside E |
|---|---|---|
| 1 | Fans first, F/In3/B. Top fan 9/18: the west-row pins have no escape | — |
| 2 | Pass-1 `08_j11.py` escape stubs. Top fan 18/18, bottom fan 6/14 | 181 after the buck |
| 3 | Bottom fan first, all 6 layers (the J11 column has no planes): 14/14. Ports at D's pass-1 ends | 16 |
| 4 | Router input localized: outside pads lose their net, outside copper dropped (`block_E_fence.py`). Without it the supply steps timed out. Plane vias of the ISO band before the ISO ports | 11 |
| 5 | Analog filters at J11 and their vias before the top fan: C analog 21/21 | 10 |
| 6 | Four E-C nets on In2. Reserve shrunk. 5V_ISOL fix (two F.Cu runs that each closed an ISOPGND island) | 10, islands 66 → 66 |

## Renders

`reports/v6/blocks/block_E/E_<layer>.png` holds one image per copper layer plus `E_signal.png` (F / In3 / B), all of
the refilled replayed board, x 39..120, y -47..47. What I saw in them:
- The planes on In1 / In2 / In4 are whole.
- The J11 fans run as a diagonal bundle across the CA area.
- The four In2 port runs come down at x 40..45 past C12.

## What was wrong in the brief

1. **`chain.sh 00 03` does not rebuild the step-03 board.** Its default base (`v6-baseboard`, 6226a75) is already the
   pass-1 board. The step-03 board needs `BASE_REV=870c026`.
2. **Windows E-B and E-F (x 40, y > 5.8) cannot be used.** They lie in the C|I barrier strip with C land behind it.
   All 20 ISO crossing nets leave north, including the taps, the INV sigma-delta pair, GPIO_BYPASS_RLY_ISO and
   PWM_TRANS6. There are 34 crossing nets with pads in E, not 32.
3. **The north band has only B.Cu, so ports cannot be fully ordered for D.** Under the edge, F.Cu is ISOPGND, In3 is
   the sdm reserve and the inner layers are planes. The ports stand above their pins; D sorts the order.
4. **The E-C window needs In2, not only F / In3 / B.** Six In3 lanes fit past R41 / C12.
5. **"Plane vias after the J11 fan" applies to the CTRL planes only.** In the ISO band the plane vias must come
   before the ISO ports, otherwise the ports take their room. The analog filters next to J11 must come before the
   top fan.
6. **J11 is a 1.27 mm header.** Its west row only gets out through the 0.152 mm escape stubs of pass-1 step 08.
7. **The router steps cannot reach the 0 target alone.** Pour nets with pads all over the board (GND, VCC,
   15V_ISO ...) time out unless the router's input is cut down to E. The P fence of `fence.py` also covers P land
   south of the CB strip (x 100..118, y -46..-37).

## Time used

About 3.5 h on 2026-11-26 and about 5 h on 2026-11-27. Much of it was waiting on the shared heavy-job lock (other
sessions' DRC / check_all / sweeps). Router and DRC runtime was about 3 h.
