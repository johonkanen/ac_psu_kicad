# Brief: route the card area of the AC PSU baseboard

You are routing the low-voltage nets of a placed 6-layer board. Read this brief, then
[`routing_list.md`](routing_list.md) (the nets), `tools/v5/card_layout.py` (the geometry) and
`~/dev/efinix_soc_board/AGENTIC_PCB_ROUTING.md` (the method: scripted and rerunnable steps, staged routing with
locked groups, numeric checks plus a look at rendered layers after every run).

Work in the repo you were started in (branch `v5-layout` or a worktree of it). Never run the KiCad AppImage
with `--version`. KiCad's Python is `tools/p2k/bin/kipy`; `kicad-cli` is `tools/p2k/bin/kicad-cli`.

## Goal

Connect the 307 open connections on 121 nets of [`routing_list.md`](routing_list.md) (groups 1–9). Done means, on the
final board with zones refilled:

- `tools/check_all.sh` ends with ALL CHECKS PASSED;
- `python3 tools/drc.py` reports 0 shorts, and its "unconnected v5 items pending" count is down to the aux
  flyback nets (the 27 parts still staged below the board) plus the DC bus of group 10;
- `tools/p2k/bin/kipy tools/v4/domain_gaps.py` reports 0 violations (5.0 mm between the domains on every layer);
- `tools/p2k/bin/kipy tools/v5/check_layout.py` is OK: no copper in a barrier strip, no track on In1/In4, every
  plane one island;
- few vias, no detours, and the special needs of each group in the routing list are met.

## The board

`kicad/ac_psu.kicad_pcb`, 246.8 × 154.7 mm; only the card area (x 39…118.6, y −36…54 in the IPC frame) is yours.
Coordinates in every tool and document here are mm in the **IPC frame: Y up, KiCad y = −y**.

The card area holds three isolated domains in four copper areas (polygons `AREAS` in `card_layout.py`,
renders `card_*.png` here):

| Area | Domain | Nets (net class) |
|---|---|---|
| CA, around J11 | CTRL | CTRLGND_A, 3V3_CTRL, … (`DOM_C`) |
| CB, around J12 | CTRL | CTRLGND, 5V_CTRL, … (`DOM_C`) |
| P, lower left | primary | GND, VCC, … (`DOM_P`) |
| I and IS, top band, right side, south of the card | ISO | ISOGND, 3V3_ISO, … (`DOM_I`) |

| Layer | Use in the card area |
|---|---|
| F.Cu | parts and routing |
| In1.Cu | ground plane of each area: **never route** |
| In2.Cu | supply plane of each area: do not route (a short hop only if nothing else works, and say so) |
| In3.Cu | routing |
| In4.Cu | ground plane of each area: **never route** |
| B.Cu | parts and routing |

Stack-up JLC06161H-3313: F.Cu–In1 and In4–B.Cu 0.10 mm, In1–In2 and In3–In4 0.55 mm, In2–In3 0.11 mm.

## Hard rules

1. **A net stays in the copper area(s) of its domain.** The 5 mm barrier strips between the areas are rule areas on all
   six layers (no tracks, vias, pours); the DRC rules of `kicad/ac_psu.kicad_dru` demand 5.0 mm between the net
   classes `DOM_C`, `DOM_P` and `DOM_I`. Only the barrier parts cross: U13/U15/U16 (CTRL | primary), U19–U21 and
   U22–U24 (CTRL | ISO). If a net seems to need to cross a strip, the netlist reading is wrong: stop and report.
2. **The DC bus band** x 58.9…118.1, y 43.2…48.8 carries the ISO DC bus as pours (F.Cu ISOPGND, B.Cu ISODC+). No
   via and no F.Cu/B.Cu track there. Signals cross under it on In3 and end on the through-hole pins of J4/J6/J8.
3. **North of J11** (x 40…59, y 51.1…55) is the only way west for the U4 pair, the divider taps, the relay line and
   the J8 signals. INU_OUT2 cannot move north (its body touches Q5/Q6), so the passage stays 2.9 mm high between the
   J8 pads and the INU_OUT2 pads (net Q5_S, the switch node: keep the clearance the DRC asks). Use In3 and In4 there and
   leave F.Cu and B.Cu free: the DC bus link may need them (group 10, the owner's decision). If the tracks do not
   all fit, report how many fit and which nets are left; do not squeeze the clearance.
3a. **The DC bus wire holes** BUSP1 (32.5, 38.5), BUSN1 (33.0, 31.5), BUSP2 (63.5, 45.5) and BUSN2 (90.5, 45.0) are
   bare soldered pads at DC-link voltage (v5 step 6). No track or via of another net within 2.5 mm of their pads on
   F.Cu or B.Cu; on In3 the pads' own 0.5 mm clearance applies. Their two unconnected items (ISODC+, ISOPGND) are
   the wires and stay open.
4. **Do not move or rotate parts, and do not touch slots, rule areas, plane zones or the power-stage pours.** If a
   placement makes a route impossible or clearly bad, report it with a proposed position; do not move it yourself.
5. Do not edit `tools/v5/card_layout.py`, `lib/*.csv`, `kicad/ac_psu.kicad_dru` or any check to make something pass.
   A check that cannot be met is a finding to report.
6. Tracks: 0.152 mm is the narrowest on this board (the v4 signal width), clearance 0.15 mm, vias 0.4572/0.3 mm
   through. Use 0.2 mm for signals where there is room, ≥ 0.4 mm for supply stubs, and the widths the routing list
   names (bucks, PE bonds, 5V_ISOL).
7. Every supply and ground pad of a placed part gets its own via to the plane next to the pad (decoupling
   capacitors: both pads, within 1 mm). Where a bottom-side capacitor sits opposite a top-side IC pin (or the other
   way round), the two vias go right at the capacitor.

## Order of work

This is the second routing run. The first one (placement revision 1, branch `worktree-agent-a37d57d89bb23f236`,
commits 9533c6b…c2050f2) left a rerunnable chain in `tools/v5/route/` and one schematic swap (U19/U20 channels in
`tools/sheets/sheet11.py`): take both from that branch and adapt them to the revision 2 placement (v5 step 5: the
primary isolators 10 mm south, U22 at (88.0, 13.25), the north row 6.6 mm east, the CTRL column beside J11 8.6 mm
wide, the primary ADC group on the bottom). The nets north of J11 and the supply pins of J4/J6/J8 were what it
could not finish: route those first.

Route in the order of the groups in the routing list, lock each finished group, check, look at the renders, then go on:

1. Sigma-delta pairs (U21 → U4, U21 → U6).
2. Divider taps and the measurement chain.
3. PWM bundle and relay line.
4. J11 fan-out.
5. CTRL analog chain, then the plane vias of the J11 piece.
6. The J12 buck.
7. Primary side of U13/U15/U16, the ADC group and the reference group.
8. ISO supply vias and 5V_ISOL.

## Swaps that are allowed

Swap to remove a crossing or a via, not for its own sake. Each swap is a schematic change in
`tools/sheets/sheet11.py` (the sheets are generated; then `python3 tools/sheets/sheet11.py`, `tools/erc.sh`,
`python3 tools/v5/make_v5_lists.py --nets`, `tools/p2k/bin/kipy tools/v4/domain_rules.py`), and the pad nets on
the board must follow (pcbnew script). List every swap in your report.

- The forward channels of U19 and U20 among each other (12 channels, 10 used: PWM_Q5–Q8, PWM_TRANS4–6,
  DAB_PWM_HI/LO_SEC, GPIO_BYPASS_RLY_ISO). The J11 pin and the J4/J6/J8 pin of a net stay.
- Channels of the same direction within U13, within U15 and within U16.
- The three AMC1311 chains (U22, U23, U24 with their dividers and difference amplifiers) among ISOADA1–3, and the two
  halves of U25.
- Not swappable: any J11/J12/J4/J6/J8 pin, U21's channel directions, anything on the primary side beyond U16.

## Tools

- **KiCadRoutingTools** at `~/dev/KiCadRoutingTools` (`py_router/route.py`, `route_planes.py`; read its README and
  the traps in the method document). Run it with KiCad's Python visible to it. It routes no track through another
  net's pour: work on a copy with the plane zones dropped and put them back (same outlines, names starting
  `v5 card`, priorities) before the checks.
- Hand-written pcbnew scripts are fine for what the router cannot do (stubs into the 1.27 mm pins of J11, the In3
  runs under the bus band, plane vias). Helpers: `tools/v4/v4board.py` (`Board.track`, `Board.via`; IPC frame).
  KiCad 10 Python traps: use `board.Delete()`, never `Remove()`; hold `zones = board.Zones()` before
  `ZONE_FILLER.Fill`; add a footprint to the board before flipping it; do not call `ZONE.SetOutline()`.
- Keep the work rerunnable: scripts under `tools/v5/route/`, intermediate boards under `build/` (not committed).
  The routed board goes to `kicad/ac_psu.kicad_pcb` at the end.
- Renders: `python3 tools/v5/render_card.py --board <file> --out <dir>` writes one PNG per copper layer with the
  domains coloured. Look at them after every run (crossings a swap would undo, avoidable vias, detours, tangles,
  planes cut into pieces, anything on In1/In4).
- The checks accept new vias and tracks only inside the `unrouted` rectangles of `lib/v5_copper.csv`
  (x 22…118.65, y −22…54; x 85…118.65, y −40…−22; x 0…22, y 36…54). Stay inside them.

## Report back

Worktree and branch, the numbers (open connections before and after per group, vias added, check results), swaps
with the reason for each, review notes per iteration, the paths of the final renders, anything left unrouted and
why, every placement you would change, and what in this brief was wrong or missing. Commit your work on your
branch (message ending with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`); do not push.
