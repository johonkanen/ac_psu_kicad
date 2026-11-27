# Block A (AFE input / filter / AFE sense): replay script, 2026-11-27

Branch `block-A`, cut from `v6-baseboard` d639e0e (blocks E and F integrated). Nothing was pushed. The replay was
tested on a fresh d639e0e board (`git show d639e0e:kicad/ac_psu.kicad_pcb`).

**Verdict.** A is done. Every connection with both ends in A is closed: 8 open before, 0 after. All crossing nets
end on fixed ports on x = -2, and F's ports are met as they are. The replayed board passes:

- DRC: 0 copper errors, schematic parity 0. The 35 accepted courtyard overlaps are unchanged.
- domain_gaps: OK.
- check_layout: OK.
- assign_nets --check: OK, and the ADCLK orphan of block F is gone (0 orphans).
- New copper keeps the 2.5 mm high-voltage rule everywhere (`block_A_hv.py`: 0 pairs with block A copper).
- High-voltage pairs inside A: 73 on the base board, 15 after the replay. The 15 left are all old v4 copper (listed below).
- Open connections on the whole board: 86 before, 76 after.

No router run was needed. Every piece is drawn by script and checked by `geo.Ctx` before it is added. No part moved.
The replay adds 15 fill keep-outs (rule areas that only stop zone fills). They are listed under the proposals for
sign-off, because the new copper needs them.

## Numbers (refilled boards, DRC with the project's .kicad_pro / .kicad_dru beside the board)

| | d639e0e | replayed A |
|---|---|---|
| Open, both ends in A (`block_of == "A"`) | 8 | **0** |
| Open, one end in A | 8 | 6. Four are the port stubs to C (15V, GND, VCC, 5V). Two are GND pairs at C's In4 strip, whose corner (-2, -80) counts as A |
| Open, whole board | 86 | **76** |
| DRC copper errors / schematic parity | 0 / 0 | **0 / 0** |
| Pour islands (`islands.py`) | 76 on 71 pour layers | **79** on 75. The 4 new AFE_CHOKE1 zones have 1 island each. The FILTER_IN1 link on In2 went from 2 islands to 1. No pour got worse |
| domain_gaps | OK | **OK** |
| check_layout | OK | **OK** |
| assign_nets --check | OK, 1 orphan (ADCLK, via at (7.884, -47.485)) | **OK, 0 orphans** |
| HV-rule pairs in A (`block_A_hv.py`: 2.5 mm HV to other nets, 1.0 mm between HV nets, SW_AFE_1 counted as HV) | 73 | **15**, none with new copper |
| Dangling items in A | 2 (the dead 15V In2 run, the AFE_CHOKE1 stub) | 4 (the port stubs to C) |

## How to replay

```
tools/p2k/bin/kipy tools/v6/route/block_A.py [--board IN] [--out OUT] [--dry]   # default: kicad/ac_psu.kicad_pcb in place
kicad-cli pcb drc --refill-zones --save-board ...                                # refill: A adds zones and fill keep-outs
```

- `block_A.py` uses the fixed seed 6500. Its data is `block_A_copper.csv` (209 rows).
- **Pad check.** It checks 26 pads: the U5 side-2 pins, R55, C64, U29, C160, R58, C52-2, C91-2, R48-1/3/4,
  FILTER_OUT1, R20-6, D10-C, R90-1 and R89-2.
- **Kept-copper check.** It checks 13 kept items:
  - 6 tracks: F's MDATA and ADCLK port runs, the SHUNT1 run of R48-1, the 15V B.Cu stub at the relay via, and the
    first diagonals of the GND / GPIO In1 runs;
  - 3 vias: 15V, GND and GPIO at the relay;
  - 4 zones, by name: the step 5 / 5c landings `v6 SW_AFE_1 F.Cu / In1.Cu` and `v6 FILTER_IN1 link In1.Cu / In2.Cu`.
- It also refuses a board where the dead or cut tracks are missing, or where A's zones are already present. A
  second run on the replayed board refuses, with 57 items missing.
- **Fence check.** Every new track end, via and zone corner lies in A or exactly on an A edge. Keep-outs may reach up
  to 3 mm past A.
- **Changes.** It deletes 36 tracks and shortens 2. It adds 93 tracks, 20 vias, 4 copper zones and 15 fill
  keep-outs, all locked. No part moves.

`tools/v6/route/block_A_chain.sh` runs the whole chain in about 1 minute. Its log is `reports/v6/blocks/block_A_chain.log`.

1. 00: refill and check the base board.
2. 10: `block_A_make.py` draws the design on the refilled base and writes the CSV. The CSV is deterministic: two
   runs give the same file.
3. 20: replay on a fresh board. `block_A_same.py` then compares it with the drawn board: same tracks, vias and zones,
   and no footprint differs.
4. 30: DRC, islands, domain_gaps, check_layout, assign_nets and `block_A_hv.py --new` on the replayed board.
5. 40: renders.
6. 50: `block_A_rows.py` writes the integration rows.

Heavy jobs wait for 6 GB of free memory and take `~/.cache/ac_psu_heavy.lock`. `block_A_drc.sh` checks a copy in
`build/blockA/drc/`, and `kicad/ac_psu.kicad_pcb` is never written.

## What A was at the start

- **Area.** A is x -128.3 … -2, y -83.1 … -12. It holds:
  - the AFE EMI filter (CM1, CM2, X / Y caps);
  - the input relay R20 with Q14 / R89 / R90;
  - the dividers R2 / R4 / R5 / R11 … R16 / R95;
  - C79 and C21;
  - the step 5 / 5c landings J5, FILTER_IN1 and FILTER_OUT1;
  - the AFE sense group R48 / U5 / U29.
- **Copper.** Except for the sense group, all of A was already joined by kept v4 copper. The 8 open connections were
  all at the sense group and at FILTER_OUT1.
- **Base-board faults found in A** (high-voltage rule, `block_A_hv.py`):
  - U29 pins 1 / 2 (5V / GND) stand in the FILTER_INPUT F.Cu pour with about a 0.3 mm ring.
  - The LEMOUT B.Cu pour is 1.25 mm from the U5 side-2 pins. It also runs under U5, between its isolation rows.
  - The old AFE_CHOKE1 stub was 0 mm from the R48 LEMOUT pin.
  - The replayed U5 VIN- run passed 0.5 mm from R48 pin 4, between pins 4 and 2.
  - The dead 15V In2 run cut the FILTER_IN1 In2 link zone in two.
  - The kept GND In1 run passed 1.0 mm from CM1 pin 3 and 1.8 mm from C21 pin 1.
  - The 15V / GND / GPIO vias and the R20 coil pins stand in the JEE F.Cu pour with a 0.55 mm ring.

## What A adds (`block_A_make.py`)

| Net | What | Layers |
|---|---|---|
| AFE_CHOKE1 | FILTER_OUT1 (choke lead) to R48 pin 4. Zones from the FILTER_OUT1 pad to a field of 12 vias (0.6 / 0.3) just north of pin 4, and a B.Cu zone over pin 4 and the field. 1 mm tracks tie each via to a pad: a via that touches only zones takes the net of the pour it stands in at the refill. The old 2 mm stub between pins 3 / 4 is deleted. | F.Cu / In1 / In2 zones (clearance 1.0 / 2.5 / 2.5), B.Cu zone (1.0) |
| SHUNT1 | R58-2 straight to C52-2 | B.Cu |
| Net-(U5-VIN-) | The replayed loop from C91-2 over R48 is deleted (8 tracks). C91-2 joins the R58-1 / C52-1 run instead. | B.Cu stub, 2 vias, In1 |
| Net-(U5-MDAT) | U5-6 to R55-1 | B.Cu |
| GND | U5-5 → C64-1 → U29-2 along the board edge (y -82.3), then from the U29-2 pin to a via beside C160-2 and on to the C port | B.Cu, In1 |
| VCC | U5-8 via under the U5 body → C64-2 via → west of U29 → C port | B.Cu stubs, In4 |
| 5V | U29-1 pin → gap between U29-4 and J5 → via beside C160-1 → C port | In4 |
| ADCLK | U5-7 via under the U5 body → F port (-2, -44) | In2 |
| MDATA | R55-2 via → F port (-2, -42) | In3 |
| 15V | The relay group's dead In2 run (9 tracks) is deleted. A new run goes from its via (-116.37, -69.80) across A to the C port. | In4 |
| GND, GPIO_BYPASS_RLY | F's kept In1 runs (ports -40.6 / -39.3) are redrawn from the end of their first v4 diagonals to x -20. They now keep 2.5 mm from CM1 pin 3 and C21 pin 1. The kept runs east of x -20 are shortened, not moved. | In1 |
| (fill keep-outs) | 15 rule areas, fill only (see proposals) | F.Cu 11, B.Cu 4 |

Side-2 vias of U5 stand under the U5 body, 6.6 mm from the side-1 pins.

## Ports (net, point on the A edge, layer)

**To F, x = -2: F's ports, met as they are.**
- MDATA -42.0 In3, new.
- ADCLK -44.0 In2, new.
- R2 -18.91, R5 -21.2, U1A+ -23.2, U1A- -24.7: In2, kept v4 copper, untouched.
- GPIO_BYPASS_RLY -39.3 In1 and GND -40.6 In1: kept. Their runs inside A are redrawn west of x -20.

**To C, x = -2: new, placed by me for the J21 pins 3.5 … 7 mm east.** Each stub ends with 4 mm straight onto the
edge.

| Net | Port | C finishes it |
|---|---|---|
| 15V | -48.6 In4 | east, then down to J21-6 (4.0, -49.86) from the north of the pin row |
| GND | -49.86 In1 | straight east to J21-2 (1.46, -49.86) |
| VCC | -52.4 In4 | to C's VCC copper at (2.6, -52.2) B.Cu |
| 5V | -53.6 In4 | east, then up to J21-7 (5.27, -51.13) from the south of the pin row |

**To B (y = -12) and G: none.** No net crosses A-B or A-G (`blocks.py nets`).

**A-C by zones (kept):** SW_AFE_1, from J5 to J5S on F.Cu / In1 (step 5c).

## What stays open (one end in A) and why

| Net | Open between | Reason |
|---|---|---|
| 15V, GND, VCC, 5V | the A port stubs at x -6 … -2 and the J21 pins / C's copper | C's half (3.5 … 7 mm) |
| GND (2 pairs) | C's `v6 strip In4 GND` corner (-2, -80), J21-9 and the F.Cu GND pour 19 | C / E plane stitching. The pour corner lies on A's edge, so the check counts it as one end in A. |

## Proposals that need sign-off

1. **The 15 fill keep-outs** (`v6 block A HV keep-out F.Cu 1..11 / B.Cu 1..4`, fill only; tracks and vias are
   allowed). Each one cuts a high-voltage pour back 2.5 mm (1.0 mm between two HV nets) from copper of another net
   that the pour came closer to:
   - FILTER_INPUT F.Cu pour 24 around U29-1/2/4/6 and the C160, U5 side-2 and VIN- vias;
   - LEMOUT B.Cu pour 10 around U5 side 2, R55, C64 and the new B.Cu runs;
   - JEE F.Cu pour 28 around the relay vias and the R20 / R10 pins;
   - AC_IN_1 B.Cu pour 12 around R89 / R90 / Q14 and the GPIO run;
   - the PGND pours around the AC_IN_1 via / R14-2 (F.Cu / B.Cu) and around C79-1 (B.Cu).

   **Without them, the new vias inside the FILTER_INPUT pour fail the HV rule after a refill** (that pour's clearance
   is 0.15 mm). The same holds for the side-2 runs next to LEMOUT. A simpler alternative: pull pour 24 back from the
   whole low-voltage sense area (x -42 … -15, y -83 … -62) by changing its outline. That is a pour change, not
   copper.
2. **R48 orientation (placement makes routing hard).** FILTER_OUT1 stands right above the LEMOUT pin (pin 3), and the
   AFE_CHOKE1 pin (pin 4) is west of it. So the choke current goes over the LEMOUT pin on F / In1 / In2 and comes
   down through 12 vias. If R48 is turned so that pin 4 lies under FILTER_OUT1 and pin 3 faces the LEMOUT pour to the
   west, a short wide B.Cu link would do. This is a part move: the Kelvin pins swap sides, and the sense copper of
   09_sense_replay would need redrawing. Not done.
3. **Other sense placement notes** (routable now, flagged as asked):
   - The U5 side-2 pins face the board edge, so GND runs along it at y -82.3 (0.65 mm from the edge).
   - C64 has GND west and VCC east, which costs the VCC via. Turning C64 by 180 degrees would save it.
   - U29 between J5 and the side-1 group leaves a single 2.5 mm gap between U29-4 and J5. 5V takes it on In4 and GND
     on In1.
4. **SW_AFE_1 (and SW_INV_B) into `hv.py`.** The switch nodes are not in the HV list, so the router and `geo` do not
   see them as high voltage. `block_A_hv.py` and `block_A_make.py` add SW_AFE_1 themselves.
5. **Old HV pairs left in A (15, all v4 copper):**
   - The divider resistors R4 / R11 / R14 / R95: the track to their own low pin passes 2.09 … 2.30 mm from their HV
     pin (6 pairs + 6 track-pad pairs).
   - The DC+ F.Cu pour 5 against the PGND pour 7: 2.0 mm, their zone clearances. Proposal: PGND pour 7 clearance
     2.5 mm.
   - C79-1 (DC+) against the PGND F.Cu pour 7: 2.18 mm. C79-1 touches the DC+ pour, so a fill keep-out would cut it
     off.
   - R20-3 (relay contact, AC_IN_1) against R90-1 (GPIO): 2.32 mm, pad to pad. A placement change: move R90 by
     0.2 mm.

## Renders

`reports/v6/blocks/block_A/` holds the refilled replayed board:
- `A_<layer>.png`: the whole block (x -130 … 0, y -85 … -10), one image per copper layer;
- `A_sense_<layer>.png`: the sense / choke-landing area (x -45 … 0, y -85 … -38).

What I saw in them:
- **F.Cu:** The AFE_CHOKE1 zone runs from the FILTER_OUT1 pad down to the via field, with pour 24 held 1 mm off. Pour 24 has round holes at U29 (2.5 mm at pins 1 / 2, 1 mm at pins 4 / 6), at the C160 vias and at the U5 side-2 vias.
- **B.Cu:** The via field and zone sit over R48 pin 4, and the LEMOUT pour is pulled back from U5 side 2 (the peninsula under U5 is gone). GND runs along the edge, and MDAT runs under U5 pin 5 to R55.
- **In1:** GND / GPIO run from the relay as before, but keep 2.5 mm from CM1 pin 3. They step up past C21 pin 1 and join their kept runs at x -20. Also on In1: the AFE_CHOKE1 zone, and GND from U29-2 to the C port.
- **In2 / In3:** ADCLK and MDATA run stacked from the U5 / R55 vias through the U29-2 / U29-4 gap, then go NE and run north along x -6 to F's ports. The FILTER_IN1 In2 link is one piece again.
- **In4:** 15V crosses A from the relay to the C port north of the sense nets. VCC goes west of U29, and 5V goes through the U29-4 / J5 gap past C160.

## Rows for the integration

`reports/v6/blocks/block_A_copper_rows.csv` is in `lib/v6_copper.csv` format (`kind,layer,x,y,x1,y1,net,note`) and
holds 162 rows:

- 109 `unrouted,*` rows:
  - one per straight leg of new copper, tight to the copper (half width + 0.1 mm);
  - one per new via;
  - one per new zone.
- 53 `area,<layer>` rows:
  - 36 deleted tracks;
  - 2 shortened runs;
  - 15 fill keep-outs, where the HV pours lose copper.

## What was wrong in the brief

1. **A was not routing work for a router.** Only 8 connections were open, all at the sense group / FILTER_OUT1. The
   EMI filter, dividers and relay were already joined by kept v4 copper. The work was those 8, the crossing nets, and
   high-voltage faults of the base board in A.
2. **No ports to B or G.** No net crosses A-B or A-G. The crossing nets of A go to F (the analog lanes and the
   sigma-delta pair) and to C (15V, GND, VCC, 5V at J21, SW_AFE_1 by zones).
3. **domain_gaps does not check the 2.5 mm HV-net rule.** It checks domain gaps only: P-I 5.0 mm, P/I-E 2.5 mm. The
   per-net rule of `hv.py` lives only in the router, in `geo.Ctx` and in pad clearances, so I wrote `block_A_hv.py`
   to check it. The switch nodes SW_AFE_1 / SW_INV_B are not in `hv.py`.
4. **"Keep the step 5 / 5c landing zones" needed one fix.** The FILTER_IN1 In2 link was cut in two by the dead 15V
   In2 run. Deleting that run made it one piece again. The zones themselves are untouched.
5. **The sense group's B.Cu copper from 09_sense_replay is not clean.** The VIN- loop passed between R48's pins 4 / 2
   and boxed R58-2 in. That is why SHUNT1 was open. I redrew it.
6. **KiCad trap:** a via that touches only zones takes the net of the pour it stands in at the refill (DRC). The AFE
   via field needed tracks to R48-4 / FILTER_OUT1.

## Time used

About 2.5 h. DRC runtime was small (8 s per refill + DRC); the heavy-job lock was free.
