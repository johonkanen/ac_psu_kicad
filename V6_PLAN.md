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
- No part taller than 4 mm within **18 mm** of either wall inside the card span (the routed card reaches about
  16 mm from the wall, its bottom edge 4 mm above the board; was 24 mm, planning session 2026-11-23). No DC or
  switch-node copper within 2.5 mm of the board edge along the walls.
- Each card's terminal pair and header: bodies **at least 20 mm** from the wall, terminal screw centres at least
  22 mm (straight screwdriver from above); within ±12 mm of the card centre in x where the board allows, header on
  the DC− side of the pair. Where bulk caps or other fixed parts are in the way, move along x first, then further
  from the wall, and record the position. (Was: 26–34 mm.)
- Lug circles (8 mm, on the 7 mm terminal top): 2.5 mm in plan view from parts taller than 5 mm (headers,
  terminals, through-hole capacitors) and from other lugs; flat parts and pads below the lug do not count.
- **Exceptions decided in step 3** (planning session 2026-11-23): the control card stands 5.3 mm above the board
  with its outline to y 46.36, so inverter leg A and the DAB secondary get **soldered pigtail holes** (two 3.0 mm
  holes per net, 6.0 mm pads, 10–16 mm from the wall) instead of REDCUBE terminals, and their headers stand
  horizontal between the control card edge and 18 mm from the wall. The baseboard then has four REDCUBE pairs,
  two pigtail pairs and six through-hole headers. AFE leg 1's pair stands west of the bulk caps C10 / C7.
  `tools/v6/check_layout_v6.py` checks these rules.
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
5. Routing (the aux flyback area goes to a helper agent, see §10), as a rerunnable chain on its own branch per pass (`v6-routing-passN`), merged into `v6-baseboard` only
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

## 9. Current sense stays on the baseboard, on the quiet side of the chokes (user 2026-11-23)

Supersedes §5 where it removes R48 / U5 and R91 / U4, and the MDAT / MCLK header pins. Reason: the sense parts did
not fit the card (CARD_REV1_PLAN.md §10).

- **R48 + U5 (AFE leg 1) and R91 + U4 (inverter leg B) stay**, with their input filters, D8 / R59, D9 / R94 and
  capacitors. They are no longer at the switch node: each shunt goes in series at the **other end of its choke**,
  between the choke lead that does not switch and the filter it feeds (AFE: the choke's line-side lead; inverter:
  the choke's output-side lead, today's J9 side). The choke current is the same at both ends, and the ADuM7701 then
  floats at a line-frequency node. Find the nodes in sheets 1 and 5; if a choke end is not on the board, say so.
- **Side-1 supply of U5 and U4:** it used to come from the gate cards (header pin 39). Now one small isolated DC/DC
  module per sensor, fed from the domain's 5 V (5V for U5, 5V_ISOL for U4), output 9–12 V into the existing
  resistor + 5.1 V zener (resistor rescaled), or 5 V out into a small LDO if the module's light-load voltage can
  exceed 5.5 V. Functional insulation is enough (both sides are inside one domain). Pick an in-stock part at JLC
  and record it.
- MDATA / ADCLK and MDATA_INU / INU_ADCLK stay on the board as today (R55, R50). **Pins 8 and 10 of all six card
  headers are no-connects.**
- J5 and J7 become plain landing terminals (card SW wire + choke lead), like AFE_OUT1 and INU_OUT2.
- Place each shunt and its ADuM7701 at the choke lead it serves, with the 2.5 mm high-voltage rule around the
  side-1 parts.
- Redo the parts of step v6_1 this touches before clearing the strips.

## 10. Aux flyback area: a helper agent delivers the routes as a script (user 2026-11-23)

One agent owns the routing chain and the board file. The aux flyback area is the one part split off, because it has
its own boundary, its own high-voltage rules and few nets leaving it, and it was what stayed open in v5 passes 4–7.

**When:** start the helper when step 3 (placement) is committed, so it works while the main worker does step 4
(pours) and the first chain steps.

**How:** the main worker spawns one helper with the Agent tool in its own worktree. An Agent worktree is cut from
`main`: tell it to check out the step 3 commit of `v6-baseboard` first.

**Helper's scope**
- Areas PX and IA of `tools/v5/card_layout.py` (`AUX_AREAS`, `HV_PADS`): T1, U18 and the parts placed by
  `tools/v5/v5_9_aux_area.py`, `v5_17_aux_gnd_pour.py`, `v5_18_u20_supply_vias.py`, `v5_19_aux_input.py`.
- Nets that lie wholly inside those areas, plus the stubs of leaving nets up to the area edge.
- It may move parts inside the areas by script and may add pours on inner layers inside them.
- It may not touch anything outside the areas, the planes that pass through, or the fixed items of §4.

**What it has to read:** STATUS.md entries for routing passes 4–7 and v5 steps 17–19 (what stayed open there and
why: AUX_VIN, AUX_LOVP, AUX_GATE, the GND pads beside HV pads, 15V), and `tools/v5/route_pass1/` on branch
`routing-pass7`.

**Method**
- Ground and supplies first (GND copper and vias, 15V), then the high-voltage nets drawn by script with the 2.5 mm
  rule as an explicit per-net clearance, then the remaining signals.
- Copper for U18's DRAIN pins: try the inner-layer area under T1 (open since v5 step 9) and report the area reached.

**What it delivers** (a script, not a board)
- `tools/v6/aux_routes.py`: a table of tracks, vias, zones and any part moves, with a fixed seed, that the main
  chain replays as one step on the current board; it must fail loudly if a pad it expects has moved.
- A boundary list: for every net leaving the area, the point and layer where it crosses the area edge. The main
  worker treats these as fixed entry points; if one has to move, the main worker says so and the helper redraws.
- A report in `reports/v6/aux_routes.md`: open connections inside the area (target 0), DRC and `domain_gaps`
  result on its own board, island count of every pour it touched before and after, renders per layer.

**Merging:** the main worker replays `aux_routes.py` early in the chain (before the CTRL buses), reruns DRC, parity,
`domain_gaps` and the island comparison on its own board, and only then keeps the step. The helper's branch is never
merged as a board file.

**If the chain stalls later:** the same pattern may be used to try two placements side by side (two helpers, each
reporting an open count; only the winner's script is kept), and for an independent review of a finished pass. Not
more than two helpers at a time.

### 10a. Memory limit (user 2026-11-23: the machine is almost out of memory)

Measured that day inside WSL: 19 GB in total, a single KRT router run of another project holds 4.4 GB, each Claude
session 0.3–0.5 GB, and other projects' sessions and router runs share the machine.

- **Never two router runs (KRT or `route.py`), zone fills or `check_all.sh` runs at the same time**, counting the
  helper's and the card's. Run them one after another.
- Before every router run, zone fill, `check_all.sh` or helper spawn: `free -g`. Start only if "available" is at
  least 6 GB; otherwise wait and look again, or do work that needs no memory (scripts, STATUS, reading).
- **At most one helper**, not two (this replaces the last paragraph of §10), and only while the main worker itself
  is not routing. While the helper runs a router, the main worker edits scripts and documents only.
- The helper is optional: if memory stays short, the main worker does the aux area itself as the first chain steps,
  with the method of §10.
- Do not kill or pause processes of other projects to make room.

### 10b. Models (user 2026-11-23: conserve the Fable limit)

- Every helper or subagent is spawned with the Agent tool's `model: "opus"` (Opus 5.5). No Fable helpers.
- Hand to an Opus subagent whatever is long and mechanical: reading router and check logs, the aux-area routes of
  §10, DRC-fix rounds on drawn tracks, renders and their description, the simulation runs on the card. Keep in the
  main session only what needs the whole picture (placement decisions, the chain order, merging).
- The memory rule of §10a still counts subagents' heavy jobs: one router run, zone fill or check run at a time.
- Reports to the planning session at milestones only, in a few lines; questions with two options and a pick.

## 11. Where the planning session left off (2026-11-23, 23:00)

For whoever continues: the planning session (Fable) reviews the worker's milestones and answers its questions; the
worker (Opus 5.5 since the evening of 2026-11-23) owns both worktrees.

**Done and accepted**
- Card (`~/dev/hb_power_card-rev1`, branch `card-rev1`, 2d4ebeb): routed, 0 unconnected, DRC clean, 33 × 58 mm,
  two populations (standard, DAB), no current sense, MID lead soldered on DAB cards, no damper footprint, R_off
  10R from the loop simulation. Simulation tables in `sim/results.txt`.
- Baseboard (`v6-baseboard`, 4b2d4c2): steps 1–3 (schematic with the sense at the choke ends, strips cleared,
  terminals / pigtails / headers / sense groups placed); `check_all.sh` passes.

**In progress when the day ended (worker, uncommitted in this worktree)**
- Moving AFE_OUT1 out from under the AFE leg 2 card (my review note on `band_primary_F.png`).
- Then step 4: DC pours, ISO DC bus into the freed strip, In4 ground; then the aux-area helper of §10 on Opus,
  under the memory rule of §10a; then the routing chain.

**Open with the user**
1. All six baseboard DC connections as soldered pigtails, or only the two beside the control card (INV A, DAB sec)?
2. Where the AFE and inverter choke leads come down in the built unit (fixes the landing terminals J5, AFE_OUT1,
   INU_OUT2, J7 and the sense positions at FILTER_OUT1 / J9).
3. Infineon's SPICE model of the IMLT65R020M2H, downloaded by hand into the card repo's `reference/`.
4. Wire gauge and M3 ring lug (4 mm² on M3 may not exist as a standard lug).

**To check on the first review tomorrow**
- Step 4: pour widths at each terminal pair (≥ 10 mm or doubled), island counts before / after, the smallest
  distance from bus copper to the wall-side edge and to the PE screws, whether the BUSP / BUSN links are really
  replaced by 8 mm on two layers along the whole run.
- The card's To-verify list in its STATUS.md (press-fit hole tolerance at JLC, 2 oz stack, T1 pins 5 / 8 gap,
  EP7 core and turns, Samtec header stock).

Nothing is pushed: `card-rev1` has no remote, and `v6-baseboard` stays local until the user says to push.

**Added at 23:15 after the worker's step 4 report (4704efe, check_all passes):** first thing to review tomorrow is
the current rating of the new bus lanes, before routing builds on them. The ISO lane is 7.9 mm on two layers and
feeds three cards from one end, so its first section carries the sum of the three card currents; inner layers of
JLC06161H-3313 are 0.5 oz. Ask for the lane cross-section per layer, the RMS current per section (inverter 2 × up
to 20 A RMS bus current, DAB about 12 A RMS AC), the temperature-rise estimate, and where a third layer or a wider
lane is possible. Same table for the 13.5 mm primary bus. The aux-area helper's script must be replayed onto
4704efe.

### 12. Inductors and landing terminals (user 2026-11-24, recorded by the worker)

One AFE choke between J5 and FILTER_OUT1 and one inverter inductor between J7 and J9 (a toroid of about 55 mm
diameter standing upright at the ISO wall; photo `reference/photos/`). The SW wire of the AFE leg 2 card lands on
FILTER_IN1, that of the inverter leg A card on J10; AFE_OUT1 and INU_OUT2 are deleted (step 4d). U29 / U30 stand on
the bottom side (10.2 mm, accepted exception to the 10 mm bottom limit). Wiring list: STATUS.md, step 4d.
