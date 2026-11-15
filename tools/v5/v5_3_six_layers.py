#!/usr/bin/env python3
"""v5 step 3 (run once, kipy): six copper layers and the JLC stack-up (V5_LAYOUT_PLAN.md phase 2).

In3.Cu and In4.Cu are added between In2.Cu and B.Cu; the existing copper is unchanged (through
pads and vias get their rings on the new layers). Stack-up JLC06161H-3313, 1.6 mm: 1 oz outer,
0.5 oz inner, prepreg 3313 0.0994 / core 0.55 / prepreg 2116 0.1088 / core 0.55 / prepreg 3313
0.0994 (reports/v5_layout/proposal.md section 5). Layer use in the card area: In1 and In4 ground,
In2 supply, In3 routing.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v4"))
from v4board import Board, F  # noqa: E402

COPPER = {"F.Cu": 0.035, "In1.Cu": 0.0152, "In2.Cu": 0.0152, "In3.Cu": 0.0152, "In4.Cu": 0.0152, "B.Cu": 0.035}
DIELECTRIC = [("prepreg", 0.0994), ("core", 0.55), ("prepreg", 0.1088), ("core", 0.55), ("prepreg", 0.0994)]

b = Board(5003)
if b.b.GetCopperLayerCount() != 4:
    raise SystemExit(f"v5 step 3 already applied ({b.b.GetCopperLayerCount()} copper layers)")
b.b.SetCopperLayerCount(6)
ds = b.b.GetDesignSettings()
thick = sum(COPPER.values()) + sum(t for _, t in DIELECTRIC)
ds.SetBoardThickness(F(1.6))
b.log.append(f"6 copper layers (In3.Cu, In4.Cu added), stack-up JLC06161H-3313: copper + dielectric {thick:.4f} mm, "
             f"board thickness 1.6 mm (was 2.267)")
b.save("v5 step 3: six copper layers, JLC06161H-3313")

# pcbnew's Python API has no stack-up editor: write the block into the saved file, then let pcbnew
# read and save it again (checks the syntax, gives KiCad's own formatting).
import board_common as bc  # noqa: E402
names = list(COPPER)
rows = ['(layer "F.SilkS" (type "Top Silk Screen"))', '(layer "F.Paste" (type "Top Solder Paste"))',
        '(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))']
for i, n in enumerate(names):
    rows.append(f'(layer "{n}" (type "copper") (thickness {COPPER[n]}))')
    if i < len(DIELECTRIC):
        kind, th = DIELECTRIC[i]
        rows.append(f'(layer "dielectric {i + 1}" (type "{kind}") (thickness {th}) (material "FR4") '
                    f'(epsilon_r {4.6 if kind == "core" else 4.1}) (loss_tangent 0.02))')
rows += ['(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))', '(layer "B.Paste" (type "Bottom Solder Paste"))',
         '(layer "B.SilkS" (type "Bottom Silk Screen"))', '(copper_finish "None")', '(dielectric_constraints no)']
text = open(bc.BOARD).read()
if "(stackup" in text or text.count("\t(setup\n") != 1:
    raise SystemExit("v5 step 3: unexpected setup block")
text = text.replace("\t(setup\n", "\t(setup\n\t\t(stackup\n" + "".join(f"\t\t\t{r}\n" for r in rows) + "\t\t)\n")
open(bc.BOARD, "w").write(text)
pcbnew.KIID.SeedGenerator(5003)
b2 = pcbnew.LoadBoard(bc.BOARD)
zones = b2.Zones()
pcbnew.ZONE_FILLER(b2).Fill(zones)
pcbnew.SaveBoard(bc.BOARD, b2)
print("  stack-up block written:", ", ".join(f"{k} {t}" for k, t in DIELECTRIC))
