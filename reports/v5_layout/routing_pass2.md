# Routing pass 2 of the card area and the aux flyback area (placement of v5 step 15)

Branch `routing-pass2`, from c280462 (`v5-layout`), chain of pass 1 brought over and repaired. A gauge of the
placement, not a layout. Coordinates: IPC frame, mm, y up. Chain: `tools/v5/route_pass1/chain.sh`; checks and
renders: `tools/v5/route_pass1/check_and_render.sh`; routed board `build/route_p2/routed.kicad_pcb` (not committed).

## Verdict

- **The ISO side does not close.** 9 of the 12 nets that go west past J11 are open (pass 1: 7). The east end is
  fixed by the new isolator order: the PWM bundle to J6 / J4 routes 6 of 6 without a crossing. What fails now is
  the west-bound traffic, and for PWM_Q5 / Q7 / TRANS6 it is proven on the final board: a search with a 40 million
  budget ends after 2.5 million steps with every reachable cell visited, so there is no path left. U19 now stands
  right under the bus wire pad BUSP2 (finding 1). For the other six open nets the router ran out of its budget
  (10 million steps each); whether they fit is not decided by this pass.
- **Supplies: CTRL and VCC are done, the rest is not.** A scripted via per plane pad plus the router closes all
  CTRL supplies and VCC. 15V_ISO, 3V3_ISO, ISOGND and GND ran into their time budget (240 s per net) and were
  skipped as whole steps; 5V_ISOL and 15V are done except three pads. What stops the ISO rails is the same
  passage: each has pads west of J11 (J8, U4, C37).
- Legal result this time: 0 shorts, 0 clearance errors, parity 0, domain gaps 0, `check_layout.py` OK, every card
  plane one island. Two blemishes are listed under the table.

## Pass 1 against pass 2

Pass 1 = `build/route2/routed.kicad_pcb` at 0fc3de5 (its report), pass 2 = `build/route_p2/routed.kicad_pcb`.
Baseline at c280462, measured here: 354 unconnected on 140 nets, 118 vias (58 on signals), parity 0, planes 1 island.

| | Pass 1 | Pass 2 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 123 on 26 nets | 63 on 22 nets |
| Signal connections open (of 174) | 19 on 15 nets | 14 on 14 nets |
| Supply open, CTRL | 2 | 0 |
| Supply open, ISO | 60 (not attempted) | 25: 15V_ISO 9, ISOGND 10, 3V3_ISO 4, 5V_ISOL 2 |
| Supply open, primary | 39 (not attempted) | 21: GND 20, 15V 1, VCC 0 |
| Wire-link items (stay) | 3 | 3 |
| Vias on signals, all / new | 175 / 117 | 201 / 143 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps (`tools/v4/domain_gaps.py`) | 0 | 0 |
| `tools/v5/check_layout.py` | FAILED, 2 errors | OK, 0 errors |
| Plane islands | In4 ISOGND 2, others 1 | all 1 |
| HV spacing (`check_pass.py`, new copper) | 0 | 0 |
| Dangling tracks / vias (warnings) | 37 / 12 | 32 / 17 |
| Existing copper changed | 0 | 0 |

Blemishes of pass 2 (`check_pass.py`):
- 15V: the router laid an In2 track at y -74.06 from x -103.2 to -62.6, far outside the allowed area, in spite of
  the fence there. It has to go; 15V then counts as more open than the table says.
- DAB_PWM_HI_SEC is closed with a hop on In2 inside the 3V3_ISO plane (10 short pieces; the plane stays one
  island). The brief allows this only as a last resort: it is one, BUSN2 stands in the straight way (finding 2).
- 88 track ends of Net-(U2-+), Net-(U7A-+) and PWM_Q8 lie at y 54..55.3, outside the `unrouted` rectangle.

## Nets still open

| Net(s) | Why |
|---|---|
| PWM_Q5, PWM_Q7, PWM_TRANS6 (U19-14 / 13 / 15 to J8) | no path on the final board (exhaustive search). See finding 1 |
| INU_ADCLK, MDATA_INU, GPIO_BYPASS_RLY_ISO, Net-(U2--), Net-(U7A--), Net-(U7B--) | router budget used up on runs of 110..130 mm; three taps did get through (In3 and In4). Capacity is not shown to be the limit |
| ADCLK_DAB_CTRL, PWM_TRANS6_CTRL (J11 to U21-4 / U19-2) | tracks on both sides of the bottom pin row, as in pass 1 (not looked at closely) |
| CLK1 | R87 pad 3, unchanged, as expected |
| AUX_VIN (1 of 6 connections) | the group R136-1 / R141-1 / C112-1 at y -5..-11 is not joined to the trunk; not analysed |
| AUX_LOVP (1 of 3) | R143-2: a low-voltage pad 1 mm from the HV pad of its own part; the router's flat 2.5 mm boxes it. Tooling |
| 5V_ISOL (2) | J8-45 and J6-45, north-row pins |
| 15V_ISO, 3V3_ISO, ISOGND | step time budget (240 s) used up, whole step skipped. Pads west of J11 need the passage |
| GND (20), 15V (1) | GND step ran out of time; its open pads are mostly in the aux area, which has no GND plane. Not analysed |

Plane vias (scripted, before the supply router): 107 vias for 123 pads (4 share a via); 37 pads have their via farther than 1.0 mm;
12 pads found no place for a via and were left to the router: C131-2, U26-5, C119-2, U24-5, R123-2, C121-1, U21-7,
U28-1, C142-2, and at U20's east end C120-1, C120-2, U20-16 (finding 2).

## Did the four moves work?

1. **Isolator order (U19 / U21 exchanged, channels reordered): half.** The crossings are gone (render
   `isorow_In3.png`: TRANS5 / Q8 / Q6 go straight to J6, TRANS4 / DAB to J4; pass 1 had 1 of 6 open, now 0).
   Worse: U19 now carries six used ISO pins at x 60.5..66.8, straight under BUSP2 (63.5, 45.5). Rule 3a's 2.5 mm
   around that 4 mm pad forbids vias north of the pin tips for x 61.0..66.0 (render `isorow_B.png`: no via there),
   and the pad itself blocks In3. In pass 1 U21 stood there with four nets, and Q5 / Q7 / TRANS6 routed.
2. **J14 to (69.0, 23.5): little effect.** The fan to U15 / U13 / U16 is again 17 of 21 on F.Cu without a via and
   21 of 21 after the leftovers step; the last four nets to U16 still loop under the pin row (render `j11_F.png`).
   J14 is now at the edge of the fan (two tracks pass north-east of it). J14 was not the cause. No harm seen.
3. **D13 next to D12: yes.** AUX_CLAMP and AUX_DRAIN route; D12-C to D13-C and D13-A to T1-11 are each about
   4 mm (render `aux_B.png`). Pass 1 left AUX_CLAMP open. Nothing got worse.
4. **R139 at U18: yes.** AUX_COMP is a few millimetres (render `aux_B.png`). Nothing got worse.

## Further placement findings

1. **BUSP2 (63.5, 45.5) against U19.** Options, for the owner: move BUSP2 east into the gap between J6 and J4, about
   (81.5, 45.5), where only unused or supply pins of U21 / U20 lie under its 2.5 mm zone (it then takes 5 mm of that
   9.4 mm gap on In3, and the wire gets 18 mm longer); or shift the three J8 nets to pins outside x 61..66.
   North is closed: the pad is already 2.8 mm from the J6 pads.
2. **BUSN2 (90.5, 45.0) against U20's east end.** Its zone covers U20-15 / 16, C120 and the way to J4-43 / 44:
   DAB_PWM_HI_SEC needed the In2 hop, and C120-1 / C120-2 / U20-16 have no place for a plane via. U20 has two free
   channels at its west end: shifting its four nets two pins west would clear pin 15.
3. **Passage north of J11.** In4 can be entered north of the bus band only in patches (`via_scan.py`: beside the J6
   pins at x 59.5..72, at x 77.5..79, above J8 at x 26..40, west of J8); elsewhere pours on F.Cu / B.Cu forbid a
   via. Lanes between the J8 pads (y 52.6) and y 55.3: 7 at 0.2 mm, 8 at 0.152 mm per layer; only 4 below y 54.
   Demand: 12 signals plus four ISO rails. This router does not pack lanes; the passage needs a drawn bus
   (scripted lanes on In3 and In4), which is the next step before judging it further.
4. From pass 1 and unchanged: R87 (CLK1), the bottom-side J11 fan under the isolator pins, the long AUX_VIN run.

## Tooling changes in this pass, and corrections to the pass 1 report

- Pass 1 said the taps fail at the U7 / U2 block. Wrong: the router's default search budget (200 000 steps) was
  used up on 125 mm runs. With a via scripted at each of the six inputs and a 6 million budget they leave the
  block (render `u7u2_F.png`).
- With the larger budget and no further fence the router walked ISO nets through the primary and aux areas
  (first try of this pass, caught by the DRC gate). It does not know the 5 mm class rules, and the barrier strips
  do not ring every domain. Each router step now gets the fence of its domain (`prep.py` DOMAIN_FENCES).
- In1 / In4 are fenced inside the card planes from the first step.
- HV rule per pad: `scripted.py hvstubs` draws an escape stub at HV pads with low-voltage copper closer than
  2.5 mm. My reading of "2.5 mm, pads as listed": the stub never comes closer to that copper than the pad itself
  is, and keeps 2.5 mm elsewhere; `check_pass.py` checks the same reading. HV nets are routed before the other
  primary nets. Result: 7 of 8 HV nets closed (pass 1: 5 of 8).
- Supplies: `scripted.py planes` (via per plane pad), then one router step per net with a time budget set up
  front. The chain was stopped once by hand at the first supply step to shorten the budgets from 420 s to 240 s.

## What is verified how

- By tool on the final refilled board: every number in the table; `check_layout.py --board`, `domain_gaps.py
  --board`, kicad-cli DRC with schematic parity (through the skill's `check_board.sh`); HV spacing by my own
  `check_pass.py` with the reading above; the no-path result for the three J8 lines (`build/diag/out.log`).
- Seen in a render: In3 and B.Cu north of the isolator row, In3 and In4 of the passage (board after the signal
  steps; the supply steps added nothing there), U7 / U2 block F.Cu, J11 fan F.Cu, aux area B.Cu.
- Not looked at: the other layers of those windows, the card overviews.
- Impression only: the cause of the two open J11 nets, the GND and AUX_VIN leftovers, the BUSP2 / BUSN2 remedies.
- `tools/check_all.sh` was not run on the routed board (it reads the design board, which is unchanged).

## Files

- Chain and tools: `tools/v5/route_pass1/` (`chain.sh`, `prep.py`, `scripted.py`, `via_scan.py`, `make_groups.py`,
  `check_pass.py`, `check_and_render.sh`), `routing.json`.
- Renders and logs: `reports/v5_layout/routing_pass2/`.
- Old track ends that look like leftovers (candidates for deletion, nothing deleted): the `track_dangling` rows
  of `reports/v5_layout/routing_pass2/check_board.txt` that are not on an open net.
