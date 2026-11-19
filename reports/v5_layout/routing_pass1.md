# Routing pass 1 of the card area and the aux flyback area (quick pass, to judge the placement)

Branch `routing-pass1`, started from 0fc3de5 (`v5-layout`). Nothing here is a finished layout: the routed board is
a measurement of the placement. Coordinates: IPC frame, mm, y up. Tools: KiCadRoutingTools driven by
`tools/v5/route_pass1/chain.sh` (rules in `routing.json`), checks by `tools/v5/route_pass1/check_and_render.sh`.

## Verdict

Routable, but not as it stands without changes on the ISO side. The CTRL pieces (J11 fan-out, analog chain, buck),
the primary side of the isolators and the low-voltage part of the aux flyback route almost completely with a coarse
chain (155 of 174 signal connections, no short, no clearance error, 0 domain-gap violations). What does not close
is the ISO traffic between the north isolator row (U21 / U19 / U20) and the parts west of J11: 8 of 18 ISO signal
nets through that region stay open in the legal run, and one ground plane (In4 ISOGND) is cut in two. The cause is
the order of the isolators and channels against their destinations, not the height of the passage itself.
The supplies of the ISO and primary side were not measured (the router did not finish them in the time given).

## Before / after

Measured with the skill's `check_board.sh` (DRC with zones refilled, parity), `check_pass.py`, `tools/v4/domain_gaps.py`
and `tools/v5/check_layout.py`. Baseline = `kicad/ac_psu.kicad_pcb` at 0fc3de5; after = `build/route2/routed.kicad_pcb`.

| | Before | After (run 2) |
|---|---|---|
| Unconnected items (DRC) | 354 on 140 nets | 123 on 26 nets |
| of these: signal connections | 174 | 19 on 15 nets |
| supply connections | 177 | 101 (CTRL: 78 -> 2; ISO 60 and primary 39 not routed: time limit) |
| bus wire links (stay) | 3 items (ISODC+ 1, ISOPGND 2) | 3 |
| Vias (all / on signals, skill count) | 118 / 58 | 283 / 175 (165 new, 117 of them on signals) |
| DRC shorts / clearance / hole errors | 0 / 0 / 0 | 0 / 0 / 0 |
| DRC errors left | 37 courtyards_overlap, 2 pth_inside_courtyard (accepted in tools/drc.py) | the same 39 |
| Dangling (warnings) | 47 tracks, 4 vias | 37 tracks, 12 vias (8 vias left by failed routes) |
| Schematic parity | 0 | 0 |
| Plane islands, card planes | every plane 1 (In2 3V3_CTRL: 1 + 7 slivers of 0.14 mm2) | every plane 1, except In4 ISOGND: 2 |
| Domain gaps (5.0 mm P / I / C) | not re-measured (given: 0) | 0 violations |
| HV spacing 2.5 mm (new copper, F / B) | - | 0 violations |
| Existing copper changed or removed | - | 0 |
| check_layout.py | given: OK | FAILED: 16 track pieces on In4 in the I plane (one tap), plane in 2 islands |
| New copper outside the `unrouted` rectangles | - | 120 track ends of 3 nets at y 54..55.3 north of J8 / J11; 3 ends of GPIO_BYPASS_RLY at y -22.05 |

Iterations:

| Run | Change | Unconnected | Signal opens | New vias (signal) | What the renders / checks showed |
|---|---|---|---|---|---|
| 1 | passage nets first, no fences, J11 west-row stubs scripted; stopped after supply_C | 132 | 29 | 197 (147) | 207 track ends outside the allowed rectangles: PWM_Q7, four taps and the relay line went north of INU_OUT2 (y > 55.3) and west of x 22; In4 ISOGND in 3 islands; PWM bundle 5 of 6 open (walled in by the passage nets); HV step 7 of 8 nets open (2.5 mm also between two HV nets: impossible, their pads are closer) |
| 2 | fences around the allowed area, PWM bundle before the passage nets, stubs for the north-row pins of J6 / J4, J11 top fan on F.Cu only in pin order, HV-to-HV 1.0 mm, split leftovers | 123 | 19 | 165 (117) | J11 top fan planar (17 of 21 without a via, 21 of 21 after leftovers); passage step 5 of 12; all copper legal except one tap on In4 |

## What stayed open, and why

| Group | Open | Nets | Why |
|---|---|---|---|
| Passage north of J11 (12 nets) | 7 | INU_ADCLK, MDATA_INU, GPIO_BYPASS_RLY_ISO, Net-(U2--), Net-(U7A--), Net-(U7B-+), Net-(U7B--) | INU pair: U21's ISO pins (x 61.7..65.6) are walled in by the In3 diagonals PWM_Q6 / Q8 / TRANS5 from U19 (x 71..77) to the west end of J6 (x 56..59). Taps: router log names the pads of the U7 / U2 block (ISOGND, REF_1V65_ISO, 3V3_ISO pads around U2-3/-4, U7-2/-3/-5/-6) as static blockers, and earlier-routed taps. Relay: U20-12 end. Not the passage height: one tap and three PWM lines pass, In4 is nearly unused there |
| PWM bundle (6) | 1 | DAB_PWM_HI_SEC | U20-14 -> J4-43 (north row): blocked by the taps / PWM_TRANS6 around J4 pins 43..48 |
| J11 to bottom isolators (14) | 3 | ADCLK_DAB_CTRL (U21-4), MDATA_INU_CTRL (U21-5), PWM_Q5_CTRL (U19-2) | pins in the middle of the row with tracks on both sides of the pin row (B.Cu) and the decoupling caps at y 28.95 |
| Primary (22) | 1 | CLK1 | R87-3: see finding 5 |
| Aux HV (8) | 7 on 3 nets | AUX_VIN (4), AUX_CLAMP, DC+ (2) | mostly tooling: the router got a flat 2.5 mm to every non-HV net and does not read pad clearances, so pads like C111-1, C68-2, R98-2 (their own part's other pad is closer than 2.5 mm) cannot be left. Not evidence against the placement; the long AUX_VIN / AUX_CLAMP runs are (finding 6) |
| Supply CTRL (5) | 2 | 3V3_CTRL 1, CTRLGND_A 1 | 76 of 78 done by the router (48 vias); not looked at pad by pad (rule 7 of the brief is not checked) |
| Supply ISO (4), primary (3) | 60 + 39 | 15V_ISO, 3V3_ISO, 5V_ISOL, ISOGND; GND, VCC, 15V | not routed: the router ran 17 min (run 1) and into the 8 min limit (run 2) without ending. Open question, not a finding |

Routed completely: sigma-delta pair to U6 (2), ISOADA chain and REF_1V65_ISO (7), ISO_DAB_SDM_RAW_VOLTAGE, J11 to
U15 / U13 / U16 (21), CTRL analog chain (17), buck (6), aux low-voltage nets (9) and AUX_W2.

## Placement findings (most valuable first)

1. **Order of the north isolator row against its destinations** (seen in the In3 renders of both runs, and the cause
   of most open nets). Every ISO net that goes west (U4 pair, six taps, relay, PWM_Q5 / Q7 / TRANS6) has to leave
   through the missing pin columns of J6 (x 60.1 and 67.7, 1.7 mm each) or the 9.4 mm gap between J6 and J4
   (x 77.0..86.5), then run west at y 52.6..55.3. Under the bus band only In3 is free, so nothing may cross there:
   - PWM_TRANS4 leaves U19-11 at x 72.7 and ends at J4-47 (86.9, 50.8); PWM_TRANS6 leaves U20-15 at x 88.7 and
     goes west. They cross each other and the J6 / J4 gap. **Swap the channels of PWM_TRANS4 and PWM_TRANS6**
     (allowed by the brief): TRANS4 then sits under J4, TRANS6 beside Q5 / Q7.
   - PWM_Q6 / Q8 / TRANS5 run from U19 (x 71.4..76.5) to J6 pins 43 / 44 / 47 at x 56.3..58.8, right across the ISO
     pins of U21 (x 61.7..65.6), whose INU pair must go the other way. **Exchange U21 and U19** (U19 to
     x 63.65, U21 to x 74.6), or assign the channels so that from west to east the row carries: J6 west-end nets
     (TRANS5, Q8, Q6) at x < 66; west-bound nets (Q5, Q7, TRANS6, relay, INU pair) at x 72..86, under the J6 / J4
     gap; J4 nets (TRANS4, DAB_PWM_HI/LO_SEC) at x 86..89. U20 has two free channels (pins 6 / 11, 7 / 10).
   - J6 pins 43, 47 and J4 pins 43, 47 are in the north row: from the south they are reached only through the
     0.46 mm gap of the south row (0.152 mm track at 0.154 mm). J6-47 / J6-48 are also 0.25 mm from the barrier
     corner at (57.3, 49.6): one lane.
2. **Passage north of J11**: the strip between the J8 pads (y 52.6) and the INU_OUT2 pads (y 55.46) holds 7 tracks
   of 0.2 / 0.15 mm per layer (In3, In4), 14 in all; demand is 12 signals plus whatever of ISOGND / 3V3_ISO /
   15V_ISO / 5V_ISOL has to reach J8 and U4 (not measured). Only 1.4 mm of it (3 tracks per layer) is inside the
   `unrouted` rectangle (y <= 54). In run 2 the passage was not the limit (see table above). Arithmetic plus one
   render, not a proof.
3. **U7 / U2 block (x 94.8..104.5, y 2.6..12.3)**: four of the six taps fail at this end; the log names the block's own
   pads as blockers. Not looked at in a zoomed render. Since the block stays (v5 step 14), the fix is on the
   routing side: a scripted via at each of the six input pins, 0.152 mm tracks.
4. **J11 fan-out**: good as placed for the top side. J11 pin order maps monotonically onto U15 / U13 / U16, the fan
   is planar on F.Cu. The west row has no way out except the 0.46 mm gaps of the east row (the area edge is 0.1 mm
   from the pads): 17 scripted 0.152 mm stubs, DRC clean. **J14 (65.3, 17.5) stands in the middle of the fan**
   (render j11_F: the fan splits around it) and the last four nets to U16 loop under the pin row; move J14 out of
   the diagonal (candidate: east of the U16 fan, about x 84, y 24; to be checked by a rerun).
   Bottom side: J11 pins 24..37 map onto U21 / U19 / U20 in scrambled order, and the channel under the pins
   (B.Cu, y 27.9..29.8) is closed by C121 / C117 / C119 at y 28.95 and the difference-amplifier block right below.
   With the channels reassigned for finding 1, order them so that northern J11 pins go to western isolator pins;
   moving the U25 / U26 blocks 2..3 mm south would open the channel (impression from render j11_B).
5. **R87 (59.34, 4.49, bottom)**: its pins 1..3 (CS1, SDATA1, CLK1; 0.5 mm pitch) face north, 0.6 mm from the edge of
   the primary area (y 5.8): room for one 0.2 mm track, two are needed. CLK1 open in both runs. Move the ADC group
   about 1 mm south or turn R87 so these pins face south (numbers from the pads; not tried).
6. **Aux flyback** (impression from the run 1 render and the pad list): AUX_VIN is one 450 V net from
   R136 / R141 / C112 / R98 (y -5..-12) to T1-11 / C111 (y -49..-53), 36..40 mm through the controller area;
   AUX_CLAMP runs 25 mm from D13 (81.3, -24.8, top) to D12 (80.9, -50.2, bottom): moving D13 next to D12 and the
   fly-lead holes makes the clamp loop local. R139 (74.4, -11.0) is 25 mm from U18-3 (AUX_COMP, wanted short):
   move it to C146. The low-voltage nets all routed.
7. **Primary PWM lines** (impression, run 1 render): PWM_G1..G4 and DAB_PWM_PRI_HI/LO from U16 go around the start-up
   chains and H4 to the old track ends at y -21.6..-24.8 and (108..109, -52..-54). My chain kept 2.5 mm from HV
   nets on In3 too (tool limit), which overstates this.

## Wrong or missing in the brief and the routing list

- The passage is given as y 51.1..55, the `unrouted` rectangle of lib/v5_copper.csv ends at y 54.
- Old track ends of PWM_G2 (63.6, -24.8), PWM_G4 (62.7, -24.7) and PWM_TRANS1 (65.0, -24.5) lie outside the
  rectangles (y >= -22 there). Most old ends to join are on In2.Cu, the layer the brief says not to route.
- The 2.5 mm rule of the HV aux nets cannot hold between two HV nets or at parts with an HV and a low-voltage pad
  (pads 1.0..2.0 mm apart); it needs the wording "tracks 2.5 mm from other nets, pads as in HV_PADS".
- The brief still says the 27 aux parts are staged below the board (placed since v5 step 9) and points to
  `tools/v5/route/` of the first run.
- DRC shows three unconnected items on the wire-link nets (ISODC+ 1, ISOPGND 2) for two wires.
- KiCadRoutingTools does not read the 5 mm class-pair rules of the .kicad_dru (only the rule-area strips kept the
  domains apart: domain_gaps 0), does not read pad clearances, and routes through another net's plane on In4
  unless fenced (done from the last step on; put it into `prep()` for the next pass).

## Files

- Chain: `tools/v5/route_pass1/chain.sh` (`prep.py`, `make_groups.py`, `check_pass.py`, `check_and_render.sh`), `routing.json`.
- Routed board (not committed, build/ is ignored): `build/route2/routed.kicad_pcb`; refilled copy `build/pass1/check/ac_psu.kicad_pcb`.
- Renders and check outputs: `reports/v5_layout/routing_pass1/` (card, passage, j11, aux per layer; run logs).
- The committed chain is the run 2 sequence; in run 2 the supply_I step was stopped by hand at 8 min and the two
  leftovers steps were rerun split by area after the first form (all signals in one step) hit the time limit.
