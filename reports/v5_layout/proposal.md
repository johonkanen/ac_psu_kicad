# v5 card-area layout: proposal (V5_LAYOUT_PLAN.md phase 1)

2026-11-15, branch `v5-layout`. **No board change yet.** Coordinates are mm in the IPC frame (Y up).

- Phase 0: `tools/check_all.sh` → ALL CHECKS PASSED; `tools/regen_check.sh` → OK.
- Geometry: `tools/v5/card_layout.py` (areas, barrier lines, slots, keep-outs, rough positions).
- Check and renders: `python3 tools/v5/layout_proposal.py` → `check.txt`, `parts.csv`, `proposal_*.png` here.
  It ends with `layout_proposal: OK`.
- Updated 2026-11-15 after the user's answer: the Ti60 card must fit (finding 9).

## 1. Findings that change the plan

Decide these before phase 2. My recommendation is first in each row.

| # | Finding | Proposal |
|---|---|---|
| 1 | **The plan's card keep-outs are out of date.** The card board (`~/dev/efinix_soc_board/kicad/ti135_card.kicad_pcb`, 2026-11-15) was re-placed after MECHANICAL.md was written. J1 (JTAG) is now at x 103.7…113.9, y −3.35; J2 (UART) at x 103.7…108.8, y −7.45; J101 at x 111.6…114.1, y −12.9; J5 (LCD, 14 pins) at x 64.0…97.0, y −16.4. The west-edge J1/J2 keep-out of the plan no longer exists. | Take the keep-outs from the card's real holes (drill/2 + 1.5 mm, in `card_layout.py`). Update MECHANICAL.md and the plan table. |
| 2 | **U8 is 1.89 mm from J12** (U8 pin 3, 5V_ISOL ↔ J12 pin 48); C94 is 4.48 mm away. ISO ↔ CTRL needs 5.0 mm. | Move U8 with C93/C94 13.36 mm west to (91.0, −20.1), along its own 15V_ISO / ISOGND pours. Trim those pours to x ≤ 102.2. U8 is outside the card outline, so this needs your approval. |
| 3 | **The J12 CTRL piece needs about 440 mm² per side** (two 8×10 polymer capacitors, L2, the buck, W1, J13, PEC2). The corner at J12 alone gives 250 mm². | Move U10, C3, C4 (3V3_ISO regulator) out to (97.5, 0.8) and let the J12 piece run from y −34.5 to +3.0 along the board edge. REF2 and its parts stay. |
| 4 | **The J11 fan-out tracks cross the new isolator row** (U19–U21 CTRL pads at y 35.8…37.9). | U13 and U15 stay where they are, with their primary-side routing. All 81 CTRL-side tracks of the J11 fan-out are deleted and re-routed. |
| 5 | **J8 ↔ J11 is 5.37 mm** (J8 pin 16, Q5_S ↔ J11 pin 38). It passes, with 0.37 mm to spare. The path from U21 to U4 must go north of J11 at y ≥ 51.1, between J8 and J6. | No part moves. The ISODC+ / ISOPGND pours end at x ≤ 39.4 west of J11 and at y ≥ 51.1 north of it. |
| 6 | **Layer order.** The plan suggests In3 = ground, In4 = routing. In JLC's stack In4 is 0.10 mm from B.Cu and 0.55 mm from In3, so B.Cu would have no ground next to it. | In3 = routing, In4 = ground (section 4). Both outer layers then have a ground plane 0.10 mm away. |
| 7 | **Heights of the hand-fit parts.** J14 is a vertical 2.54 mm header (8.5 mm, more with a plug): it cannot sit on top under the card (5.3 mm gap). PEC1's screw and lug do not fit there either. | J13 and J14 on the bottom, as right-angle headers or soldered wires (a plugged vertical header exceeds the 10 mm bottom limit). PEC1/PEC2 lugs on the bottom; on top only the trimmed pin. |
| 8 | **Slots and strength.** Slots on every free run would leave the J11 piece hanging on narrow webs, and J11 takes the card's insertion force. | Slots under the nine isolators and U17, plus five runs (section 3). No slot on the west and north side of J11; ≥ 2 mm webs. The 5.0 mm copper gap alone meets the printed-wiring creepage there. |
| 9 | **The Ti60 card must fit too (user, 2026-11-15).** Its JTAG tails (x 69.4, y 27.7…37.8) and UART tails (x 63.5, y 32.9…37.9) would land on the CTRL pads of U19 and U21 if those sat on top. | **Decided: U19, U20 and U21 go on the bottom side**, at the same positions, with their decoupling next to them on the bottom. All Ti60 holes (JTAG, UART, 5 V header, LCD, RJ45, from its IPC netlist) are keep-outs now, next to the Ti135 card's. No placed or moved part lies under a tail of either card (`check.txt`). The Ti60 card's own bottom-side parts are small passives where new top-side parts go; nothing tall meets anything tall. |
| 10 | Card J5 pin 8 at (81.76, −16.4) is 2.0 mm from the centre of mounting hole H4 (screw head). C36, R37 and U14 also sit under J5 tails. All are v4 parts and stay. | Trim the J5 tails (the card's STATUS already says so). No baseboard change. |

## 2. Parts

Full table: [`parts.csv`](parts.csv) (ref, value, footprint, domain, action, side and position now, area, proposed
side and rough position, note). Positions are rough; phase 3 sets exact positions and rotations, and
`check_layout.py` checks them.

| Action | Count | Parts |
|---|---|---|
| **place** (v5, from staging) | 71 | Sheet 11: all 52. Sheet 7, J12 piece: W1, D16, C137–C144, R131–R135, U28, L2, J13, PEC2 |
| **move** (v4) | 33 | U16, C81, C82 · U7 with C38, C56, C103–C108, R46, R51–R54, R56 · U2 with C2, C87, C101, C102, R1, R76, R77 · U10, C3, C4 · R97 · U8, C93, C94 |
| **fixed** (v4, courtyard in the card outline) | 77 | J11, J12, U13, U15, C83, C86 · all primary logic (U1, U3, U11, U12, U14, AD1, REF1, L1 and their R/C: 49 parts) · U6, R64 and their parts, REF2 group, C92 · U17 (spare) · H4, C15, C36 |
| stay staged | 27 | The sheet-7 flyback parts (T1, U18, Q15–Q17, D11–D15, …): out of scope |

No fixed pad breaks the proposal: every fixed pad lies in an area of its own domain and ≥ 5.0 mm from the other
domains' areas.

Where the groups go:

| Group | Area | Side | Rough position |
|---|---|---|---|
| U15, U13 (fixed), U16 | CTRL (J11) \| primary | top | y 18.3, x 56.0 / 68.0 / 80.0; U16 turns from −135° to −90° |
| U21, U19, U20 | CTRL (J11) \| ISO | **bottom** | y 41.5, x 57.3 / 68.5 / 79.7; CTRL pins south, ISO pins north |
| U22, U23, U24 (AMC1311) | ISO \| CTRL (J11) | **bottom** (phase 2: the DWV package can be 2.8 mm, above the 2.65 mm top limit) | x 92.5, y 36.7 / 29.9 / 23.1; VIN side east |
| U25, U26 and R116–R127, C132, C133 | CTRL (J11) | top | x 74.5…85.4, y 24.5…35.0, next to the AMC1311 outputs |
| R128–R130, C129–C131 (output filters) | CTRL (J11) | top | x 48.0…50.4, y 24.6…30.5, at J11 pins 1/3/4 |
| U27, C134–C136; J14; PEC1 | CTRL (J11) | bottom; THT | (62.5, 30.0); (55.5, 30.0); (50.3, 33.0) |
| U16 and AMC1311 decoupling (C82, C123–C128) | each side's area | C82 bottom, C123–C128 top | opposite pin 1 / 8 of its IC, two vias each |
| U19–U21 decoupling (C117–C122) | each side's area | bottom | beside pin 1 (y 34.7) and pin 16 (y 48.3), same side as the IC |
| R110–R115 (×0.4 dividers) | ISO | top | column x 99.2…100.8 at each AMC1311 VIN |
| U7 block, U2 block | ISO | top | x 95.5…106.0, y 14.5…20.3; x 95.5…104.0, y 8.5…13.8 (next to REF2) |
| U10, C3, C4; R97; U8, C93, C94 | ISO | as now | (97.5, 0.8); (99.6, 43.0); (91.0, −20.1) |
| C81 | primary | top | (84.4, 11.3), south of U16 pin 16 |
| C137, C138 (polymer, 10 mm) | CTRL (J12) | bottom | (112.6, −1.6) and (112.6, −10.6), under the card |
| L2, U28 and its parts, C142, C143, J13 | CTRL (J12) | bottom | x 107.4…117.9, y −28.5…−13.5 |
| D16; W1; PEC2 | CTRL (J12) | top; THT | (109.5, −24.5); (107.2, −31.2); (115.3, −31.6) |

Quality rules of the plan and how the proposal meets them:
- U19/U20 ISO pins face J4/J6/J8 (3 mm below the J6 pads), on the bottom side. PWM_Q5–Q8 and TRANS4–6 leave straight north on B.Cu.
- U21 is the west-most isolator: about 50 mm to U4 and 65 mm to U6.
- U13/U15/U16 primary sides stay next to the primary logic.
- The six divider taps of U7/U2 come from x −15…−2 (R67, R68, R71, R82, R85, R256). They now cross the top band
  y 44…49 next to the PWM bundle: route them on In3 under the ISOGND plane (routing list, phase 4).

## 3. Domain boundaries

Each domain has a **copper area** valid on all six layers. Every pair of areas is ≥ 5.0 mm apart
(`check.txt`: CA–I 5.00, CA–P 5.00, CB–I 5.00, I–P 5.00, CB–P 21.7 mm). The barrier centre line runs 2.5 mm from
both.

| Area | Nets | Copper area (polygon) | mm² |
|---|---|---|---|
| **CA** CTRL at J11 | CTRLGND_A, 3V3_CTRL, 5V_CTRL_A | (44.4, 20.8) (90.0, 20.8) (90.0, 39.0) (47.3, 39.0) (47.3, 46.1) (44.4, 46.1) | 851 |
| **CB** CTRL at J12 | CTRLGND, 5V_CTRL, CTRL_RAW | (107.2, 3.0) (118.1, 3.0) (118.1, −34.5) (102.5, −34.5) (102.5, −27.0) (107.2, −27.0) | 444 |
| **P** primary | GND, VCC | (42.55, −20.66) (69.65, −20.66) (69.65, −3.36) (85.5, −3.36) (85.5, 15.8) (42.55, 15.8) | 1292 (card part) |
| **I** ISO | ISOGND, 3V3_ISO | (52.3, 44.0) (52.3, 46.38) (118.1, 46.38) (118.1, 8.0) (102.2, 8.0) (102.2, −9.4) (90.5, −9.4) (90.5, 15.7) (93.0, 16.2) (95.0, 18.0) (95.0, 44.0) | 1230 (card part) |

P is today's GND plane outline with the top edge at 15.8 (was 14.95) and a square north-east corner. P and I
continue outside the card as today.

Barrier centre lines:

| Line | Between | Polyline |
|---|---|---|
| B-CP | CTRL \| primary | (41.9, 18.3) → (87.75, 18.3) |
| B-CI north | CTRL \| ISO | (41.9, 18.3) → (41.9, 46.8) → (43.3, 48.5) → (47.2, 48.6) → (49.3, 47.6) → (49.8, 46.1) → (49.8, 41.5) → (92.5, 41.5) |
| B-CI east | CTRL \| ISO | (92.5, 41.5) → (92.5, 19.4) → (90.8, 18.3) → (87.75, 18.3) |
| B-PI | primary \| ISO | (87.75, 18.3) → (88.0, 15.8) → (88.0, −3.36), then as today |
| B-IC J12 north | ISO \| CTRL | (104.7, 5.5) → (118.6, 5.5) |
| B-IC J12 west | ISO \| CTRL | (104.7, 5.5) → (104.7, −27.0) → (100.0, −27.0) → (100.0, −34.5) |

Each line gets a 5 mm wide rule area on all copper layers (no tracks, vias or zones; footprints allowed).

Pad rows against the strip (inner pad edge to inner pad edge): Proteus SOIC-16W 7.51 mm, KiCad SOIC-16W 7.25 mm,
SOIC-8W (AMC1311) 8.85 mm. All leave ≥ 1.1 mm on each side of the 5 mm strip.

Slots (Edge.Cuts, 1.2 mm wide, rounded ends, each ≥ 1.4 mm from any copper area):

| Slot | From – to | Length |
|---|---|---|
| U15, U13, U16 | y 18.3: x 51.5–60.5, 63.5–72.5, 75.5–84.5 | 9.0 each |
| U21, U19, U20 | y 41.5: x 52.8–61.8, 64.0–73.0, 75.2–84.2 | 9.0 each |
| U22, U23, U24 | x 92.5: y 34.4–39.0, 27.6–32.2, 20.8–25.4 | 4.6 each |
| U17 (spare), P\|I run | x 88.0: y −4.0–5.0, 7.0–13.5 | 9.0, 6.5 |
| C\|P west run | y 18.3: x 44.5–49.5 | 5.0 |
| J12 north, west a, west b | y 5.5: x 107.0–116.0; x 104.7: y −11.0–2.5, −25.0–−13.0 | 9.0, 13.5, 12.0 |

Webs between slots are ≥ 2.0 mm. See finding 8 for the runs left without a slot.

## 4. Layer plan

Stack order F.Cu, In1, In2, In3, In4, B.Cu. Every zone of a domain uses that domain's copper area, so no two domains
overlap on any pair of layers.

| Layer | CTRL (J11) | CTRL (J12) | Primary | ISO | Outside the card area |
|---|---|---|---|---|---|
| F.Cu | parts, routing | parts, routing, CTRLGND pour | parts, routing (as today) | parts, routing | unchanged |
| In1 | CTRLGND_A plane | CTRLGND plane | GND plane (today's) | ISOGND plane | unchanged |
| In2 | 3V3_CTRL plane | 5V_CTRL plane | VCC plane (today's) | 3V3_ISO plane | unchanged |
| In3 | routing | routing | routing | routing (divider taps, sigma-delta) | empty |
| In4 | CTRLGND_A plane | CTRLGND plane | GND plane | ISOGND plane | empty |
| B.Cu | parts, routing | parts, routing, CTRLGND pour | parts, routing (as today) | parts, routing | unchanged |

- In1 and In4 are never routed. In2 is a supply plane; short hops only if nothing else works.
- Outside the card area In3/In4 stay empty: the power stage needs no extra copper, and every through-hole pad and via
  gets its ring on the new layers anyway, which `domain_gaps` then checks on all six layers.
- The ISODC+ (B.Cu) and ISOPGND (F.Cu) pours keep their nets and are pulled back from CA and P by the DRC rules.

## 5. Stack-up

JLC 6-layer 1.6 mm, **JLC06161H-3313** (the stack of the Ti60F225 tube-PSU card, from that repo's
`docs/jlcpcb_production_checklist.md`; I did not re-check JLC's site today):

| Layer | Thickness (mm) | Copper |
|---|---|---|
| F.Cu | 0.035 | 1 oz |
| prepreg 3313 | 0.0994 | |
| In1 | 0.0152 | 0.5 oz |
| core | 0.55 | |
| In2 | 0.0152 | 0.5 oz |
| prepreg 2116 | 0.1088 | |
| In3 | 0.0152 | 0.5 oz |
| core | 0.55 | |
| In4 | 0.0152 | 0.5 oz |
| prepreg 3313 | 0.0994 | |
| B.Cu | 0.035 | 1 oz |

Total 1.54 mm plus solder mask. The board file holds 2.267 mm today (the Proteus stack); phase 2 sets 1.6 mm.

- **Inner copper 0.5 oz:** acceptable. No power-stage current runs on In1/In2. They hold the logic planes, the
  gate/source patches under J1–J8 (pulsed gate current) and the 15V_ISO return (194 mm², below 1.5 A). The largest
  new plane current is 5V_CTRL, about 1.15 A across a ≥ 10 mm wide plane. The PE bonds of PEC1/PEC2 go on the
  1 oz outer layers.
- **Insulation:** the three prepregs (0.10–0.11 mm) are below 0.4 mm, so the plan's rule stands: the same 5 mm gap
  on all six layers. The two 0.55 mm cores are above 0.4 mm, but the proposal does not use that.

## 6. Renders

Domain areas (green CTRL, red primary, blue ISO), barrier centre lines (dashed), slots (orange) and the proposed
positions (black) over today's board:

- [`proposal_F.png`](proposal_F.png): top side. Purple circles = the Ti135 card's through-hole keep-outs; brown
  circles = the Ti60 card's (finding 9).
- [`proposal_B.png`](proposal_B.png): bottom copper (seen from the top) with the bottom-side parts.
- [`proposal_In1.png`](proposal_In1.png), [`proposal_In2.png`](proposal_In2.png): today's planes under the new areas.

## 7. What phase 3 deletes

539 v4 tracks and vias become ratsnest (`check.txt`):

| Count | What |
|---|---|
| 261 | ISO copper in or within 5 mm of the J11 CTRL piece (old ISOADA routes, PWM remnants, 5V_ISOL) |
| 105 | ISO copper in or near the J12 CTRL piece (5V_ISOL to U10 and up the east edge, U8) |
| 81 | The J11 fan-out in the CTRL piece |
| 77 | Tracks and vias on nets of moved parts (U16, U7, U2) |
| 15 | CTRL tracks near the primary or ISO areas |

Zones: In1 ISOGND, In2 3V3_ISO and In1 GND / In2 VCC are replaced by one zone per domain per layer. Eight small
pours at U10, U8 and C15 are moved or trimmed. ISODC+ and ISOPGND are pulled back.

## 8. Routing hand-off (from the agentic routing documents)

I read `~/dev/ti60f225_tube_psu_control_card/docs/io_routing_brief.md` and the write-up
`~/dev/efinix_soc_board/AGENTIC_PCB_ROUTING.md`. What I take from them:

- **Fixed layer roles**, as in section 4: which layers carry signals and which are never routed.
- **A placement script that can be rerun.** I develop `v5_4_card_area.py` against a copy in `build/` until
  check_layout and the renders are right, then run it once on the board (the repo rule stays: one committed
  script, refuses to run twice).
- **Two more checks** in `check_layout.py`: each plane is one island per area and reaches all its vias; no tracks
  on In1/In4.
- **Render review after every run**, per layer, not only DRC numbers.
- **Swap groups, so routing can untangle by swapping instead of adding vias:**
  - the 12 forward channels of U19/U20 (10 used; the J11 pin and the J4/J6/J8 pin of a net stay);
  - same-direction channels within U13, U15 and U16;
  - the three AMC1311 chains (U22–U24) and the op-amp halves of U25/U26.
  Each swap is a change in `tools/sheets/sheet11.py`, then regenerate and re-run the checks.
- **A routing brief** as the phase 4 hand-off: goal, layers, rules, net groups in order (sigma-delta pairs and the
  divider taps first, then the PWM bundle, then the rest), known traps, and the report to return.

The plan keeps routing with you in the GUI. The brief would also let a routing agent (KiCadRoutingTools, as on
the Ti60 card) do the low-voltage nets inside the card area. That answers the plan's open item on Freerouting:
I would use KRT, because it is already proven on your boards. Your choice.

## 9. Decisions (user, 2026-11-15)

1. U8 (with C93/C94) and U10 (with C3/C4) move as proposed.
2. In3 = routing, In4 = ground.
3. J13/J14: wires soldered into the holes, no headers.
4. Slots as in section 3, none around J11's west and north side.
5. The Ti60 card must fit: U19–U21 on the bottom.
6. Stack-up JLC06161H-3313, 0.5 oz inner copper.
7. Routing by a routing agent (method: `~/dev/efinix_soc_board/AGENTIC_PCB_ROUTING.md`).

## 10. What changed after the proposal (phases 2 and 3)

The sections above are the proposal as approved. The board as placed (`tools/v5/v5_4_card_area.py`, geometry in
`tools/v5/card_layout.py`, renders `card_*.png`) differs in these points:

| Point | Proposal | As placed | Why |
|---|---|---|---|
| Isolator row U21, U19, U20 | y 41.5, top, then bottom | **y 35.5, bottom**, x 57.05 / 68.0 / 78.95 | The band y 43.2…48.8 carries the DC bus between the ISO DC link and the DAB secondary (F.Cu ISOPGND, B.Cu ISODC+). The proposal put the ISO pins into it. Now the band has no parts, and the signals reach J4/J6/J8 on In3 under it. |
| U22 (AMC1311) | east line | in the isolator row at (87.75, 35.5) | The shorter east line holds two AMC1311, not three. |
| U22–U24 | top | bottom | The DWV package can be 2.8 mm; the top limit is 2.65 mm. |
| East barrier line | x 92.5 | x 97.6 | Room for the four parts in the row. |
| CTRL area at J11 | x 44.4…90.0, y 20.8…39.0, 851 mm² | x 44.4…95.1, y 20.8…33.0 (+ the J11 column), 657 mm² | Follows from the two rows above. |
| Difference amplifiers, U27 | top | bottom, below the isolator row | Same side as the AMC1311 outputs; the top side stays free under the Ti60 headers. |
| U7 and U2 blocks | new arrangement | moved as they are, with their tracks, to x 95.2…106.5, y 8.5…15.5 and x 94.3…101.5, y 1.7…8.2 | Keeps the proven v4 routing of the op-amp circuits. |
| R97 | moved | stays | No conflict left. |
| J12 piece | PEC2, W1, D16 south | C138 under D16 (rectifier loop), C137 and L2 under the card, U28 on top between the card's tail rows | Exact placement against the Ti135 and Ti60 tails. |
| Slots | 15 | 15, at the new part positions (`card_layout.SLOTS`) | |

**Found during placement, open:** the DC bus itself has been cut at J11 since v5 step 1. ISODC+ (B.Cu) and ISOPGND
(F.Cu) are each in two pieces, west and east of J11, because the pours must keep 5 mm from J11 and J8 / INU_OUT2
close the corridor north of it. STATUS.md lists the options.
