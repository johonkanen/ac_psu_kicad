#!/usr/bin/env python3
"""Renders of the card area with the domains coloured (V5_LAYOUT_PLAN.md phase 4): one PNG per copper
layer and side into reports/v5_layout/card_<layer>.png. Green = CTRL, red = primary, blue = ISO; dashed =
barrier centre lines; orange = slots; grey hatch = the DC bus band.

  python3 tools/v5/render_card.py [--board FILE] [--out DIR]
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "v5"))
import card_layout as L  # noqa: E402

X0, X1, Y0, Y1, PPM = 36.0, 121.0, -38.0, 58.0, 18
COL = {"C": (30, 160, 60), "P": (215, 50, 50), "I": (50, 90, 220)}
LAYERS = (("F", "F.Cu,F.SilkS,Edge.Cuts"), ("In1", "In1.Cu,Edge.Cuts"), ("In2", "In2.Cu,Edge.Cuts"), ("In3", "In3.Cu,Edge.Cuts"),
          ("In4", "In4.Cu,Edge.Cuts"), ("B", "B.Cu,B.SilkS,Edge.Cuts"))


def main():
    a = sys.argv[1:]
    board = a[a.index("--board") + 1] if "--board" in a else os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "reports", "v5_layout")
    tmp = os.path.join(ROOT, "build", "v5_layout")
    os.makedirs(tmp, exist_ok=True)
    px = lambda p: ((p[0] - X0) * PPM, (Y1 - p[1]) * PPM)
    for name, layers in LAYERS:
        bg = os.path.join(tmp, f"card_{name}_bg.png")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "v4", "render_area.py"), str(X0), str(X1), str(Y0), str(Y1), bg,
                        "--layers", layers, "--ppm", str(PPM), "--board", board], check=True, capture_output=True)
        im = Image.open(bg).convert("RGBA")
        im = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        for k, (dom, poly) in L.AREAS.items():
            dr.polygon([px(p) for p in poly], fill=COL[dom] + (38,), outline=COL[dom] + (255,))
        bx0, by0, bx1, by1 = L.BUS_BAND
        dr.rectangle([px((bx0, by1)), px((bx1, by0))], outline=(90, 90, 90, 255), width=2)
        dr.text(px((bx0 + 0.5, by1 - 0.3)), "DC bus band (no parts, no signal copper on F/B)", fill=(60, 60, 60, 255))
        for _, _, pl in L.LINES:
            for p, q in zip(pl, pl[1:]):
                n = max(2, int(math.dist(p, q)))
                for i in range(0, n, 2):
                    dr.line([px((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n)),
                             px((p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n))], fill=(0, 0, 0, 255), width=2)
        for _, p, q in L.SLOTS:
            dr.line([px(p), px(q)], fill=(255, 140, 0, 200), width=int(L.SLOT_W * PPM))
        dr.rectangle([px((L.CARD[0], L.CARD[3])), px((L.CARD[2], L.CARD[1]))], outline=(0, 0, 0, 255), width=2)
        for k in range(40, 121, 10):
            dr.text(px((k, Y1 - 0.3)), str(k), fill=(90, 90, 90, 255))
        for k in range(-30, 58, 10):
            dr.text(px((X0 + 0.3, k)), str(k), fill=(90, 90, 90, 255))
        Image.alpha_composite(im, ov).convert("RGB").save(os.path.join(out, f"card_{name}.png"))
        print(f"render_card: {os.path.join(os.path.relpath(out, ROOT), 'card_' + name + '.png')}")


if __name__ == "__main__":
    main()
