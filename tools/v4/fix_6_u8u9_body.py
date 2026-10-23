#!/usr/bin/env python3
"""v4 fix 6 (run once, kipy): U8/U9 (VXO7805) body graphics on the component-face side of the pin
row, away from J12, as the Proteus silk draws it and a photo of the built board shows (2026-10-23).
The project footprint Converter_DCDC_RECOM_R-78E-0.5_THT_Proteus now mirrors the R-78E graphics
across the pin row (tools/gen_footprints.py flip_body); this copies its silk, fab, courtyard,
reference/value positions and 3D model onto U8 and U9. Pads, nets and positions are unchanged."""
import pcbnew
from v4board import Board, T, load_fp

b = Board(4106)
keep = []  # removed shapes stay referenced: freeing them breaks the SWIG wrappers (pcbnew 10)
for ref in ("U8", "U9"):
    fp = b.fp(ref)
    pos = fp.GetPosition()
    old = [g for g in fp.GraphicalItems() if g.GetLayerName() == "F.Courtyard"]
    if old and T(old[0].GetBoundingBox().GetBottom() - pos.y) > 5.0:
        raise SystemExit("fix 6 already applied")
    lib = load_fp(fp.GetFPIDAsString())
    lib.SetPosition(pos)
    lib.SetOrientation(fp.GetOrientation())
    keep.append(lib)
    for ftype in (pcbnew.FIELD_T_REFERENCE, pcbnew.FIELD_T_VALUE):
        src, dst = lib.GetField(ftype), fp.GetField(ftype)
        dst.SetPosition(src.GetPosition())
        dst.SetLayer(src.GetLayer())
    fp.Models().clear()
    for m in lib.Models():
        fp.Models().push_back(m)
    cy = [g for g in lib.GraphicalItems() if g.GetLayerName() == "F.Courtyard"][0].GetBoundingBox()
    b.log.append(f"{ref} at ({T(pos.x):.3f},{-T(pos.y):.3f}): body graphics from the library footprint, "
                 f"courtyard y {-T(cy.GetBottom()):.3f} ... {-T(cy.GetTop()):.3f}")
    new = list(lib.GraphicalItems())
    for g in list(fp.GraphicalItems()):
        fp.Remove(g)
        keep.append(g)
    for g in new:
        lib.Remove(g)
        fp.Add(g)
        g.thisown = False
b.save("fix 6: U8/U9 body graphics away from J12")
