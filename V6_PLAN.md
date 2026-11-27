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

### 13. v6 goes to main once roughly routed (user 2026-11-24, recorded by the worker)

Main still holds the v5 design that will not route, so v6 replaces it as soon as a routing pass is legal.
- **Roughly routed** = a pass that is legal: 0 shorts, 0 clearance errors, parity 0, `domain_gaps` and both layout
  checks (`tools/v5/check_layout.py`, `tools/v6/check_layout_v6.py`) OK, no pour split, `tools/check_all.sh` passing
  with the open connections listed as pending. Open connections may remain; their count is given by net group.
- When pass 1 (or the first later pass) reaches that, the worker merges it into `v6-baseboard`, runs `check_all`
  there and updates the top of STATUS.md and the README so that a reader landing on main sees: this is v6, the
  power-card baseboard; the state of the routing and what is open; the v5 TO-247 layout is abandoned and kept on
  branch `v5-layout`. Then the worker tells the planning session.
- The planning session fast-forwards main to `v6-baseboard` and pushes; the worker never pushes to main.
- Later passes keep merging into `v6-baseboard`; main is fast-forwarded at each legal milestone.
- So a legal board with most of it routed comes before closing the last nets.
- Pass branches that are pushed take baseboard steps by `git merge v6-baseboard`, never by a rebase.

## 14. Magnetics of the built unit (user 2026-11-26; files in `reference/magnetics/`, top-view photo in `reference/photos/`)

**AFE choke and inverter inductor: the same part, one each.** Listing "184125-1MH", upright toroid
(`inductor_184125-1MH_listing.jpg`): outer diameter 53.2 mm, thickness 27.9 mm, two leads of 2.0 mm wire, 22 mm
long, lead pitch 23.8 mm (adjustable), one lead on each side of the thickness. Nominal 1 mH at 1 kHz / 0.3 V.

- In the unit both stand upright with the plane of the toroid parallel to the heatsink wall, so the leads are
  spaced across the wall direction: inverter inductor on J7 / J9 (17.2 mm apart in y), AFE choke between J5 and
  FILTER_OUT1.
- **Profile for the layout check (corrected 2026-11-26, planning session; replaces the 54 × 28 mm box):** the toroid
  is round, so the free height under it falls off towards its centre. Strip 27.9 mm wide across the wall, centred
  between the two leads; along the wall at distance d from the centre the free height is
  s + R − sqrt(R² − d²), R = 26.6 mm, s = standoff. Centres chosen from the parts around them: AFE x −17
  (y −77.8 … −49.9), inverter x −72 (y 43 … 71). Both stand on a **5 mm insulating spacer** (or are tied to the
  wall sheet), height 58 mm under the 70 mm lid: an assembly requirement. The check is in
  `tools/v6/check_layout_v6.py` (rule 5) with real part heights; disc caps 16 mm is an assumption to verify.
- To check against it: the M4 terminals under the toroids themselves (J7, J9, J5, FILTER_OUT1), FILTER_IN1 inside
  the AFE envelope, the AFE leg 1 pair J32 / J31 at its east edge, C19 / C21 at FILTER_OUT1.
- Not known: the core material and how much inductance is left at 25 A and at the 50 A peaks (planning session's
  rough estimate for a µ125 powder core of this size: a small fraction of 1 mH, which would make the switching
  ripple large at the peaks). To measure or to read from the seller's data.

**DAB transformer:** two stacked Metglas MICROLITE MP7109MDGC toroids (`metglas_microlite_toroids_bulletin.pdf`,
table on page 5), about 20 turns, wound so that the leakage is the DAB's series inductance (user).

| Per core | Value | Two stacked |
|---|---|---|
| OD / ID / height | 57.21 / 37.44 / 15.32 mm | height about 31 mm |
| Path length | 14.64 cm | same |
| Cross-section | 1.03 cm² | 2.06 cm² |
| A_L | 217.4 nH/N² (µ 245) | about 435 nH/N² |
| Volume / mass | 15.13 cm³ / about 109 g | about 217 g |

Planning session's arithmetic from the bulletin, for 20 turns and ±200 V on the primary (half bridge on split
capacitors at a 400 V bus); estimates to be checked against the real turns and a temperature measurement:

| | 60 kHz | 120 kHz |
|---|---|---|
| Magnetising inductance | about 174 µH | same |
| Peak flux density | 0.20 T | 0.10 T |
| Peak magnetising current | 4.8 A | 2.4 A |
| Core loss by the bulletin's formula | about 275 W/kg, about 60 W | about 100 W/kg, about 22 W |

The magnetising inductance and the split-capacitor reactance belong in the DAB model of the card's `sim/`.

## 15. Inductor leads land in plain holes; the power cards are the mainline design (user 2026-11-26)

**User: "The half bridge boards that are connected to the walls is going to be the mainline design what we will
move forward."** v6 with the six wall-mounted power cards is the design from here on; v5 stays on `v5-layout`
for reference only.

**Inductor landings (user: go with the planning session's recommendation).** First step of the next session,
before routing pass 2, as a numbered step on `v6-baseboard`:

- J7, J9 (inverter inductor) and J5, FILTER_OUT1 (AFE choke) change from M4 REDCUBE terminals back to plain
  soldered holes for the 2.0 mm leads: 2.3 mm finished hole, 5 mm pad. Positions stay unless the envelope check
  asks for a move; the listing's lead pitch is 23.8 mm and adjustable, the holes are 17.2 mm (J7 / J9) and about
  30 mm (J5 / FILTER_OUT1) apart, which bent leads reach.
- The switch-node ends J7 and J5 each get a wire landing for the card's SW wire **outside** the inductor envelope
  of §14: an M4 REDCUBE (the part these had), joined to the lead hole by copper at least 8 mm wide on two layers,
  2.5 mm from everything else. These two short pieces are the only switch-node copper on the baseboard; give them
  the net names SW_INV_B and SW_AFE_1 so the rule checks see them.
- J9 and FILTER_OUT1 are the quiet ends and keep their nets (INU_CHOKE, AFE_CHOKE1) to the shunts; holes only.
- Layout check: the two envelopes of §14 (54 × 28 mm, 56 mm tall, top side) with nothing taller than 3 mm inside
  except the lead holes. Move what stands inside: expected FILTER_IN1 (M4, inside the AFE envelope; it is the
  landing of the AFE leg 2 SW wire and may go anywhere near the filter input) and the AFE leg 1 pair J32 / J31 if
  their lug circles reach the envelope. Report what moved.
- Then check_all, and routing pass 2 as planned in STATUS.md.

**Done in step 5 (`tools/v6/v6_5_inductors.py`, 2026-11-26), what moved:**

- J5, J7, J9, FILTER_OUT1: `WireHole_D5.0mm_Drill2.3mm`, positions unchanged.
- J7S (M4, SW_INV_B) at (−47, 64.6), east of the inverter inductor (14 mm free over its 11 mm); joined to the J7
  hole by a 5.15 mm band along the wall on F.Cu / In1.Cu / In2.Cu (three layers because the band between the wall
  edge rule and U30 is narrower than 8 mm). The inverter inductor takes the 5 mm spacer for this (item 5).
- U30 3 mm south (pins clear of the band by 2.5 mm), still within 30 mm of R91.
- J10 (M4, inverter leg A SW) to (−49.5, 48.5), 11.5 mm free over 11 mm; joined to CM3 pin 2 by an 8 mm L on
  In1.Cu / In2.Cu plus the existing F.Cu pour.
- FILTER_IN1 (AFE leg 2 SW): no legal place for an M4 terminal outside the AFE profile in the filter area, so it is a
  soldered pigtail hole (`WirePigtail_D6.0mm_Drill3.0mm`, as the ISO pigtails) at (−58.5, −68.5), joined to CM1
  pin 1 by an 8 mm L on In1.Cu / In2.Cu plus the F.Cu pour.
- J32 / J21 stay under the AFE choke's rim (11.0 in 11.4 mm, 5.3 in 9.2 mm free).
- **J5S (step 5c, `tools/v6/v6_5c_j5s.py`, user 2026-11-27):** no legal M4 place north of the bus band beside J21
  (5 mm between the band and the C79 / C11 cans, the M4 pads span 9 mm). The AFE leg 1 SW wire is soldered into a
  pigtail hole J5S (6 mm pad) at (−1, −77.5), between J32 and the wall, under the AFE choke's rim (10 mm free, the
  wire needs about 8). West enough that the PGND band on B / In2 feeds J32 at full width east of it. Linked to J5
  by 8 mm copper along the wall on F.Cu / In1.Cu (net SW_AFE_1, renamed from SHUNT1_FORCE).

## 16. Routing by blocks (user 2026-11-26: "do it", the worker's proposal with its picks)

Routing pass 2 onwards is done block by block instead of one long chain over the whole board.

**Blocks** (IPC frame, mm; picture `reports/v6/blocks/blocks_F.png`, data `tools/v6/route/blocks.py`):

| Block | Area x / y | Contents | Start from |
|---|---|---|---|
| A AFE input / filter / AFE sense (P) | -128 ... -2 / -83 ... -12 | AC input, CM chokes, filter caps, AFE choke holes, R48 / U5 / U29 | clean |
| B Inverter filter / AC out / INV sense (I) | -128 ... -38 / -12 ... 72 | J7 / J9 / J10, CM3, output caps, relay, R91 / U4 / U30 | clean |
| C Primary card band (P) | -2 ... 119 / -83 ... -46 | headers J21-J23, terminals J31-J36, DC bus | pass-1 copper kept |
| D ISO card band + west of J11 (I) | -38 ... 119 / 46 ... 72 | headers J24-J26, J37-J42, ISO lane | pass-1 copper kept |
| E Control-card area (C / I / P) | 40 ... 119 / -46 ... 46 | J11 / J12 fan-out, isolators, analog chain, buck | clean |
| F Bulk caps / dividers / op-amps (P / I) | -38 ... 40 / -46 ... 46 | snap-in caps, divider chains, U7 / U2, taps | clean |
| G Aux flyback | 67 ... 97.5 / -55 ... -4 | aux area of section 10 | routed, frozen |

"Clean" means the routed signal copper of earlier passes inside the block is removed before the block is routed;
the v4 / v5 power pours and planes stay in every block.

**Method**
1. Area reservation: block outlines and the inter-block corridors in `tools/v6/route/blocks.py`; a check fails if
   new copper lies outside its block or corridor.
2. Ports: every net crossing a block edge gets a fixed point and layer on that edge, placed by the worker from the
   corridor lane counts before routing (a corridor short of lanes is reported before any routing).
3. Each block is routed on its own, fenced to its outline and its ports, and delivered as a replay script with a pad
   check (as `tools/v6/aux_routes.py`), never as a board file.
4. Trunks: the crossing nets are routed or drawn port to port inside the corridors (the two sigma-delta pairs and the
   PWM bundles drawn by script).
5. Integration chain: base board -> blocks in a fixed order -> trunks -> plane vias and stitching -> clean-up ->
   check_all; island counts and the 2.5 mm high-voltage rule at every step, as before.

**Order:** the inductor landings of section 15 first (they change A and B); then E (29 connections open inside, its
lanes fix the ports to C and D); then F; then A and B (sense groups last, they may still move with the toroids);
C and D last. One router run at a time (section 10a); a block run is minutes, not hours.

**Block E done (2026-11-27, `tools/v6/route/block_E.py` + `block_E_copper.csv`, report `reports/v6/blocks/block_E.md`):**
open inside E 262 -> 10 (7 real: GPIO_BYPASS_RLY_ISO at U19-15, CTRLGND_A at U19-3, CLK1 and ADA3 near U13, the
kept v4 ends of GPIO_BYPASS_RLY / ADCLK, two GND stubs near U13; PWM_TRANS3 stops short of its port). Ports: south
y -46 x 41.5 ... 45.5 (In2 / In3), west x 40 (kept v4 copper + MDATA on In3), north y 46 (20 ISO nets, mostly B.Cu;
block D sorts them). Followed by step 6b (`tools/v6/v6_6b_orphans.py`: D's pass-1 stubs that lost their E end).
User decisions 2026-11-27:
- **Via-in-pad allowed:** the about 51 vias inside SMD pads (SOIC pins of U13 / U15 / U16 / U19 / U20 / U21 / U28,
  some 0603) stay; order filled and capped vias (JLC via-in-pad; check the price on the order page).
- **Reserve shrunk:** the In3 rule area "v6 route reserve sdm U21 to the corridor In3" keeps only its part north of E.
Brief corrections for later blocks (from the helper): the E-B / E-F windows lie in the C|I barrier strip, so all ISO
nets leave E north; plane vias before ports in the ISO band; supply nets need the router input cut to the block.

**Block F done (2026-11-27, `tools/v6/route/block_F.py`, report `reports/v6/blocks/block_F.md`):** 0 open inside F
(kept v4 copper already joined it); the 8 crossing nets drawn by script to fixed ports on x -2 (A), x -38 (B) and
y 38 (D2), no router run. Block shapes as resolved by `block_of` (first block in ORDER wins): A covers F's
south-west corner (x < -2, y < -12), D2 F's top 8 mm, so F is L-shaped.

**Block A done (2026-11-27, `tools/v6/route/block_A.py`, report `reports/v6/blocks/block_A.md`):** the 8 connections
inside A closed by script (AFE sense side 2, AFE_CHOKE1 zones and via field, faulty VIN- copper and the dead 15V In2
run redrawn); ports to C on x = -2 (15V -48.6 In4, GND -49.86 In1, VCC -52.4 In4, 5V -53.6 In4); no B / G ports.
User 2026-11-27: the 15 fill keep-outs stay; C64 180°, R90 0.2 mm, PGND pour 7 at 2.5 mm and R48 rotated are
approved as a follow-up step.
