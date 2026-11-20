# Routing pass 3 (placement of v5 step 16): the passage north of J11 as a drawn bus

Branch `routing-pass3`, from 7ecd979. A gauge, not a layout. Coordinates: IPC frame, mm, y up. Chain
`tools/v5/route_pass1/chain.sh`; final board `build/route_p3c/routed.kicad_pcb` (not committed), refilled copy
`build/pass3/check/ac_psu.kicad_pcb`.

## Verdict

- **The result is not legal: the DC bus pour is cut.** The B.Cu ISODC+ pour ("Proteus B.Cu pour 5 (fix 14) (part
  2)", zone clearance 1.95 mm) passes north through the gap between J6 and J4. Three new vias in that gap sever
  its neck: my scripted via for Net-(U7A--) at (77.75, 50.60) and two router vias of Net-(U7A-+) at (81.60, 50.10)
  and (85.38, 51.42). The pour is in 2 islands (pass 2: 1), DRC shows one more unconnected ISODC+ item. My via
  scan tested 0.25 mm to pour fills, not the zone's own clearance, so the "via patch" at x 77.5 .. 79 of pass 2
  does not exist. Everything below stands with that defect; the fix is a via keep-out over the gap and no
  In4 entry there.
- **The ISO side does not close**, with or without the rails: 5 of the 12 west-bound signals are open (pass 2: 9),
  all five at their west end, none in the passage itself.
- **The passage does not fit everything.** 16 lanes exist (8 per layer at 0.152 mm), all 16 are assigned, and
  3V3_ISO (2 lanes at 0.4 mm) and 5V_ISOL (4 lanes at 0.8 mm) have none: 6 lanes short. Net-(U7A--) has a lane but
  no legal entry to it (see above).
- **Supplies**: CTRL and VCC closed. 15V_ISO, 3V3_ISO, 5V_ISOL, 15V and GND end with a few open pads each;
  ISOGND again used up its budget (420 s) and was skipped as a step.

## Pass 2 against pass 3

| | Pass 2 | Pass 3 |
|---|---|---|
| Unconnected items (kicad-cli DRC, zones refilled) | 63 on 22 nets | 39 on 17 nets |
| Signal connections open (of 174) | 14 on 14 nets | 9 on 9 nets |
| of these west-bound through the passage (12 nets) | 9 | 5 |
| Supply open, CTRL | 0 | 0 |
| Supply open, ISO | 25 | 18: ISOGND 11, 15V_ISO 3, 5V_ISOL 3, 3V3_ISO 1 |
| Supply open, primary | 21 | 8: GND 7, 15V 1 |
| Items on the wire-link nets | 3 | 4 (ISODC+ 2: the cut pour) |
| Vias on signals, all / new | 201 / 143 | 212 / 154 |
| Shorts / clearance errors | 0 / 0 | 0 / 0 |
| Schematic parity | 0 | 0 |
| Domain gaps (`tools/v4/domain_gaps.py --board`) | 0 | 0 |
| `tools/v5/check_layout.py --board` | OK | OK |
| Card plane islands | all 1 | all 1 |
| B.Cu ISODC+ pour (part 2) islands | 1 | **2** |
| Signal tracks on In2 inside the card planes | 10 pieces (DAB_PWM_HI_SEC) | 0 |
| HV spacing (`check_pass.py`, my reading of pass 2) | 0 | 0 |
| Existing tracks / vias changed | 0 | 0 |

Also from `check_pass.py`: 32 track ends of 7 nets at y 54 .. 55.3 (the upper lanes; outside the `unrouted`
rectangle, inside the brief's passage); 17 ends of 15V on B.Cu at x 59.5 .. 65, y -24.35 .. -25.25 and 3 of
GPIO_BYPASS_RLY at y -22.05 (outside the rectangle by up to 3.3 mm). The router laid the stray 15V track on In2 at
y -74 again; the new prune step deleted it (2 tracks). The cause is in the router (its power-net passes ignore
keep-outs), only the effect is removed.

## The passage: lanes against demand

Lanes between the J8 north-row pads (y 52.605) and the fence y 55.3: 8 per layer at 0.152 mm, pitch 0.305 mm
(y 52.84 .. 54.975). The upper four per layer lie above y 54.

| Layer | Lanes | Assigned | Entry |
|---|---|---|---|
| In3 | 0 .. 4 | five taps: Net-(U7B--), (U7B-+), (U2--), (U2-+), (U7A-+) | from the J6 / J4 gap, no via |
| In3 | 5 .. 7 | PWM_TRANS6, PWM_Q7, PWM_Q5 | from the gap, straight above U20 pins 10 .. 12 |
| In4 | 0 + 1 | ISOGND, 0.4 mm | off the In4 plane edge through the J6 column at x 60.09, no via |
| In4 | 2 .. 4 | GPIO_BYPASS_RLY_ISO, MDATA_INU, INU_ADCLK | vias at y 49.95 below J6, column at x 68.98 |
| In4 | 5 | Net-(U7A--) | via (77.75, 50.60): **not legal**, cuts the DC bus pour |
| In4 | 6 + 7 | 15V_ISO, 0.4 mm | from through-hole pin J4-48, no via; around J8 to pin J8-48 |

Demand 12 signals + 4 rails. Rails at the brief's minimum for a supply (0.4 mm, two lanes): ISOGND yes,
15V_ISO yes, **3V3_ISO no lane**, **5V_ISOL (0.8 mm, four lanes) no lane**. Short: 6 lanes, and a legal In4 entry
for the twelfth signal. All bus copper passed the DRC gate (0 conflicts) and `check_layout.py`.

## Nets still open

| Net | Open item (DRC) | Why |
|---|---|---|
| INU_ADCLK | In4 lane end (25.2, 54.1) to U4-7 | the router did not make the end from the J8 column to the scripted via at U4-7; not analysed |
| PWM_Q7 | In3 lane end (25.2, 54.7) to the J8-43 stub | the link south of J8 past the PWM_Q5 end; not analysed. Source end at U20-11 closed by a scripted via |
| Net-(U2-+), Net-(U2--), Net-(U7B-+) | lane to the old In2 copper west of J8 | the old ends at (20.4, 43.9), (21.1, 43.5), (18.9, 44.4) lie under F.Cu / B.Cu pours where no via fits; they need an In2 run from a via farther off. Impression |
| DAB_PWM_PRI_HI_ISO | J11-22 to U16-3 | fan to U16, leftovers step failed this time (closed in pass 2) |
| CLK1 | R87 pad 3 | unchanged placement |
| AUX_VIN | C112-1 group to the trunk | as pass 2 |
| AUX_LOVP | R143-2 | low-voltage pad 1 mm from an HV pad of its own part; router's flat 2.5 mm |
| 15V_ISO (3) | lane at J4-48 to U8's copper (89.9, -11.2); lane to the old In2 end at J6-48; old pieces at J8 | the lane is there, its feeds are not |
| 3V3_ISO (1) | west island (U4-8, C37) | no lane |
| 5V_ISOL (3) | J8-45, J6-45, J4-45 | no lane |
| ISOGND (11) | lane ends (J8-46 / C37, J6-46, J4-46), C120-2, C125-2, U24-3, T1-9 / R109 / C116, others | supply step ran out of its 420 s and was skipped whole |
| GND (7) | C68-1, C112-2, C114-2, R102-2, C145-2, R105-2 in the aux area, one at (105, -49.4) | see below |
| 15V (1) | R101-1 | not analysed |

**GND in the aux area: a pour is not what stops it in this run.** Six of the seven open GND pads are the
low-voltage pad of a part whose other pad, or whose neighbour, is high voltage (C68, C112, R105 at D12, ...): the
router's flat 2.5 mm boxes them in, the same tooling limit as AUX_LOVP. Each is one short link from GND copper that
is already there. A GND pour on an inner layer under the controller would still be the better layout (one via per
pad); that is an impression, not a result.

## Did the step 16 channel change work?

- **J11 to the bottom isolators: yes.** 14 of 14 (pass 2: 12 of 14).
- **PWM bundle to J6 / J4: yes, 6 of 6, without In2.** This needed one routing-side change: the escape stubs of
  the north-row pins J6-43 and J4-43 now leave on the east side (through the missing pin column), so the three
  nets of each header arrive in pin order. DAB_PWM_HI_SEC closes legally.
- **J8 nets on U20 pins 10 .. 12 under the gap: yes at the source.** With a scripted via beside each pin they go
  straight up into their lanes. PWM_TRANS6 and PWM_Q5 are complete; PWM_Q7 is open at J8.
- Nothing seen that it made worse.

## Why PWM_Q8 and PWM_Q7 were open in the first try (render-checked)

- PWM_Q8 (J6-44): the stub of J6-43 stood west of pin 44, so PWM_Q6 had to cross under pin 44. In pass 2 PWM_Q8
  escaped by looping over J6; the lanes now fill that space. Fixed by the east-side stub.
- PWM_Q7 (U20-11): the router found no via beside the pin (pour edges on both outer layers), put a via in the
  pad and gave up; the taps of the next step then ran across the pins. Fixed by the scripted hooks and by routing
  the six pin-fed bus nets before the taps.
- A router step of the primary side deleted drawn lanes of nets that were still open; the HV step now runs
  before the bus. Lanes of the three taps that stayed open were again partly removed by later steps.

## Verified how

- By tool on the final refilled board: the table; `check_layout.py --board` OK; `domain_gaps.py --board` 0;
  kicad-cli DRC with parity; pour islands (pcbnew); bus and hooks gated by DRC before routing.
- Seen in a render of the final board: B.Cu and In3 of the isolator row (the cut neck, the hooks), In3 and In4
  of the passage.
- Not looked at: In4 of the isolator row, the other windows.
- Impression: the reasons marked so above, the GND pour remark.
- This was not one clean run: three tries of the chain (lanes deleted; source ends boxed; then the run reported
  here, resumed from the bus board of the second try). `tools/check_all.sh` was not run on the routed board.

## Files

- `tools/v5/route_pass1/` (`chain.sh`, `prep.py`, `scripted.py` with `bus` and `hooks`, `via_scan.py`,
  `check_pass.py`, `check_and_render.sh`), `routing.json`.
- `reports/v5_layout/routing_pass3/`: renders (isorow, passage, u7u2, j11, aux, card), `check_board.txt`,
  `check_pass.txt`, `check_layout.txt`, `domain_gaps.txt`, `chain_run.log` (final try), `chain_try2.log`,
  `chain_run_stopped.log` (first try).
