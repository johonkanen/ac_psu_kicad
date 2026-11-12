# v5 layout plan: the area under the control card (for Claude Fable 5.2)

Written 2026-11-12 for a Claude Fable 5.2 session in `/home/jari/dev/ac_psu_kicad`. Coordinates are mm in the
IPC frame (Y up, KiCad y = −IPC y) unless a line says otherwise.

## 1. Goal and user decisions (2026-11-12)

Place the control and measurement parts under the control card. Reshape the planes there so the area holds
**three isolated domains**:

| Domain | Colour in the user's sketch | Holds | Ground / supply nets |
|---|---|---|---|
| **CTRL (C)** | green: around J11 (top left), plus a small piece around J12 (bottom right, "2") | J11, J12, isolator CTRL sides, AMC1311 low sides, diff amps, U27 LDO, J13/J14, PEC1/PEC2, the J12-side buck | CTRLGND_A / 3V3_CTRL / 5V_CTRL_A (J11 piece); CTRLGND / 5V_CTRL (J12 piece) |
| **Primary (P)** | red, "1": lower left | primary logic: U11, AD1, U12, U14, U1, REF1 and their parts, the B sides of U13/U15/U16 | GND / VCC |
| **Secondary / ISO (I)** | blue, "3": right side | ISO measurement: U7, U2, REF2, U10 and their dividers/filters, the AMC1311 high sides and their ×0.4 dividers, the ISO7760F/CA-IS3742 ISO sides | ISOGND / 3V3_ISO |

The sketch's shapes are a guide only ("the shapes do not need to be like drawn"):
- The CTRL piece at J11 takes the top left of the card area, from J11 to about the middle of the card, and down
  to the row of U13/U15/U16.
- The primary area is below it, down to the card's bottom edge.
- The ISO area takes the right part, from the top edge to near J12.
- The CTRL piece at J12 is a small corner area.

Further decisions:
- **6 copper layers** (today 4).
- **Parts may go on the bottom side.**
- **What Fable may move:** the 98 v5 parts, plus the v4 parts this plan lists (section 4). Their tracks inside
  the card area are deleted and re-routed later.
- **Routing stays with the user** in the KiCad GUI. Fable leaves a clean ratsnest and a routing list.
- **The two CTRL pieces stay separate,** as in CTRL_ISOLATION_PLAN.md 7/8: one domain, two ground nets, joined
  only through the card and the J13 → J14 link.

## 2. Read first

Rules and current state:
- next_prompt.md (repo rules) and README.md.
- STATUS.md sections "v5 passives", "v5 step 2", "v5 step 1" and "v4 fix 16".

Isolation plans:
- CTRL_ISOLATION_PLAN.md sections 2, 4, 7 and 8 (barriers B2/B3/B4, distances, islands, decisions).
- V5_PLAN.md section 8.

Tools:
- tools/v5/v5_parts.py, tools/v5/v5_1_aux_ctrl.py and tools/v5/v5_2_refdes.py (script pattern: seed, refuses to run
  twice).
- tools/v4/v4board.py.
- tools/v4/domains.py (net → domain P/I/E/C; barrier parts).
- tools/v4/domain_gaps.py, tools/v4/domain_rules.py, tools/deviations.py and tools/check_all.sh.

Mechanics and fab:
- `~/dev/efinix_soc_board/MECHANICAL.md`: the card outline, the card-to-baseboard gap, and the card's through-hole
  tails.
- fab/README.md (BOM, both-side assembly).

Repo rules that apply throughout:
- Never run the KiCad AppImage with `--version`.
- The board is changed only by small committed pcbnew scripts (`tools/v5/v5_N_*.py`), each with its own KIID seed
  (next free: 5003), refusing to run twice.
- Every intended difference from Proteus goes into the deviation CSVs.
- Work on a branch `v5-layout`. Commit with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Do not
  push.
- If a check cannot be met, stop and report it. Never loosen a check or a gap to make it pass.

## 3. Hard constraints

**Isolation** (IEC 61010-1 basis, user-confirmed):
- **Gaps:** P↔I, P↔C and I↔C ≥ 5.0 mm on every copper layer; P/I↔PE ≥ 2.5 mm. C↔E needs no gap (CTRL is
  bonded to PE).
- **Adjacent layers:** different domains must not overlap on adjacent copper layers. No 6-layer prepreg or core
  reaches the 0.4 mm of reinforced solid insulation. So each boundary needs the same 5 mm gap stacked through all
  six layers.
- **Recommended method:** draw each boundary as a centre line, and keep every domain's copper (pads, tracks, vias,
  zones) ≥ 2.5 mm from it on all layers. A 5 mm wide rule area (keep out tracks, vias and zones; footprints
  allowed) along the line on all copper layers enforces this.
- **Slots:** ≥ 1.0 mm wide, inside the barrier strip, under every isolator body (U13, U15, U16, U19, U20, U21,
  U22, U23, U24), and wherever the strip is crossed by nothing. Use Edge.Cuts slots. Keep ≥ 1 mm of FR4 web next
  to each SOIC body for strength.
- **Barrier parts straddle their boundary** with one pad row on each side:
  - U13/U15/U16: C | P;
  - U19/U20/U21: C | I;
  - U22–U24: I (VDD1/VIN side) | C (VDD2/VOUT side).
  - The SOIC-16W and SOIC-8W pad rows are ≥ 7 mm apart, so the 5 mm strip fits between them. Verify per footprint.
- **No net may have pads in two domains** except through a barrier part. Check the ratsnest for that after
  placement.

**Mechanics:**
- **Card outline:** x 42.599 … 118.599, y −18.766 … 46.361. **J11 and J12 do not move** (the card mates with
  them).
- **Card-to-baseboard gap ≈ 5.3 mm**, from MECHANICAL.md. Height limits:
  - **top-side parts under the card ≤ 2.65 mm** (SOIC-16W height; the card's underside parts are up to 2.0 mm);
  - L2 (4.5 mm) and the polymer capacitors C115/C116/C137/C138 (10 mm) never go on top under the card; on
    the bottom they may.
- **No top-side parts under the card's through-hole tails.** Card frame → baseboard IPC: x + 11.068,
  y − 1.946 (checked on J11 pin 1).

  | Card feature | Keep-out (IPC frame, no top-side parts) |
  |---|---|
  | J1/J2 headers | x 42.6 … 47.6, y −17.95 … 21.05 |
  | J101 bench input | x 114.8 … 117.4, y −12.8 … −7.6 |
  | RJ45 jack (pins, LED pins, pegs) | x 101.7 … 118.6, y 28.4 … 44.4: no parts under its hole positions (pins y ≈ 30.7, pegs (112.06, 30.68) / (112.06, 42.11), LED pins x ≈ 116.96) with 1 mm margin; low parts between them are allowed |

- **Bottom-side parts:** the board stands on **15 mm standoffs** (user 2026-11-12).
  - **Height:** bottom parts may be up to **10 mm** tall. That leaves ≥ 5 mm of air to the chassis (assumed
    metal and PE-bonded), above the 2.5 mm basic and the ≥ 4 mm clearance used for hazardous-live parts.
  - L2 and the polymer capacitors (10 mm) may go on the bottom, also under the card.
  - **Mounting holes:** keep a 4 mm radius around each mounting hole (H1–H4) free on the bottom, for the
    standoff and the screw head.
  - SMD preferred; JLC assembles both sides, and the BOM already has bottom parts (U4).
- **Fixed v4 parts:** the sigma-delta modulators U4/U5/U6 and their shunts (R48, R64, R91) stay next to the
  shunts. Do not move the power stage, J4/J6/J8, terminals, the PE pads, or any part outside the card area that
  section 4 does not list.

## 4. Parts in scope

Classify every part with `tools/v4/domains.py` (domain of its nets; barrier parts by their two sides). Do not
trust this list alone. Fable produces the full table in phase 1.

- **v5 parts (98, staged below the board):**
  - sheet 11, all → J11 CTRL piece / ISO area;
  - sheet 7 island B parts (W1, D16, C137–C144, R131–R135, U28, L2, J13, PEC2) → J12 CTRL piece. L2 and the polymer
    capacitors go on the bottom (or on top outside the card outline, y < −18.77).
  - **Out of scope:** the sheet-7 flyback parts (U18, Q15–Q17, T1, D11–D15, …) stay in the aux area
    (x 65 … 110, y −62 … −10). T1's pin grid is not verified yet (next_prompt point 2).
- **v4 parts inside the card outline (movable):**
  - primary logic (U11, AD1, U12, U14, U1, REF1 and their R/C);
  - the isolators U13/U15/U16 and C82/C83/C86;
  - the ISO measurement (U7, U2, REF2, U10, their dividers/filters, C95–C108, C2, C3, C5, C6, C110);
  - J11-adjacent parts (R87 and others: classify).
  - Fable lists every footprint whose courtyard intersects the card outline and marks each as move / fixed.

**Placement quality:**
- Decoupling capacitors ≤ 2 mm from their pins on the same side, or directly opposite on the bottom with two vias.
- AMC1311 divider and input filter at its VIN pins. Diff amps U25/U26 next to the AMC1311 outputs. Output
  8.2k/C filters near J11.
- U19/U20 outputs on the ISO side facing the PWM bundle's route to J4/J6/J8 (y ≈ 50–52).
- U21 close to the paths to U4/U6. U13/U15/U16 B sides close to the primary logic.
- Short sigma-delta clock/data paths.
- Group each function. Leave routing channels (≥ 2 mm) between groups.

## 5. Phases (stop at each STOP)

**Phase 0 – verify.** On a new branch `v5-layout`: `tools/check_all.sh` → ALL CHECKS PASSED, and
`tools/regen_check.sh` → OK.

**Phase 1 – proposal, no board change.** Write `reports/v5_layout/proposal.md` with:
1. **Parts table:** every in-scope part: domain, move/fixed, proposed side, proposed rough position.
2. **Domain boundaries:** centre lines as polylines, each domain's area in mm², and the slot positions.
3. **Layer plan per domain** for all six layers. Suggestion:
   - **F.Cu / B.Cu:** parts and short routes.
   - **In1:** the domain grounds (GND, CTRLGND_A, ISOGND), as today.
   - **In2:** supplies (VCC, 3V3_CTRL, 3V3_ISO), as today.
   - **In3:** a second ground per domain (reference for the B.Cu routes).
   - **In4:** routing.
   - Outside the card area: In3/In4 empty or extra power copper (propose).
4. **Stack-up:** JLC 6-layer, 1.6 mm. Record each dielectric thickness and the copper weights. Flag it if the
   inner layers drop to 0.5 oz where today's In1/In2 power planes carry current.
5. **Renders:** the proposed boundaries drawn over today's board (`tools/v4/render_area.py`), plus the keep-out
   map.

**STOP: the user approves or changes the proposal.**

**Phase 2 – tooling for 6 layers and moved parts.** No placement yet; every check passes before and after.
1. **Layer count:** `tools/v5/v5_3_six_layers.py` sets 6 copper layers (In3/In4 added between In2 and B.Cu,
   existing copper unchanged) and the chosen stack-up/thickness.
2. **Copper-layer lists:** update every tool that lists copper layers: `tools/board_common.py`,
   `tools/v4/domain_gaps.py` (the adjacency order is the stack order), `tools/gerber_roundtrip.py`,
   `fab/make_fab.sh`, and grep for others. In3/In4 have no Proteus image: the roundtrip compares only
   F/In1/In2/B. DRC, assign_nets and domain_gaps check all six layers.
3. **New deviation kinds** in `tools/deviations.py` (with `validate()`):
   - `moved` (v5): a Proteus part placed elsewhere. Its pads are not compared with the Proteus positions (as
     `footprint` swaps are not), but pad numbers and nets still are. Used by check_board, ipc356_diff,
     check_footprints and gerber_roundtrip.
   - `unrouted`: a rectangle where only DRC "unconnected" items and opens are excused. Clearance and domain gaps
     stay strict. It replaces the broad `pending` rows for the card area once phase 3 is done.
4. **New check `tools/v5/check_layout.py`** (added to check_all). It checks:
   - every moved/placed part lies inside its domain area (barrier parts across their boundary);
   - no courtyard overlaps among parts in the card area;
   - top-side parts under the card ≤ 2.65 mm, from a height table in tools/v5 per footprint;
   - nothing on top in the keep-outs of section 3;
   - bottom parts ≤ 10 mm tall, none within 4 mm of a mounting hole;
   - every slot sits inside a barrier strip.

**Phase 3 – placement and planes.** `tools/v5/v5_4_card_area.py`:
1. Delete the tracks and vias of the moved v4 parts inside the card area, so their connections become ratsnest.
2. Place and flip the parts.
3. Draw the barrier rule areas and the slots.
4. Replace the zones in the card area with one zone per domain per layer (outer outlines only; KiCad keeps the
   clearances, fix 16).
5. Pull the ISODC+ and other pours back from the new boundaries, then refill.
6. Update lib/v5_copper.csv (`unrouted` rows for the card area; drop its `pending` rows) and the `moved` rows.

Done when check_all passes with **domain_gaps and DRC clearance strict in the card area** and check_layout OK.

**Phase 4 – review and hand-off.**
1. Renders of the card area per layer and both sides, with the domains coloured, in reports/v5_layout/.
2. A routing list per domain: net, from–to, special needs (sigma-delta pairs, the PWM bundle to J4/J6/J8,
   protective-bond width on PEC1/PEC2 per CTRL_ISOLATION_PLAN.md 7.3).
3. A STATUS.md section, a new next_prompt.md, and fab/README (stack-up, 6 layers, bottom parts) updated.
4. regen_check, then commit.

**STOP: the user routes in the GUI.**

## 6. Open items for the user

- 6-layer stack-up and inner copper weight (phase 1, item 4); JLC price for 6 layers with both-side assembly.
- T1 pin grid (next_prompt point 2) before the aux area and W1's final position.
- Whether the routing in phase 4 may be tried with Freerouting for the low-voltage nets (not part of this plan).
