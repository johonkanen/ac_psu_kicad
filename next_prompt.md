# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase
(or session that stops mid-phase), see PLAN.md section 9 "Handoff prompt".

```
Read PLAN.md and STATUS.md in /home/jari/dev/ac_psu_kicad. Use Opus 5.5.
Phases 1 and 2 are done: the 11-sheet schematic matches the IPC-D-356A netlist (267/267 parts,
0 errors), every part except TR1 has a footprint, and tools/check_footprints.py fits every
footprint onto the IPC pads (worst residual 0.038 mm, pad numbers = IPC pin ids). Start Phase 3
(PLAN.md section 5): build kicad/ac_psu.kicad_pcb with the footprints placed where Proteus put
them, convert the Proteus copper gerbers into tracks/vias, give every copper item its net, and
turn the pours into zones.

Read first: STATUS.md (sections "Phase 2 footprints", especially the KiCad placement recipe and
"Footprint decisions"), PLAN.md sections 5 (3a-3e) and 6.2, reports/footprint_fit.csv (per part:
side, kicad_x, kicad_y, kicad_orientation), tools/fpgeom.py (docstring), tools/check_footprints.py,
reference/ipc356_pads.json (898 component pads, 173 'via' records with net + position, 4 'hole'
records = unnetted plated 3.0 mm mounting holes with 4.0 mm pads), source/cadcam/*.GBR.
Tools: tools/bin/kipy = AppImage python3.11 with pcbnew; tools/bin/kicad-cli (10.0.7). Both mount
the AppImage on demand (never run the AppImage with --version, it hangs). KiCad std footprints:
<mount>/share/kicad/footprints (mount path in /tmp/ac_psu_kicad_mount.<uid>); project footprints
lib/ac_psu.pretty (registered in kicad/fp-lib-table); gen_footprints.footprint_path(fpid) resolves
both. pcbnew objects must be added to a BOARD before Flip() (segfault otherwise).

Verify state first: tools/check_all.sh. At handoff it printed
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
(the 8 ERC warnings are expected, see STATUS.md).

Steps:
1. tools/build_pcb.py (kipy, re-runnable, writes kicad/ac_psu.kicad_pcb): there is no headless
   "Update PCB from schematic", so do it in Python: export the netlist (kicad-cli sch export
   netlist --format kicadxml, as tools/compare_netlists.py does), create the board with 4 copper
   layers (F.Cu, In1.Cu, In2.Cu, B.Cu), add every footprint (skip TR1 / excluded parts), set
   reference, value, the symbol link (KIID_PATH /<root-sheet-uuid>/<sheet-uuid> + symbol uuid,
   so eeschema<->pcbnew cross-probing and later "Update PCB" work; symbol UUIDs are deterministic
   now, see STATUS.md), and every pad's net from the netlist. Place each footprint with the recipe
   from reports/footprint_fit.csv: SetPosition(kicad_x, kicad_y); bottom parts Flip(pos,
   FLIP_DIRECTION_LEFT_RIGHT); then SetOrientationDegrees(kicad_orientation). Keep the Proteus
   origin (KiCad y = -IPC y). Board outline on Edge.Cuts from "Mechanical 1.GBR" (246.8 x 154.7 mm).
   Add the 4 mounting holes (plated 3.0 mm drill, 4.0 mm pad, no net) at the IPC 'hole' records.
   Extend tools/check_footprints.py (or a new check) to re-measure the pads on the saved board
   against the IPC file (every pad within 0.05 mm, same net as the IPC record).
2. tools/gerber_to_tracks.py (PLAN.md 3b): parse the 4 copper gerbers (X2, metric, FSLAX45Y45,
   linear D01 only, D03 flashes, G36/G37 regions, %LPC% clear polarity) and the plated drill
   gerber. D01 draws with circular apertures -> PCB_TRACK on the right layer; via flashes +
   drill -> PCB_VIA (cross-check against the 173 IPC via records, which carry nets); skip
   component-pad flashes (footprints provide them). Write the positive G36 region outlines to a
   User layer as reference.
3. tools/assign_nets.py (PLAN.md 3c): union-find over pads, track ends/overlaps per layer and
   vias; every connected group takes the net of its pads/IPC vias. Report shorts (groups with
   pads of 2+ nets), orphans (no pad) and opens (net split over several groups).
4. Pours -> zones (PLAN.md 3d): net of each G36 region from the pads/vias inside it; create
   ZONEs on the right layer with that net and outline; fill with pcbnew (ZONE_FILLER). After the
   fill the remaining opens from step 3 should vanish; whatever remains is a real finding.
5. DRC via kicad-cli pcb drc (report in reports/); add the board checks (pad positions/nets,
   assign_nets report, DRC unconnected = 0 and shorts = 0) to tools/check_all.sh. Clearance rules
   may need Proteus values (smallest track aperture 0.152 mm).

Open points left from Phase 2 (tell the user, do not change without asking): KiCad pad sizes
were accepted; KiCad drills are smaller than Proteus for TO-247 (1.5 vs 1.651), VXO7805 (1.0 vs
1.2), C21/C25/C33/C34 (1.2 vs 1.27) and the snap-in caps (2.0 vs 2.032) - switching to Proteus
sizes = a derived project footprint with ipc_sizes=True in tools/gen_footprints.py. C67: symbol
C_Polarized on sheet 7 vs ac_psu:C in part_map, on a non-polar 1206 land pattern (STATUS.md).
Footprints built from IPC pads (TR2, CM1-3, R48/R64/R91, R20/R79, terminals) have simple
rectangle courtyards; adjust them if courtyard DRC complains.

Done when: kicad/ac_psu.kicad_pcb exists and is generated by re-runnable scripts; every
footprint pad is within 0.05 mm of its IPC pad and carries the IPC net; all gerber tracks and
vias are on the board with nets; pours are zones; assign_nets reports 0 shorts and 0 opens
after zone fill; kicad-cli DRC reports 0 shorts and 0 unconnected items (list and justify any
other remaining DRC violations); tools/check_all.sh passes including the new board checks;
STATUS.md updated; next_prompt.md replaced with the handoff prompt for Phase 4 (Fable 5.1:
verification + final review, PLAN.md section 6), committed, and the session ends with that
prompt.
```
