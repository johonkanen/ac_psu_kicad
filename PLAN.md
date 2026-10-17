# Proteus → KiCad migration plan: single_phase_inverter_psu_v3

Goal: redraw the Proteus schematic in KiCad 10, then rebuild the PCB in KiCad from the
Proteus gerbers so that every pad, track, via and pour carries the net from the redrawn
schematic. Verify that the KiCad schematic is electrically identical to the Proteus one.

## 1. What we have (inventory, checked 2026-10-17)

Source (Windows path `C:\Users\jaarh\Sync\proteus_projektit\Projects\single_phase_inverter\psu\v3\`,
copies in `source/`):

| Item | Notes |
|---|---|
| `single_phase_inverter_psu_v3.pdsprj` | Zip containing binary `ROOT.DSN` / `ROOT.LYT` (Proteus 8.12). Not parseable; only useful via `strings` for part/package names. |
| Schematic PDF | 11 sheets: afe, fpga connector, regulators, DC links, VSI, Dual Active Bridge, Auxiliary supply, SDM current measurements, primary side ADC, (sheet 10: isolator/relay drive, untitled), signal isolators. Text layer is extractable. Page renders in `source/schematic_pdf/hi-NN.png`. |
| CADCAM zip | Gerber X2, metric, 4.5 format, 4 copper layers (Top, Inner 1, Inner 2, Bottom), silk/mask/paste both sides, Top/Bottom Assembly, Mechanical 1 (board outline, 246.8 × 154.7 mm), plated drill **as a gerber** (no Excellon), and an **IPC-D-356A netlist**. All files share one coordinate system (`TF.SameCoordinates`). |
| IPC-D-356A netlist | 208 nets, 265 reference designators, 562 THT pad records (`317`) + 513 SMD pad records (`327`), 34 N/C pads. Each record = net, refdes, pin id, X/Y (µm), pad size, rotation, side. **This is the only link between geometry and nets** – the gerbers contain no `TO.N`/`TO.C` object attributes. |
| KiCad | `~/kicad/kicad-10.0.7-x86_64.AppImage`. Contains `kicad-cli`, GerbView, and the `pcbnew` Python bindings (`shared/lib/python3.11/dist-packages/pcbnew.py` + `_pcbnew.so`, interpreter `bin/python3.11` inside the AppImage). `kicad-cli pcb import` does **not** support gerbers or Proteus; GerbView's "Export to KiCad PCB" is GUI only. |

Facts that shape the plan:

- Gerber copper pours are exported as `G36` regions with `%LPC%` (clear) polarity for
  thermal reliefs/isolation: 95–187 regions per layer. KiCad has no negative objects, so
  pours must become KiCad zones, not imported graphics.
- Drill file is `Plated,1,4,PTH` only: no blind/buried vias.
- Pin ids in the IPC file: resistors/caps/ICs/connectors use numbers, diodes use `A`/`C`,
  MOSFETs `1,2,3`, shunts (FKK5R0020FE) `1..4`, relays `1..6`. KiCad symbol pin numbers
  must match these exactly or a translation table is needed.
- Refdes is truncated to 6 characters in IPC: `AFE_OU`, `FILTER` (both FILTER_IN and
  FILTER_OUT collapse to the same name), `DAB_PR`, `DAB_SE`, `INU_OU`. These are the
  single-pin test terminals; disambiguate by coordinate.
- Proteus power-net names: `GND=POWER`, `VCC/VDD=POWER`. Rename to `GND`, `VCC` in KiCad
  via a net-name alias table used by the comparison script.
- Odd refdes in the original: `R256` (keep it, it is in the IPC file and the PDF).
- Component counts: R 98, C 87, U 17, Q 14, J 12, D 10, PE 8, CM 3, REF 2, ACIN/ACOUT 4,
  TR 1, PWM 1, L 1, AD 1, plus 5 terminals.
- Packages named in `ROOT.LYT`: 0603, SOT23, SOT23-5, SOT23-8, SOT-323, SOT-523, SOT-26,
  SOIC127P1030X265-16N (SOIC-16W), SOIC127P1031X265-8N, SOT95P280X145-5N, X2QFN, QFN10X10,
  TO-247AC, DIP08_300, SNAP_IN_35MM (35 mm snap-in elko), EF20 transformer, SLA relay,
  WE-CMBNC choke, EEEFTE221XAP, resistor arrays, shunts.

## 2. Phase 0 – project skeleton and tooling (½ day)

1. `git init` in `~/dev/ac_psu_kicad`; layout:
   ```
   source/          Proteus exports (read-only reference)
   tools/           Python scripts (run with the AppImage's python so `import pcbnew` works)
   lib/             project symbol + footprint libraries
   kicad/           ac_psu.kicad_pro / .kicad_sch / .kicad_pcb
   ```
2. `tools/kicad_env.sh`: mounts the AppImage (`--appimage-mount`) and exports a `kipy`
   wrapper = AppImage `bin/python3.11` with `PYTHONPATH` set to the dist-packages dir.
   Also expose `kicad-cli`.
3. `tools/ipc356.py`: parse the IPC-D-356A file into a JSON/CSV table
   `(net, refdes, pin, x_mm, y_mm, side, pad_w, pad_h, rot, is_tht, drill)`.
   Fix up the truncated refdes using a hand-written table keyed by (truncated name, x, y).
   Apply the net-name alias table (`GND=POWER` → `GND`, etc.).
4. From that table generate `reference/pin_nets_by_component.md`: per refdes, a list of
   pin → net. This is the cheat sheet while redrawing, and the authoritative
   definition of "electrically identical".

## 3. Phase 1 – redraw the schematic in KiCad (bulk of the manual work, 1–2 days)

Approach: manual redraw in eeschema, one KiCad sheet per Proteus sheet (11 sheets,
hierarchical, root sheet = sheet index), using the PDF renders as the picture to copy.

Rules that make the later net mapping work:

- Keep every refdes exactly as in Proteus (including `R256`, `PE1..PE8`, `ACIN1`, etc.).
- Symbol pin numbers must equal the IPC pin ids. Watch: diodes (`A`/`C` – KiCad's
  standard diode symbols use `1`/`2`, so use `Device:D` with a custom pin-number
  override or project-library copies with `A`/`C`), MOSFET pin order of the TO-247
  C3M0065090D (gate/drain/source = 1/2/3), the 10-pin EF20 transformer, relays, shunts,
  CM chokes, the "HB GT CONNECTOR" (only pins 15–48 used), J11 (38-pin, 50 mil), J12.
- Use the IPC net names as KiCad net labels wherever the Proteus net has a real name
  (`G1_GATE_HI`, `PWM_TRANS1_ISO`, `ISOGND`, …). 74 Proteus nets are auto-named
  (`#00xxx`); the comparison in Phase 4 is done
  by pad-set equivalence, not by name, so naming is only a convenience.
- Power symbols (project library, names = IPC nets): `GND`, `PGND`, `ISOGND`, `ISOPGND`,
  `DGND`, `DAB_GROUND`, `RET_ISO`, `VCC`, `3V3_ISO`, `5V`, `5V_ISOL`, `20V`, `20V_ISO_SEC`,
  `DC+`, `ISODC+`. There is no `3V3` net: the PDF's `3V3`/`3v3` terminals are net `VCC`, and
  `DC-`/`AGND` are net `GND` (see STATUS.md, Phase 1 transcription rules).
- Sheet order (easiest first, builds the label vocabulary): 2 fpga connector → 3
  regulators → 11 signal isolators → 10 → 9 primary side ADC → 8 SDM current → 1 afe →
  5 VSI → 6 DAB → 4 DC links → 7 Auxiliary supply.
- Symbol sourcing: KiCad standard libs for passives, OPA2353, TLV316, TPS73033, REF3025,
  ADR380, SN74LV4051, BSS138, 2N7000, ADuM7701 (check `Isolator` lib), Si8660 (check),
  ADS7056, IW1830 (custom), C3M0065090D (TO-247-3 generic), relays SLA-12VDC-SL
  (custom), WE-CMBNC (custom 4-pin), FKK5R0020FE shunt (custom 4-pin Kelvin), EF20
  transformer (custom 10-pin), VXO7805-500 (custom).
- Run ERC after each sheet. Run the Phase 4 netlist comparison after each sheet too, so
  errors are caught sheet by sheet rather than at the end.

Alternative considered: generating the schematic programmatically from the IPC netlist
(symbols + global labels, no wires). It is electrically complete but unreadable; not
worth it since the user wants a proper redraw. It *could* be used as a throw-away
reference to drive "Update PCB from schematic" early, if the PCB work should start
before the redraw is finished.

## 4. Phase 2 – footprints (½–1 day)

1. Assign a KiCad footprint to every symbol. Pad numbers must match the IPC pin ids
   (same constraint as the symbols).
2. `tools/check_footprints.py`: for each refdes, take the KiCad footprint's pad centres
   and the IPC pad centres for that refdes and solve the rigid transform (rotation
   0/90/180/270 + mirror for bottom side + translation) that maps one onto the other.
   Report residual per pad. Residual > 0.05 mm = wrong footprint, wrong pin numbering, or
   different pad pitch. This is cheap and catches almost all footprint mistakes before
   anything is placed.
3. Where the Proteus pad geometry differs from the KiCad library footprint (pad size,
   custom shapes like the 4 mm / 5.08 mm round pads of the snap-in caps, TO-247 pad
   sizes), either accept the KiCad footprint (the gerbers will then differ slightly from
   Proteus, which is fine if DRC passes) or copy the IPC pad size into a project footprint.
   Decide per footprint; default is to accept KiCad's.
4. Package → footprint candidates: 0603 → `Resistor_SMD:R_0603_1608Metric` /
   `Capacitor_SMD:C_0603_1608Metric`; SOT23 → `Package_TO_SOT_SMD:SOT-23`; SOT23-5 /
   SOT95P280X145-5N → `SOT-23-5`; SOIC127P1030X265-16N → `Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm`;
   SOIC127P1031X265-8N → `SOIC-8_3.9x4.9mm_P1.27mm` (check width, 1031 = 10.31 mm long?
   measure against IPC); TO-247AC → `Package_TO_SOT_THT:TO-247-3_Vertical`; DIP08_300 →
   `Package_DIP:DIP-8_W7.62mm`; SNAP_IN_35MM → `Capacitor_THT:CP_Radial_D35.0mm_P10.00mm_SnapIn`;
   X2 safety film caps, chokes, relays, transformer, shunts, J1–J8 2×17 header
   (pins 15–48 of a 2×24), J11 2×19 50 mil, J12 2×3 → verify from IPC geometry; create
   custom ones in `lib/ac_psu.pretty` where no match.

## 5. Phase 3 – build the PCB and map the gerbers onto the nets (1–2 days)

### 3a. Footprints with nets, placed where Proteus put them

1. eeschema → "Update PCB from schematic": all footprints land in the board with nets.
2. `tools/place_from_ipc.py` (pcbnew Python): for each footprint reuse the transform from
   `check_footprints.py` and set position, orientation and side. Set the board outline on
   `Edge.Cuts` from the Mechanical 1 gerber (a 246.8 × 154.7 mm rectangle, corner at
   (−128.2, −83.0) mm). Keep the Proteus coordinate origin (no offset) so every later
   import lines up without translation; set KiCad's drill/grid origin there.
3. Result: pads of every footprint sit on top of the Proteus copper pads with the right
   nets. Already at this point `check_footprints.py` can re-run against the board.

### 3b. Tracks and vias

Two options; recommended is the first.

- **Own converter `tools/gerber_to_tracks.py`** (recommended): parse the 4 copper gerbers
  (X2, metric, `FSLAX45Y45`, linear `D01` draws only – check for `G02/G03` arcs) and the
  plated drill gerber. Every `D01` segment drawn with a `Conductor` circle aperture →
  `PCB_TRACK` with that width; every `ViaPad` flash in copper + matching `ViaDrill` flash
  in the drill file → `PCB_VIA` (through, 0.457 mm pad / 0.3 mm drill). Component-pad
  flashes are skipped (the footprints already provide them). `G36` regions and
  `%LPC%` items are collected separately (see 3d). Deterministic, scriptable, no GUI.
- **GerbView → File → Export to KiCad PCB**: quick for a first look, but it produces
  flashed pads as one-pad dummy footprints, treats negative items badly, and needs manual
  layer mapping. Use only for the non-copper reference layers (silk, assembly) on
  `User.1`…`User.4` as an underlay.

### 3c. Net assignment on the imported copper

`tools/assign_nets.py`: load the board, build a geometric union-find over all copper
items: pad ↔ track endpoint/overlap (per layer), track ↔ track (shared endpoints,
tolerance 1 µm), via ↔ anything on any copper layer at the via centre. Each connected
component inherits the net of the pads it contains. Report:

- components containing pads of **two or more nets** → a short in the import or a real
  difference between the Proteus netlist and the redrawn schematic;
- components with **no pad** → stray copper (usually a pour fragment or a track to a via
  that lands only in a pour);
- nets whose pads fall into **more than one** component → opens, usually because the
  connection goes through a pour (expected for GND/PGND/ISOGND/DC+ etc.) – resolved in 3d.

KiCad itself can do part of this: after `BuildConnectivity()` the board's own ratsnest
shows unconnected pads, and DRC reports shorts; use both as a cross-check of the script.

### 3d. Pours → zones

Proteus pours arrive as `G36` outlines with clear-polarity cut-outs; they cannot be
imported as-is. Plan:

1. `gerber_to_tracks.py` additionally writes the **outer boundary** of each positive `G36`
   region as a polygon on a User layer (reference underlay), tagged with the layer.
2. Determine each pour's net by sampling which pads/vias fall inside the outer boundary
   (from the IPC table). Create a KiCad `ZONE` with that net, that outline and that layer,
   with thermal reliefs; let KiCad refill. Zone fill/clearance settings are KiCad's; the
   result will not be pixel-identical to Proteus, which is acceptable.
3. Any remaining opens from 3c should disappear after zone fill. Remaining opens are real
   findings (Proteus design relied on something the redraw does not have).

### 3e. Silkscreen and mask

Use the KiCad footprints' own silk, mask and paste. Keep the Proteus silk/assembly gerbers
only as a User-layer underlay for checking orientation and polarity marks. Reference
designator positions can be copied from the Top/Bottom Assembly gerbers later if wanted.

## 6. Phase 4 – verification (continuous, ½ day at the end)

1. **Schematic ≡ Proteus** (`tools/compare_netlists.py`): export the KiCad netlist
   (`kicad-cli sch export netlist --format kicadxml`), build the set of
   `{frozenset of (refdes, pin)}` per net for both sides (after refdes fix-ups and
   net-name aliases), and diff. Output: pins on the wrong net, missing/extra parts,
   missing/extra pins, N/C mismatches. Target: zero differences. Run after every sheet.
2. **Copper ≡ nets**: `assign_nets.py` report empty of shorts/opens; KiCad DRC with
   zero unconnected items and zero clearance/short errors (clearance rules may need to be
   set to Proteus' values, e.g. 0.152 mm minimum track seen in the apertures).
3. **Gerber round-trip**: `kicad-cli pcb export gerbers` from the KiCad board, render both
   sets with `gerbv` (or KiCad's gerbview) to PNG and overlay/XOR per copper layer. Expect
   differences only in pour fill detail and pad shapes where KiCad library footprints were
   accepted.
4. **Pad list**: regenerate an IPC-D-356 from KiCad (`kicad-cli pcb export ipc356` if
   present in 10.0.7, otherwise from pcbnew Python) and diff coordinates against the
   Proteus file: every pad within 0.05 mm, same net class.

## 7. Risks and open points

- Pin-id convention mismatch between KiCad library symbols/footprints and the IPC ids is
  the most likely source of silent errors → the Phase 2 geometric check and Phase 4 netlist
  diff both catch it; do not skip them.
- `strings ROOT.DSN` gives part numbers but not values; values come from the PDF text
  layer (`source/schematic_pdf/schematic_text.txt`). Some values are only legible in the
  rendered image (e.g. `R26 NA`).
- Sheet 10 has no title; the notes on sheet 7 (`V5.1`, `R64 = 39k / v2 trans`) suggest
  hand edits after the layout – the PDF (printed 2026-10-17 from the same project) and the
  CADCAM (same date) should still agree, but the comparison script is what confirms it.
- Arcs in the gerbers: checked, the four copper layers contain no `G02/G03` commands, so the
  converter only needs linear `D01` draws, `D03` flashes and `G36/G37` regions.
- Pad sizes in KiCad library footprints differ from Proteus pads; decide per footprint
  (see Phase 2 step 3) before the gerber round-trip check, or the diff is noisy.

## 8. Rough effort

| Phase | Effort |
|---|---|
| 0 tooling + IPC parser | ½ day |
| 1 schematic redraw (11 sheets, ~265 parts) | 1–2 days |
| 2 footprints + geometric check | ½–1 day |
| 3 PCB build, converters, net assignment, zones | 1–2 days |
| 4 verification and fix-ups | ½ day |

## 9. Claude model usage plan

Principle: the repo is the shared memory, not the chat session. Every phase ends with its
state written to files (scripts, libraries, `STATUS.md`, verification reports), so any
session with any model can pick up where the last one stopped. Sessions are therefore
split by **phase**, not by model, and switching model inside a session with `/model` is
fine when a phase needs it.

| Phase | Model | Why |
|---|---|---|
| 0 Tooling, IPC parser, cheat sheet | Opus 5.5 | Well-specified scripting; output is checked by counting pads/nets against the IPC file. |
| 1 Schematic redraw – symbol library + power symbols | Opus 5.5 | Mechanical work with a clear spec (pin ids from the IPC table). |
| 1 Schematic redraw – transcribing the 11 sheets from the PDF images | Fable 5.1 | Reading dense schematic images and keeping cross-sheet label context is where accuracy differs. Do it one sheet per turn and run `compare_netlists.py` after each sheet before moving on. If drawing by hand in eeschema instead, no model is needed here. |
| 1 Fixing diffs reported by the netlist comparison | Opus 5.5 first, Fable if a diff survives two attempts | Most diffs are a single wrong label or pin number. |
| 2 Footprints + geometric fit check | Opus 5.5 | Scripted check gives a hard pass/fail per footprint. |
| 3 PCB build, converter, net assignment, zones | Opus 5.5 | Scripting with DRC and the net-assignment report as oracle. Escalate to Fable only for stubborn shorts/opens that need design judgment. |
| 4 Verification + final review | Fable 5.1 (one pass) | Independent read of the end-to-end result; cheap relative to the rest. |

Session layout:

1. One session per phase (phases 1 and 3 may take several sessions; start a new one when
   the context gets long rather than letting it be summarized repeatedly).
2. Each session starts by reading `PLAN.md` and `STATUS.md`, and ends by updating
   `STATUS.md` (what is done, what the last verification report said, what is next) and
   committing.
3. Do not share one session across models for the sheet transcription: start a Fable
   session per batch of sheets, with the cheat sheet and the page PNGs as input, so the
   context holds the images at full fidelity instead of a summary.
4. Keep every verification script runnable with one command (`make check` or
   `tools/check_all.sh`) so a new session can confirm the state before touching anything.

### Handoff prompt (required at the end of every phase)

When a phase is finished (or a session ends mid-phase), the agent must end its last
message with a **ready-to-paste prompt for the next agent**, in a fenced code block. The
prompt is self-contained and includes:

1. Which model the next session should use (from the table above) and which phase/step
   it starts on.
2. The files to read first (`PLAN.md`, `STATUS.md`, plus the phase-specific inputs such as
   `reference/pin_nets_by_component.md` or the page PNGs).
3. The exact command that verifies the current state (e.g. `tools/check_all.sh`) and what
   its output looked like at handoff.
4. Known open problems or decisions left for the next phase.
5. The definition of done for the next phase, including which verification must pass.

The same prompt is written to `next_prompt.md` (replacing the previous one) and committed,
so it is not lost if the chat is closed. `STATUS.md` only points to it.
