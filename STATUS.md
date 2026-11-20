# Status

Updated: 2026-11-19 (v5 step 14: R108 3.3k; U7 / U2 not moved, see there; v5 step 13: PE6 / PE7 accepted as they are; v5 step 12: PE screw holes 3.0 mm; v5 step 11: cable ties removed, blade tabs for the DAB wires; v5 step 10: spare isolator U17 removed); 2026-11-18 (v5 step 9: aux flyback area placed; v5 step 8: aux flyback on the EEL19 with the SMD controller ICE5AR0680AG; v5 step 7: aux flyback controller ICE5AR0680BZS; v5 step 6: DC bus wire link past J11); 2026-11-17 (v5 step 5: card-area placement revision 2, routing open); 2026-11-15 (v5 steps 3–4: six layers, card area placed in three isolated domains, routing open); 2026-11-15 (BOM complete, REF3125 for REF3025); 2026-11-12 (v5 passives: JLC codes in fab/jlc_bom.csv); 2026-11-09 (v5 step 2: refdes AFE_OUT1, FILTER_IN1, FILTER_OUT1 so the GUI "Update PCB from Schematic" works); 2026-11-05 (v5 step 1: aux flyback + CTRL isolation in the schematic, board staged for the GUI layout); 2026-11-05 (v4 fix 16: pours without holes, KiCad clearances, domain DRC rules); 2026-11-01 (v4 fix 15: cable-tie anchors at 8 soldered lead pins; user confirmed IEC 61010-1 and the 5.0 / 2.5 mm spacing); 2026-10-31 (v4 fix 13/14 on branch `v4-terminals`: M4 terminals on 7 lead connections, insulation spacing P-I 5.0 mm / P,I-PE 2.5 mm; tools/v4/domain_gaps.py in check_all); 2026-10-30 (v4 fix 11/12: measurement filters from reports/noise, AMC1306M05 in the BOM); 2026-10-29: U8 → K7805-2000R3 with C93/C94, fix 10; user answers to the JLC questions recorded; v5 aux flyback planned, decisions taken except D4; board frozen, edited by tools/v4/fix_*.py)

## v5 step 18 – supply vias of U20 pin 16 and C120 beside BUSN2 (2026-11-20, branch `v5-layout`)

User 2026-11-20 "Go with your recommendation" (move C120; move the two 10M chains towards T1).
- **C120 NOT moved; two fixed vias instead** (`tools/v5/v5_18_u20_supply_vias.py`, seed 5018). On the board
  without signal tracks legal via sites exist right at the pads; passes 2..6 lost them to signals routed first.
  3V3_ISO via at (90.0, 38.7) with a B.Cu stub from U20 pin 16 and an F.Cu track from C120 pad 1 (4.09 mm from
  the BUSN2 pad); ISOGND via at (91.3, 40.15) east of C120 pad 2 (2.69 mm from the BUSN2 pad, 2.5 needed).
  drc: 349 unconnected v5 items pending (was 352), 0 clearance; domain_gaps OK; check_layout OK.
- **The 10M chains are NOT moved; back to the user.** A scan of the primary aux area shows no room for six 1206
  parts near T1. Free: bottom side x 68..74.5, y -44..-53 (south of U18, west of the fly-lead holes), enough for
  R98 (2512) and C112 (1210) only. Proposal: R98 and C112 go there, so that DC+ -> R98 -> AUX_VIN -> C111 / C112 /
  T1 pin 11 is local, and the chains R136..R138 / R141..R143 stay under the card but take their high end from
  DC+ instead of AUX_VIN (schematic change, sheet 7; 10R apart). Waiting for the user's decision.
- `tools/check_all.sh` ALL CHECKS PASSED, `tools/regen_check.sh` OK.

## Routing pass 6 – 16 unconnected, legal (2026-11-20)

Branch `routing-pass6`, commit b1f3412 (not pushed), worktree `.claude/worktrees/agent-a3594812f032992fa/`, report
`reports/v5_layout/routing_pass6.md` there; on the step 17 board (d5654c3), nothing merged. DRC, domain_gaps and
check_layout rerun here on its refilled board: 0 shorts, 0 clearance errors, parity 0, 0 gap violations,
check_layout OK; 16 unconnected on 10 nets (3 of them the wire links).

- The In2 GND pour worked: vias at 10 GND pads, 15V closed in 48 s (all 6), GND 7 -> 5 open.
- CLK1 closed: the escape between the pad rows of R87 passed the DRC gate. DAB_PWM_PRI_HI_ISO closed (routed
  first and alone).
- Regression: DAB_PWM_LO_SEC_CTRL, INU_ADCLK_CTRL, PWM_Q5_CTRL (J11 -> bottom isolators) open, closed in pass 5;
  probably the changed step order (not analysed).
- Open: AUX_VIN 2 (trunk in two pieces, no legal F.Cu path under 2.5 mm), AUX_LOVP 1 (R143-2 beside the HV pad of
  its own part), GND 5 (C68-1 and C112-2 outside the pour; C145-2 skipped by the script, a 1.3 mm link is free;
  two links at U9 east of the pour), 3V3_ISO at U20-16 and ISOGND at C120-2 beside BUSN2 (nearest legal via
  sites 5.4 mm and 3.9 mm away).

## v5 step 17 – GND pour on In2 under the aux flyback controller (2026-11-20, branch `v5-layout`)

User 2026-11-20 "Go with your recommendation" (after the pass 5 follow-up: seven GND pads open in the aux area).
- `tools/v5/v5_17_aux_gnd_pour.py` (seed 5017): zone "v5 aux P In2.Cu GND" over the primary aux area PX from
  y -21.6 to -54.6, zone clearance 1.0 mm. One island, 266 mm2: it fills x 72..82.9 (the controller and its small
  parts); the strip x 67..72 is taken by the existing In2 PWM tracks. Tied to GND at T1 pin 2 for now.
  In2 because In1 / In4 are 0.10 mm from the outer layers (DC+ pour on F.Cu, U18 drain pads on B.Cu).
- **R87 / CLK1: the ADC group is NOT moved** (I had proposed 1 mm south). The group has about 80 tracks and four
  vias tied to U11's pads on the top side; a 1 mm shift is a hand re-layout. Instead the next routing pass draws
  an escape for CLK1 between the two pad rows of R87: 0.127 mm track at y 4.489 from pad 3 east past the unused
  pads 4 / 5 to (60.75, 4.489); the gap between the rows is 0.45 mm, clearance 0.16 mm (rule 0.15, min track 0.10).
  No placement or schematic change.
- `tools/check_all.sh` ALL CHECKS PASSED (92 zones), `tools/regen_check.sh` OK.

## Routing pass 5 – the ISO signals close (2026-11-20)

Branch `routing-pass5`, commit 457b4f9 (not pushed), worktree `.claude/worktrees/agent-a3594812f032992fa/`, report
`reports/v5_layout/routing_pass5.md` there; step 16 board, nothing merged. DRC, domain_gaps and check_layout rerun
here on its refilled board: 0 shorts, 0 clearance errors, parity 0, 0 gap violations, check_layout OK; 29
unconnected on 11 nets.

- All 12 west-bound signals closed (six taps, sigma-delta pair, relay, PWM_Q5 / Q7 / TRANS6): lanes, tap runs and
  most ends drawn by script (`tools/v5/route_pass1/maze.py` there), DRC-gated before the router ran. In3 11 of
  11 lanes, In4 about 10 of 11 (5V_ISOL, ISOGND, 15V_ISO, 3V3_ISO, one tap). No pour cut, no signal on In2.
- Signals open: CLK1 (R87 pad 3, placement, user's decision), DAB_PWM_PRI_HI_ISO (not analysed), AUX_VIN,
  AUX_LOVP (script skipped pads that already have a stub).
- Supply pads open: 15V_ISO 7 and 15V 6 (both router steps skipped at a 300 s budget set too short; pass 4 needed
  206 s / 260 s), GND 7 in the aux area (no simple legal link under the per-pad HV rule; not shown impossible),
  3V3_ISO 1 and ISOGND 1 at U20-16 / C120-2 beside BUSN2 (no plane-via site).
- Cheapest next step: rerun only the supply steps with the pass 4 budgets
  (`ROUTE_DIR=$PWD/build/route_p5 tools/v5/route_pass1/chain.sh "" supply_15V_ISO`, about 25 minutes).
- Not checked: that the tap pairs run side by side all the way (U7B is split over In3 / In4).
- Follow-up run (commit a519c6e on `routing-pass5`, rechecked here: legal, 22 unconnected on 10 nets): 15V_ISO
  closed (313 s). 15V (6 pads, all in the aux area) ran out of 420 s. GND 7: C114-2, C112-2 and C145-2 are shut in
  by signal tracks routed before GND, C68-1 and R102-2 by HV / LOVP copper: the aux area wants GND first or a GND
  pour on an inner layer. AUX_VIN, AUX_LOVP: no legal F.Cu path found by the script. DAB_PWM_PRI_HI_ISO: three
  vias in front of its J11-22 stub at (47.0, 35.95); a route-it-first step is written, not run.

## Routing pass 4 – fanned bus: legal, 25 unconnected (2026-11-20)

Branch `routing-pass4`, commit 41b0f63 (not pushed), worktree `.claude/worktrees/agent-a3594812f032992fa/`, report
`reports/v5_layout/routing_pass4.md` there; step 16 board, nothing merged. DRC, domain_gaps and check_layout rerun
here on its refilled board: 0 shorts, 0 clearance errors, parity 0, 0 gap violations, check_layout OK; 25
unconnected on 17 nets (pass 3: 39, pass 2: 63, pass 1: 123). No pour cut, no signal on In2.

- Passage: 14 lanes per layer fit in the pinch under INU_OUT2; the neck between its west pad and the corner pin
  of J8 (41.4, 52.2) passes 11 per layer (drawn, DRC-gated). In3 11 of 11 used (12 signals minus the relay),
  In4 about 7 of 11 (5V_ISOL 0.8 mm, ISOGND 0.4 mm, relay).
- Closed now: PWM_Q5 / Q7 / TRANS6, sigma-delta pair, relay, 5V_ISOL, INU_ADCLK at U4-7, PWM_Q7 at J8-43.
- Open, routing tool rather than placement: the six divider taps (lanes and west ends exist, the router fails the
  60 mm from the U7 / U2 block to the lane entries near (79.5, 49.3) and deleted three drawn lanes); 15V_ISO (2)
  and 3V3_ISO (1) have no drawn In4 entry (free lanes exist; the relay's way in via (99.3, 51.75) is unproven
  for them); DAB_PWM_PRI_HI_ISO (step order at J11-22); ISOGND J4-46; GND 7 / 15V 1 / AUX_VIN / AUX_LOVP in the
  aux area (router's flat 2.5 mm at pads beside an HV pad). Open by placement: CLK1 at R87 pad 3.
- The sigma-delta pair and the taps are on In3 (0.11 mm above the Q5_S pour on In2): In4 can only be entered from
  a through-hole pin, a plane edge or far east.

## Passage north of J11: fanned bus instead of moving INU_OUT2 (2026-11-20)

User: "Move inu out 2", then, after the report below, "Go with option 1".
- INU_OUT2 (M4 terminal at (47, 60), net Q5_S) NOT moved: its north-east pad is 2.35 mm from Q6 pin 1 (gate; Q5_S
  is Q6's drain; the TO-247's own pad gap is 2.41 mm), and its body touches Q5 / Q6.
- It limits the passage only at x 42.5..51.5 (two south pads): ISO corridor y 51.1..55.46 there, about 13 lanes
  per layer. Over J8 and J6 In3 / In4 are empty up to y 60; pass 3's 8 lanes per layer came from straight lanes
  above the J8 pins and the fence at y 55.3.
- Option 1: lanes fan out north of J8 / J6 up to y 58 on In3 / In4 (tracks only). No change to lib/v5_copper.csv
  (its rectangles concern F.Cu / B.Cu copper and vias). Routing brief updated; pass 4 on branch `routing-pass4`.
- Known cost: lanes 0.11 mm from the Q5_S pour (In2) and 0.10 mm from the Q7_S pour (B.Cu), both switch nodes.

## Routing pass 3 – finished (2026-11-20): the passage north of J11 is 6 lanes short

Branch `routing-pass3`, commit e61031b (not pushed), worktree `.claude/worktrees/agent-a3594812f032992fa/`, report
`reports/v5_layout/routing_pass3.md` there; on the step 16 board (7ecd979). Nothing merged into `v5-layout`.
DRC, domain_gaps and check_layout rerun here on its refilled board: 0 shorts, 0 clearance errors, parity 0,
0 gap violations, check_layout OK; 39 unconnected on 17 nets (pass 2: 63, pass 1: 123), 9 signal connections open.

- **Not legal as routed**: three new vias in the gap between J6 and J4 ((77.75, 50.60), (81.60, 50.10),
  (85.38, 51.42)) cut the B.Cu ISODC+ pour (zone clearance 1.95 mm) into 2 islands. The gap needs a via keep-out;
  the "via patch" at x 77.5..79 named in pass 2 does not exist.
- **Passage** (y 52.6..55.3): 16 lanes at 0.152 mm (8 on In3, 8 on In4), all assigned: 12 signals, ISOGND (2 lanes,
  0.4 mm), 15V_ISO (2 lanes). No lane for 3V3_ISO (2) and 5V_ISOL (4): 6 short. Net-(U7A--) has a lane but no
  legal entry. The upper 4 lanes per layer lie at y 54..55.3, outside the `unrouted` rectangle.
- Step 16 worked: J11 -> bottom isolators 14 of 14, PWM bundle to J6 / J4 6 of 6 without In2, the J8 nets leave
  U20 pins 10..12 straight into their lanes.
- Open: INU_ADCLK and PWM_Q7 at their J8 / U4 ends (not analysed); three taps at their old In2 ends near
  (19..21, 44) under F / B pours; DAB_PWM_PRI_HI_ISO (closed in pass 2); CLK1 (R87); AUX_VIN, AUX_LOVP and 6 GND
  pads in the aux area (router's flat 2.5 mm at pads next to an HV pad: tooling, not placement); ISOGND 11
  (step out of time); 15V_ISO 3, 5V_ISOL 3, 3V3_ISO 1.
- Decision waiting for the user: how 3V3_ISO and 5V_ISOL reach the parts west of J11 (U4, C37, J8-45), since
  the passage cannot carry them.

## v5 step 16 – U19 / U20 channels after routing pass 2 (2026-11-19, branch `v5-layout`)

Routing pass 2 (branch `routing-pass2`, commit fc1b889, report `reports/v5_layout/routing_pass2.md` there) on the
step 15 placement: legal (0 shorts, 0 gap violations, check_layout OK), 63 unconnected (pass 1: 123), 14 signal
connections open. D13 / D12 and R139 did what they should; J14 made no difference. **The isolator exchange of
step 15 was half wrong**: the J6 / J4 nets now route straight, but PWM_Q7 / Q5 / TRANS6 on U19 pins 13..15 sat
under the bus wire pad BUSP2 (63.5, 45.5), whose 2.5 mm keep-out leaves no via site: no path (exhaustive search).

User 2026-11-19: "go ahead with your recommendations" (channels again instead of moving BUSP2; passage as a
scripted bus in the next pass). `tools/v5/v5_16_channels.py` (seed 5016), `tools/sheets/sheet11.py`:

- U19 (x 63.65): pins 10..12 = PWM_TRANS5, Q8, Q6 (J6, as in step 15), pin 15 = GPIO_BYPASS_RLY_ISO (x 66.83,
  outside the keep-out), pins 13 / 14 free (inputs 3 / 4 tied to CTRLGND_A).
- U20 (x 85.55): pins 10..12 = PWM_TRANS6, Q7, Q5 (x 82.4..84.9, under the gap between J6 and J4), pins
  13..15 = PWM_TRANS4, DAB_PWM_LO_SEC, DAB_PWM_HI_SEC (as in step 15). No free channel left on U20.
- Not solved by this: BUSN2 (90.5, 45.0) stands over U20 pin 15 / 16 and C120 (pass 2 closed DAB_PWM_HI_SEC only
  with a hop on In2); the passage north of J11 (12 signals + ISO rails on 7..8 lanes per layer) is undecided
  until it is drawn as a bus; R87 / CLK1; GND in the aux area (no plane there).
- `tools/check_all.sh` ALL CHECKS PASSED, `tools/regen_check.sh` OK.

## v5 step 15 – placement changes after routing pass 1 (2026-11-19, branch `v5-layout`)

Routing pass 1 (branch `routing-pass1`, commit 23ed936, report `reports/v5_layout/routing_pass1.md` there; a quick
chain over the card and aux areas, nothing merged) closed 155 of 174 signal connections with 0 shorts and 0 domain
gap violations. Its placement findings, applied on the user's "Go with your recommendation" (2026-11-19) by
`tools/v5/v5_15_pass1_placement.py` (seed 5015) and `tools/sheets/sheet11.py`:

- **North isolator row**: U19 and U21 change places (U19 to x 63.65, U21 to x 74.6) and the channels of
  U19 / U20 are reordered. ISO pins west to east: U19 10..15 = PWM_TRANS5, Q8, Q6 (J6), Q7, Q5, TRANS6 (J8);
  U21 as before (MDATA_DAB, MDATA_INU, ADCLK_DAB, INU_ADCLK); U20 12..15 = relay, PWM_TRANS4, DAB_PWM_LO_SEC,
  DAB_PWM_HI_SEC (J4). Before, TRANS4 / TRANS6 crossed and Q6 / Q8 / TRANS5 ran across U21's ISO pins.
  The J11 side stays scrambled for some nets (J11 pins are fixed); the ISO side had priority because it has to
  pass the J6 / J4 pin rows. C121 / C122 now stand at U19 and C117 / C118 at U21 (same nets, not moved).
- **J14** (5 V link holes): pad 1 from (65.33, 17.5) to (69.0, 23.5), out of the diagonal of the J11 fan-out,
  between the LDO block and the difference amplifiers (free on both sides, clear of card tails).
- **Clamp**: D13 from the top side at (79.2, -24.75) to the bottom side at (79.2, -53.3), anode below fly-lead
  hole 11 (AUX_VIN), cathode below D12's cathode; D12 1.0 mm north to (80.9, -47.2). The loop was 25 mm long.
  D12's drain pad keeps 1.5 mm to R105 (a first try with 1.5 mm north left 1.03 mm: DRC stopped it).
- **R139** (FB RSel 750k): from (73.6, -11.0) to (80.7, -35.1) between T1 pins 1 and 2 on the bottom side,
  3.7 mm from U18 pin 3 (was 25 mm), GND end at T1 pin 2.
- **R87 NOT changed.** CLK1 stays open at R87 pad 3 (no way out between pads 2 and 4, 0.6 mm from the edge of
  the primary area). Tried: SCLK / CLK1 on the unused unit D at the east end of the array. The Proteus comparisons
  (compare_netlists_v4, check_board, assign_nets, ipc356_diff) have no deviation kind for a v4 pin that becomes
  N/C or an N/C pin that gets a net, so the change was backed out rather than loosen them. Options left: move
  the ADC group 1 mm south (v4 copper inside the group moves with it), or add that deviation kind.
- Not placement, for the next routing pass: fence In4 from the start (pass 1 put a tap on the ISOGND plane),
  scripted vias at the six U7 / U2 inputs, HV rule per pad (card_layout.HV_PADS) instead of a flat 2.5 mm.
- `tools/check_all.sh` ALL CHECKS PASSED, `tools/regen_check.sh` OK; drc: 0 shorts, 352 unconnected v5 items
  pending (as before).

## v5 step 14 – R108 3.3k; U7 / U2 stay (2026-11-19, branch `v5-layout`)

User 2026-11-19: "Move u7 and u2 and change r108".

- **R108** (preload on the regulated 15 V output of the aux flyback): 4.7k -> **3.3k**, 4.5 mA, 68 mW in 0805
  (125 mW). The controller's reference design needed about 5 mA on the regulated rail at light load.
  `tools/v5/v5_14_r108.py` (seed 5014), JLC C26010 (1.2 million in stock 2026-11-19). R109 stays 4.7k.
- **U7 / U2 blocks NOT moved; reported back to the user.** Looking at the west region showed that the earlier
  suggestion does not hold:
  - The taps arrive as differential pairs and the difference amplifiers sit at the receiving end, on the
    ISOGND / 3V3_ISO planes next to the AMC1311 inputs. West of x 58.9 there are no ISO planes; an amplifier
    there would send a single-ended output about 100 mm past the DC bus, referenced to a ground without plane.
  - It does not unload the passage north of J11: instead of six taps, three outputs plus REF_1V65_ISO (it comes
    from REF2 at x 114) would cross, and 3V3_ISO / ISOGND would have to come from U4 by tracks.
  - Space is there (top side x -30..3, y 27..62 is empty), but the ISODC+ pour on F.Cu starts at x 5.4 and the
    divider chains with up to 450 V are underneath on B.Cu.
  The six taps keep the routing rule of `reports/v5_layout/routing_list.md` group 2 (pairs side by side on In3).
- `tools/check_all.sh` ALL CHECKS PASSED.

## v5 step 13 – PE6 and PE7 accepted between their Y capacitors (2026-11-19, branch `v5-layout`)

User 2026-11-19 on the open point of step 12: "We will go with 3 for now" = the holes stay, the 6.0 mm pan head
may touch the bodies of the Y capacitors (drawn bodies: C30 0.15 mm, C29 / C31 / C32 0.05 mm under the head).
`tools/v5/v5_13_pe6_pe7.py` (seed 5013) applies the copper rule of step 12 there: the INDUCTOR_OUTPUT pour on
B.Cu is cut back at PE6; after the fill PE6 has 4.10 / 2.55 mm (F.Cu / B.Cu) and PE7 4.90 / 8.80 mm to other
copper. `tools/check_all.sh` ALL CHECKS PASSED.

**Still to check on the real parts ("for now"):** the head against the Y capacitors at PE6 / PE7, and PE6's
standoff, which reaches about 0.45 mm over the west board edge (hole centre 2.75 mm from the edge).

## v5 step 12 – PE screw holes (2026-11-19, branch `v5-layout`)

User 2026-11-19: all PE connections are M3 screws, "standoff and a m3 pan head"; "positions are not fixed, move the
holes". `tools/v5/v5_12_pe_screws.py` (seed 5012), log `reports/v5_layout/v5_12_pe_screws.log`.

- **Holes:** PE2, PE4 (2.0 mm), PE3 (2.55 mm) and PE8 (1.52 mm, 3.0 mm pad) now have the 3.0 mm hole and 4.0 mm
  pad of PE1 / PE5 / PE6 / PE7. The footprints `Terminal_D4.0mm_Drill2.0mm` and `Terminal_D3.05mm_Drill1.52mm`
  are no longer used and are removed from the library.
- **Head and standoff are PE metal on the solder mask:** taken as 6.0 mm (pan head, top) and 6.4 mm (5.5 mm
  hexagon across the corners, bottom). At PE1, PE2, PE3, PE4, PE5 and PE8 the pours of other nets are cut back to
  2.5 mm (basic insulation to PE) from those circles; measured after the fill: 2.55 mm or more on both sides.
- **PE4 moved 0.8 mm west** to (-89.8, -43.5), the middle between C24 and R10: the head has 0.2 mm to the drawn
  body of each (3.2 mm from the hole centre). Tight; a head of 5.6 mm (ISO 7045) has 0.4 mm.
- **OPEN, PE6 and PE7 not changed:** each stands in the middle of the space between two Y capacitors (C29 / C30:
  5.8 mm, C31 / C32: 5.9 mm between the drawn 5.0 mm wide bodies), with the board edge 2.7 / 3.2 mm west and a
  7 uF film capacitor east. No hole position fits a 6.0 mm head there; the capacitors would have to move apart
  by about 0.8 mm, or a smaller head is used, or the head may touch the capacitors. Also open at PE6: 2.2 mm from
  the 6.4 mm standoff to the INDUCTOR_OUTPUT pour on B.Cu (cut back not done), and the standoff reaches 0.5 mm
  over the board edge.
- Terminal areas for the six changed places are in `lib/v5_copper.csv`. `tools/check_all.sh` ALL CHECKS PASSED.

## v5 step 11 – cable-tie anchors removed, blade tabs for the DAB transformer wires (2026-11-19, branch `v5-layout`)

User 2026-11-19: remove the cable ties and use vertical blade connectors; the PE connections are screws; blade tabs
go on the DAB transformer wires and the AC input and output; the other wire holes are soldered links inside the
unit. This replaces v4 fix 15 (second fixing of soldered wires by cable ties).

- **Removed:** the eight board-only anchors `TIE_*` (16 unplated 3.0 mm holes) and their 12 rows in
  `lib/v4_copper.csv`; the pours refill.
- **AC terminals** ACIN1, ACIN2, ACOUT1, ACOUT2: unchanged. Their Proteus footprint already is the pattern of a
  vertical 6.35 mm tab (two 1.4 mm holes 5.00 mm apart).
- **DAB_PRI_1, DAB_PRI_2, DAB_SEC_1, DAB_SEC_2:** footprint `ac_psu:Tab_FASTON250_TE_62409-1_Vertical` (TE 62409-1,
  customer drawing C-62409: two posts 5.08 mm apart, 1.4 mm holes, 12.6 mm high) instead of the single 3.0 mm
  hole; `tools/v5/v5_11_blade_tabs.py` (seed 5011) picks for each the position within 3 mm of the old hole with
  the largest distance to other nets, both posts in the net's pour, no courtyard overlap. Kind `footprint` rows
  come from `v5_parts.FOOTPRINT_SWAPS`; terminal areas are in `lib/v5_copper.csv`.
- **Distances to the nearest other net** (pad edge to copper, measured): DAB_PRI_1 2.75 mm (was 2.8), DAB_PRI_2
  3.0 (was 2.3), DAB_SEC_2 3.1 (was 2.3), **DAB_SEC_1 2.0 mm (was 2.7)**: it stands in 11 mm between C47 pad 1
  (ISODC+) and C50 pad 1 (DAB_CAP_SEC), centred, with the 2.0 mm pad variant of the footprint.
- **Not changed:** PE1–PE8 (screws), AFE_OUT1 and the other soldered links.
- `tools/check_all.sh` ALL CHECKS PASSED.

**Open:** no current rating for the TE 62409-1 was found in TE's documents, and the DAB and AC currents are not
recorded here: check before ordering (`fab/hand_fit.csv`). The first attempt of this step put a tab on AFE_OUT1;
that was a wrong guess and is not on the board.

## v5 step 10 – spare isolator U17 removed (2026-11-19, branch `v5-layout`)

The user deleted U17 (unpopulated spare SOIC-16W across the P|I barrier, all pins unconnected) in the schematic
editor. The sheets are generated, so the change is made in `tools/sheets/sheet11.py` and `tools/v5/v5_parts.py`
(`REMOVED`), the generated schematic files replace the editor's saved copies (same netlist: compared part by part,
only U17 differed), and `tools/v5/v5_10_remove_u17.py` (seed 5010) deletes the footprint. The slot under it stays
(`card_layout.SLOTS` "P|I run south"). `tools/check_all.sh` ALL CHECKS PASSED.

## v5 step 9 – aux flyback area placed (2026-11-18, branch `v5-layout`)

User 2026-11-18: "do the real placement on the aux area". All 33 aux parts have left the staging area; nothing is
routed. Geometry and positions: `tools/v5/card_layout.py` (`AUX_AREAS`, `AUX_LINES`, `HV_PADS`, `PLACE`); script
`tools/v5/v5_9_aux_area.py` (seed 5009), log `reports/v5_layout/v5_9_aux_area.log`; renders
`reports/v5_layout/aux_F.png` and `aux_B.png`.

- **Two more copper areas:** PX (primary, x 67.0…82.9, y −54.6…−4.0, including the free strip under the card) and
  IA (ISO, x 88.0…97.5, y −48.0…−25.5, joined to the ISO copper at U8). 5.1 mm apart; a barrier rule area along
  x 85.42 (no slot: T1 has 10.8 mm between its pad rows).
- **T1** (EEL19) at (87.4, −38.6) between U8 and J3: primary row and fly-lead holes west, isolated row east. Its
  footprint changed once more: the fly-lead holes are 4.8 mm apart (2.6 mm between pads, was 1.3 mm) and hole 12
  (drain) is the one next to the controller.
- **ISO side (bottom):** D15, C116, R109 at T1's pins 9 / 10.
- **Primary side:** U18 on the bottom at (73.7, −37.25), DRAIN pins at fly-lead hole 12; C113, C114, C147 north of
  it; the VERR / FB / line-sense parts in a column east of it; D14 and C28 at T1's pins 1 / 2; clamp diode D12 at
  hole 12, TVS D13 on the top side north of T1; C111 on the top side at hole 11; R98 and the two 10M chains on the
  top side under the card (low parts), side by side with equal voltages; C112, R139, C41 below them on the bottom.
- **Moved v4 parts:** C28 and C41 (they stood in T1's slot) and C68 (turned 180° and 1.3 mm west: its GND pad was
  1.1 mm from fly-lead hole 11).
- **High-voltage spacing:** the pads of the drain, the fly-lead holes, the clamp, the input capacitors and R98
  carry their own clearance (2.5 / 2.0 / 1.5 mm, `HV_PADS`); zone fills and the DRC keep it. The PGND pour on the
  bottom is pulled back from U18's DRAIN pins. Old copper inside these clearances, in the barrier, within 5 mm of
  the other domain's area or under new pads is deleted (15V, GND, DC+ and three PWM lines to J3: ratsnest now);
  the small GND pour at C68 is gone; the 15V and GND pours at U9 are cut back from the ISO aux area.
- **Checks:** `check_layout.py` covers the aux areas too (`POLY_ALL`); the aux rectangles of `lib/v5_copper.csv`
  are `unrouted` now (clearance and domain gaps strict). `tools/check_all.sh` ALL CHECKS PASSED: domain_gaps 0
  violations and nothing pending, DRC 0 clearance items pending, every pour still one piece.

**Not solved by the placement:**
- **Copper on U18's DRAIN pins.** There is no room for the 230 mm² the loss estimate assumed: the PGND pour, the
  fly-lead holes and the FB parts surround the pins. With little copper the estimate is about 115 °C at 450 V and
  55 °C air (94 K/W), up to 160 °C at the upper bound of the loss. Inner-layer copper under T1 (with vias at the
  pins) is the option to try in routing; measure on the first board.
- The primary switching loop (C111 → hole 11 … hole 12 → U18 → R105) is compact; the clamp loop (D12 → D13) is
  about 25 mm long, and RSel R139 is 25 mm from the FB pin (C146 is at the pin).
- Routing: 354 open connections on 140 nets (`reports/v5_layout/routing_list.md`, group 8a = aux flyback).

## v5 step 8 – aux flyback on the EEL19, controller ICE5AR0680AG in PG-DSO-12 (2026-11-18, branch `v5-layout`)

A rough automatic placement (scratch study, not in the repo) showed that the aux supply of step 7 does not fit
its space: no place for the EE25 at all with C28/C41 where they are, a 28.0 mm slot for its 28.6 mm courtyard
once they move, and the DIP controller 37 mm from the drain pin. User 2026-11-18: use the tube PSU's EEL19 if it
is smaller and the SMD controller; the EEL19 has room for 15–20 W at the ICE5's frequency; the ICE5AR0680AG will
be bought from JLC. Record: V5_PLAN.md 5.5, `reports/aux_flyback/controller_ice5ar.txt`.

- **T1:** EEL19 PC40, vertical 4+6 bobbin, footprint `Transformer_EEL19_V_4+6_SideLeads` (fly-lead holes beside
  the body). 70 / 11 / 11 / 7 turns, Lp 322 µH, 230 mT at the 19.8 W load, window 56 % full. **Hand calculation:**
  losses 0.33–0.70 W, 11–20 K rise; a winding design run and measurements are still needed.
- **U18:** ICE5AR0680AG, footprint `Infineon_PG-DSO-12_CoolSET`, JLC C17699638. Line over-voltage stop at 478 V
  (R141–R144, C147).
- **Dropped:** C115; C28 is the 15V output capacitor.
- **Board** (`tools/v5/v5_8_aux_eel19.py`, seed 5008): footprints swapped in the staging area, 28 pad nets
  updated. `tools/v4/domains.py`: T1's isolated side is now bobbin pins 5–10.
- **Checks:** `tools/check_all.sh` ALL CHECKS PASSED.

**Open:** the aux area is still not placed. C28 and C41 must move. With the real footprints the rough placement
finds a spot for every part (`reports/v5_layout/aux_fit_rough.png`: top side left, bottom side right; an
automatic packing, not a layout); a usable layout needs the controller next to fly-lead hole
12 and copper on its DRAIN pins.

## v5 step 7 – aux flyback controller ICE5AR0680BZS (2026-11-18, branch `v5-layout`)

User 2026-11-18: change the aux flyback to the ICE5 family as in the tube PSU, for board space; "does not need to
be the exact same part"; **DC+ is limited to 450 V maximum** so that an 800 V integrated switch can be used; the
part is hand-soldered if JLC has none (8 pcs today). Record: V5_PLAN.md 5.0 and 5.4,
`reports/aux_flyback/controller_ice5ar.txt`.

- **Part:** ICE5AR0680BZS (100 kHz, 800 V, 0.71 Ω, PG-DIP-7). The tube PSU's ICE5AR4780BZS is too resistive here
  (about 1.7 W at 100 V input and 20 W).
- **Schematic (sheet 7):** U18 new symbol and footprint; start-up chain R136–R138; VCC from 15V (R100 10R, D11,
  C113 47 µF electrolytic, C114 1 µF); the 15V rail is regulated directly by R101/R102 (365k / 49.9k) at VERR;
  FB network R139, R140, C145, C146; clamp TVS D13 SMBJ150A. Removed: Q15, Q16, Q17, R103, R104, R106, R107.
- **Board** (`tools/v5/v5_7_aux_controller.py`, seed 5007): the aux parts are still in the staging area; the
  step swaps the footprints there and updates values and 26 pad nets.
- **Transformer:** unchanged; at 100 kHz the design load needs 1.17 A peak. The MKF report is still the 71 kHz
  run (PyOpenMagnetics is not installed here).
- **BOM:** `fab/jlc_bom.csv` (new passives, C113, D13; UCC28710, MOSFET and buffer rows removed),
  `fab/hand_fit.csv` (U18).
- **Checks:** `tools/check_all.sh` ALL CHECKS PASSED.

**To measure on the first board:** U18 temperature at 450 V and full load (estimate 0.64 W, upper bound 1.12 W;
copper on the DRAIN pin is required in the layout), the drain peak at 450 V, the 15V load step.

## v5 step 6 – DC bus wire link past J11 (2026-11-18, branch `v5-layout`)

The isolated DC bus (ISODC+ on B.Cu, ISOPGND on F.Cu) has been cut at J11 since v5 step 1, and INU_OUT2 cannot
move to open a copper path. User 2026-11-18: join it with two pieces of **2.5 mm round enamelled copper wire,
soldered**, on the bottom side (15 mm standoffs; about 10 A). Blade tabs (TE 63951-1) were tried first and
dropped: the 34 mm straight run of the receptacle fits at the west ends only.

**Step 6** (`tools/v5/v5_6_bus_link.py`, seed 5006; log `reports/v5_layout/v5_6_bus_link.log`):
- Four solder holes `ac_psu:Terminal_D4.0mm_Drill3.0mm` (schematic sheet 4, symbol PIN): BUSP1 (32.5, 38.5) and
  BUSP2 (63.5, 45.5) on ISODC+, BUSN1 (33.0, 31.5) and BUSN2 (90.5, 45.0) on ISOPGND. Each sits in a pour of
  its own net, joined without thermal relief.
- Clearance to other nets on the outer layers ≥ 2.5 mm (bare soldered pads at DC-link voltage): pad clearance
  2.5 mm at BUSP1/BUSN1; at BUSP2/BUSN2 0.5 mm (they pass the ISO planes and In3) and the distance by position:
  the dead end of the F.Cu ISOPGND pour west of x 68 is removed. Every pour is still one piece (measured before
  and after).
- BUSN2 is not between Q6 and Q8: there the hole cut the Q6 gate strap on In1, or lay under Q6's body.
- No cable-tie anchors: the wire is solid and soldered at both ends.

**Checks:** new deviation kind `wire` in `lib/v5_copper.csv` (two rows). `assign_nets.py` counts the two pads of a
wire as joined, `drc.py` takes one unconnected item per wire as the wire, `gerber_roundtrip.py` accepts the
holes' drills. `tools/check_all.sh` ALL CHECKS PASSED: 381 footprints, ISODC+ no longer open; ISOPGND keeps one
open connection at R97 that belongs to the routing.

**Assembly:** `fab/README.md` (wire forms and distances) and `fab/hand_fit.csv`. The enamel is not safety
insulation: the wires are formed to stay ≥ 5 mm from J11's pin tails and the CTRL parts.

**Open:** routing of the card area (339 unconnected items pending; `reports/v5_layout/routing_brief.md`, rule 3a
for the holes).

## v5 step 5 – card-area placement, revision 2 (2026-11-17, branch `v5-layout`)

**Why:** the routing agent's first run on the step 4 placement stopped at 87 of 311 open connections (branch
`worktree-agent-a37d57d89bb23f236`, not merged): the CTRL column beside J11 was 2.9 mm wide, the CTRL area 12.2 mm
high. User 2026-11-17: tighten the primary logic block, move the primary isolators south, move one output-side
isolator east, use the bottom side. Record: `reports/v5_layout/proposal_r2.md`.

**Step 5** (`tools/v5/v5_5_card_area_r2.py`, seed 5005; log `reports/v5_layout/v5_5_card_area_r2.log`; geometry
`tools/v5/card_layout.py`, revision 1 kept as `card_layout_r1.py`):
- U15/U13/U16 and the C|P line 10 mm south (y 8.3) and 3.6 mm west; primary area up to y 5.8; CTRL area at J11
  y 10.8…33.0 (22.2 mm high).
- North isolator row U21/U19/U20 6.6 mm east; CTRL column beside J11 8.6 mm wide (x 44.4…53.0; J6 pin 48 limits
  it); DC bus band from x 58.9.
- U22 on the bottom at (88.0, 13.25), on the east edge of the southern CTRL part.
- Primary ADC group (AD1, U12, L1, …) mirrored to the bottom under U11; 1.65 V reference group 24.75 mm east on
  the top side; both with their tracks. 143 tracks and vias deleted.
- Barrier rule areas, 15 slots and the 10 plane zones rebuilt; pours cut back again.
- The script fills the zones a second time on the reloaded board: the fill made in the same session did not see
  a via that had moved (it stayed inside the GND pours).

**Not done: INU_OUT2 2–3 mm north** (the user had agreed). The terminal's body touches Q5/Q6 and its pads are
2.06 mm from Q6's gate pad. The passage north of J11 is unchanged; the DC bus is still cut (open 1 below).

**Checks:** `tools/check_all.sh` ALL CHECKS PASSED; 306 open connections on 120 card-area nets
(`reports/v5_layout/routing_list.md`). `tools/assign_nets.py --check` handles In3/In4 tracks (commit 37c6ac2).
Tool changes: `layout_proposal.py` and `check_layout.py` read revision 2; `routing_list.py` group 7 covers the
whole primary side.

## v5 steps 3–4 – six layers, card area in three isolated domains (2026-11-15, branch `v5-layout`)

User 2026-11-15: "Follow V5_LAYOUT_PLAN.md from phase 0". Phases 0–4 are done; routing is next (a routing agent,
user decision). Record: `reports/v5_layout/proposal.md` (proposal, decisions, section 10 = what changed while
placing), geometry in `tools/v5/card_layout.py`, renders `reports/v5_layout/card_{F,In1,In2,In3,In4,B}.png`.

**User decisions:** U8 and U10 may move; In3 = routing, In4 = ground; J13/J14 = wires soldered into the holes, no
headers; slots as proposed, none around J11's west and north side; the Ti60 card must still fit; JLC06161H-3313
with 0.5 oz inner copper; routing by a routing agent.

**Step 3** (`tools/v5/v5_3_six_layers.py`, seed 5003): In3.Cu / In4.Cu added, stack-up JLC06161H-3313 (prepreg
0.0994 / core 0.55 / prepreg 0.1088 / core 0.55 / prepreg 0.0994, 1 oz outer, 0.5 oz inner), board thickness 1.6 mm
(was 2.267, the Proteus stack). Existing copper unchanged.

**Step 4** (`tools/v5/v5_4_card_area.py`, seed 5004; log `reports/v5_layout/v5_4_card_area.log`):
- **Areas** (copper allowed on all six layers, ≥ 5.0 mm apart): CTRL at J11 x 44.4…95.1, y 20.8…33.0 plus the
  J11 column; CTRL at J12 x 107.2…118.1, y −34.5…3.0 with a leg to x 102.5; primary = the v4 GND plane area up
  to y 15.8; ISO = the right side, the top band from y 38.0, and the U8 / 15V_ISO copper south of the card.
- **Placed:** 71 v5 parts (sheet 11 and the J12 buck). **Moved:** 32 v4 parts: U16 in line with U13/U15; the U7,
  U2 and U10 blocks as they are, with their tracks; U8 with C93/C94 13.36 mm west (it was 1.89 mm from J12);
  C56, C81, C82. Everything else in the card outline stays, with the primary routing.
- **Bottom side:** U19–U21 (the Ti60 card's JTAG and UART tails end above them), U22–U24 (DWV package up to
  2.8 mm), the difference amplifiers, U27, C137/C138, L2.
- **DC bus band** x 52.3…118.1, y 43.2…48.8: no parts. It carries the bus between the ISO DC link and the DAB
  secondary (F.Cu ISOPGND, B.Cu ISODC+). The isolator ISO pins sit south of it; their signals go to J4/J6/J8 on
  In3 under the bus.
- **Barriers:** rule areas 5 mm wide on all copper layers (no tracks, vias, pours), 15 slots 1.2 mm wide on
  Edge.Cuts under U13/U15/U16, U19–U24, U17 and five free runs.
- **Planes:** In1 ground, In2 supply, In4 ground per area (zones named `v5 card …`); the old In1 ISOGND / In2
  3V3_ISO planes are gone; every other pour is cut back 5 mm from the other domains' areas (pieces that fell
  apart are zones of their own, `(part 2)`).
- **Deleted copper:** 402 v4 tracks and vias (J11 fan-out, ISO copper in the CTRL areas, everything in a
  barrier strip, nets of moved parts). They are ratsnest now.

**Checks** (new or changed):
- `tools/v5/check_layout.py` (in check_all): areas ≥ 5 mm apart, pads in their domain area, courtyards, heights
  (top under the card ≤ 2.65 mm, bottom ≤ 10 mm), no part under a through-hole tail of the Ti135 or the Ti60
  card, bus band free, slots, nothing in a barrier strip, no tracks on In1/In4, each plane one island.
- Deviation kinds `moved` (22 Proteus parts: pad numbers and nets checked, not positions) and `unrouted`
  (rectangles where only unconnected items, opens and vias are excused). **domain_gaps and DRC clearance are
  strict in the card area.** domain_gaps checks six layers.
- The card keep-outs of V5_LAYOUT_PLAN.md section 3 were out of date (MECHANICAL.md of the card repo is older
  than the card's placement). `card_layout.CARD_HOLES` holds the card's real holes, `TI60_HOLES` the Ti60's.

**Open, in this order:**
1. **The DC bus is cut at J11** (since v5 step 1, now visible): ISODC+ (B.Cu) and ISOPGND (F.Cu) are each in two
   pieces. The pours must keep 5 mm from J11, and J8's pins and the INU_OUT2 terminal close the corridor north of
   J11 (y 51.1…53.5). West piece: C8 and the inverter bridge. East piece: the band under J6, C47/C48, Q11, R64.
   Options: (a) a link on In3/In4 through that corridor (0.5 oz, about 2 mm wide: thin for the DAB current);
   (b) move INU_OUT2 2–3 mm north to open the corridor on F.Cu/B.Cu; (c) a wire or bus bar. Needs the user.
2. **Routing** of the card area: `reports/v5_layout/routing_brief.md` and `routing_list.md` (276 open connections
   on 104 nets).
3. PEC1 / PEC2: lug and screw on the bottom; J13 → J14: a double-insulated two-wire cable soldered from the bottom.
4. Slots weaken the board around J11 (card insertion force): check on the first board.
5. The aux flyback (27 parts staged), T1 pin grid, M4 terminals: as before.
6. `~/dev/efinix_soc_board/MECHANICAL.md` still describes the card's old header positions.

Last verification: `tools/check_all.sh` ALL CHECKS PASSED – compare 365/365 parts, 0 wrong-net; check_board 377
footprints, 1202 pads, 71 pads of 22 moved parts, 3389 tracks, 140 vias, 90 zones; assign_nets 0 shorts, 0 opens,
121 v5 opens pending; drc 0 shorts, 0 unconnected, 311 unconnected + 2 clearance pending (the 2 are in the staging
area); domain_gaps 0 violations, 1 pending (staging); check_layout 103 parts, 15 slots, 10 plane zones, 0 errors;
ipc356_diff 0 mismatches; roundtrip OK. `tools/regen_check.sh` OK.

## BOM complete, REF3125 replaces REF3025 (2026-11-15)

User 2026-11-15: "do the BOM completion and the REF3025 replacement".
- **BOM:** fab/jlc_bom.csv now holds every v5 IC and discrete (U18, Q17, U19–U28, D11–D16, Q15/Q16).
  fab/hand_fit.csv holds T1/W1, J13/J14 and PEC1/PEC2.
- **Coverage:** every schematic part is in one of the two lists, except TR1 (off-board) and U17
  (spare). One-off check: no reference outside the schematic; U4–U6 appear in both on purpose
  (the Mouser backup row).
- **REF1/REF2:** REF3025AIDBZR (0 stock) → **TI REF3125AIDBZR (C33297)**. Same DBZ pinout (1 IN,
  2 OUT, 3 GND, per both TI data sheets), stable with any capacitive load, 10 mA, 20 ppm/°C. BOM
  substitution only; the schematic keeps REF3025 (fab/README.md substitutions).
- **Stock** for 5 boards (fab/jlc_stock_2026-11-15.json): every BOM line in stock except AMC1306M05
  (known). IPD95R450P7 has only 18.

## v5 passives – JLC codes picked (2026-11-12)

User 2026-11-12: "pick the JLC codes for the passives". fab/jlc_bom.csv: the 23 parts deleted in v5
are out (sheet-7 IW1830 supply), the 71 v5 resistors, capacitors and L2 are in (70 lines, 257 parts);
fab/hand_fit.csv: PWM1/TR2 removed, the step-2 refdes (AFE_OUT1, FILTER_IN1/OUT1, TIE_AFE_OUT1) applied.
Every BOM refdes is in the schematic, none twice, values match (one-off check). Stock check for 5
boards (fab/jlc_stock_2026-11-12.json): all v5 passives in stock; short are AMC1306M05 (known) and
REF3025AIDBZR (0, new). Substitutions and the reasons are in fab/README.md "v5 passives": R105 0.56R
(no 0.562R stocked), C113 22u 35V X5R (no 15u / 22u 50V 1210; effective CDD near TI's 12.9 µF:
verify start-up on the prototype), R98 2 W, polymer output capacitors (ripple), TORCH 47n 1 kV.
The schematic values are unchanged. Still to pick: the v5 ICs/discretes; the CPL after the layout.

## v5 step 2 – refdes with a trailing number, "Update PCB from Schematic" works (2026-11-09)

User 2026-11-09: "Update PCB from Schematic" stopped with "the schematic needs to be fully annotated".
Cause: three Proteus terminals had references without a number (AFE_OUT, FILTER_IN, FILTER_OUT); KiCad
takes a reference that does not end in a digit as unannotated. kicad-cli ERC does not run this
annotation check (only the GUI does), so the checks never saw it.
- New deviation kind `refdes` (lib/v5_deviations.csv, from tools/v5/v5_parts.py REFDES): AFE_OUT ->
  AFE_OUT1, FILTER_IN -> FILTER_IN1, FILTER_OUT -> FILTER_OUT1. tools/deviations.py maps the Proteus
  refdes of the IPC records, of pin/net lists and of the deviation rows to the KiCad names; the CSV rows
  of the other kinds and the copper-area notes keep the Proteus names. `validate()` checks that `from`
  is an IPC refdes and `to` is not. The Proteus rebuild (AC_PSU_PROTEUS=1) is unaffected.
- Schematic: sheet01.py, lib/part_map.csv and lib/footprint_map.csv (gen_footprints.py) use the new names.
- Board: `tools/v5/v5_2_refdes.py` (seed 5002, refuses to run twice) renames the three footprints and
  TIE_AFE_OUT -> TIE_AFE_OUT1 and re-links the footprints to the renamed symbols (the symbol UUIDs follow
  the refdes). Tracks, vias and zones unchanged (zones refilled).
- Checked: every board footprint links to its schematic symbol (0 path mismatches); the 12 board-only
  footprints (H1-H4, TIE_*) are marked board-only, so Update PCB keeps them. No other reference lacks a
  trailing number.

## v5 step 1 – aux flyback and CTRL isolation: schematic done, board staged (2026-11-05)

User 2026-11-05: "do 1, the v5 aux flyback", scope "Flyback + CTRL isolation" (schematic and board
placement; the logic-area re-layout is GUI work). Design record: V5_PLAN.md section 8 (bobbin creepage
re-check: pin grid assumed 5.0 x 12.7 mm from the vertical CSV former, **verify on a CPV sample**;
row-to-row 10.7 mm on the PCB, 12.0 mm over the former; pins to core 2.25 mm per side -> core
insulation, as before), CTRL_ISOLATION_PLAN.md section 8 (decisions taken: CTRLGND / CTRLGND_A, J13/J14
5 V link to island A, ISOADA x0.4 / x2.49 scaling, PEC1/PEC2 PE bonds).

**Schematic** (all generated): sheet 7 rewritten (UCC28710 U18, IPD95R450P7 Q17, MMBT3904/3906
buffer, US1M + SMBJ170A clamp, T1 EE25, Out1 15V / Out2 15V_ISO, W1 CTRL winding -> TPS54202 U28 ->
5V_CTRL, J13, PEC2; kept C28/C41/C36/C15/C67/C58/C57/C68), sheet 11 to A2 with CTRL island A (U19/U20
ISO7760F, U21 CA-IS3742, U22-U24 AMC1311, U25/U26 OPA2350, U27 TPS73033, J14, PEC1; U13/U15/U16 A
sides on 3V3_CTRL/CTRLGND_A), sheet 2 J11/J12 on the CTRL nets, sheets 1/3/5/10 20V -> 15V and
20V_ISO_SEC -> 15V_ISO. Part list in `tools/v5/v5_parts.py` (98 new, 23 removed). ERC 0 errors (the 8
old warnings).

**Deviation framework:** `lib/v5_deviations.csv` (from `tools/v5/make_v5_lists.py`: 23 remove,
2 rename, 37 pin moves - exactly J11 x19, J12 x6, U13/U15/U16 pins 1/8, C82/C83/C86 - 98 part/value,
335 add rows incl. N/C pins) and `lib/v5_copper.csv` (4 **pending** areas: aux area, card area, signal
bundle J11 -> J4/J6/J8/U4, staging area). `tools/deviations.py` knows `remove`, `rename` and the
pending areas; check_board / ipc356_diff / gerber_roundtrip / check_footprints / gen_footprints skip
removed parts; DRC unconnected and clearance items, copper opens and domain gaps of the v5 change
(v5 parts, moved pads, cut chains, pending areas) are listed as **pending** instead of failing.
Negative test: dropping the J12-48 pin row fails compare and check_board.

**Domains:** C (CTRLGND, CTRLGND_A) added to tools/v4/domains.py (barriers T1, U19-U21, U22-U24);
net class DOM_C, rules P-C and I-C 5.0 mm in kicad/ac_psu.kicad_dru (C-E none: CTRL is bonded to PE).

**Board** (`tools/v5/v5_1_aux_ctrl.py`, seed 5001, refuses to run twice): deleted the 23 footprints,
126 tracks/vias and 4 zones of the 15 nets left without pads; 20V/20V_ISO_SEC copper renamed; the 37
moved pads took their CTRL nets and 240 tracks/vias hanging off them were cut (to the first pad or
branch; whole chains for the ISO-side PWMs, which now come from U19/U20); the 98 new parts are
**unplaced in a staging area below the outline** (IPC y -92 .. -152: aux flyback / island B /
island A rows). The CTRL rules make the ISO pours retreat 5 mm from the J11/J12 area.

**Left for the KiCad GUI** (the pending lists in the check output are the to-do list): place T1, U18,
Q17 and the flyback in the aux area (vertical former below y -18.8, outside the card outline; core
insulated), the island B parts at J12 and the island A parts at J11; re-cut In1/In2 under the islands;
route; slots >= 1 mm under every isolator; then delete each pending row of lib/v5_copper.csv whose area
is done, so the checks become strict there again. Also open: M4 ring-lug terminals for the 17 soldered
leads (v5), fab BOM/CPL after the layout, the CPV pin grid.

Last verification: `tools/check_all.sh` ALL CHECKS PASSED - compare 365/365 parts, 1170 pins, 0
wrong-net; check_footprints OK; check_board 377 footprints, 1202 pads, 217 IPC nets 1:1, 20 v4 vias,
24 Proteus vias deleted by v5; assign_nets 562 groups, 0 shorts/orphans/opens, 87 v5 opens pending;
domain_rules 113 P / 95 I / 8 E / 64 C nets; drc 291 (44 courtyards, 2 pth_inside_courtyard + warnings),
0 shorts, 0 unconnected, 0 parity, 262 unconnected + 427 clearance pending; domain_gaps 0, 208 pending;
ipc356_diff 0 mismatches; roundtrip OK, 0 drill mismatches.

## v4 fix 16 – pours without holes (2026-11-05)

User request 2026-11-05: "remove the holes from copper pours so the kicad automatically draws the
clearances to the inner parts". The Proteus pours came over with Proteus' own cut-outs as zone
holes (406 holes in 80 zones: 132 around other-net copper, 274 thermal / same-net cut-outs).

- `tools/v4/fix_16_pour_holes.py` (seed 4116, refuses to run twice): every copper zone keeps only
  its outer outline. Per-zone clearance = the smallest gap Proteus left to other-net copper of the
  same domain inside the zone's holes, rounded down to 0.05 mm (minimum 0.15 mm): In1 GND / In2 VCC
  0.30, ISOPGND/PGND/JEE 0.55, DC+ 1.50, LEMOUT 1.25, JEE (B.Cu) 1.45, INU_FILTER_INPUT / AFE_RELAY /
  ISODC+ 1.95, PGND (F.Cu) / INDUCTOR_OUTPUT 2.00, 20V 0.25; all others 0.15. So KiCad keeps at
  least the Proteus gap everywhere inside a pour. Nesting check: no zone lay inside an other-net
  zone's hole, so no priority changed; no adjacent-layer P/I overlap appeared, so no keep-out was
  needed. Same-net cut-outs are gone: those pads/vias now connect solid (the zones were solid already;
  the Proteus spoke tracks stay).
- The IEC 61010-1 domain gaps are now KiCad rules, so the zone filler and DRC keep them by
  themselves: `tools/v4/domain_rules.py` writes net classes DOM_P / DOM_I / DOM_E (copies of
  Default) with one exact-name pattern per net into `kicad/ac_psu.kicad_pro`, and
  `kicad/ac_psu.kicad_dru` with clearance rules P-I 5.0 mm, P-E / I-E 2.5 mm. `--check` (in
  check_all) fails when a schematic change moves or renames a net without regenerating them.
  The rules were proven to act by a test with I-P set to 30 mm (499 DRC clearance violations).
- Copper: +238 / −35 mm² on F.Cu, +74 / −3 on In1, +49 / −4 on In2, +159 / −28 on B.Cu. The losses
  are the larger per-zone clearances next to J7, J9, INU_OUT2 and the two U5 HV vias (conservative
  side). Connectivity unchanged: assign_nets 247 groups, 0 shorts, 0 opens; DRC 295 (as before).
- `tools/gerber_roundtrip.py`: new category **pour refill**: a difference inside a KiCad copper
  zone outline (+0.1 mm for the Proteus edge stroke) is no longer compared with Proteus (also the
  Proteus pour-stroke draws inside zones); tracks, pads and drills outside pours are still strict.
- `tools/v4/apply_all.sh` runs fixes 1–15 with the project file of 8c4b5ac (fix 14's fills depend on
  the rules) and then fix 16; replayed on the tag's board it gives the committed board byte for byte.

Last verification: `tools/check_all.sh` ALL CHECKS PASSED (compare 290/290 parts, 0 wrong-net pins;
check_board 302 footprints, 972 pads, 207 nets 1:1, 20 v4 vias, 84 zones; assign_nets 247 groups,
0 shorts, 0 opens; domain_rules OK; drc 295, 0 shorts, 0 unconnected, 0 parity; domain_gaps 0;
ipc356_diff 0 mismatches; roundtrip OK with 54/37/30/19 pour-refill clusters on F/In1/In2/B).

## v4 fix 15 – cable-tie anchors at the soldered lead pins (2026-11-01, branch `v4-terminals`)

User decision 2026-11-01 ("option 2"): the 17 lead connections without an M4 terminal keep their
soldered pins in v4 (ACIN1/2, ACOUT1/2, PE1–PE8, AFE_OUT, DAB_PRI_1/2, DAB_SEC_1/2 – verified against
`fab/hand_fit.csv`), and every wire gets a second, independent mechanical fixing: a cable tie through
the board next to the pin (IEC 61010-1 internal wiring: solder + tie). Full M4 terminals for these 17
move to v5.

**Anchor:** board-only footprint `ac_psu:CableTie_NPTH_2x3.0mm_P5.5mm` (gen_footprints, `board_only`):
two 3.0 mm NPTH holes 5.5 mm apart, no copper (mask openings only), courtyard = the holes; reference
`TIE_<lead>` (hidden). `tools/v4/fix_15_cable_ties.py` (seed 4115) places 8:

| Lead | Holes (IPC frame) | Pair centre from the pin centre | Direction |
|---|---|---|---|
| ACIN1 | (−116.81, −49.56), (−112.92, −53.45) | 7.25 mm | 225° |
| ACOUT1 | (−97.30, −9.25), (−97.30, −3.75) | 7.5 mm | 0° |
| ACOUT2 | (−117.53, 36.10), (−118.96, 30.79) | 7.5 mm | 165° |
| PE1 | (−60.75, −60.25), (−60.75, −65.75) | 9.25 mm | 180° |
| PE2 | (−124.46, −55.42), (−119.14, −54.00) | 8.5 mm | 285° |
| PE3 | (−91.75, −70.63), (−89.00, −65.87) | 6.5 mm | 330° |
| PE5 | (−61.40, 31.35), (−61.40, 25.85) | 6.0 mm | 180° |
| AFE_OUT | (54.07, −72.98), (51.32, −68.22) | 6.0 mm | 30° |

Rules of the search (`/tmp/claude-1000/v4term/ties.py`, positions fixed in the script): each hole edge
3–8 mm from its pin's copper (the tie clamps insulation, not bare conductor) and nearer to its own pin
than to any other terminal; ≥ 0.5 mm from every pad/track/via of any net; outside every courtyard;
≥ 1 mm from the board edge; not within 5 mm of both primary and ISO copper; the strap under the board
between the holes clear of bottom-side parts; then the nearest spot, preferring the direction of the
nearest board edge (the likely wire exit) and little pour cut. Pours refill around the holes:
assign_nets 247 groups, 0 opens; domain_gaps 0 violations; DRC unchanged (295, 0 shorts / unconnected /
parity). Records: `lib/v4_copper.csv` area rows `TIE <lead>` (checked by check_board: every TIE_ hole
NPTH, no net, inside its area) and 4 small areas at pour border strokes the holes cut (round trip).

**No room (9):** ACIN2, PE4, PE6, PE7, PE8, DAB_PRI_1, DAB_PRI_2, DAB_SEC_1, DAB_SEC_2 – every spot
3–8 mm from the pin is inside a neighbour's courtyard (Y/X capacitors around PE4/PE6/PE7/PE8 with
PE6/PE7 also 2.8–3 mm from the board edge; J3/Q10/C35 around DAB_PRI; Q11/Q12/C47/C49/C50/J4 around
DAB_SEC; C14/R10/C25 and ACIN1 around ACIN2), or nearer to another terminal than to its own. Smaller
holes (2.7 mm, 4.5 mm apart) do not change that. These wires need another fixing (e.g. tie them to the
neighbouring wire or anchor, or adhesive at the pin) or the v5 re-layout – user decision.

Verification (68d0e5f): `tools/check_all.sh` ALL CHECKS PASSED (check_board 302 footprints, 8 cable-tie
anchors; assign_nets 247 groups 0 opens; DRC 295, 0 shorts/unconnected/parity; domain_gaps 0;
ipc356_diff 0 mismatches; roundtrip OK); `tools/regen_check.sh` OK; the replay of fixes 1–15 on the
tag's board gives the board and `reports/v4_board_edits.txt` byte for byte.

Hand-fit (`fab/hand_fit.csv`): UV-resistant nylon PA66 cable ties, UL94 V-2 or better, 2.5 × 100 mm;
tie each wire within 10 mm of its pin, around the insulation. Renders: `reports/v4/fix15_{ACIN1,PE1,
AFE_OUT,ACOUT2}.png`.

## v4 fix 13/14 – M4 terminals and insulation spacing (2026-10-31, branch `v4-terminals`)

User decisions 2026-10-31: fix the insulation spacing on the v4 board before ordering (IEC 61010-1,
bench-top lab supply; reinforced primary ↔ ISO, basic to PE), and replace the soldered flying-lead
pins with **M4 threaded terminals + ring lugs** (about 4 kW: DAB leads up to 25 A RMS, mains/AC
output and inductor leads 17–20 A, PE bond test 25 A).

**Domains and the check.** `tools/v4/domains.py` sorts every net into P (primary incl. mains),
I (isolated DC link / AC output) or E (PE terminals) by joining nets through all parts except the
barrier parts (TR1 PRI/SEC, TR2 pins 1–5/6–10, U13/U15/U16/U17 1–8/9–16, U4/U5/U6 1–4/5–8, the
Y capacitors pin by pin). `tools/v4/domain_gaps.py` (kipy, pcbnew polygons only, ≈ 5 s) grows each
domain's copper per layer by the required gap and intersects it with the other domains' copper:
**P ↔ I ≥ 5.0 mm, P/I ↔ E ≥ 2.5 mm on every layer, and no P/I copper overlapping between adjacent
layers**. Added to `tools/check_all.sh`. (The 5.0 / 2.5 mm are the IEC 60664-1 printed-wiring PD2
500 V-row values that IEC 61010-1 Annex K builds on.) **User confirmed (2026-11-01): IEC 61010-1 is the
standard, and the PCB spacing targets are 5.0 mm primary ↔ ISO (reinforced) and 2.5 mm primary/ISO ↔
PE (basic).**

**Gaps before → after (main board 2104b5b → this branch):**

| Layer | Barrier | Spot (IPC frame) | Before | After |
|---|---|---|---|---|
| F.Cu | P ↔ I | via Net-(R2-Pad1) ↔ ISOPGND pour (41.5, 0.7) | 3.36 mm | ≥ 5.0 |
| F.Cu | P ↔ I | AC_IN2 pour ↔ AFE_RELAY pour / ACOUT1 (−68…−110, −9…−14) | 3.62 / 3.81 mm | ≥ 5.0 |
| B.Cu | P ↔ I | FILTER_INPUT track ↔ ISODC+ pour (−47.0, −8.2) | 3.17 mm | ≥ 5.0 |
| B.Cu | P ↔ I | JEE pour ↔ AC_OUT_1 pour (−90.0, −9.3) | 4.10 mm | ≥ 5.0 |
| F/B.Cu | P ↔ E | pours around PE1/C19/C20/C23, PE3, PE4, PE8 (12 spots) | 1.25–2.00 mm | ≥ 2.5 |
| In1.Cu | P ↔ E | GND track ↔ PE3 (−97.0, −64.0) | 1.88 mm | ≥ 2.5 |
| In2.Cu | P ↔ E | 20V track ↔ C22-1 (−96.2, −71.7) | 1.71 mm | ≥ 2.5 |

`domain_gaps`: 18 violations → **0**. No P/I overlap between adjacent layers (before and after).

**Fix 14 (`tools/v4/fix_14_insulation_gaps.py`, seed 4114): pours give way.** Every copper zone
loses the part of its outline within gap + 0.1 mm of another domain's pads/tracks/vias, and of
another domain's larger pour (the smaller of two facing pours gives way); two passes. 12 pours
changed (names suffixed "(fix 14)"; list and areas in `reports/v4_board_edits.txt`). Three tracks
re-routed: the In1 GND diagonal past PE3 runs 0.71 mm beside the GPIO_BYPASS_RLY diagonal, so
both move 0.75 mm away from PE3 together; the In2 20V track dips 0.95 mm under C22.
Pour areas: LEMOUT (B.Cu) 1175 → 1089 mm², FILTER_INPUT (F.Cu) 2102 → 2068 mm², AC_IN2 (F.Cu)
993 → 939 mm², the others < 1 %. Narrowest necks (first split when eroding the fill): unchanged on
every changed pour except FILTER_INPUT F.Cu (1.0 → 0.5 mm, a small appendage next to PE1/C19 – the
main FILTER_INPUT path stays wide, `reports/v4/fix14_PE1_F.png`). Connectivity unchanged:
`assign_nets --check` 247 groups, 0 opens/shorts.

**Fix 13 (`tools/v4/fix_13_m4_terminals.py`, seed 4113): M4 terminals.**
- **Part:** Würth REDCUBE THR **74650074R** (WP-THRBU, M4 through-hole thread, 7 × 7 × 3 mm brass,
  4 solder pins Ø 1.85 mm drill / 3.2 mm pad at ± 2.935 mm, 50 A; Mouser ≈ 7300 in stock, JLC
  C5118857 0 stock) – hand-soldered. Project footprint `Wuerth_REDCUBE-THR_74650074_M4_PTH` =
  KiCad's `TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRBU_74650074_THR` with the 4.3 mm NPTH
  turned into a **plated 4.3 mm hole in a 7.4 mm square pad 1 on all layers** (copper under the cube
  that other nets keep out of, and the landing of the old pin's tracks). Courtyard 10.1 × 10.1 mm.
  Alternatives (other footprints): Amphenol AMT0440007DB0000G (M4, 35 A, JLC C22466633), Keystone
  7799 (M4, 30 A, JLC C5370873).
- **Hardware per terminal:** M4 × 6 pan-head screw + lock washer (about 1.2 Nm), insulated M4 ring
  lug (4.3 mm stud) for 2.5–6 mm² (`fab/hand_fit.csv`).
- **Swapped (7):** FILTER_IN (in place), FILTER_OUT (−33.00, −48.50 → −52.00), INU_OUT2 (48.50, 61.50
  → 47.00, 60.00), J5 (−14.70, −77.40 → −75.65), J7 (in place), J9 (in place), J10 (−56.70, 40.40 →
  −58.20, 42.15). Each sits in its own pour; the moves (≤ 3.5 mm) keep the old pin position inside
  the new square pad, so the old tracks still land on copper.
- **Ring lugs:** no other-domain copper within 30 mm of any new terminal on the P ↔ I barrier; PE
  copper ≥ 11.8 mm away (FILTER_OUT, J10) – with the lug 3 mm above the board that is ≥ 3.5 mm of air
  for a 10 mm bare-metal lug radius, so **the lugs can point in any direction**.
- **Not swapped – need re-layout (user decision):**
  - **DAB_PRI_1/2** (7.1 mm apart, between J3 and Q10, 25 A), **DAB_SEC_1/2** (6.3 mm apart, among
    J4, Q11/Q12, C49/C50), **ACIN1/2** (6.0 mm, between C14, R10, C25), **ACOUT1/2** (ACOUT2 under
    C34's courtyard): two M4 lugs of different nets need ≥ 12 mm centre distance and a 10 × 10 mm
    courtyard each; none of these pairs has room without moving parts.
  - **AFE_OUT:** the only free spot puts the terminal across the B.Cu G1_SOURCE_HI pour and cuts it
    in two (checked: assign_nets open).
  - **PE1–PE8:** wedged between Y capacitors / X capacitors / the board edge (PE2, PE6, PE7 1.5–3 mm
    from the edge); a 10 mm terminal overlaps their courtyards everywhere within 16 mm.
  These stay soldered pins; they need GUI re-layout (or the v5 re-layout).
- **Checks taught the swap** (`lib/v4_deviations.csv` kind `footprint` + one `area,*` row per terminal
  in `lib/v4_copper.csv`, note starting with the refdes): gen_footprints (map override),
  check_footprints (pad numbers = IPC pins, no fit), check_board (pads inside the terminal area on
  the IPC net), ipc356_diff (KiCad records of the swapped refs in their area, nets checked),
  gerber_roundtrip (old pin drill gone / new drills inside terminal areas), assign_nets (paste-only
  pads skipped).

**Replay.** pcbnew's `FootprintLoad` parses every footprint of the library directory and draws
UUIDs for all of them, so adding the M4 footprint to `lib/ac_psu.pretty` shifted the UUIDs of every
earlier fix in the replay (only UUIDs; geometry identical – checked). `tools/v4/v4board.load_fp` now
loads the one file from a temporary directory, which makes the replay independent of the library
contents (checked with a dummy footprint added); the board was therefore re-made by replaying all
14 fixes on the tag's board, so fixes 1–12 carry new UUIDs (no other change). `tools/build_pcb.py`
(the Proteus rebuild) is unchanged.

**DRC:** 295 violations (was 293): 0 shorts, 0 unconnected, 0 parity; courtyards_overlap 52 (−1),
pth_inside_courtyard 2, silk_overlap 38 (+2), silk_edge_clearance 1 (+1: J7's reference near the
bottom edge), track_dangling 1, via_dangling 2, silk_over_copper 199.

Verification (dd9bacb): `tools/check_all.sh` ALL CHECKS PASSED (compare 290/290, check_board 294
footprints / 972 pads / 35 swap pads, assign_nets 247 groups 0 opens, DRC 295 / 0 shorts / 0
unconnected / 0 parity, domain_gaps 0 violations, ipc356_diff 0 mismatches, roundtrip OK);
`tools/regen_check.sh` OK; replaying `tools/v4/apply_all.sh` on the tag's board gives the board and
`reports/v4_board_edits.txt` byte for byte (twice, and with an extra footprint in the library).

Renders (before = main 2104b5b): `reports/v4/fix13_<REF>[_before].png`,
`reports/v4/fix14_{PE1,ACIN2_ACOUT,PE3_PE4,R2via_PE8}_{F,B}[_before].png`,
`reports/v4/fix14_tracks_{In1,In2}[_before].png`.

## v4 fix 11/12 – measurement filters (2026-10-30)

The user asked to apply the hardware findings 1–5 of `reports/noise/README.md`. The defaults below
were taken without the user's answers to the report's questions; **all are reversible**.

**Schematic (sheets 1, 3, 4, 5, 9; `_common.diff_amp` par_caps, `sheet03.vref` rcap):**
- **C95–C106: 1 nF C0G 0402** across every 10k leg of the six difference amplifiers: U1A R21/R17,
  U1B R7/R8, U14 R37/R38, U2 R1/R76, U7A R52/R53, U7B R46/R51. Corner 15.9 kHz; the tap nodes are
  low-impedance at the switching edges (finding 1). The + leg cap goes to the amp's own reference
  (REF_1V65, REF_1V65_ISO, GND or ISOGND).
- **R7 1k → 10k** (finding 2): U1B's + leg is now matched. **The ADA3 firmware scaling changes**:
  before, ADA3 ≈ 1.705 V + 0.0038·V(LEMOUT) − 0.0366·V(FILTER_INPUT), measured against GND; now
  1.65 V + 0.0366·(V(LEMOUT) − V(FILTER_INPUT)).
- **Output filters (finding 3):**
  - AC signals: R18/R9 100R → 8.2k with C88/C89 1n → 4.7 nF C0G (ADA2, ADA3); new C107/C108
    4.7 nF C0G on ISOADA1/ISOADA2 at R54/R56. All 4.1 kHz.
  - DC links: C42/C2 1n → 10 nF C0G (ADA1, ISOADA3): 1.9 kHz.
  - With the 15.9 kHz pole: −24 dB (AC) / −30 dB (DC) at 30 kHz, −37 / −45 dB at 66 kHz.
  - Phase lag 0.87° (48 µs) at 50 Hz on the AC signals.
  - **Source impedance at J11 for the control card (efinix session):** ISOADA1/2 are
    8.2 kΩ ∥ 4.7 nF and ISOADA3 is 8.2 kΩ ∥ 10 nF, so the card's ADC sampling capacitor is fed
    from those capacitors. ADA1–3 go through U11 and the U12 buffer to the ADS7056, which is fine.
- **C109/C110: 100 nF** on REF_1V65 / REF_1V65_ISO (finding 5).
- **R64 (DAB) L/R:** not changed. The shunt's L is not known (5–10 nH); 12.4 Ω per leg with
  100 nF matches 5 nH (τ = 2.48 µs = L/R at 2 mΩ). For 10 nH use 25 Ω per leg. Tune R73/R74 on the
  bench (noise report, measurement 6).

**Board** (`tools/v4/fix_11_meas_filters.py`, seed 4111; `fix_12_silk_new_refs.py`, seed 4112):
- **Top side, beside their resistor with two 0.25 mm tracks:** C95, C97, C101–C105, C109, C110,
  and C108 (pad 2 on a via to the In1 ISOGND plane).
- **Bottom side with vias** (the top was blocked by U1, U14 and the output resistors): C96, C98,
  C99, C100, C106, C107.
  - 7 new vias, all in `lib/v4_copper.csv` with their IPC nets, plus 15 changed-copper areas.
  - The C98 via sits between R8-1 and R9-2 (same net, 0.05 mm from both pads; the vias are
    tented).
- **Six amplifier-output nets got new KiCad auto names**, e.g. `Net-(R17-Pad1)` →
  `Net-(C96-Pad1)`; the board copper and pads are renamed to match.
- Fix 12 re-runs fix 8's silkscreen placement for the new references. The only new silk warning
  is R19's text over C109's outline; R19 had no free spot already in fix 8.
- **DRC:** 293 violations (was 292), 0 shorts, 0 unconnected, 0 parity, no new courtyard
  overlaps.
- Renders: `reports/v4/fix11_U1.png`, `fix11_U14.png`, `fix11_U7_U2.png`, `fix11_REF2.png`.
- `reports/v4_board_edits.txt` comes from the replay of fixes 1–12 on the tag's board. Fix 3
  therefore logs C88/C89 with today's schematic value (4.7n C0G); fix 3's own run had 1n.

**BOM (`fab/`):**
- New lines: 1 nF C0G C307441 (12 caps), 4.7 nF C0G C1518204 (C88, C89, C107, C108),
  10 nF C0G C22400107 (C2, C42).
- Moved: R7 into the 10k line, R9/R18 into 8.2k, C109/C110 into 100 nF.
- **U4/U5/U6 → AMC1306M05DWVR (C701717, user):**
  - ±50 mV linear, ±64 mV clip, 4.9 kΩ input resistance, CMTI 50 kV/µs min / 100 typ
    (checked in SBAS734D).
  - ±25 A full scale on the 2 mΩ shunts, **5× more counts per amp than the M25: firmware
    scale**.
  - 2 × 12.4 Ω against 4.9 kΩ is ≈ 0.5 % gain error: calibrate it out.
  - JLC has 5 in stock, enough for one board; Mouser/Digikey and hand-soldering otherwise.
- **The minimum CMTI (50 kV/µs) is close to the SiC edge rates (30–50 V/ns).** Check the edge
  rate of the AFE and VSI legs: U4/U5 float on the switch nodes.
- Stock for 5 boards: every line except the AMC1306M05 (5 in stock).
- CPL: 205 parts.

## Switching-noise analysis (2026-10-30; hardware findings 1–5 applied in fix 11/12, see below)

`reports/noise/README.md`: why every measurement showed spikes at the switching edges on the v3
boards (AFE/VSI 30 kHz, DAB 66 kHz, free-running ADC). Top findings:
1. The diff-amp tap nodes (91k/10k) have no capacitor and run 70–100 mm on In2, the U7/U2 pairs
   1.5–2 mm from the J8/J6 gate and source traces. Node-injected charge reaches the output at
   about 1×, the signal at 0.0366×.
2. U1B's R7 is 1k, not 10k, so ADA3 has about 24× the common-mode gain of a matched amp.
3. The output RCs are 1.6 MHz (ADA2/3), 19 kHz (ADA1, ISOADA3) or missing (ISOADA1/2).
4. The current spikes come from L·di/dt in the shunts and are covered by v4 fix 4; still open:
   the L tuning (DAB first) and the sinc window = PWM period.
5. REF_1V65 and REF_1V65_ISO have no decoupling.
6. Firmware sampling: 66.67 kHz aliases to 6.67 kHz at 30 kHz sampling.

Proposed fixes by class: BOM values (R7, R18/R9, C88/C89, C42/C2), new caps by board script
(12 × 1 nF across the 10k legs, 2 × 100 nF on the references, 2 × 4.7 nF on ISOADA1/2),
firmware, and layout (v5). Plus measurements to do on a v3 board first. Nothing changed yet.

## v5 aux flyback – planned (2026-10-24)

v5 open item (2026-11-01): full M4 ring-lug terminals for the 17 lead connections that keep
soldered pins in v4 (ACIN1/2, ACOUT1/2, PE1–PE8, AFE_OUT, DAB_PRI_1/2, DAB_SEC_1/2; v4 fix 13/15).

Plan in `V5_PLAN.md` (no design change yet): replace the sheet 7 IW1830/EF20 supply with the
INN3694C/EE25 design of `reports/aux_flyback/`. User decisions (2026-10-24): D1 Out1 → `20V`
(GND), Out2 → `20V_ISO_SEC` (ISOGND); D2 15 V is enough; D3 reinforced between {primary, Out1,
bias} and Out2; D5 in place on the main board; D6 rename to `15V` / `15V_ISO`. **D4 (controller
sourcing) is still open.** Plan only – act on it when the user asks.
Relays R20/R79 (12 V coils): today 167 % on the 20 V rails, with the two 15 V rails 125 %; the
user considers that acceptable.

## Clean-up and JLC (2026-10-24)

Board edits as before (one-shot scripts, seeds 4107–4109, `tools/v4/apply_all.sh` on the tag's
board reproduces the committed board and `reports/v4_board_edits.txt` byte for byte).

- **C67 ceramic (fix 7)** – sheet 7 draws C67 with `C` instead of `C_Polarized` (non-polar 1206
  land pattern like C57/C58, no polarity mark in Proteus); fix 7 copies the symbol's Description
  to the footprint (schematic parity). BOM: Murata GRM31CR61A107MEA8L 100 µF 10 V X5R (C883598).
  *A decision the user can reverse* (if a tantalum/polymer part is wanted: symbol back, and the
  board needs a polarity mark).
- **Silkscreen references (fix 8)** – `tools/v4/fix_8_silk_refdes.py` moves the Reference fields
  (only) off pads (+0.1 mm), other silk (+0.05 mm), other references (+0.3 mm, 0.05 mm where
  nothing else fits) and the board edge (0.3 mm): candidates around the courtyard, angle 0/90,
  1.0 mm text or 0.8 mm as a fallback. 276 references: 146 already clear, 128 moved, 2 left
  (DAB_SEC_1 – between the Q11/Q12 outlines, R58 – crowded U5 corner). DRC warnings:
  silk_overlap 199 → 35, silk_edge_clearance 12 → 0, silk_over_copper with a reference 6 → 0.
  KiCad caps every DRC type at 199, so the old silk counts were really higher; the 199
  silk_over_copper that remain are footprint outlines over the enlarged Proteus THT pads
  (snap-in C8/C72/…, MKS film caps) – a footprint-graphics change, not done. Renders
  `reports/v4/fix8_afe_F.png`, `fix8_aux_F.png`, `fix8_U5_B.png`.
- **R19/R32 422R (fix 9)** – 420R is not an E96 value and not stocked; 422R gives 2.5 V ×
  820/1242 = 1.6506 V (420R: 1.6532 V). Sheet 3 values + note, two `value` rows in
  `lib/v4_deviations.csv`, board values.
- **Pad sizes / drills (KiCad vs Proteus): no change, closed** unless the user objects. The KiCad
  IPC pads are DRC-clean and assemble well at JLC (0402/0603 KiCad pads are the smaller ones);
  the larger KiCad drills (C_Disc, J12, PWM1, R10, C24) are the pin-fitting library values.
- **JLC manufacturing** – `fab/README.md`: BOM 53 lines / 203 parts, all in stock for one board
  (`fab/jlc_bom_check.py`, `fab/jlc_stock_2026-10-24.json`; tight: SI8660BD 6, OPA2353EA 16,
  ADS7056 52); `fab/hand_fit.csv` for the rest; `fab/make_fab.sh` makes the gerber/drill zip
  (fab/out/, not committed) and `fab/jlc_cpl.csv` (rotation corrections per package – check in
  JLC's preview). 12.4R (C477607) for a 5 nH shunt inductance. Substitutions in the BOM only
  (schematic unchanged):
  - U4/U5/U6 ADuM7701-8BRIZ (0 stock) → **TI AMC1306M25DWVR** (C471874, 313): same 8 pin
    functions and 8-lead wide SOIC (11.5 mm span), ±250 mV / ±320 mV clip, 5–21 MHz, data after
    the rising clock edge, reinforced. Differences: 32-clock test pattern at power-up, AVDD
    ≥ 3.0 V. Confidence high for pins/package (TI datasheet SBAS734D vs this project's
    ADuM7701 symbol), medium for the FPGA side (check the decimation filter start-up).
  - U13/U15 Si8661BD-B-IS (2 in stock) → **Chipanalog CA-IS3761LW** (C528659, 2607): identical
    16-pin assignment incl. the reverse channel (pin 10 in → pin 7 out), default low.
    Confidence high (Chipanalog CA-IS376x pin table). U17 is the unfitted spare.
  - R87 value unknown in the Proteus data (only "RESISTOR_ARRAY") → **assumed** 4 × 33R
    (4D02, C25501), SPI series termination.
  - C1/C35/C45–C50 2.2 µF 2220: 250 V part → TDK 450 V X6S (C445674); each sees half of DC+.
  - 14 × 2n2 disc → TDK CS45 X1/Y2 (C96522).
  - Not available at JLC / hand-fit (`fab/hand_fit.csv`): FKK5R0020FE shunts (no JLC part fits
    the 4-terminal land pattern), snap-in 470 µF 450 V, 7 µF MKS4 film, WE-CMBNC chokes,
    TWW10J15RE, VXO7805 (R-78E5.0 clones in stock – check their body side vs fix 6), the 1.27 mm
    connectors, TO-247 (23 in stock but heatsink-mounted), terminals, C68, IW1830/TR2 (v5).
  - Voltage ratings checked against the nets: 91k chains are 3 × 91k from DC+/ISODC+/AC nodes
    (≤ 167 V each at 500 V on 200 V parts – no 500 V 1206 in stock); 0402/0603/1206 caps on
    3V3/5V/20V rails are 16–50 V (fine); **C68 (100 nF 1206, DC+ to GND) had a 50 V part in the
    BOM** – it needs ≥ 630 V (Samsung CL31B104KIHNNNE 1 kV, 0 stock → hand-fit).

User answers (2026-10-29) – all questions closed:
- DC+ maximum 450 V (the snap-ins are 450 V parts, OK). Margins at 450 V: 91k chains 150 V per
  200 V resistor (75 %), 2220 split caps 225 V on 450 V (50 %), C68 450 V on 500 V (90 %).
- C68: the built boards had a 630 V part. No ≥ 630 V 1206 is stocked at JLC; the BOM uses the
  closest, TCC1206X7R104K501HT 500 V (C5448934); hand-fit Samsung CL31B104KIHNNNE (1 kV) if
  more margin is wanted.
- R87 = 4 × 33R, confirmed. Y2 is enough for the 2n2 discs.
- C21/C24/C25/C33/C34: 7 µF 250 VAC film capacitors (hand-fit).
- J1–J4, J6, J8, J11, J12: female 1.27 mm sockets (hand-fit).
- The user places the THT relays and the Y capacitors: moved out of the JLC BOM/CPL to
  `fab/hand_fit.csv`. JLC BOM now 54 lines / 190 SMD parts, all in stock.
- AMC1306M25DWVR (C471874) is the **accepted** substitution for U4/U5/U6 (the start-up test
  pattern is fine for the firmware).
- CM1–CM3 and the main inductors: sourced by the user (AliExpress) and hand-soldered, no order
  code; the off-board inductors (J7/J9) are the user's too.

## U8 → Mornsun K7805-2000R3 (fix 10, 2026-10-29)

Requested by the efinix control-card session (`~/dev/efinix_soc_board/POWER_BUDGET.md`: the
Ti135 card on J12 needs more than the 1 A of the VXO7805-1000 on 5V_ISOL). U8 becomes the
Mornsun K7805-2000R3 (5 V / 2 A, 8–36 V in, SIP-3 1 Vin / 2 GND / 3 Vout, 2.54 mm, Ø1.2 mm holes,
body 11.5 × 9.0 × 17.5 mm standing, pin row 2.15 mm from one face; datasheet rev 2019.10.24-A/5).
- Value only on the board (same footprint, which U9 shares; U9 stays VXO7805-500). The courtyard
  (R-78E graphics mirrored by fix 6: 2.275 mm toward J12, 6.775 mm away) is 0.075 mm short of
  the K7805's 6.85 mm depth away from J12 – kept, no separate footprint variant.
- Datasheet Fig. 2 capacitors, new v4 parts on the bottom side just south of U8's pins:
  C93 10 µF 50 V X7R 1210 (Samsung CL32B106KBJNNNE, C138687 – no 22 µF 50 V is stocked in
  1206/1210; the nearest is 1812 FS43X226K500ERG C22388553) between pin 1 (20V_ISO_SEC, also in
  the B.Cu pour) and pin 2 (ISOGND, on the In1 ISOGND zone); C94 22 µF 10 V 0805
  (CL21A226MPQNNNE, C29277) under pin 3 (5V_ISOL), its ISOGND pad tied to C93's. 0.6 mm B.Cu
  tracks. Render `reports/v4/fix10_U8_B.png`.
- Deviation rows: U8 value, parts C93/C94 with 4 pins and values, B.Cu area. Sheet 3 + part map.
- BOM: C93/C94 at JLC; the genuine Mornsun module on the hand-fit list (JLC has clones only,
  e.g. YLPTEC C18212380).
- 2 A at 5 V is ≈ 11 W from 20V_ISO_SEC; the present IW1830 aux supply was not designed for it –
  see `V5_PLAN.md` (Out2 power vs the upgraded U8).

Replay note: the board scripts' UUIDs depend on `kicad/ac_psu.kicad_pro` too (pcbnew loads it
with the board), so `apply_all.sh` reproduces the board only with the committed project file.
On 2026-10-29 the sheets and the project file were re-saved from outside this session (newer
eeschema format, netlist unchanged, plus `kicad/.history/`); they were restored to the committed
versions (a patch was kept in the session scratchpad), `kicad/.history/` is untracked.

## v4 design fixes – done (2026-10-23)

Five design fixes for board revision v4 (built v3 boards needed bodges: missing ground
connections, noisy measurements, no shunt-inductance compensation on the sigma-delta inputs).
Coordinates below: mm, IPC frame (Y up), like the rest of this file; KiCad y = −y.

### Flow change: the board is frozen (user decision "option 1")

- `kicad/ac_psu.kicad_pcb` is no longer generated from the Proteus gerbers. It was the
  Proteus-generated board at tag `proteus-conversion-complete`; the v4 changes were made by
  one-shot pcbnew scripts `tools/v4/fix_1_ret_iso.py … fix_12_silk_new_refs.py` (helpers in
  `tools/v4/v4board.py`, run in order by `tools/v4/apply_all.sh`, log in
  `reports/v4_board_edits.txt`). Each script refuses to run twice; applied to the tag's board they
  reproduce the committed board byte for byte (UUID seeds 4101–4112; re-checked after fix 12). Further board changes:
  new scripts (or the KiCad GUI, then say so here).
- `tools/make_pcb.sh` never writes the design board: it rebuilds the *Proteus* board from the
  tag's schematic/footprint fit/reports (`git archive`) into
  `build/proteus/src/kicad/ac_psu.kicad_pcb` with the raw Proteus reference
  (`AC_PSU_PROTEUS=1`, `AC_PSU_BOARD/SCHEMATIC/REPORTS` overrides in `tools/board_common.py`,
  `AC_PSU_PRETTY` in `tools/gen_footprints.py` for the tag's project footprints – added with fix 6,
  the first change to a project footprint since the tag).
  The result is byte-identical to the tag's board, and `tools/regen_check.sh` now checks exactly
  that (board and `reports/pour_nets.json`).
- Schematic: still generated by `tools/sheets/sheetNN.py` (changed scripts re-run).

### Deviation list (the only accepted differences from Proteus)

`lib/v4_deviations.csv` (netlist/parts/values) and `lib/v4_copper.csv` (board copper), read by
`tools/deviations.py` (`validate()` checks every row against the IPC, so stale rows fail).
Applied by project-local code only (the `tools/p2k` submodule is unchanged):
`tools/compare_netlists_v4.py` and `tools/check_symbols_v4.py` (thin wrappers that swap the IPC
loader of `p2k.compare_netlists` / `p2k.check_symbols`; the compare wrapper also checks the
`value` rows against the schematic), `board_common.ipc_records()` (used by check_board,
assign_nets), `check_board.py`, `check_footprints.py`, `gen_footprints.py` (added parts),
`ipc356_diff.py`, `gerber_roundtrip.py` (clusters/coverage misses fully inside an `area` are
category "v4 deviation"; v4 via drills accepted). Negative-tested: dropping the J5 pin row makes
compare and check_board fail; dropping the fix 2 area and one GND via row makes the round trip
(other cluster, extra drill) and check_board fail.

| Fix | Deviation rows |
|---|---|
| 1 | merge RET_ISO → ISOGND (TR2-6, C15-2, C36-2, R49-1 + 2 vias); 3 vias ISOGND; area In1.Cu (90.7,−24.3)–(108.9,−12.7), area all layers (93.9,−19.8)–(96.6,−14.9) |
| 2 | merge DGND → GND (U11-6); area F.Cu (59.1,−1.4)–(60.2,−0.55) |
| 3 | parts C88, C89 (`Capacitor_SMD:C_0402_1005Metric`, 1n): C88 1 = ADA2, C89 1 = ADA3, 2 = GND; vias ADA2 (59.6,−8.5), GND (61.4,−9.35), ADA3 (57.6,−6.741), GND (57.6,−9.35); area (56.9,−10.0)–(62.0,−6.2) |
| 4 | values R92 R93 R57 R58 R73 R74 10R → 12.4R; parts C90/C91/C92 (`Capacitor_SMD:C_1206_3216Metric`, 100n C0G), pin 1 = VIN+ / pin 2 = VIN− nets #00428/#00429 (U4), #00349/#00350 (U5), #00360/#00361 (U6); 6 vias; areas U4 (6.8,35.9)–(13.6,45.3), U5 (2.3,−67.4)–(11.2,−60.9), U6 (106.3,31.7)–(111.9,34.8) |
| 5 | pin R48-3 and J5-1 SHUNT1 → SHUNT1_FORCE (new net, KiCad `/01 afe/SHUNT1_FORCE`); area B.Cu (1.9,−71.7)–(4.6,−67.5) |

### Fix 1 – RET_ISO joined to ISOGND

Why: sheet 7's `ISO_GND` terminal was wired to `RET_iso`, so the isolated 20 V return (TR2-6,
C15, C36, R49) had no connection to ISOGND although U8 (pin 2) and the gate-driver connectors
take 20V_ISO_SEC with ISOGND as return.
- Schematic (sheet07.py): the return rail ends in an ISOGND power symbol (RET_ISO symbol and its
  PWR_FLAG removed; ISOGND keeps its flag on sheet 2); text note "v4: …". `gen_symbols.py`: the
  RET_ISO power symbol is gone from the library.
- Board (fix_1): every RET_ISO pad/track/via/zone → ISOGND (4 pads, 24 items incl. the F.Cu and B.Cu
  pours and the vias (93.535,−18.204), (95.516,−21.635)); new **In1.Cu ISOGND zone** "v4 fix 1 …",
  rectangle x 91.0…108.6, y −24.0…−13.0, priority 90, 0.15 clearance, solid pads: TR2-6 and U8-2
  (THT) connect in it and it overlaps the existing In1 ISOGND plane (x ≥ 105.6, y ≥ −18.75);
  3 stitching vias 0.4572/0.3 at (96.0,−15.5) near C15-2, (94.5,−17.25) near C36-2,
  (95.0,−19.25) near R49-1. TR2-7 (D1 anode) and the U8 pins 1/3 get the zone clearance; the TR2
  primary pins (y ≈ −33.5) stay ≈ 8.7 mm away. assign_nets: 0 opens (ISOGND is one copper group).

### Fix 2 – U11 INH tied to GND

- Schematic (sheet09.py): U11-6 → GND power symbol (DGND symbol and its PWR_FLAG removed; DGND
  dropped from the library), note. Board (fix_2): pad net DGND → GND, F.Cu track 0.25 mm
  (59.949,−0.98) → (59.299,−0.98) to the GND pad 7 (inside the pad row).

### Fix 3 – C88 / C89 1 nF on ADA2 / ADA3

- Schematic (sheet09.py): C88 (ADA2–GND), C89 (ADA3–GND), 1n, beside U11, note; part_map rows
  (sheet 9). JLC C1523 (0402B102K500NT, as C42).
- Board (fix_3), bottom side under U11 (In1.Cu is the GND plane there): **C88** at (60.08,−9.35),
  rot 0, pad 1 ADA2 (59.6,−9.35), pad 2 GND (60.56,−9.35); ADA2 via (59.6,−8.5) on the F.Cu ADA2
  track + B.Cu 0.2 mm stub; GND via (61.4,−9.35) + 0.3 mm stub. **C89** at (57.6,−8.03), rot 270,
  pad 1 ADA3 (57.6,−7.55), pad 2 GND (57.6,−8.51); ADA3 via (57.6,−6.741) on the F.Cu ADA3
  diagonal; GND via (57.6,−9.35). ≈ 3 mm from U11-13/U11-12. No courtyard collisions.

### Fix 4 – shunt-inductance RC compensation (U4, U5, U6)

Shunts R91 (U4), R48 (U5), R64 (U6), FKK5R0020FE 2 mΩ, ≈ 5 nH → τ = L/R = 2.5 µs. Per channel a
100 nF C0G across VIN+/VIN− and both series resistors 12.4 Ω: τ_RC = 2 · 12.4 Ω · 100 nF = 2.48 µs.
**Tuning rule** (also a text note on sheets 8 and 10): with 100 nF, R_leg ≈ 2.5 Ω per nH of shunt
inductance (4 nH → 10 R, 5 nH → 12.4 R, 6 nH → 15 R); measure the real shunt L and re-pick R.
The 220 pF common-mode caps (C54/C51, C53/C52, C75/C74) stay.
- Schematic: `_common.adum_block(..., cdiff=(ref, val))` draws the differential cap (pin 1 VIN+)
  and the notes; sheet10.py C90 (U4), sheet08.py C91 (U5), C92 (U6); R92/R93/R57/R58/R73/R74 =
  12.4R. Parts: C0G 100 nF is only stocked in 1206 at JLC (0805/0603: no stock) → C170182
  (1206N104J500CT, NP0 50 V); 12.4 R 0402 → C477607 (Yageo RC0402FR-0712R4L).
- Board (fix_4): values of the 6 resistors (footprints unchanged). At every ADuM7701 VIN+ and
  VIN− are fenced in by each other and by GND1 copper, so one net jumps through vias.
  - **U4** (bottom, INU shunt, switching node; F.Cu above is the ISODC+ pour): **C90** bottom at
    (10.233,37.3), rot 180, pad 1 VIN+ (11.708,37.3) fed by a B.Cu track straight down from R92-1;
    pad 2 VIN− (8.758,37.3); VIN− via (11.678,43.35) on the R93-1→C51-1 track → In1.Cu 0.2 mm track
    → via (8.758,39.0) → B.Cu stub. **F.Cu pour keep-outs** (rule areas, zone fills only) r 1.8 mm
    around both vias (via copper ≥ 1.57 mm from the ISODC+ pour, as the designer's 1.5 mm HV spacing;
    user-approved 2026-10-23).
  - **U5** (bottom, AFE shunt, switching node; F.Cu above is the PGND pour): **C91** bottom at
    (8.1,−64.025), rot 270, pad 1 VIN+ (8.1,−62.55) fed from R57-1 (B.Cu), pad 2 VIN− (8.1,−65.5);
    VIN− via (4.2,−62.75) on the R58-1→C52-1 track → In1.Cu → via (9.3,−65.5) → B.Cu stub; F.Cu
    keep-outs r 1.8 around both vias. The only free spot between U5's pins and R48-2: C91's
    courtyard overlaps U5's (+1 courtyards_overlap, accepted type); copper clearances ≥ 0.15 (U5-1
    0.17 mm, R48-2 0.4 mm).
  - **U6** (top, DAB shunt, ISOGND level): **C92** bottom at (108.6,33.0) under the U6 input pins,
    rot 180, pad 1 VIN+ (110.075,33.0), pad 2 VIN− (107.125,33.0); VIN+ F.Cu stub R73-1 → via
    (111.3,34.3); VIN− via (108.6,34.306) on the F.Cu VIN− track; B.Cu stubs to the pads (In1/In2 are
    the ISOGND/3V3_ISO planes there, vias get their clearance).

### Fix 5 – R48 Kelvin connection

Verified first: FKK5R0020FE land pattern pads 1/2 are 2.9 × 1.0 mm (sense), 3/4 are 2.9 × 5.6 mm
(force); R91 and R64 use 1/2 for the ADuM7701 side. R48-1 (2.1,−67.3) = sense end A, R48-3
(2.1,−71.4) = force end A (B.Cu pour with J5-1).
- Schematic (sheet01.py): pins 1 and 3 no longer tied: pin 1 → global SHUNT1 (U5 side: U5-4,
  R58-2, C52-2, C53-2, D8-A, C71-2, C73-2), pin 3 → local label SHUNT1_FORCE → J5; notes.
- Board (fix_5): deleted the 6 B.Cu tracks (0.152 mm) that joined pad 1 to pad 3:
  (3.891,−67.3)→(4.317,−67.726)→(4.317,−68.667)→(4.317,−70.893)→(3.816,−71.394)→(2.106,−71.394)→
  (2.1,−71.4). Pad 1 keeps its route (2.1,−67.3)→(3.891,−67.3)→(4.31,−66.882)→… to R58-2 and the U5
  parts. Pad 3, J5-1, the B.Cu pour (x −24.1…3.6, y −80.6…−68.4) and its 8 spoke/stub tracks →
  `/01 afe/SHUNT1_FORCE`. The two nets now meet only inside the shunt (assign_nets: 0 shorts).

### Fix 6 – U8/U9 (VXO7805) body side (2026-10-23)

The open Phase 2/4 point "U8/U9 body side" is settled by the user's photo of the built board:
the modules' component faces (toroid, SMD parts) point away from J12 (the photo was matched to
the board by C28, TR2 and the C67/C58/C57 silk). With the datasheet's side view (pin row 1.8 mm
from the module-PCB face, 5.4 mm from the component face) the body is on the side of the pin row
away from J12, as the Proteus silk draws it; the datasheet's "recommended layout" view was the
wrong one. Change: `tools/gen_footprints.py` `flip_body` mirrors the R-78E graphics (silk, fab,
courtyard, texts) of `Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus` across the pin row and turns
the 3D model 180° about the pin-row centre; pads unchanged. `tools/v4/fix_6_u8u9_body.py` copies
the new graphics, field positions and model onto U8 and U9 (no copper or net change, no deviation
rows). Courtyard now 2.275 mm toward J12, 6.775 mm away (the R-78E body is 8.6 mm deep, the
VXO78 7.2 mm, so it is conservative). DRC: the 4 J12-pin / U8 `pth_inside_courtyard` errors are
gone; U9 now also overlaps C57 and C58 (as before C67): on the built board these 1206 parts sit
under U9's component-side overhang (visible in the photo), so the overlap is real and fine.
Render: `reports/v4/fix6_F.png`.

### Renders (checked by eye)

Schematic: `reports/render/{01,07,08,09,10}_*.png`. Board (kicad-cli SVG, `tools/v4/render_area.py`):
`reports/v4/fix1_In1.png`, `fix1_B.png`, `fix2_F.png`, `fix3_FB.png`, `fix4_U4.png`, `fix4_U5.png`,
`fix4_U6.png`, `fix5_B.png`, `fix6_F.png`.

### DRC

468 violations (Phase 4: 469): 0 shorts, 0 unconnected, 0 parity; courtyards_overlap 53 (+1:
C91/U5, see fix 4; +2: U9/C57, U9/C58, see fix 6), pth_inside_courtyard 2 (−4, fix 6), warnings unchanged (silk 199/199/12, via_dangling 2,
track_dangling 1). No new error type; `tools/drc.py` unchanged. ERC: 0 errors, the same 8 warnings.

### For the KiCad GUI (by eye)

- Fix 4 keep-outs: the 4 F.Cu rule areas cut ≈ 10 mm² each out of the ISODC+ (U4) / PGND (U5)
  pours; check that you are happy with the 1.8 mm radius and that no HV copper sliver remains.
- C91 sits between U5 and R48-2 with a courtyard overlap with U5 (0.17 mm copper gap to U5-1):
  check assembly access; C90 is ≈ 2 mm below U4 pin 1.
- New silkscreen references of C88–C92 use KiCad defaults (overlap other silk, as elsewhere).
- Fix 1: the new In1 zone under the aux-transformer secondary (TR2-7 switching node gets 0.15 mm
  zone clearance on In1); check against your isolation rules.

User review 2026-10-23: nothing to change. Shunt inductance not measured accurately (5–10 nH,
about 5 nH); the 12.4R placeholder (5 nH) stays.

`tools/regen_check.sh` (clean clone of 68d0e5f, regenerate everything incl. the Proteus board
from the tag): `regen_check: OK (every generated file byte-identical)`.

### Last verification (`tools/check_all.sh`, fix 12 done)

```
pcbnew 10.0.7
ipc356: nets=208, records=1075, refdes_raw=265, tht_records=562, smd_records=513, smd_top=341, smd_bottom=172, nc_pads=34, vias=173, free_pads=0, holes=4, parts=267
ipc356: OK
check_sources: OK
gen_symbols: lib/ac_psu.kicad_sym up to date (45 symbols)
symbols: 31 part types, 291 refdes, 13 power symbols
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
v4 deviations: 2 net merges, 2 pin moves, 23 new parts (46 pins), 37 values; copper: 20 new vias, 24 changed areas
compare_v4: 37 deviation values checked against the schematic
compare: parts 290/290 present, 0 missing, 0 extra; pins compared 940, wrong-net pins 0; IPC nets touched 243, complete 243
compare: per sheet (drawn/total) 1:52/52 2:8/8 3:22/22 4:41/41 5:49/49 6:16/16 7:31/31 8:24/24 9:12/12 10:24/24 11:11/11
compare: OK
gen_footprints: 290 parts, 45 footprints (28 project), up to date
check_footprints: pcbnew placement of 267 parts, worst pad offset 0.038 mm
check_footprints: 267/267 parts fitted, 898 pads, 42 footprints, worst residual 0.038 mm (limit 0.05); v4 parts without IPC pads (footprint/pads checked): C100 C101 C102 C103 C104 C105 C106 C107 C108 C109 C110 C88 C89 C90 C91 C92 C93 C94 C95 C96 C97 C98 C99
check_footprints: OK
check_board: v4 pads without Proteus pad (nets checked): C110-1@(114.443,12.395) C110-2@(113.483,12.395) C105-1@(78.657,35.237) C105-2@(79.617,35.237) C104-1@(74.487,39.317) C104-2@(74.487,38.357) C108-1@(84.787,40.717) C108-2@(84.787,39.757) C97-1@(54.230,-0.139) C97-2@(53.270,-0.139) C95-1@(54.230,-6.439) C95-2@(53.270,-6.439) C109-1@(53.890,3.920) C109-2@(53.890,4.880) C103-1@(74.487,36.457) C103-2@(74.487,37.417) C102-1@(94.987,36.380) C102-2@(94.987,35.420) C101-1@(88.787,38.630) C101-2@(88.787,37.670) C91-1@(8.100,-62.550) C91-2@(8.100,-65.500) C96-1@(50.200,-6.900) C96-2@(51.160,-6.900) C93-1@(103.925,-22.900) C93-2@(106.875,-22.900) C98-1@(51.200,1.580) C98-2@(51.200,0.620) C106-1@(82.930,38.000) C106-2@(82.930,37.040) C90-1@(11.708,37.300) C90-2@(8.758,37.300) C89-1@(57.600,-7.550) C89-2@(57.600,-8.510) C92-1@(110.075,33.000) C92-2@(107.125,33.000) C100-1@(59.810,-15.300) C100-2@(58.850,-15.300) C107-1@(77.360,41.020) C107-2@(78.320,41.020) C99-1@(61.950,-13.800) C99-2@(61.950,-14.760) C94-1@(109.440,-22.350) C94-2@(109.440,-24.250) C88-1@(59.600,-9.350) C88-2@(60.560,-9.350)
check_board: 294 footprints, 944 pads, worst pad offset 0.038 mm (limit 0.05), 207 IPC nets mapped 1:1, 4 mounting holes
check_board: 20 v4 vias (lib/v4_copper.csv) at their positions and nets
check_board: 4099 tracks, 193 vias, 84 zones
check_board: OK
assign_nets: after zone fill: 247 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
assign_nets: OK (report reports/assign_nets.txt)
drc: 293 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
drc:     53 error    courtyards_overlap  accepted: KiCad courtyards vs the Proteus placement
drc:      2 error    pth_inside_courtyard  accepted: KiCad courtyards vs the Proteus placement
drc:    199 warning  silk_over_copper
drc:     36 warning  silk_overlap
drc:      2 warning  via_dangling
drc:      1 warning  track_dangling
drc: OK
ipc356_diff: Proteus 1075 records, KiCad 1141; matched 1075 (898 pads incl. 36 N/C, 173 vias, 4 holes), worst position offset 0.039 mm (limit 0.05)
ipc356_diff: 207 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
ipc356_diff: v4 deviations applied (v4 deviations: 2 net merges, 2 pin moves, 23 new parts (46 pins), 37 values; copper: 20 new vias, 24 changed areas); 66 KiCad records of v4 parts/vias, nets checked
ipc356_diff: KiCad drill larger (footprint kept): 6x 0.558->0.65, 7x 0.762->0.8, 28x 0.812->1.001, 2x 1.01->1.199, 2x 1.016->1.199
ipc356_diff: pads with another size in KiCad (info): C 150, D 20, J 6, L 2, PWM 7, R 184, U 37
ipc356_diff: OK
roundtrip: F.Cu   XOR  143.26 mm^2, beyond 0.05 mm: only Proteus  39.59, only KiCad  66.96 mm^2; clusters >= 0.01 mm^2: 192 pad shape, 46 v4 deviation; draws/flashes off the other copper: 0 Proteus, 0 KiCad (+23 inside v4 areas)
roundtrip: In1.Cu XOR  267.16 mm^2, beyond 0.05 mm: only Proteus   0.82, only KiCad 246.04 mm^2; clusters >= 0.01 mm^2: 91 pad shape, 13 v4 deviation; draws/flashes off the other copper: 0 Proteus, 0 KiCad (+9 inside v4 areas)
roundtrip: In2.Cu XOR  116.76 mm^2, beyond 0.05 mm: only Proteus   1.12, only KiCad  93.42 mm^2; clusters >= 0.01 mm^2: 117 pad shape, 3 clearance, 20 v4 deviation; draws/flashes off the other copper: 0 Proteus, 0 KiCad (+7 inside v4 areas)
roundtrip: B.Cu   XOR  179.57 mm^2, beyond 0.05 mm: only Proteus   2.19, only KiCad 133.24 mm^2; clusters >= 0.01 mm^2: 317 pad shape, 30 v4 deviation; draws/flashes off the other copper: 0 Proteus, 0 KiCad (+44 inside v4 areas)
roundtrip: drills 0 mismatches; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png
roundtrip: OK
ALL CHECKS PASSED
```

## Shared tools – proteus2kicad (2026-10-21, branch `p2k-submodule`)

- The generic tools moved to https://github.com/johonkanen/proteus2kicad, a submodule at
  `tools/p2k` (pinned commit): `sexpr`, `geom2d`, `gerber`, `fpgeom`, `sch_builder`,
  `render_sheet`, `ipc356`, and the `kipy` / `kicad-cli` / `kicad_env.sh` wrappers (mount
  state now `/tmp/p2k_kicad_mount.<uid>`). Board values are in `p2k_config.py`. The other
  scripts in `tools/` stay here for now and import the shared modules from `p2k`; they move
  to proteus2kicad when tube_psu_kicad needs them, with this board as the regression test.
  Paths in the phase sections below (`tools/bin/kipy`, `tools/ipc356.py`, …) are historical.
- New check in `check_all.sh`: `p2k check_sources` (Gerber X2 pad/via/drill flashes vs IPC,
  outline 246.8 × 154.7 mm) – passes.
- Regression proof: `tools/check_all.sh` output identical to before apart from the new step
  and the extra IPC counts (records 1075, smd_top 341, smd_bottom 172, free_pads 0).
  Regenerating everything from a fresh `--recurse-submodules` clone (`p2k ipc356`,
  `gen_symbols`, the 11 sheet scripts, `gen_footprints`, `make_pcb.sh`, `assign_nets --check`)
  reproduces every committed file byte for byte; `kicad/`, `lib/`, `reports/` are unchanged
  against `main`. `make_skeleton` (one-shot, random UUIDs) runs. `reference/` changed only in
  format: new column `refdes_proteus` (= `refdes` on this board) and header lines; pad, net
  and alias data identical.
- `tools/regen_check.sh [REF]`: the regression check above as a script (clean clone,
  regenerate everything, fail on any difference; negative-tested with a changed sheet value).
  Run it, plus `tools/check_all.sh`, after every `tools/p2k` bump.
- 2026-10-22 (tube_psu Phase 1 preparation): `check_symbols`, `compare_netlists`,
  `make_skeleton`, the generator helpers of `gen_symbols` (`p2k.symgen`) and the generic sheet
  helpers of `tools/sheets/_common.py` (`p2k.sheetkit`) moved to proteus2kicad; skeleton values
  in `p2k_config.py` (`SHEETS`, `SCH_*`). `check_all.sh` output identical, `regen_check.sh` OK.

Previous update: 2026-10-19 (Phase 4 done – gerber round trip and IPC-D-356 diff against Proteus pass; the migration is complete apart from the open points listed under Phase 4)

## Phase 0 – done

- `tools/kicad_env.sh`: mounts `~/kicad/kicad-10.0.7-x86_64.AppImage` with
  `--appimage-mount` (background, mount path cached in `/tmp/ac_psu_kicad_mount.<uid>`,
  reused while alive) and puts `tools/bin` on PATH. `tools/bin/kipy` = AppImage
  python3.11 with the pcbnew dist-packages on PYTHONPATH; `tools/bin/kicad-cli`.
  Both wrappers mount on demand, so they work without sourcing anything.
- `tools/ipc356.py`: parses the IPC-D-356A file (stdlib only, plain `python3`).
  Writes `reference/ipc356_pads.{json,csv}`, `reference/pin_nets_by_component.md`
  (redraw cheat sheet) and `reference/pins_by_net.md`. `--check` verifies counts,
  fix-ups and that the reference files are up to date.
- `tools/check_all.sh`: runs the pcbnew import check and the parser self-check.

### Last verification (`tools/check_all.sh`)

```
== KiCad environment
pcbnew 10.0.7
== IPC-D-356A parser self-check
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
ipc356: OK
ALL CHECKS PASSED
```

`refdes_raw=265` counts the blank refdes of vias/holes; 264 real (truncated) refdes,
267 after the fix-up. The 562 THT records = component THT pads + 173 vias + 4
unnetted mounting holes (3.0 mm).

### Findings that matter for Phase 1

- Truncated refdes resolved from the PDF (by coordinate, nets cross-checked):
  `AFE_OUT`→G3_SOURCE_HI, `FILTER_IN`→FILTER_INPUT, `FILTER_OUT`→LEMOUT,
  `INU_OUT2`→Q5_S, `DAB_PRI_1`→DAB_SOURCE_HI_PRI, `DAB_PRI_2`→DAB_CAP_PRI,
  `DAB_SEC_1`→DAB_SOURCE_HI_SEC, `DAB_SEC_2`→DAB_CAP_SEC.
- **TR1** (ETD34 DAB transformer, sheet 6) is **not on the PCB**; it connects through the
  DAB_PRI/DAB_SEC terminals. The IPC's only transformer is **TR2** (EF20, aux supply).
  In KiCad give TR1 "Exclude from board" and have the comparison ignore it.
- 74 nets have Proteus auto names `#00xxx` (PLAN.md assumed none). Comparison must be by
  pad-set equivalence; names are irrelevant for them.
- ACIN1/2, ACOUT1/2 have two holes both numbered pin 1 (same net) – the footprint needs
  two pads numbered 1.
- R87 (resistor array) pins 4 and 5 have no net record at all (not N/C).
- Single-pin nets: ADA0, ADA4, ADA5, ADA6 (U11 inputs), DGND (U11-6 only).
- PDF net labels are sometimes lowercase (`lemout`, `filter_input`); IPC names are
  uppercase. Use the IPC spelling in KiCad.

## Phase 1 preparation – done (Opus 5.5)

New files:

- `tools/sexpr.py` – KiCad s-expression reader/writer (stdlib).
- `tools/gen_symbols.py` → `lib/ac_psu.kicad_sym` (47 symbols, generated; `--check` verifies
  it is up to date). Simple parts are flattened copies of KiCad 10 std symbols with pins
  renumbered (diodes `A`/`C`; C3M0065090D 1=G 2=D 3=S; 2N7000 1=D 2=G 3=S as in Proteus;
  FKK5R0020FE 1/3 one end, 2/4 other end; WE-CMBNC windings 1-4 and 2-3). ICs, relay,
  EF20, IW1830, connectors are boxes with the **Proteus** pin names. 15 power symbols with
  IPC net names + `PWR_FLAG`. `ETD34_TRAN_1P1S` (TR1) has `on_board no`.
- `lib/part_map.csv` – refdes → PDF sheet, `ac_psu:` symbol, value (268 rows = 267 IPC parts
  + TR1). Values are only filled for non-passives; R/C values come from the PDF.
- `tools/check_symbols.py` – pin set of every mapped symbol (all units) == IPC pin ids of
  that refdes; every IPC refdes mapped; power symbol names are IPC nets.
- `tools/compare_netlists.py` – exports the kicadxml netlist and compares by pad-set
  equivalence. Only refdes present in KiCad are pin-compared, so it works sheet by sheet.
  Reports missing/extra parts, missing/extra pins, merged nets (KiCad net with pins of
  several IPC nets), split nets, N/C mismatches (incl. KiCad-unconnected pin of a multi-pin
  IPC net), name hints, and a per-sheet drawn/total summary. `--sheet N` limits the
  missing-part list to PDF page N; `--allow-missing` makes missing parts warnings.
  Parts with "exclude from board" (TR1) and `#` refs are ignored. Tested on a throw-away
  fixture with deliberate errors (merge, split, extra part, unplaced units, N/C flags).
- `tools/make_skeleton.py` (one-shot, refuses to overwrite) → `kicad/ac_psu.kicad_pro`,
  `kicad/sym-lib-table` (`ac_psu` → `${KIPRJMOD}/../lib/ac_psu.kicad_sym`), root sheet
  `kicad/ac_psu.kicad_sch` with 11 hierarchical sheets `01 afe` … `11 signal isolators`
  (files `kicad/01_afe.kicad_sch` …; sheet 10 is untitled in the PDF → `INU SDM and relay
  drive`). All sub-sheets are empty, A3.
- `tools/sch_builder.py` – helper to write sub-sheets from Python: `Sheet(path).place(sym,
  ref, x, y, rot, unit, value)` returns pin connection points; `power`, `pwr_flag`, `label`,
  `glabel`, `no_connect`, `wire`, `junction`, `text`, `save`. Rotation verified via netlist.
- `tools/erc.sh` – ERC via kicad-cli, fails on ERC errors, report in `reports/erc.rpt`.
- `tools/check_all.sh` now also runs: symbol library up to date, symbol pin sets, ERC,
  netlist comparison (`--allow-missing` until all sheets are drawn – remove it then).

### Last verification (`tools/check_all.sh`)

```
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: 31 part types, 268 refdes, 15 power symbols
symbols: OK
erc: 0 errors, 0 warnings (reports/erc.rpt)
compare: parts 0/267 present, 267 missing, 0 extra; pins compared 0, wrong-net pins 0; IPC nets touched 0, complete 0
compare: per sheet (drawn/total) 1:0/48 2:0/8 3:0/18 4:0/37 5:0/43 6:0/16 7:0/31 8:0/22 9:0/10 10:0/23 11:0/11
compare: OK
ALL CHECKS PASSED
```

### Findings

- **REF3025 pinout**: Proteus/IPC have REF1/REF2 pin 1 = GND, 2 = VIN, 3 = VOUT. The TI
  SOT-23 pinout (and KiCad's `REF3025`) is 1 = IN, 2 = OUT, 3 = GND. The project symbol
  follows Proteus (pin ids must match the IPC). Either the Proteus footprint numbers pads
  differently from their physical position, or the board has REF1/REF2 wired wrong –
  check in Phase 2 (pad geometry vs footprint) and tell the user.
- There is **no `3V3` net**: every `3V3`/`3v3` terminal in the PDF is net `VCC`
  (`VCC/VDD=POWER`). `DC-` and `AGND` (sheet 9) are net `GND`. Sheet 7's `ISO_GND`
  terminal is wired to `RET_iso` → net `RET_ISO` (it is *not* `ISOGND`).
- The relays have refdes **R20/R79** and pins 1,2,3,5,6 (no 4). PWM1 (IW1830) has no pin 6.
- J7 is a single-pin PIN terminal (like J5, J9, J10), not a gate-driver connector.
- Gate-driver connectors J1–J4, J6, J8 have pins 15–26, 29–40, 43–48 only.

### Transcription rules (for the sheet sessions)

- Use only `ac_psu:` symbols, exactly the `lib_id` in `lib/part_map.csv` for each refdes.
  Refdes exactly as there (R256, PE1…, DAB_PRI_1, FILTER_IN, INU_OUT2, …).
- Power nets → power symbols: GND, PGND, ISOGND, ISOPGND, DGND, DAB_GROUND, RET_ISO, VCC,
  3V3_ISO, 5V, 5V_ISOL, 20V, 20V_ISO_SEC, DC+, ISODC+ (mapping above for 3V3/DC-/AGND/ISO_GND).
  Add PWR_FLAGs where ERC reports undriven power pins (each power net once, on the sheet
  where it is generated or enters).
- Other named nets → labels with the IPC spelling (uppercase, e.g. `lemout` → `LEMOUT`,
  `filter_input` → `FILTER_INPUT`, `Mdata` → `MDATA`). Proteus terminals are global, so use
  **global labels** for every net that appears on more than one sheet; local labels are fine
  for nets that stay on one sheet. Auto-named `#00xxx` nets need no label (plain wires).
- N/C pins in the IPC (place a no-connect flag): J1-25 J1-39 J2-25 J3-25 J3-39 J4-39
  J6-25 J6-39 J8-25 J11-38 TR2-5 TR2-8 TR2-9 TR2-10 U3-4 U10-4 R20-5 R79-5 U17-1…16.
  R87 pins 4/5 have no net: place R87 unit D (4-5) with no-connect flags, or leave it
  unplaced (compare reports it as info only).
- Single-pin nets ADA0, ADA4, ADA5, ADA6 (U11 inputs) and DGND (U11-6): label/power
  symbol on one pin; ERC "isolated label" warnings for them are expected.
- TR1 (sheet 6) is drawn with `ETD34_TRAN_1P1S` (excluded from board); its pins connect to
  DAB_SOURCE_HI_PRI / DAB_CAP_PRI / DAB_SOURCE_HI_SEC / DAB_CAP_SEC as in the PDF.
- Keep symbols, wires and labels on the 1.27 mm grid (ERC flags off-grid ends).
- After each sheet: `tools/check_all.sh` (or `tools/compare_netlists.py --sheet N` and
  `tools/erc.sh`). Target per sheet: 0 missing on that sheet, 0 compare errors, 0 ERC errors.

## Phase 1 transcription – done (Fable 5.1, 2026-10-18)

Each sub-sheet is generated by a re-runnable script `tools/sheets/sheetNN.py` (uses
`tools/sheets/_common.py` helpers and `tools/sch_builder.py`; `Sheet.clear()` rebuilds the
sheet from scratch). Visual check: `tools/render_sheet.py kicad/NN_*.kicad_sch` →
`reports/render/NN_*.png` (kicad-cli SVG + librsvg/cairo via ctypes).
`compare_netlists.py` reports a *split* IPC net only as a warning while the net still has
pins on undrawn parts ("pending sheets ..."); it becomes an error once all its parts are drawn.
`tools/check_all.sh` now runs the comparison without `--allow-missing`.

| Sheet | Parts | Status |
|---|---|---|
| 2 fpga connector | 8/8 | done 2026-10-18; compare 0 errors, ERC 0 errors (source groups use PGND/ISOPGND/DAB_GROUND power symbols, see notes) |
| 3 regulators | 18/18 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 11 signal isolators | 11/11 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 10 INU SDM and relay drive | 23/23 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 9 primary side ADC | 10/10 | done 2026-10-18; compare 0 errors, ERC 0 errors (R87:D placed with N/C flags) |
| 8 SDM current measurements | 22/22 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 1 afe | 48/48 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 5 VSI | 43/43 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 6 Dual Active Bridge | 16/16 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 4 DC links | 37/37 | done 2026-10-18; compare 0 errors, ERC 0 errors |
| 7 Auxiliary supply | 31/31 | done 2026-10-18; compare 0 errors, ERC 0 errors |

Notes:

- PWR_FLAGs for GND, 20V, ISOGND, 20V_ISO_SEC are temporarily on sheet 2 (they enter
  through the connectors). Move them to sheet 7 (aux supply) when it is drawn – one flag per
  net. 5V/5V_ISOL/VCC/3V3_ISO are driven by power-output pins on sheet 3 (no flag needed).
- Two-pin parts get centred Reference/Value text from `sch_builder.place()` (KiCad mirrors
  or swaps field justification for rotated symbols); `vert2`/`horiz2` in `_common.py` place a
  two-pin part with a chosen pin at the top/left – check the IPC pin order (on sheet 3 every
  capacitor has pin 1 on the ground side).
- **PDF alias labels of power nets**: the PDF labels J1 15-20 / 29-34 and J3 29-34 as
  `G2_SOURCE_LO` / `G4_SOURCE_LO` / `DAB_SOURCE_LO_PRI`, J6 15-20 / 29-34 as `Q8_S` / `Q6_S`,
  J4 15-20 as `DAB_SOURCE_LO_SEC`; in the layout these are the power nets PGND, ISOPGND and
  DAB_GROUND. KiCad ERC reports *multiple_net_names* (error) when such a label shares a net
  with a power symbol, so sheet 2 uses the power symbols and shows the PDF names in brackets
  (rule: power nets → power symbols). Signal aliases that differ only in case are spelled
  like the IPC (`LEMOUT`, `FILTER_INPUT`, `SHUNT1`, ...).
- PWR_FLAG placement (final, one flag per net): 20V, GND, 20V_ISO_SEC, RET_ISO and the
  IW1830 Vcc node on sheet 7 (aux supply); ISOGND on sheet 2 (it is not generated on the
  board, it enters through J12 / J4 / J6 / J8); DC+ and PGND on sheet 1; ISODC+ on sheet 5;
  ISOPGND and DAB_GROUND on sheet 8 (R64); DGND and the L1-filtered ADC supply on sheet 9;
  the floating VDD1/GND1 rails of U4/U5/U6 on sheets 10/8. 5V, 5V_ISOL, VCC, 3V3_ISO are
  driven by power-output pins on sheet 3.
- Kelvin shunts: R48 pins 1 and 3 are the same net (SHUNT1) in the IPC, so they are wired
  together on sheet 1 (the symbol has no internal connection); R91 (sheet 5) has 4 distinct
  nets, R64 (sheet 8) too.
- Sheet 8 lower half: the PDF shows an unlabelled zener next to R75; it has no refdes and no
  pads in the IPC, so it is not drawn (text note on the sheet).
- R87 unit D (pins 4/5, no net in the IPC) is placed on sheet 9 with no-connect flags so the
  footprint's pads exist; compare treats the no-net pins as info.
- Two-pin parts get centred Reference/Value text from `sch_builder.place()` (KiCad mirrors
  or swaps field justification for rotated symbols); `vert2`/`horiz2` in `_common.py` place a
  two-pin part with a chosen pin at the top/left (rotation derived from the library pin
  geometry) – check the IPC pin order (most capacitors have pin 1 on the ground side).
  `terminal()` draws the Proteus PIN terminals, `adum_block()` the ADuM7701 blocks.

### Last verification (`tools/check_all.sh`, Phase 1 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
compare: per sheet (drawn/total) 1:48/48 2:8/8 3:18/18 4:37/37 5:43/43 6:16/16 7:31/31 8:22/22 9:10/10 10:23/23 11:11/11
compare: OK
ALL CHECKS PASSED
```

The 8 ERC warnings are expected: `isolated_pin_label` for the single-pin nets ADA0, ADA4,
ADA5, ADA6 (U11 inputs, as in Proteus); `ground_pin_not_ground` for the GND1 pins of
U4/U5/U6 (they float on the shunt nets INU_SHUNT2 / SHUNT1 / DAB_SHUNT2 by design) and for
U9 pin 3, whose Proteus name "+VOUT/GND" contains GND but carries 5V.

### Findings from the transcription (for Phase 2 and the user)

- **C67** (100 µF, 5 V rail, sheet 7): in the IPC its pin 1 is on GND and pin 2 on 5V, while
  the other polarized caps (C28, C15, C8, C11, C12, C61, C72, C79) have pin 1 on the positive
  rail. Either the footprint's pad 1 is the negative pad or the part is reversed – check the
  Proteus footprint / silkscreen polarity mark in Phase 2 and tell the user.
- **REF3025** pin ids follow Proteus (1 = GND, 2 = VIN, 3 = VOUT; TI: 1 = IN, 2 = OUT, 3 = GND),
  see above – resolve against the pad geometry in Phase 2.
- Sheet 8 shows an unlabelled zener next to R75 (U6 supply) that has no refdes and no pads
  in the IPC; it is not drawn. Sheet 7: R26 is "NA" (not fitted) in the PDF; drawn with value NA.
- The PDF's `ISO_GND` terminal on sheet 7 is wired to `RET_iso`: the isolated 20 V return
  (RET_ISO: TR2-6, C15, C36, R49) has no connection to ISOGND on this board.
- R96 / R97 (0 R) are the only links PGND–GND and ISOPGND–ISOGND (sheet 4).
- TR1 (sheet 6) is excluded from the board; the PDF's TR1 winding note is printed on page 7.
- Component values were read from the PDF renders (`source/schematic_pdf/hi-NN.png`); the
  PDF shows no footprints, so Phase 2 takes packages from `ROOT.LYT` strings and the IPC pad
  geometry (see PLAN.md section 4).

Visual check of every sheet: `reports/render/NN_*.png` (regenerate with
`tools/render_sheet.py kicad/NN_*.kicad_sch`). Layout follows the PDF pages; the per-sheet
scripts in `tools/sheets/` are the editable source of the sub-sheets (rerun a script, then
`tools/check_all.sh`).

## Phase 2 footprints – done (Opus 5.5, 2026-10-18)

New / changed files:

- `tools/fpgeom.py` – footprint pad loader (.kicad_mod → pads, Y up) and the rigid fit
  (pads matched by number, least-squares rotation snapped to 45°, mirror for bottom side,
  pads sharing a number paired by permutation) + pad-size comparison. Its docstring has the
  **KiCad placement recipe** (see below).
- `tools/gen_footprints.py` → `lib/footprint_map.csv` (refdes → footprint, generated) and
  `lib/ac_psu.pretty/` (20 project footprints, generated). `--check` verifies both are up to
  date (needs the AppImage mount for the KiCad base footprints). Assignment = `RULES` keyed by
  symbol + IPC pad pattern (pad count, span, pad size, drill); project footprints = `PROJECT`
  (derived from a KiCad footprint: renumber / drop pads / move pad centres onto the Proteus
  positions, or built from the IPC pads).
- `kicad/fp-lib-table` registers `ac_psu` → `${KIPRJMOD}/../lib/ac_psu.pretty` (KiCad std
  libraries come from the global table).
- `tools/sch_builder.py`: `place()` fills the Footprint field from `lib/footprint_map.csv`;
  **UUIDs are now deterministic** (uuid5 per sheet file; symbol/pin UUIDs keyed by refdes, unit
  and pin number, the rest by drawing order). Re-running a sheet script now reproduces the
  file byte for byte, so the symbol UUIDs the PCB will link to stay stable. All 11 sheets were
  regenerated (no layout change).
- `tools/check_footprints.py` – reads the Footprint field of every symbol in `kicad/*.kicad_sch`,
  checks it equals `lib/footprint_map.csv`, fits each footprint onto the IPC pads and fails on a
  missing footprint, pad-number mismatch, or residual > 0.05 mm. `--pcbnew` (under `kipy`) also
  places every footprint on a pcbnew BOARD with the KiCad recipe and re-measures the pads.
  Writes `reports/footprint_fit.csv` (per part: side, angle, origin in IPC and KiCad
  coordinates, worst residual, size/drill deltas – the input for Phase 3 placement) and
  `reports/footprint_pads.csv` (per pad: residual, IPC vs footprint size and drill).
  Negative-tested (plain SOT-23 for REF1 → 0.151 mm, plain SOT-23-5 for U2 → 0.068 mm,
  empty field → error).
- `tools/check_all.sh`: new steps "Footprint library and map up to date" and
  "Footprints vs IPC pad geometry".

KiCad placement recipe (verified with pcbnew 10.0.7 on all 267 parts, worst 0.038 mm):
position = (x, −y) of the IPC origin; top part → `SetOrientationDegrees(angle)`; bottom part →
`Flip(pos, FLIP_DIRECTION_LEFT_RIGHT)` then `SetOrientationDegrees((180 + angle) % 360)`.
`reports/footprint_fit.csv` already has `kicad_x, kicad_y, kicad_orientation`. 190 parts top,
77 bottom (all bottom parts are SMD). THT parts are taken as top side; every THT pattern fits
unmirrored (the chiral ones – PWM1 DIP-8 – confirm top), so no THT part is on the bottom.

### Footprint decisions

| Parts | Footprint | Worst residual |
|---|---|---|
| R 0402 (33) | `Resistor_SMD:R_0402_1005Metric` | 0.010 |
| R 0603 (4) + R25/R26/R29/R31/R44 (Proteus pads 1.73 mm apart) | `Resistor_SMD:R_0603_1608Metric` | 0.038 |
| R59/R75/R94 0805 | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` | 0.000 |
| R23/R24/R45/R47/R49 1206 | `Resistor_SMD:R_1206_3216Metric` | 0.013 |
| R 1206 with pads 3.15 mm apart (41) | `Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | 0.025 |
| R10 TWW10J15RE | `Resistor_THT:R_Radial_Power_L13.0mm_W9.0mm_P5.00mm` | 0.000 |
| C 0402 (28) / 0603 (15) | `Capacitor_SMD:C_0402_1005Metric` / `C_0603_1608Metric` | 0.030 / 0.025 |
| C 1206 (9, incl. C67) | `Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` | 0.013 |
| C 2220 2.2u (8) | `Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder` | 0.038 |
| C 2n2 THT P7.5 (14) | `Capacitor_THT:C_Disc_D12.5mm_W5.0mm_P7.50mm` (Proteus silk ~13 × 6 mm) | 0.000 |
| C21/C25/C33/C34 7u P27.5 (Proteus drill 1.27) / C24 (Proteus drill 1.016) | `ac_psu:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus` (Phase 3: Proteus pads/drills) / `Capacitor_THT:C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4` | 0.000 |
| SNAP_IN_35MM (6) | `ac_psu:CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus` (Phase 3: Proteus 5.08 pads, 2.032 drills) | 0.000 |
| C15/C28 EEEFTE221XAP | `ac_psu:CP_Elec_6.3x7.7_EEEFTE221XAP` (KiCad graphics, Proteus pads) | 0.000 |
| D1/D2/D6 SMA | `ac_psu:D_SMA_AC` (KiCad D_SMA, pads C/A, Proteus centres) | 0.000 |
| D3–D5/D7/D10, D8/D9 SOD-323 | `ac_psu:D_SOD-323_AC` (KiCad HandSoldering, pads C/A, Proteus centres) | 0.001 |
| L1 | `Inductor_SMD:L_0805_2012Metric` | 0.025 |
| Q13/Q14 2N7000, REF1/REF2 | `ac_psu:SOT-23_Proteus` (KiCad SOT-23 renumbered 3→1, 1→2, 2→3; Phase 3: Proteus pad sizes and centres) | 0.020 |
| U2/U12/U14 TLV316, U3/U10 TPS73033 | `ac_psu:SOT-23-5_TLV316` (Phase 3: Proteus pad sizes) / `SOT-23-5_TPS73033` (Proteus rows 2.39 / 2.50 mm) | 0.001 |
| U1/U7 OPA2353UA | `ac_psu:TSSOP-8_3x3mm_P0.65mm_Proteus` (the pads are MSOP/TSSOP-8, not SO-8; Phase 3: Proteus pads, no 0.2 mm footprint clearance) | 0.000 |
| U11 | `ac_psu:TSSOP-16_4.4x5mm_P0.65mm_Proteus` (Phase 3: Proteus pads) | 0.013 |
| U13/U15/U16/U17 | `ac_psu:SOIC-16W_7.5x10.3mm_P1.27mm_Proteus` (U16 at 225°; Phase 3: Proteus pads) | 0.030 |
| U4/U5/U6 ADuM7701 | `ac_psu:SOIC-8W_7.5x5.85mm_P1.27mm_ADuM7701` (rows 9.70 mm) | 0.001 |
| AD1 ADS7056 | `ac_psu:X2QFN-8_1.5x1.5mm_P0.5mm_ADS7056` (Proteus pads and sizes) | 0.000 |
| R87 | `ac_psu:R_Array_Convex_4x0402_Proteus` (pads 4/5 kept, no net) | 0.000 |
| PWM1 IW1830 | `Package_DIP:DIP-8-N6_W7.62mm` | 0.000 |
| Q1–Q12 | `ac_psu:TO-247-3_Vertical_Proteus` (1=G 2=D 3=S; Phase 3: Proteus 3.048 pads, 1.651 drills) | 0.011 |
| J1–J4, J6, J8 | `ac_psu:PinHeader_2x24_P1.27mm_Vertical_Pins15-48` (pads 1–14, 27, 28, 41, 42 removed; Phase 3: Proteus 0.812 pads) | 0.000 |
| J11 / J12 | `ac_psu:PinHeader_2x19_P1.27mm_Vertical_Proteus` (Phase 3: Proteus 0.812 pads) / `ac_psu:PinHeader_2x03_P1.27mm_Vertical_Pins43-48` | 0.000 |
| U8/U9 VXO7805 | `ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus` (Phase 3: Proteus 1.8 pads, 1.2 drills) | 0.000 |
| TR2, CM1–CM3, R48/R64/R91, R20/R79 | `ac_psu:Transformer_EF20_2x5_P3.81mm`, `L_CommonMode_WE-CMBNC`, `R_Shunt_FKK5R0020FE`, `Relay_SLA-12VDC-SL-A` (built from the IPC pads; simple rectangle outlines) | 0.000 |
| PIN terminals | `ac_psu:Terminal_D4.0mm_Drill{2.0,2.55,3.0}mm`, `Terminal_D3.05mm_Drill1.52mm`; ACIN1/2, ACOUT1/2 `Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm` (two pads "1") | 0.000 |
| TR1 | none (excluded from board) | – |

41 distinct footprints (21 KiCad library, 20 project) at the end of Phase 2; 42 (14 KiCad
library, 28 project) after the Phase 3 pad/drill decisions. Footprints built purely from the IPC
pads have generic outlines (TR2 22 × 14 mm body from the Proteus silk, others the pad box);
Phase 3 tightened their courtyards to 0.25 mm around body and pads (circles for single PIN
terminals).

### Residual report

`tools/check_footprints.py`: 267/267 parts, 898 pads (894 pins + the 4 duplicate "1" holes
of ACIN/ACOUT), worst residual **0.038 mm** (R 0603 group with Proteus pads 1.73 mm apart,
C 2220). Per footprint: `tools/check_footprints.py -v`; per pad: `reports/footprint_pads.csv`.

Pad sizes: KiCad sizes accepted (PLAN.md 4.3). Largest differences: TO-247 (KiCad 2.5 × 4.5
oval vs Proteus 3.05 round), snap-in caps (4.0 vs 5.08), C_Rect P27.5 / R10 / C_Disc
(2.0–2.4 vs 1.52–2.29). **Drills where KiCad is smaller than Proteus**: TO-247 1.5 vs 1.651,
VXO7805 1.0 vs 1.2, C21/C25/C33/C34 1.2 vs 1.27, snap-in 2.0 vs 2.032 – the user may want the
Proteus drills (then derive a project footprint with `ipc_sizes=True` in `gen_footprints.py`).
**Resolved in Phase 3** (user decision 2026-10-19): these parts now use the Proteus drills and
pads, and 8 SMD/header packages use the Proteus pad sizes, see "Phase 3 – footprint changes".

### Polarity / pinout findings (for the user)

- **REF1/REF2 (REF3025) – board is wired correctly.** In the IPC the pad Proteus calls 1 (GND)
  sits alone on one side of the SOT-23 and pads 2 (VIN) and 3 (VOUT) on the other. A top-side
  (unmirrored) fit of KiCad's JEDEC SOT-23 matches only with Proteus 1 = JEDEC pin 3,
  Proteus 2 = pin 1, Proteus 3 = pin 2 (0.020 mm; the plain numbering gives 0.151 mm). TI's
  REF3025 pinout is 1 = IN, 2 = OUT, 3 = GND, so physically IN = VCC, OUT = VOUT net,
  GND = GND. Proteus simply numbers the SOT-23 pads differently. Same for Q13/Q14 (2N7000 in
  SOT-23, Proteus 1 = D, 2 = G, 3 = S): JEDEC pin 3 = D, 1 = G, 2 = S – also correct.
- **C67 (100 µF, 5 V)** sits on a plain 1206 land pattern identical to C57/C58 (22 µF ceramics);
  the Proteus top silk and assembly layers show a plain 1206 box with no polarity mark (C28/C15,
  the SMD electrolytics, have a bar at their negative pad 2). So the Proteus footprint is
  non-polar and "pin 1 on GND" is only pad numbering: fine for a 100 µF ceramic, but if a
  polarized part (tantalum/polymer) is fitted, the board does not show its polarity. KiCad
  footprint: the same non-polar 1206 as C57/C58. Note: sheet 7 draws C67 with `C_Polarized`
  (pin 1 at GND) while `lib/part_map.csv` says `ac_psu:C` – left as drawn; switch the symbol to
  `C` in `tools/sheets/sheet07.py` if the part is ceramic.

### Last verification (`tools/check_all.sh`, Phase 2 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 41 footprints (20 project), up to date
check_footprints: pcbnew placement of 267 parts, worst pad offset 0.038 mm
check_footprints: 267/267 parts fitted, 898 pads, 41 footprints, worst residual 0.038 mm (limit 0.05)
ALL CHECKS PASSED
```

## Phase 3 PCB – done (Opus 5.5, 2026-10-19)

`kicad/ac_psu.kicad_pcb` is generated by re-runnable scripts; `tools/make_pcb.sh` runs them in
order (≈10 s) and two runs give a byte-identical board (UUIDs seeded per script with
`KIID.SeedGenerator`). Do not hand-edit the board while it is still generated – change the
scripts (or stop regenerating it and say so here).

| Step | Script | What it does |
|---|---|---|
| 3a | `tools/build_pcb.py` | Exports the kicadxml netlist, creates the board (4 Cu layers, Proteus origin, KiCad y = −IPC y), one footprint per symbol (TR1 skipped) with reference, value, Datasheet/Description, symbol link (path = sheet path + symbol UUID, sheet name/file → DRC schematic parity 0) and pad nets; placement from `reports/footprint_fit.csv` with the Phase 2 recipe; outline on Edge.Cuts from Mechanical 1 (246.8 × 154.7 mm); mounting holes H1–H4 = `ac_psu:Terminal_D4.0mm_Drill3.0mm`, board-only, no net, at the IPC 'hole' records; design rules (below); User.1–4 renamed `Proteus.{F,In1,In2,B}.Pours`; board thickness 2.267 mm (Proteus stack). |
| 3b | `tools/gerber_to_tracks.py` | Parses the copper and drill gerbers (`tools/gerber.py`). Conductor D01 draws → 4052 tracks; **pour edge strokes are not tracks** (Proteus strokes every G36 region and every clear hole with the pour's edge width, 0.1016/0.1524/0.254 mm; a draw whose ends are consecutive region vertices is a stroke – stroke count equals region edge count on every layer); ViaPad flashes on all 4 layers + ViaDrill → 173 through vias 0.4572/0.3 (= the 173 IPC vias); every pad flash lands on a footprint pad, every drill on a pad hole or via; positive G36 outlines → User.1–4 (79 pours); the 3 NonConductor draws (two floating 0.15 mm lines beside J6 pins 29–34, top) → F.Cu graphic lines, no net. `load_copper()` is the shared reader (tracks, vias, pad flashes, pours with their holes and stroke width). |
| 3c | `tools/assign_nets.py` | Union-find over copper shapes (`tools/geom2d.py`: segment/polygon cores grown by a radius, pours with holes). Stage A (Proteus pad flashes + tracks + vias): 447 groups, 0 shorts, 16 orphans (vias that only touch pours), 45 opens (connections through pours) – expected. Stage B (+ Proteus pours): **248 groups = 244 KiCad nets + 4 mounting holes, 0 shorts, 0 orphans, 0 opens**; every track/via gets its group's net (4225), every pour its net → `reports/pour_nets.json`. Via nets cross-checked against the IPC via records (IPC → KiCad net map built from the pads, 208 nets 1:1). `--check`: same analysis on the saved board with KiCad pads, tracks, vias and the filled zones; every item must carry its group's net. Report `reports/assign_nets.txt`. |
| 3d | `tools/pours_to_zones.py` | One ZONE per pour: outline = Proteus copper = region grown by half the stroke minus its clear holes shrunk by half the stroke (62 stroke-closed holes vanish, 405 kept), net from `pour_nets.json`, solid pad connection, min width 0.1 mm, islands removed, priority = Proteus draw order; filled with ZONE_FILLER. |
| 5 | `tools/drc.py` | `kicad-cli pcb drc --schematic-parity --severity-all` → `reports/drc.json` (not committed); fails on shorts, unconnected items, parity issues and error types not in its `ACCEPTED` list. |
| – | `tools/check_board.py` | Saved board vs IPC: 898 pads within 0.05 mm (worst 0.038) and on the IPC net (IPC ↔ KiCad nets 1:1 via the pads, N/C pins on no/`unconnected-` nets), 4 mounting holes (plated 3.0/4.0, no net), 173 vias at the IPC via positions on the IPC net, every track/via/zone has a net. |

How Proteus pours work (and why the zones look like this): the pour copper is the G36 region
plus its edge stroke; clear (`%LPC%`) regions after it are its holes: clearance cut-outs around
other-net copper, **thermal reliefs** (a hole around a same-net pad bridged by short spoke
*tracks*, which are imported as ordinary tracks), and deliberate isolation of a same-net via or
pad from the pour on that layer. Pads inside the pour without a hole are connected solid. The
zones keep every hole, so the KiCad fill reproduces the Proteus copper; KiCad's 0.15 mm
clearance applies on top (it only bites where a KiCad pad is larger than the Proteus pad).
Exported F.Cu (kicad-cli svg) was compared by eye with a render of the Proteus top copper:
same pours, holes, spokes and tracks.

Design rules (board setup, stored in `kicad/ac_psu.kicad_pro`): clearance 0.15 mm (Proteus
uses 6 mil: the smallest gap between different nets in the gerbers is 0.1514 mm, arc
rounding), min track 0.1 mm (thinnest Proteus track 0.1016), via 0.45 min / annular 0.075 /
drill 0.3 (Proteus vias 0.4572/0.3), hole clearance 0.15, hole-to-hole 0.25, copper-edge 0.25;
Default netclass 0.254 track, 0.4572/0.3 via.

### Phase 3 – footprint changes (user decision 2026-10-19)

The first DRC with KiCad library pads gave 2 shorts (U11 pins 9–11 touched the ADA3 track
routed past their ends; U2 pin 3 touched an ISOGND track), 54 clearance errors and 4 mask
bridges – all where KiCad pads are larger than the Proteus pads and reach Proteus tracks. The
user chose (1) Proteus pad sizes for exactly those packages and (2) Proteus pads + drills
where the KiCad drill was smaller than Proteus. `tools/gen_footprints.py` now derives
(`ipc_sizes=True`, pad centres and sizes/drills from one IPC part, KiCad graphics kept):

| Footprint | From | Change |
|---|---|---|
| `PinHeader_2x24_P1.27mm_Vertical_Pins15-48` (J1–J4, J6, J8), `PinHeader_2x19_P1.27mm_Vertical_Proteus` (J11) | J1 / J11 | pads 1.0 → 0.812 mm |
| `TSSOP-16_4.4x5mm_P0.65mm_Proteus` (U11), `TSSOP-8_3x3mm_P0.65mm_Proteus` (U1, U7) | U11 / U1 | pads 1.475×0.4 → 1.1×0.4; TSSOP-8's 0.2 mm footprint clearance dropped (Proteus land patterns use the board rule) |
| `SOT-23-5_TLV316` (U2, U12, U14), `SOT-23_Proteus` (Q13, Q14, REF1, REF2) | U2 / REF1 | pads 1.325×0.6 → 0.635×0.508; 1.475×0.6 → 1.016×0.889 |
| `SOIC-16W_7.5x10.3mm_P1.27mm_Proteus` (U13, U15–U17) | U13 | pads 2.05×0.6 → 1.85×0.65 |
| `TO-247-3_Vertical_Proteus` (Q1–Q12) | Q1 | pads 3.048 round (pin 1 square), drill 1.5 → 1.651 |
| `Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus` (U8, U9) | U8 | pads 1.8, drill 1.0 → 1.2 |
| `C_Rect_L33.0mm_W20.0mm_P27.50mm_MKS4_Proteus` (C21, C25, C33, C34) | C21 | pads 2.286, drill 1.2 → 1.27 (C24 keeps the KiCad footprint: its Proteus drill is 1.016) |
| `CP_Radial_D35.0mm_P10.00mm_SnapIn_Proteus` (C8, C11, C12, C61, C72, C79) | C11 | pads 4.0 → 5.08, drill 2.0 → 2.032 |

Courtyards of the footprints built from the IPC pads (TR2, CM1–3, R48/R64/R91, R20/R79, PIN
terminals, ACIN/ACOUT, mounting holes) were tightened from pad box + 1.0 mm to 0.25 mm around
body and pads (circles for single round PIN terminals): 60 → 50 courtyard overlaps.
The schematic sheets were re-run so their Footprint fields follow `lib/footprint_map.csv`
(only Footprint fields changed).

### Remaining DRC items (all justified, `tools/drc.py` passes)

| Type | Count | Why it stays |
|---|---|---|
| shorting_items / unconnected / schematic parity | 0 / 0 / 0 | – |
| courtyards_overlap (error) | 50 | Proteus placed parts closer than KiCad's IPC-7351 courtyards (mostly 0402/1206 passives beside ICs, film/disc caps, terminals). Parts sit exactly at the Proteus positions; accepted in `tools/drc.py`. |
| pth_inside_courtyard (error) | 6 | J4 pins 47/48 inside J6's courtyard (the 2×24 outline still covers J6's unfitted pins 1–14; physical 2×24 housings would clear by ≈0.1 mm), J12 pins inside U8's courtyard (see U8/U9 finding). Accepted. |
| silk_overlap / silk_over_copper / silk_edge_clearance (warning) | 199 / 199 / 12 | KiCad footprint silk and default reference positions on a dense Proteus placement (PLAN 3e: silk comes from the KiCad footprints; refdes positions could be taken from the Proteus assembly layers later). |
| via_dangling (warning) | 2 | Proteus copper as drawn: GND via at (91.80, −49.09) and VCC via at (43.69, −20.29) (IPC coordinates, Y up) connect on one layer only. |
| track_dangling (warning) | 1 | 0.14 mm PWM_TRANS5 stub on In2.Cu at (47.7, 43.6) (IPC coordinates) in the Proteus copper. |

### Findings (for the user / Phase 4)

- **U8/U9 (VXO7805) body side**: the Proteus top silk draws the converter body (11.5 × 7.3 mm)
  entirely on the −y side of the pin row (away from J12), the KiCad R-78E footprint puts most
  of the body on the +y side, over J12's pins (hence the J12/U8 courtyard errors). Pads and pin
  order match, so only the body/courtyard graphics differ. Check the VXO7805 datasheet: if
  Proteus is right, mirror the body graphics in the project footprint
  (`Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus`). **Note:** the orientation of the mirrored
  graphics needs to be checked (body side relative to the pin row and J12, pin-1 marking,
  courtyard) against the datasheet and the Proteus silk.
- C67 symbol (`C_Polarized` on sheet 7 vs `ac_psu:C` in part_map, non-polar 1206 land pattern)
  is still open (Phase 2 finding).
- KiCad pads are still larger than Proteus on footprints that have no DRC conflict (e.g.
  0402/0603/1206 passives, J12, TPS73033). The gerber round trip (Phase 4) will show them.

### pcbnew 10.0.7 quirks found in Phase 3

- `board.Remove(item)` + garbage collection of the item's Python proxy breaks SWIG's type
  table: later calls return untyped `SwigPyObject`s (`GetNetInfo()`, `ZONE.Outline()`) and
  "memory leak … no destructor found" floods stderr. Use `board.Delete(item)`; set
  `thisown = False` on items created in Python after `board.Add()`.
- `LoadBoard` re-derives track nets from the connected pads (a wrong net written into the file
  is silently corrected on load), and `SaveBoard` writes the board design settings into the
  `.kicad_pro`.
- `KIID.SeedGenerator(n)` makes new UUIDs reproducible.

### Last verification (`tools/check_all.sh`, Phase 3 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 42 footprints (28 project), up to date
check_footprints: pcbnew placement of 267 parts, worst pad offset 0.038 mm
check_footprints: 267/267 parts fitted, 898 pads, 42 footprints, worst residual 0.038 mm (limit 0.05)
check_board: 271 footprints, 898 pads, worst pad offset 0.038 mm (limit 0.05), 208 IPC nets mapped 1:1, 4 mounting holes
check_board: 4052 tracks, 173 vias, 79 zones
assign_nets: after zone fill: 248 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
drc: 469 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
drc:     50 error    courtyards_overlap  accepted: KiCad courtyards vs the Proteus placement
drc:      6 error    pth_inside_courtyard  accepted: KiCad courtyards vs the Proteus placement
drc:    199 warning  silk_overlap
drc:    199 warning  silk_over_copper
drc:     12 warning  silk_edge_clearance
drc:      2 warning  via_dangling
drc:      1 warning  track_dangling
ALL CHECKS PASSED
```

Negative tests: footprint moved 0.1 mm → check_board fails; via deleted → check_board and
assign_nets --check (open VCC) fail; track net changed in memory → assign_nets --check reports
the foreign net.

## Phase 4 verification and review – done (Fable 5.1, 2026-10-19)

Independent checks of the end result against the Proteus CADCAM files, plus a review of the
Phase 3 findings. Both new checks are part of `tools/check_all.sh` (pass/fail).

New / changed files:

- `tools/gerber.py` now also reads KiCad's plots: 4.6 format, obround apertures, aperture
  macros with several primitives and `$n` expressions (KiCad's `RoundRect`: outline + circles
  + vector lines), and the `%TO.P/.N/.C` object attributes (attached to every object as
  `.attrs`). The Proteus side is unchanged (`tools/make_pcb.sh` still reproduces the board
  byte for byte).
- `tools/gerber_roundtrip.py` (system python3: numpy, scipy, PIL) – PLAN 6.3. Exports the 4
  copper layers and the plated drill of the board with kicad-cli (gerbers + drill as gerber,
  to a temp dir), rasterises both gerber sets on one 0.025 mm grid (objects in file order with
  their polarity, so Proteus' clear regions cut the pours like a plotter; the Proteus board
  outline that Proteus draws into every copper gerber with a `Profile` aperture is skipped) and
  per layer: raw XOR area, differing area after a 0.05 mm tolerance, 8-connected difference
  clusters with side, area, position, nearest IPC pad/net and via, and a category (**pad shape**
  = inside the XOR of the two sets' pad flashes; **clearance** = Proteus copper within 0.15 +
  0.05 mm of a KiCad pad that is larger than the Proteus pad; **zone fill** = Proteus copper
  thinner than the 0.1 mm zone minimum width; **other** = finding). Because a 0.05 mm
  tolerance cannot see features thinner than 0.1 mm (thinnest Proteus track 0.1016 mm), it
  also checks **coverage**: the centre line of every draw and the centre of every flash of each
  set must lie on copper of the other set (1 px slack; samples inside the clearance / pad
  shape masks are explained). Drills: every Proteus drill has a KiCad drill within 0.05 mm
  and vice versa; KiCad may be larger (footprints kept with the KiCad drill, Phase 3 decision)
  but never smaller. Report `reports/roundtrip/roundtrip.txt` (every cluster ≥ 0.01 mm², pad
  shape clusters per footprint, drill table), overlays `reports/roundtrip/{F_Cu,In1_Cu,In2_Cu,
  B_Cu}.png` (0.1 mm/px: common copper grey, only Proteus red, only KiCad cyan, differences
  absorbed by the tolerance dim yellow). `--check` fails on an `other` cluster, an uncovered
  draw/flash or a drill mismatch. ≈ 40 s.
- `tools/ipc356_diff.py` (stdlib) – PLAN 6.4. Exports the board's IPC-D-356 with kicad-cli and
  matches every Proteus record (same truncated refdes + pin, nearest position; vias; mounting
  holes) to a KiCad record within 0.05 mm, then checks THT/SMD, side, drill (KiCad never
  smaller) and net by pad-set equivalence (Proteus nets ↔ KiCad nets 1:1; Proteus N/C and
  net-less pads ↔ KiCad `unconnected-(…)` / N/C). KiCad's file: units `CUST 0` = 0.0001 inch,
  net names > 14 characters as `NNAME` aliases, `Y0000` for round pads, refdes `VIA`, mounting
  holes `H1..H4` as N/C, bottom side = access code 04 (copper layer count).
- `tools/check_all.sh`: steps "IPC-D-356 from the board vs Proteus" and "Gerber round trip vs
  Proteus (copper, drills)".

### Gerber round trip (`tools/gerber_roundtrip.py`)

| Layer | Proteus copper | KiCad copper | raw XOR | only Proteus (> 0.05 mm) | only KiCad (> 0.05 mm) | clusters ≥ 0.01 mm² | uncovered draws/flashes |
|---|---|---|---|---|---|---|---|
| F.Cu | 19439.7 mm² | 19501.2 mm² | 94.38 mm² | 2.62 mm² | 58.34 mm² | 188 pad shape | 0 / 0 |
| In1.Cu | 6395.0 | 6489.9 | 99.09 | 0.00 | 81.57 | 91 pad shape | 0 / 0 |
| In2.Cu | 6519.7 | 6627.9 | 112.07 | 0.04 | 92.08 | 117 pad shape, 3 clearance | 0 / 0 (3 Proteus strokes explained) |
| B.Cu | 15580.9 | 15707.4 | 144.19 | 1.42 | 99.01 | 316 pad shape | 0 / 0 |

No `other` cluster on any layer: outside the pads the KiCad copper (tracks, vias, zone fills
with their holes and thermal spokes, the NonConductor lines) is the Proteus copper to within
0.05 mm, and every Proteus draw/flash is on KiCad copper and vice versa. Every cluster is
explained (the full list is in the report):

- **pad shape, only KiCad** (the bulk, 58–99 mm² per layer): the square pad 1 of the TO-247s
  (Proteus round 3.048; ≈ 20 mm² on F/B.Cu), the 2.0 mm pads of the 14 disc capacitors
  (`C_Disc_D12.5mm` vs Proteus 1.524; ≈ 31 mm² on the inner layers), the rounded-square pad 1
  of the 6 snap-in caps (Proteus round 5.08), the 1206 hand-solder pads (`R_1206 …
  Pad1.30x1.75mm`, 41 parts, vs Proteus 1.016 × 1.524; 26.6 mm² on B.Cu), R10 and C24 (KiCad
  2.4 mm pads vs Proteus 1.52 / 2.29), PWM1 (DIP-8 1.6 oval vs 1.524), J12 (1.0 vs 0.812),
  D_SMA/D_SOD-323 hand-solder pads, U4–U6 (ADuM7701 pads), U8/U9 (square pad 1), R59/R75/R94
  (0805), `C_1206 … Pad1.33x1.80mm`, and the round-rect corners of KiCad pads in general.
- **pad shape, only Proteus** (0–2.6 mm² per layer): Proteus pads are *larger* than KiCad's on
  the 0402 and 0603 passives (e.g. C 0402 0.609² vs KiCad 0.56 × 0.62, R 0603 group with 1.73 mm
  spacing 0.939 × 0.99 vs 0.9 × 0.95), the plain `R_1206_3216Metric` (R23/R24/R45/R47) and L1
  (0805, Proteus 1.6 × 1.0 pads). So the Phase 3 note "KiCad pads larger than Proteus on
  0402/0603" is the wrong way round; it is right for the 1206 hand-solder pads and J12.
  TPS73033 (U3/U10): 0.03 mm² in total.
- **clearance** (In2.Cu, 0.04 mm² in 3 clusters) and the 3 explained coverage misses: the
  ISOGND pour's edge strokes at the corners of J12-43, where KiCad's 0.15 mm clearance around
  the 1.0 mm square KiCad pad bites into Proteus copper that was 0.15 mm from the round 0.812 pad.
- Drills: 562 = 562 matched within 0.05 mm. Equal diameters everywhere (0.5588 vs 0.558 is
  rounding) except where the KiCad footprint drill is larger: 28 × 0.8128 → 1.0 (C_Disc), 7 ×
  0.762 → 0.8 (PWM1), 6 × 0.5588 → 0.65 (J12), 2 × 1.01 → 1.2 (R10), 2 × 1.016 → 1.2 (C24).

Blind spots of the round trip: a 0.05 mm tolerance hides differences in features narrower
than 0.1 mm – covered for tracks and flashes by the coverage check, not for pour slivers
under 0.1 mm (KiCad's zone minimum width removes those anyway); and copper that is redundant
with a same-net zone (a track inside its own pour) is, correctly, no copper difference.
Negative tests: a 53 mm F.Cu track (y = 44.6, mostly inside its pour) turned into a move → the
parts of it outside the pour appear as 3 `other` clusters (0.87 mm²), FAILED; a 0.33 mm In1.Cu
spoke inside its zone removed → no difference (as it should be); the board outline left in the
raster → 200 mm² `other` ring on every layer (how the Profile skip was found).

### IPC-D-356 diff (`tools/ipc356_diff.py`)

1075 Proteus records = 1075 KiCad records, all matched: 898 pads (incl. the 36 N/C / net-less
pads and the duplicate pin-1 holes of ACIN/ACOUT), 173 vias, 4 mounting holes; worst position
offset 0.039 mm; THT/SMD and side equal everywhere; 208 Proteus nets ↔ 208 KiCad nets 1:1;
**0 mismatches**. KiCad drills larger as above; pad sizes differ on 406 pads (info, the pad
shape list above). Negative test: one record moved to another net and one shifted 0.1 mm →
FAILED (the moved record breaks the 1:1 net mapping, the shifted one has no record within 0.05 mm).

### Review of the Phase 3 findings and the spot checks

- **Thermal reliefs / zone holes**: 79 zones with 409 holes, solid pad connection, 0.1 mm
  minimum width; the round trip shows the filled copper equals the Proteus pours with their
  holes and spoke tracks. Confirmed.
- **NonConductor lines beside J6**: 3 F.Cu graphic lines without net (0.1524 mm): (64.5, 52.7)–
  (69.05, 52.7), (65.39, 50.0)–(68.2, 50.0) and a 0.026 mm stub at (69.05, 52.7) – Phase 3 said
  "two lines", the third draw is the stub. Present in both gerber sets (coverage 0 misses).
- **Mounting holes** H1–H4: at the IPC positions, 3.0 mm plated, 4.0 mm pad, no net; the drill
  files agree. Confirmed.
- **Bottom-side parts**: 77, all SMD, pads only on B.Cu, silk on B.SilkS; the IPC diff confirms
  the side of every pad (KiCad access 04 ↔ Proteus 16). Confirmed.
- **ACIN1/2, ACOUT1/2**: two pads "1" per part, both on the net, matched by position. Confirmed.
- **R87 pads 4/5**: on `unconnected-(R87D-R4.1-Pad4)` / `…Pad5`, no net in Proteus; no copper
  touches them (DRC 0 shorts). Confirmed.
- **Kelvin shunts**: R48 1/3 = SHUNT1, 2 = SHUNT2, 4 = G1_SOURCE_HI; R64 DAB_SHUNT2 /
  DAB_SHUNT1 / ISOPGND / DAB_GROUND; R91 INU_SHUNT2 / INU_SHUNT1 / Q7_S / Net-(J7-Pad1) – as in
  the IPC. Confirmed.
- **Single-pin nets** ADA0/ADA4/ADA5/ADA6 (U11-15/1/2/4) and DGND (U11-6): one pad each, no
  track, no zone. Confirmed.
- **Dangling via/track warnings**: the copper is Proteus' to 0.05 mm, so the two vias
  connected on one layer only and the 0.14 mm PWM_TRANS5 stub are Proteus artefacts. Confirmed.
- **U8/U9 (VXO7805) body side** – resolved 2026-10-23 by v4 fix 6 (photo of the built board: Proteus was right). Was: still open, now with the datasheet facts (CUI VXO78-500,
  rev. 05/2023, mechanical drawing p. 3): body 10.0 × 7.2 × 11.0 mm, pins Ø 1.2 on 2.54 mm, pin
  row 1.80 mm from the module-PCB face and 5.40 mm from the component face; the front view
  (component side, toroid visible) numbers the pins 1-2-3 left to right. With pin 1 at −x
  (U8/U9 at 0°) that puts the body bulk on the **−y side of the pin row – the Proteus silk**
  (body entirely on −y, away from J12); the KiCad R-78E graphics put 6.56 mm on +y and 2.06 mm
  on −y (KiCad frame: body −6.56 … +2.06, pin 1 at x = 0). **But** the same page's
  "Recommended PCB Layout Top View" draws the outline on the other side of the pin row (pins
  at the bottom edge, pin 1 left), so the datasheet is internally inconsistent. If Proteus is
  right the footprint body should span y = −5.4 … +1.8 (IPC frame; plus 0.25 mm courtyard),
  which would also remove the 4 J12/U8 `pth_inside_courtyard` errors (J12's pads are 3.1 mm
  on the +y side). Not changed – decide with a physical part in hand; after mirroring, check
  pin-1 marking, body side vs J12 and the courtyard again.
- **C67** (`C_Polarized` on sheet 7 vs `ac_psu:C` in part_map, non-polar 1206 land pattern):
  unchanged, open.
- **KiCad pads larger than Proteus** where there is no DRC conflict: quantified above
  (per footprint in `reports/roundtrip/roundtrip.txt`); largest only-KiCad copper on the TO-247
  square pad 1, the disc caps, the snap-in pad 1 and the 1206 hand-solder pads; 0402/0603 are
  the other way round. All within DRC (0 clearance errors).
- Scripts read for the review (`build_pcb.py` rules, `pours_to_zones.py`, `assign_nets.py`,
  `check_board.py`, `drc.py`): nothing found that the two independent checks did not already
  cover; design rules in the board are the Proteus values (clearance 0.15, track 0.1, via
  0.45/0.3, 4 layers, 2.267 mm).

### Final state of the migration

- Schematic: 11 sheets generated by `tools/sheets/sheetNN.py`, pin-for-pin identical to the
  Proteus IPC-D-356A netlist (`compare_netlists.py`: 267/267 parts, 894 pins, 0 wrong-net pins,
  244/244 nets complete), ERC 0 errors (8 expected warnings).
- Footprints: 42 (14 KiCad library, 28 project), every pad within 0.038 mm of the Proteus pad.
- Board: generated by `tools/make_pcb.sh` from the schematic and the Proteus gerbers,
  reproducible byte for byte; 271 footprints, 4052 tracks, 173 vias, 79 zones; copper
  connectivity 0 shorts / 0 opens; DRC 0 shorts, 0 unconnected, 0 parity issues (50 + 6
  courtyard errors and 413 silk/dangling warnings accepted, see Phase 3); KiCad copper = Proteus
  copper to 0.05 mm except pad shapes (listed above); KiCad IPC-D-356 = Proteus IPC-D-356
  (positions, sides, nets).
- Open points (user decisions): U8/U9 body graphics (done: v4 fix 6), C67 symbol, silk/refdes positions
  (KiCad footprint defaults, PLAN 3e), KiCad vs Proteus pad sizes where DRC does not force a
  choice, KiCad drills larger than Proteus on C_Disc/J12/PWM1/R10/C24.

### Last verification (`tools/check_all.sh`, Phase 4 done)

```
pcbnew 10.0.7
ipc356: nets=208, refdes_raw=265, tht_records=562, smd_records=513, nc_pads=34, vias=173, holes=4, parts=267
gen_symbols: lib/ac_psu.kicad_sym up to date (47 symbols)
symbols: OK
erc: 0 errors, 8 warnings (reports/erc.rpt)
compare: parts 267/267 present, 0 missing, 0 extra; pins compared 894, wrong-net pins 0; IPC nets touched 244, complete 244
gen_footprints: 267 parts, 42 footprints (28 project), up to date
check_footprints: 267/267 parts fitted, 898 pads, 42 footprints, worst residual 0.038 mm (limit 0.05)
check_board: 271 footprints, 898 pads, worst pad offset 0.038 mm (limit 0.05), 208 IPC nets mapped 1:1, 4 mounting holes
check_board: 4052 tracks, 173 vias, 79 zones
assign_nets: after zone fill: 248 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
drc: 469 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
ipc356_diff: Proteus 1075 records, KiCad 1075; matched 1075 (898 pads incl. 36 N/C, 173 vias, 4 holes), worst position offset 0.039 mm (limit 0.05)
ipc356_diff: 208 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
roundtrip: F.Cu   XOR   94.38 mm^2, beyond 0.05 mm: only Proteus   2.62, only KiCad  58.34 mm^2; clusters >= 0.01 mm^2: 188 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In1.Cu XOR   99.09 mm^2, beyond 0.05 mm: only Proteus   0.00, only KiCad  81.57 mm^2; clusters >= 0.01 mm^2: 91 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In2.Cu XOR  112.07 mm^2, beyond 0.05 mm: only Proteus   0.04, only KiCad  92.08 mm^2; clusters >= 0.01 mm^2: 117 pad shape, 3 clearance; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: B.Cu   XOR  144.19 mm^2, beyond 0.05 mm: only Proteus   1.42, only KiCad  99.01 mm^2; clusters >= 0.01 mm^2: 316 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: drills 0 mismatches; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png
ALL CHECKS PASSED
```

## Next

v4 design fixes are done (section at the top). Open: the user's by-eye review in the KiCad GUI
(list in "For the KiCad GUI"), measuring the real shunt inductance (then re-pick the 12.4 R per the
tuning rule; a value change only needs the sheet scripts, `lib/v4_deviations.csv` value rows and
a small board script for the footprint values), and the older optional clean-up points (U8/U9 body
graphics, C67 symbol, silk positions, pad sizes – Phase 4 "Final state"). `next_prompt.md` has the
prompt.

## Next prompt

See `next_prompt.md`.
