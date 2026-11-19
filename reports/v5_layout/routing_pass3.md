# Routing pass 3 (placement of v5 step 16): STOPPED UNFINISHED, status

Branch `routing-pass3`, from 7ecd979. The chain was stopped on request (end of session) while the step `aux_iso`
(step 16 of about 28) was running. There is no final board, and no check has been run on a routed board of this pass:
every number below except the bus gate comes from the router's own step logs and is **not verified**.

## Resume

```
cd <worktree>
ROUTE_DIR=$PWD/build/route_p3 tools/v5/route_pass1/chain.sh "" aux_iso
tools/v5/route_pass1/check_and_render.sh build/route_p3/routed.kicad_pcb build/pass3
```

The step boards `build/route_p3/01_prep.kicad_pcb` .. `15_aux_lv.kicad_pcb` are kept (build/ is not committed; if
they are gone, run the chain without arguments: about 50 minutes). Still to run: aux_iso, left_ctrl, left_pri,
left_iso, plane_vias, the supply steps (420 s budget each; ISO rails and GND with `--quick`), prune, finish.

## Done

- Chain of pass 2 brought over. New: `scripted.py bus` (the passage as drawn lanes), In2 fenced inside the card
  planes too (no signal hop on In2 there), `prep.py prune` (deletes new copper that lies inside a fence, for the
  stray 15V track of pass 2), supply budgets 420 s.
- **The bus is drawn and gated**: 11 signal lanes plus ISOGND, DRC gate 0 conflicts, and `check_layout.py` OK
  on the board with only the bus (these two are verified by tool).
- Router steps finished so far (router logs, unverified): PWM bundle 4 of 6 (open: DAB_PWM_HI_SEC, PWM_Q8),
  passage ends 7 of 12 complete (partial: Net-(U2-+), Net-(U2--), Net-(U7B-+) at their far-west old copper,
  PWM_Q7 at U20-11; Net-(U7A--) has no lane), sigma-delta 2 of 2, measurement chain 8 of 8, J11 top fan 17 of 21
  (leftovers step not run yet), **J11 to the bottom isolators 14 of 14** (pass 2: 12), CTRL analog 17 of 17,
  buck 6 of 6, HV aux 6 of 8 (AUX_VIN, DC+ partial), primary 21 of 22 (CLK1), aux low voltage 8 of 9 (AUX_LOVP).

## Passage north of J11: lanes against demand

- Lanes between the J8 north-row pads (y 52.605) and the fence at y 55.3: **8 per layer** at 0.152 mm track and
  0.305 mm pitch (y 52.84 .. 54.975), on In3 and In4: 16. The upper four of each layer (y >= 54.06) lie in the
  strip y 54 .. 55.3 outside the `unrouted` rectangle.
- Demand: 12 signals and 4 rails (ISOGND, 3V3_ISO, 15V_ISO, 5V_ISOL all have open connections across the
  passage at the baseline) = 16 nets. At minimum width that is exactly 16 lanes. At the widths the brief asks
  (ISOGND / 3V3_ISO 0.4 mm = 2 lanes each, 15V_ISO 0.5 mm = 3, 5V_ISOL 0.8 mm = 4) it is 23 lane widths:
  **7 short**.
- Entries are tighter than lanes. In3: all 8 lanes can be entered without a via from the gap between J6 and J4.
  In4: three signal tracks fit through the missing J6 pin column at x 68.98 (vias below the south row at 0.61 mm
  pitch), and ISOGND comes straight off its In4 plane edge through the column at x 60.09. Drawn: In3 lanes 0..7 =
  five taps, PWM_TRANS6, PWM_Q7, PWM_Q5; In4 = ISOGND (two lanes wide), relay, MDATA_INU, INU_ADCLK. In4 lanes
  5..7 are free but have no drawn entry. **Without a lane: Net-(U7A--), 3V3_ISO, 15V_ISO, 5V_ISOL.**
- Step 16 channel order at U20: the three J8 nets enter west to east as TRANS6, Q7, Q5, which is the order the
  lanes need only because all three now leave through the J8 column at x 24.89 and reach their pins from the
  south. Not yet shown to close (PWM_Q7 partial at the U20 end).

## Files

- `tools/v5/route_pass1/` (chain as it stood when stopped), `routing.json`.
- `reports/v5_layout/routing_pass3/`: `chain_run_stopped.log`, renders of In3 / In4 of the passage after the
  passage step (`after_passage_step_In3.png`, `after_passage_step_In4.png`; not the final board).
