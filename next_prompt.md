# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every phase
(or session that stops mid-phase), see PLAN.md section 9 "Handoff prompt".

The migration (Phases 0–4) is complete; this prompt is for the optional clean-up of the open
points. It needs user decisions first, so the session should start by asking.

```
Read PLAN.md and STATUS.md in /home/jari/dev/ac_psu_kicad. Use Opus 5.5.
Phases 0-4 are done: the 11-sheet KiCad schematic is pin-for-pin identical to the Proteus
IPC-D-356A netlist, kicad/ac_psu.kicad_pcb is rebuilt from the Proteus gerbers by
tools/make_pcb.sh (byte-for-byte reproducible), DRC 0 shorts / 0 unconnected / 0 parity
issues, the gerber round trip shows the KiCad copper equals the Proteus copper to 0.05 mm
except pad shapes (reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png), and the
KiCad IPC-D-356 matches the Proteus one (1075/1075 records, 0 mismatches). Read STATUS.md
"Phase 4" (results, review, "Final state of the migration") first.

Verify the state first: tools/check_all.sh (≈ 3 min; the last two steps are
tools/ipc356_diff.py and tools/gerber_roundtrip.py --check). At handoff it ended with
  ipc356_diff: 208 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
  roundtrip: F.Cu/In1.Cu/In2.Cu/B.Cu ... clusters >= 0.01 mm^2: pad shape only (+3 clearance on In2.Cu);
             draws/flashes off the other copper: 0 Proteus, 0 KiCad; drills 0 mismatches
  ALL CHECKS PASSED
Tools: tools/bin/kipy (AppImage python3.11 with pcbnew, no numpy), tools/bin/kicad-cli
(10.0.7); system python3 has numpy/scipy/PIL. Never run the AppImage with --version (hangs).
Do not hand-edit the board or the sheets: change the generating scripts
(tools/gen_footprints.py, tools/sheets/sheetNN.py, tools/build_pcb.py ...) and re-run
tools/make_pcb.sh, then tools/check_all.sh.

Open points – ask the user which to do before changing anything (none of them affects the
netlist or the copper checks, but each changes the generated files):
1. U8/U9 (VXO7805-500, footprint ac_psu:Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus): the
   Proteus silk draws the body on the -y side of the pin row (away from J12), the KiCad R-78E
   graphics put it on the +y side (body -6.56..+2.06 in the footprint frame, pin 1 at x=0),
   hence the 4 J12/U8 pth_inside_courtyard errors. The CUI VXO78-500 datasheet (mechanical
   drawing p. 3) says: pin row 1.80 mm from the module-PCB face, 5.40 mm from the component
   face, pins 1-2-3 left to right seen from the component side -> body bulk on the -y side
   with pin 1 at -x, i.e. Proteus is right; but the same page's "Recommended PCB Layout Top
   View" shows the outline on the other side, so confirm with a physical part. If mirroring:
   body y = -5.4..+1.8 (IPC frame, 10.0 wide), courtyard 0.25 mm, keep the pin-1 marking at
   pad 1; afterwards check the orientation of the mirrored graphics (body side vs the pin row
   and J12, pin-1 marking, courtyard) against the datasheet and the Proteus silk, and expect
   the J12/U8 courtyard errors to disappear (update drc.py / STATUS counts).
2. C67 (100 µF, 5 V, sheet 7): drawn with C_Polarized (pin 1 on GND) while lib/part_map.csv
   says ac_psu:C and the land pattern is a non-polar 1206 (same as C57/C58). If the part is a
   ceramic, switch the symbol to C in tools/sheets/sheet07.py (and part_map stays); if it is a
   polarized part, tell the user the board has no polarity mark for it.
3. Silkscreen / reference positions are the KiCad footprint defaults (199 silk_overlap + 199
   silk_over_copper + 12 silk_edge_clearance warnings). Option (PLAN 3e): take the refdes
   positions/rotations from the Proteus Top/Bottom Assembly gerbers (tools/gerber.py parses
   them; text is stroked, so locate each refdes by the IPC part origin and the nearest text
   cluster) in build_pcb.py.
4. Pad sizes/drills kept from KiCad where DRC does not force a choice (see the per-footprint
   list in reports/roundtrip/roundtrip.txt): TO-247 and snap-in square pad 1, C_Disc 2.0 mm
   pads / 1.0 drills (Proteus 1.524 / 0.8128), 1206 hand-solder pads, J12 1.0 / 0.65 (Proteus
   0.812 / 0.5588), PWM1 1.6 / 0.8 (1.524 / 0.762), R10 and C24 2.4 / 1.2 (1.52 / 1.01, 2.29 /
   1.016), 0402/0603 (Proteus pads slightly larger). Switching any of them to the Proteus
   sizes = ipc_sizes=True in gen_footprints.py for that footprint, then make_pcb.sh; the
   round trip's only-KiCad / only-Proteus areas for that footprint should drop to ~0.

Done when: the chosen points are implemented in the generating scripts, tools/check_all.sh
passes (update the accepted DRC counts in STATUS.md / tools/drc.py if the courtyard errors
change), STATUS.md gets a short "Clean-up" section, next_prompt.md is replaced, committed.
If the user wants none of them, just record the decision in STATUS.md and stop.
```
