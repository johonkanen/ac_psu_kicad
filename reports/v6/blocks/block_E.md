# Block E (control-card area): work in progress, 2026-11-26

Branch `block-E` (from `v6-baseboard` 6226a75). Stopped at the user's end of day: **no replayable copper yet**
beyond the clean-up. Nothing was pushed.

## State

| Piece | State |
|---|---|
| `tools/v6/route/block_E.py` | Done for step 1 (clean start). It checks every pad in its table to within 0.01 mm, deletes the pass-1 copper inside E (E minus block G) item by item, and cuts the 23 pass-1 tracks that cross the E edge back to the edge. If any listed item is missing, it saves nothing. It also does part moves, tracks, vias and zones from the CSV, but the CSV holds no routed copper yet. It was tested on the 6226a75 board with `--clean-only`. |
| `tools/v6/route/block_E_copper.csv` | Clean-up rows only: 1434 `deltrack`, 209 `delvia`, 23 `cuttrack`. |
| `block_E_make.py` | `clean` writes the clean-up rows by diffing against the step-03 board. `copper` writes the copper rows from (00 board, routed board). |
| `block_E_chain.sh` | The development chain. Each step is fenced to E plus its domain (`block_E_fence.py`). Each crossing net gets a temporary port pad 0.5 mm inside its window point; the finish step adds the piece out to the edge. Every refill / DRC waits for 6 GB free and takes the shared lock (`block_E_drc.sh`). |
| `block_E_ports.py` | The port list (below). |
| `block_E_planes.py` | Step 07's plane vias, limited to E. It runs after the J11 fans (not run yet). |

## Numbers so far (`build/blockE/`, DRC with the project rules)

| Step | Open inside E | Open, one end in E | DRC errors in E |
|---|---|---|---|
| 00 clean start (6226a75 minus the pass-1 copper in E) | 262 | 24 | 0 |
| 08 J11 west-row escape stubs (pass-1 `08_j11.py`) | 262 | 24 | 0 |
| 09 J11 bottom fan, all 6 layers: **14/14** (pass 1: 6/14) | 248 | 23 | 0 |
| 10 / 11 J11 top fan (even pins on In3 / B first, then odd pins on F.Cu): **18/18** | 230 | 24 | 0 |
| 12 C analog chain: 18/21 | 197 | 25 | 0 |
| 13 buck: 6/6 | 181 | 25 | 0 |
| 14 P logic | stopped mid-run | | |

Most of the 181 are supply / plane pads (CTRLGND_A 36, 3V3_CTRL 24, ISOGND 22, 3V3_ISO 13, CTRLGND 10, GND 8,
VCC 7, ...). Steps 20 to 23 will close them: plane vias first, then supply routes.

An earlier try (try1) ran steps 14 to 17:
- P logic: 8/10.
- P ports: 9 of 10 reached (DAB_PWM_PRI_LO missed).
- I logic: 10/13 (DAB_SHUNT2, INU_ADCLK_U21 and ISO_DAB_SDM_RAW_VOLTAGE left).
- I ports: 11 of 18 reached, with 5 DRC errors. Those errors came from port points that sat on the ends of D's pass-1
  copper. The port list below fixes that, but it has not been rerun.

Not measured yet: domain_gaps, island counts and renders of a final E board. No part has moved.

## Ports (`block_E_ports.py`)

- **South edge, y -46, all on In3.** F.Cu there is the DC+ pour and B.Cu the PGND pour. All ports lie west of C12,
  because its DC+ pad keeps 2.5 mm.
  - x 41.5 to 45.5 at 0.5 mm pitch, west to east: PWM_G1, G2, TRANS1 (to J21); G3, G4, TRANS2 (to J22);
    DAB_PWM_PRI_HI, PRI_LO, TRANS3 (to J23).
  - This order lets the trunks run without crossing: the J21 trunks turn west, the J23 trunks turn east, and the J22
    trunks go straight south between them.
- **West edge, x 40:**
  - MDATA: new port at (40, -22.0) on In3.
  - These leave on kept v4 inner-layer copper: R2-Pad1 at y -11.3 (In2), R5-Pad1 at -13.6 (In2), U1A+ at -15.7 (In2),
    U1A- at -18.21 (In2), ADCLK at -19.98 (In2), GPIO_BYPASS_RLY at -27.56 (In1).
  - The ADCLK and GPIO copper inside E is not yet joined to R22-2 and U15-12.
- **North edge, y 46.** "p1" marks the end of D's pass-1 copper, which stays.
  - 15V_ISO 58.89 F (p1), PWM_TRANS5 60.5 B (p1), GPIO_BYPASS_RLY_ISO 62.2 B (p1), PWM_Q6 63.0 F (p1), PWM_Q5 63.6 B (p1),
    5V_ISOL 64.2 F (p1)
  - PWM_TRANS6 71.2 B (p1), Q7 71.9 B (p1), Q8 72.5 B
  - MDATA_INU 73.5 B, INU_ADCLK 74.0 B
  - The divider taps U7B-, U7B+, U7A-, U7A+, U2-, U2+ at 90.9 to 93.9, 0.6 mm pitch, In3 (p1)
  - DAB_PWM_HI_SEC 94.5 B, LO_SEC 95.0 B, TRANS4 95.5 B
  - 15V_ISO's port at 58.89 lies 0.11 mm west of the window range (59 to 117).

## Next

1. Rerun the chain from step 14 (`tools/v6/route/block_E_chain.sh 14 99`). It runs P logic, P ports, I logic and
   I ports, then plane vias (step 20), supplies (21 to 23) and leftovers (30 to 32).
2. Look at the renders and take up to two more tries on what stays open (C analog 3, I logic 3).
3. Run `block_E_make.py copper`, then replay `block_E.py` on a fresh 6226a75 board.
4. Refill, then DRC, domain_gaps, island comparison (`islands.py`) and renders. Then finish this report.
5. Open question: should the tiny cut pass-1 remnants just outside E (15V_ISO and 5V_ISOL B.Cu, 0.28 mm each, at
   (92.2, 46) and (96.15, 46)) be deleted? They are D's copper and dangle.

## What was wrong in the brief

- **`chain.sh 00 03` does not rebuild the step-03 board.** Its default base, `v6-baseboard`, is 6226a75, which is
  already the routed pass-1 board. The step-03 board needs `BASE_REV=870c026`. With that it reproduces the
  405 open of pass 1.
- **Windows E-B and E-F (x 40, y 25 to 45 and -15 to 25) cannot be used.** At x 40 above y 5.8 lies the C|I barrier
  strip, with C land behind it. No I net can reach those windows. All I crossing nets leave E north (E-D), including
  the U7 / U2 taps, the INV sigma-delta pair, GPIO_BYPASS_RLY_ISO and PWM_TRANS6.
- **There are 34 crossing nets with pads in E, not 32.**
- **J11 is a 1.27 mm header.** Its west-row pins can only get out through the pass-1 escape stubs (`08_j11.py`, a
  0.152 mm track between the east-row pads), so the fan steps need them first.
- **Several E-A nets already leave E on kept v4 In1 / In2 copper**, two of them at y -11.3 and -13.6, outside the
  window range.
- **The router steps alone give DRC errors at the ports.** DRC must run beside the project's `.kicad_pro` / `.kicad_dru`;
  a bare board copy gives hundreds of false via and track errors. Port points must keep clear of the ends of D's
  pass-1 copper on the edge.

Time used: about 3.5 h. About 40 min of that was router and DRC runs (DRC waits on the shared lock).
