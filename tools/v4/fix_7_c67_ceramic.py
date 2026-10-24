#!/usr/bin/env python3
"""v4 fix 7 (run once, kipy): C67 (100 uF on 5V, non-polar 1206 land pattern like C57/C58) is a
ceramic capacitor: sheet 7 draws it with `C` instead of `C_Polarized`; this copies the symbol's
Datasheet / Description fields onto the footprint (schematic parity). No copper change."""
import pcbnew
from v4board import Board

b = Board(4107)
fp = b.fp("C67")
fields = b.comps["C67"]["fields"]
desc = fp.GetField(pcbnew.FIELD_T_DESCRIPTION)
if desc.GetText() == fields.get("Description", ""):
    raise SystemExit("fix 7 already applied")
for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
    f = fp.GetField(ftype)
    b.log.append(f"C67 {fname}: {f.GetText()!r} -> {fields.get(fname, '')!r}")
    f.SetText(fields.get(fname, ""))
b.save("fix 7: C67 ceramic (symbol C)")
