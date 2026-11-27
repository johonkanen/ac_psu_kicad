# Block F (bulk caps / dividers, middle area): replay script, 2026-11-27

Branch `block-F`, cut from `v6-baseboard` 3227a58 (block E integrated). Nothing was pushed. I tested the replay on a
fresh 3227a58 board.

**Verdict.** F is done: 0 open connections inside F, before and after. The block was already connected by kept v4
copper. The work was the eight nets that cross its edges. Each one now ends on a fixed port on F's edge. The replayed
board is legal:

- DRC: 0 copper errors, schematic parity 0.
- domain_gaps: OK.
- Pour islands: 76 before, 76 after.
- check_layout: OK.
- assign_nets --check: OK.
- Open connections on the whole board: 87 before, 86 after (C148's GND is closed).

No router run was needed. No part moved. No rule area changed.

## Numbers (refilled boards, DRC with the project's .kicad_pro / .kicad_dru beside the board)

| | 3227a58 | replayed F |
|---|---|---|
| Open, both ends in F (`block_of == "F"`) | 0 | **0** |
| Open, one end in F | 8 (9 in a second run; see note 1) | 8: 7 port stubs waiting for A / D2 / D, plus the DC+ pour link (see below) |
| Open, whole board | 87 | **86** |
| DRC copper errors (board) / DRC errors in F | 0 / 0 | **0 / 0** (the 35 accepted courtyard overlaps remain) |
| Schematic parity | 0 | **0** |
| Pour islands (`islands.py`, 71 pour layers) | 76 | **76** (none worse) |
| domain_gaps (5.0 / 2.5 mm between domains, adjacent layers) | OK | **OK** |
| check_layout (In1 / In4 inside the card, barrier strips) | OK | **OK** |
| assign_nets --check (copper groups without a pad) | OK (1 orphan: the ADCLK group, net from an IPC via) | **OK** (the same orphan, see below) |
| Dangling items in F | 5 (v4 runs ending at the old ISO card place) | 7 (the 7 new port stubs, which end on the edge) |

Notes:
1. The base DRC listed C's 15V trunk once from an item in F and once from one in C. It is the same open: the 15V
   end at (48.9, -54) to C150, which is block C's.
2. The ADCLK group has no pad until block E joins R22-2 to the kept run (one of E's 7 open connections). Until then,
   the IPC via at the end of its v4 tail in C, (7.884, -47.485), gives the group its net in assign_nets. I tried
   deleting that tail and assign_nets failed, so the tail stays and F's branch tees off it. C or A can delete the tail
   once ADCLK is joined end to end.

## How to replay

```
tools/p2k/bin/kipy tools/v6/route/block_F.py [--board IN] [--out OUT] [--dry]   # default: kicad/ac_psu.kicad_pcb in place
kicad-cli pcb drc --refill-zones --save-board ...                                # refill; F adds no zones
```

- `block_F.py` uses a fixed seed of 6400. Its data is `block_F_copper.csv` (51 rows).
- **Pad check.** It checks 9 pads: C148-2, R82-1, R85-1, R68-1, R67-1, J24-9, J24-6, C11-1 and C11-2.
- **Kept copper check.** It checks the 11 kept items the new copper joins (rows `needtrack` / `needvia`).
- If any pad differs or any listed item is missing, it saves nothing.
- **Fence check.** Every new track end and via must lie in F (`block_of == "F"`) or exactly on an F edge. Otherwise it
  saves nothing.
- **Changes.** It deletes 2 dead v4 tracks and adds 24 tracks and 5 vias, all locked. There are no zones, no part
  moves and no rule-area changes.

`tools/v6/route/block_F_chain.sh` runs the whole chain. Its log is in `reports/v6/blocks/block_F_chain.log`.
1. It refills and checks the base board.
2. `block_F_make.py` turns the drawn design into the CSV and checks the design against the base board.
3. `block_F.py` replays it on a fresh `git show 3227a58` board.
4. It runs DRC, islands, domain_gaps, check_layout and assign_nets on the replayed board, then makes the renders.

`block_F_drc.sh` checks a copy beside copies of the project files in `build/blockF/drc/`. It never writes
`kicad/ac_psu.kicad_pcb`.

## What F was at the start

- **Area.** F is the rectangle x -38 … 40, y -46 … 46 minus block A (x < -2, y < -12) and block D2 (y > 38). That
  leaves an L shape: x -2 … 40 for y -46 … -12, and x -38 … 40 for y -12 … 38. Its pads are:
  - the bulk caps C8 / C72 (ISODC+ / ISOPGND) and C11 (DC+ / PGND);
  - the divider chains R65 … R70 (AC_OUT_1 / AC_OUT_2 to the U7B taps) and R80 … R85 (ISODC+ to the U2 taps).
  U2 / U7 themselves lie in E. C79 and the R2 / R5 / R11 … R16 dividers lie in A.
- **Copper.** Almost all of F's copper is kept v4 copper. It makes every pad-to-pad connection in F, and it carries
  the A ↔ E analog lanes on In2 (R2, R5, U1A±) and In1 (GPIO_BYPASS_RLY). On In1 / In2 / In3 / In4 in F there are no
  pours, so the inner layers are free apart from those lanes. F.Cu and B.Cu are HV pours: ISODC+, ISOPGND, DC+ and
  PGND.
- **No clean start.** Pass 1 added only about 40 items in F (diff 870c026 → 3227a58), and I kept both of them:
  - The pass-1 **15V B.Cu trunk** of block C, (31.95, -46.8) → (39.1, -44.2) → (48.9, -54). It grazes F's south-east
    corner, which is the same track E left whole at its corner. Deleting it would open C.
  - The pass-1 **U7B-+ via (2.87, 37.3) and its In1 run** into D2. It is exactly what F would draw, and its D2 end is
    D's pass-1 copper. It is F's U7B-+ port.

## What F adds (`block_F_make.py`, all drawn)

| Net | Path in F | Port |
|---|---|---|
| MDATA (sigma-delta data, P) | from E's port (40, -22) In3: south along x 39, then west along y -42. This keeps it clear of the analog In2 lanes at y -18.9 … -24.7 and of C11's DC+ pad. | (-2, -42.0) In3 → A |
| ADCLK (sigma-delta clock, P) | tees off its kept v4 In2 run at (3.913, -43.5), then west along y -44, 2 mm from MDATA | (-2, -44.0) In2 → A |
| ISOGND (ISO card supply) | the dead v4 In1 diagonal is deleted. The new run goes from the v4 end (10.27, 19.17) up x 12.6 on In1. | (13.27, 38.0) In1 → D2, straight below J24-9 |
| 15V_ISO | the dead v4 In2 diagonal is deleted. In2 to a 0.6 mm via at (13.5, 19.17), then In3 up x 16.4. | (16.4, 38.0) In3 → D2. D's In3 run passes (16.4, 43) to J24-6. |
| Net-(U7B--) (divider tap) | from the dangling v4 In2 end (17.39, 35.51): via, then In1 east and north | (26.0, 38.0) In1 → D2 column |
| Net-(U2-+) | from the v4 In2 end (14.18, 29.48): via, then In1 east and north | (26.6, 38.0) In1 → D2 column |
| Net-(U2--) | from the v4 In2 end (14.07, 27.37): via, then In1 east and north | (27.2, 38.0) In1 → D2 column |
| GND | A's In1 run ends in F at (1.1, -40.6). The new run goes to a via at (2.77, -44.9), then F.Cu to C148-2 on the F / C edge. | closes C148-2 |

Why the taps use In1: In2 is cut by the kept GPIO_BYPASS_RLY_ISO run (diagonal and vertical at x 22.1), so the taps
hop once. In1 is free in F. In the D2 column between J38 and J37 (x 25.8 … 29.2 with J37's 2.5 mm), In1 is the one
free inner layer: GPIO_BYPASS_RLY_ISO crosses on In2 and 15V_ISO on In3. That is also the layer D's pass-1 tap copper
uses at (28.75, 58). The northernmost tap is the westmost, so the three runs do not cross. Over x > 23.6, F.Cu above
In1 is ISOPGND.

## Ports (net, point on the F edge, layer)

**To A, x = -2 (y -46 … -12).** A's sense block fence starts at (-17, -42), so the sigma-delta pair arrives at its
north-east corner.
- New:
  - MDATA -42.0 In3
  - ADCLK -44.0 In2
- Kept v4 copper:
  - Net-(R2-Pad1) -18.91 In2
  - Net-(R5-Pad1) -21.2 In2
  - Net-(U1A-+) -23.2 In2
  - Net-(U1A--) -24.7 In2
  - GPIO_BYPASS_RLY -39.3 In1
  - GND -40.6 In1

**To B, x = -38 (y -12 … 38), all kept.**
- ISOGND 19.17 In1
- 15V_ISO 19.17 In2
- GPIO_BYPASS_RLY_ISO 21.3 In2
- ISOPGND 12.5 / 35.0 B.Cu (pour)

**To D2, y = 38.**
- New:
  - ISOGND x 13.27 In1
  - 15V_ISO x 16.4 In3
  - Net-(U7B--) x 26.0 In1
  - Net-(U2-+) x 26.6 In1
  - Net-(U2--) x 27.2 In1
- Kept:
  - Net-(U7B-+) x 2.85 In1 (pass 1, D's run continues to (20.45, 56.05))
  - GPIO_BYPASS_RLY_ISO x 22.14 In2
  - AC_OUT_1 x -31.5 B.Cu
  - AC_OUT_2 x -28.4 / -20.6 / -20.0 B.Cu
  - Net-(U7B-+) B.Cu meander x -1.0 … 0.8, which dips 0.45 mm into D2 between R67 and the via
- The D2 trunks for the taps go up In1 between J38 and J37 to D's pass-1 ends at (28.75, 57.89 / 58.5) In1. D's
  U7B-- end is (60.0, 55.45) In3.

**To E, x = 40: E's points, met as they are.**
- MDATA (40, -22) In3 (new F copper starts here)
- ADCLK -19.99 In2
- R2 -11.32, R5 -13.59, U1A+ -15.68, U1A- -18.2: all In2
- VCC -24.11 In2
- GPIO_BYPASS_RLY -27.52 In1
- 15V -45.11 B.Cu (C's trunk)

**To C, y = -46, kept.**
- VCC 6.52 In2
- 15V 32.75 B.Cu
- GND: C148-2 (2.77, -46.0), the pad on the edge, now closed

## What stays open (one end in F) and why

| Net | Open between | Reason |
|---|---|---|
| MDATA | port (-2, -42) and R55-2 in A | A's half of the trunk |
| ADCLK | port (-2, -44) and U5-7 in A | A's half of the trunk. On the E side R22-2 is still open (E). |
| ISOGND | port (13.27, 38) and J24-9 | D2: 4.3 mm straight north on In1 |
| 15V_ISO | port (16.4, 38) and D's In3 run at (16.4, 43) | D2: 5 mm straight north on In3 |
| Net-(U2-+), Net-(U2--), Net-(U7B--) | D2 column ports and D's pass-1 tap ends | the D2 / D trunk |
| DC+ | "v6 bus DC+ In1 / In3" (C) and "Proteus F.Cu pour 5" (the part in F) | pour stitching between C's bus and the F.Cu pour; it belongs to the integration step (plane vias and stitching), not to F |

## Part moves, rule areas, via-in-pad

- No part moved and no rule area changed.
- No via is inside a pad. The GND via stands 1.1 mm beside C148-2.
- **Kept on purpose:** C's pass-1 15V B.Cu trunk at F's south-east corner, the pass-1 U7B-+ link, and ADCLK's v4
  tail into C (note 2).
- **Deleted:** the two dead v4 diagonals ISOGND In1 / 15V_ISO In2, (10.27, 19.17) → (23.0, 31.9).

## Renders

`reports/v6/blocks/block_F/F_<layer>.png` holds one image per copper layer, and `F_inner.png` shows In1 + In2 + In3
stacked. All are of the refilled replayed board, x -40 … 42, y -48 … 48. What I saw in them:
- **In1:** ISOGND turns north at x 12.6 off the v4 run. The three taps run east and then north as a 0.6 mm bundle at
  x 26 … 27.2 to the D2 edge, and they do not cross. GND drops to C148 at the bottom.
- **In3:** MDATA runs down E's edge and along y -42 to x -2. 15V_ISO runs up x 16.4. In3 is otherwise empty in F.
- **In2:** the kept v4 lanes are unchanged. 15V_ISO ends at its via, and ADCLK's new branch is at the bottom left.
- **F.Cu / B.Cu:** the pours are whole. The new vias in the ISODC+ pours have their round 2.5 mm clearances.

## What was wrong in the brief

1. **The neighbours are not where the brief put them.** A is south-west of F and overlaps F's rectangle at x < -2,
   y < -12. B is west, and D2 covers F's top 8 mm (y 38 … 46). So F is an L shape, and its A ports lie on x = -2, not
   on the west edge.
2. **"Start clean" did not apply.** At 3227a58 there were 0 open connections inside F. Its copper is kept v4 copper
   that makes the divider chains. Pass 1 added only about 40 items in F: C's 15V trunk and the U7B-+ link, both kept.
   The block's real work was the 8 crossing nets, and they needed no router: 24 drawn tracks and 5 vias.
3. **The step-03 board for clean-up matching is not available in a fresh worktree.** `build/` is empty, and
   `chain.sh 00 03` writes `kicad/ac_psu.kicad_pcb` (the permission check refused it). I used a diff of the 870c026
   and 3227a58 boards instead. Steps 01 / 02 touch only block G, and step 03 only deletes, so the result is the same
   for F.
4. **The `tools/p2k` submodule is not checked out in an agent worktree.** I linked `tools/p2k/bin` and `tools/p2k/p2k`
   to the main checkout's copies. They are not committed.
5. **"U7 / U2" are not in F.** They are in E. The taps cannot use window E-F (barrier strip, see block_E.md); they
   reach E through D2 and D.
6. **"No copper groups without a pad" cannot hold strictly yet.** The ADCLK group has no pad until E closes R22-2. The
   base passes only through the IPC via on the v4 tail.

## Time used

About 1.5 h, of which about 15 min was DRC runtime.
