# v6 plan: baseboard for six half-bridge power cards (for the Opus 5.5 worker)

Written 2026-11-22 by Claude Fable 5.2, who takes the design decisions for this draft. The user abandoned the v5
TO-247 power stage on 2026-11-22: the switches, gate drivers and switch nodes move onto six vertical cards
(`~/dev/hb_power_card-rev1/CARD_REV1_PLAN.md`). Do the card first, then this board.

## 1. Goal

A first draft of the v6 baseboard: schematic changed, power strips cleared, card terminals and headers placed, the
whole board routed, checks passing. It is a draft: nothing is ordered, nothing is pushed.

This worktree is `~/dev/ac_psu_kicad-v6`, branch `v6-baseboard`, cut from `v5-layout` at ccedf45 (step 19 board:
aux supply and card area placed, not routed).

## 2. Read first

1. `~/dev/hb_power_card-rev1/BASEBOARD.md` §1–§5 and §7d: what leaves the board and what arrives.
2. `~/dev/hb_power_card-rev1/CARD_REV1_PLAN.md` §4 (CTRL pinout) and §8.
3. `STATUS.md` here, from the top down to v5 step 15: board state and what seven routing passes found.
4. `V5_PLAN.md` and `V5_LAYOUT_PLAN.md` §3 (hard constraints; they still apply where this plan is silent).
5. `reports/v5_layout/routing_brief.md`, and the branch `routing-pass7` (`tools/v5/route_pass1/`): the routing
   chain to start from.
6. `~/dev/efinix_soc_board/AGENTIC_PCB_ROUTING.md` and the `kicad-agentic-routing` skill.

## 2a. Environment (facts that are not in the repo)

- KiCad 10.0.7 exists only as `~/kicad/kicad-10.0.7-x86_64.AppImage`. Do not run it directly (the GUI hangs);
  use `tools/p2k/bin/kipy` (pcbnew Python) and the scripts in `tools/`, which mount it. `tools/check_all.sh`
  passed in this worktree on 2026-11-22 and takes about 8 minutes.
- Router: `~/dev/KiCadRoutingTools` (KRT).
- Control card (ordered, fixed): `~/dev/efinix_soc_board`; its real hole positions are in
  `kicad/ti135_card.kicad_pcb`, not in its MECHANICAL.md.
- Today's gate card: `~/dev/ac_psu_gate_drive`.
- The board edge is about 2 mm from each heatsink face (measured on the built unit).
- An Agent-tool worktree is cut from `main`, not from this branch: tell a routing subagent to start from the
  commit you want.

## 3. Working rules

- The schematic is generated: change `tools/sheets/sheetNN.py`, never the `.kicad_sch` files.
- The board is changed only by numbered scripts `tools/v6/v6_N_<name>.py` with a fixed seed, one commit per step,
  a log in `reports/v6/`, and a STATUS.md entry on top (same style as the v5 steps).
- `tools/check_all.sh` must pass after every step. The Proteus comparisons get the v6 differences from
  `lib/v6_deviations.csv` and `lib/v6_copper.csv` (same mechanism as v4 / v5). The two cleared strips are listed
  as areas, the removed parts by refdes.
- pcbnew traps are in the STATUS.md history: use `board.Delete()`, reload the board before a zone fill, script
  zone fill ignores `.kicad_dru`, a zone keeps only its first outline.
- A choice this plan does not cover: take the option that keeps the draft moving and record it in STATUS.md under
  "Decisions taken by the worker" with the reason.
- Stop and ask only for the items in §8.
- Do not push, do not order, do not touch `v5-layout` or `main`.

## 4. Decisions: what stays fixed

| Item | Decision |
|---|---|
| Outline, mounting holes, PE screws PE1–PE8 | unchanged (the unit's heatsinks and enclosure exist) |
| Control card connectors J11 / J12 and their pin nets | unchanged: the control card is ordered |
| Stackup and layer roles | 6 layers, JLC06161H-3313; In3 routing, In4 ground, as on v5 |
| Insulation | P–I 5.0 mm, P / I–PE 2.5 mm, CTRL barrier as on v5; high-voltage nets 2.5 mm functional |
| Aux flyback area (T1, U18 and their parts) | placement stays; it gets routed in this pass. Small moves by script are allowed if routing needs them |
| Isolators U13 / U16 / U19 / U20 / U21 and their channel assignment | unchanged; only the far ends of the nets move |
| Bulk caps, Y caps, AC input and output filters, relays, measurement circuits not named in §5 | unchanged |

## 5. Decisions: what changes

### Removed

Q1–Q12; headers J1, J2, J3, J4, J6, J8; Fastons DAB_PRI_1 / DAB_PRI_2 / DAB_SEC_1 / DAB_SEC_2; DAB split caps C1,
C35, C45, C46, C47–C50; switch-node sense R48 + U5 + D8 + R59 and R91 + U4 + D9 + R94 + C55 + C78 with their input
filters and local supplies. Every net that then has no pin left is removed. Check the list against the schematic:
if a part on it also serves something that stays, keep it and record why.

### Added, per card (six times)

| Part | Decision |
|---|---|
| CTRL header | keyed 2×5 1.27 mm, the part and pinout of CARD_REV1_PLAN.md §4, net map of BASEBOARD.md §4 (PWM_HI, PWM_LO, PWM_TRANS, 15 V, 5 V, GND per domain; MDAT / MCLK only at AFE leg 1 and inverter leg B). Unused MDAT / MCLK pins are no-connects |
| DC+ and DC− terminals | the same M3 REDCUBE as on the card, pad centres ≥ 10 mm apart, ≥ 2.5 mm between the pads and between each lug circle (8 mm) and other-net copper |

- PWM_TRANS1…6: one per card as in BASEBOARD.md §4.
- MDAT at AFE leg 1 goes to R55 (MDATA), MCLK to ADCLK; at inverter leg B to R50 (MDATA_INU) and INU_ADCLK.
- The DAB secondary card's DC− terminal is DAB_GROUND, then R64 to ISOPGND as today.
- Add 100 nF on 15 V and 5 V at each header.

### Added, once

- **U6 supply:** a 5 V regulator from 15V_ISO for U6 side 1, feeding the node R75 fed before. Use the regulator
  type already used for the removed U4 / U5 side-1 supplies if it takes 17 V in; otherwise a 5 V LDO already in
  the BOM. Reference is the DAB_GROUND / ISOPGND side as today.

### Switch-node landing terminals

J5, AFE_OUT1, INU_OUT2 and J7 stay as wire landing points (card SW wire in, choke lead or output out). With R48
and R91 gone, each is one net with the pads of the choke lead or output it serves.

- **INU_OUT2 moves out of the routing passage** north of J11 (it left 2.9 mm there). Put it beside the inverter
  output path, clear of the card's back-side envelope.
- J5 and J7 may move if that shortens the path to the choke-lead pads.

### Placement

- Card centres at x 32.2, 66.2, 100.2 on each wall, order as in BASEBOARD.md §3.
- No part taller than 4 mm within 24 mm of either wall inside the card span (the cards hang there, bottom edge 4 mm
  above the board). No DC or switch-node copper within 2.5 mm of the board edge along the walls.
- Each card's terminal pair and header: 26–34 mm from the wall, within ±12 mm of the card centre in x, header on
  the DC− side of the pair. Where bulk caps or other fixed parts are in the way, move along x first, then further
  from the wall, and record the position.
- The freed strips are otherwise for routing and for the DC pours.

### Copper

- DC+ / PGND from the bulk caps to the three primary terminal pairs, ISODC+ / ISOPGND to the three ISO pairs:
  pours ≥ 10 mm wide on an outer layer, doubled on a second layer where a neck is narrower. Each pair carries up
  to 20 A RMS.
- **ISO DC bus past J11:** the wire links BUSP1 / BUSP2 / BUSN1 / BUSN2 stay unless the freed ISO strip gives a
  copper path at least 8 mm wide on two layers with all clearances. If it does, replace the links by copper and
  record it; if it is close, keep the links.
- Ground pour on In4 extended over the freed strips, per domain. No power-stage copper is left there.

## 6. Steps

1. `v6_1`: schematic changes of §5 (sheets 1, 4, 5, 6, 8, 11 as needed), new symbols and footprints, deviation
   lists, ERC and netlist checks passing.
2. `v6_2`: remove the old footprints, their tracks and pours from the board; cut the pours back.
3. `v6_3`: place the terminals, headers, U6 regulator and the moved landing terminals. Render both sides with the
   card envelopes drawn. `tools/v5/check_layout.py` gets the v6 rules of §5 (or a `tools/v6/check_layout.py`).
4. `v6_4`: DC pours and ground pours; island counts before and after.
5. Routing, as a rerunnable chain on its own branch per pass (`v6-routing-passN`), merged into `v6-baseboard` only
   when the pass is legal:
   - supplies and grounds first in the aux area (pass 5–7 lesson), then the HV aux nets drawn by script, then the
     CTRL-side buses, then the rest;
   - the 2.5 mm high-voltage rule is in pad clearances only: give it to the router as an explicit rule per net;
   - compare every pour's island count before and after each pass.
6. Done when: 0 unconnected (wire links excepted), 0 DRC errors, parity 0, `domain_gaps` and the layout check OK,
   `check_all.sh` passes. Then a STATUS.md review list for the user: renders per layer, decisions taken, items to
   verify, and what differs from v5.

If routing does not close after three passes, do not keep iterating: write up which nets are open and why, and
propose one placement change.

## 7. Not in this draft

Fab files, the JLC BOM update, ordering, the noise fixes that are not already in v5, any change to the control
card.

## 8. Stop and ask

- A change to J11 / J12 pin nets, the outline or the mounting holes.
- An isolator channel that has to change.
- A card interface change that CARD_REV1_PLAN.md §8 does not allow.
- A fixed part of §4 that must move more than a few millimetres.
