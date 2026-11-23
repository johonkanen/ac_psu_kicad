#!/usr/bin/env python3
"""Renders of the two power-card bands of the v6 baseboard (V6_PLAN.md step 3): F and B side of each wall with the
card envelopes (18 mm from the wall, card spans), the 20 mm terminal line and the control card outline drawn.

  python3 tools/v6/render_v6.py [--board FILE] [--out DIR]     -> reports/v6/band_<wall>_<side>.png
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PPM = 9
WALL_P, WALL_I = -83.05, 71.75
CARDS_X = (32.2, 66.2, 100.2)
CTRL_CARD = (42.599, -18.766, 118.599, 46.361)
VIEWS = {"primary": (-50.0, 120.0, -84.0, -38.0), "iso": (-110.0, 120.0, 30.0, 72.5)}
SIDES = (("F", "F.Cu,F.SilkS,F.Fab,Edge.Cuts"), ("B", "B.Cu,B.SilkS,B.Fab,Edge.Cuts"))


def main():
    a = sys.argv[1:]
    board = a[a.index("--board") + 1] if "--board" in a else os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb")
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "reports", "v6")
    tmp = os.path.join(ROOT, "build", "v6_render")
    os.makedirs(tmp, exist_ok=True)
    for wall, (X0, X1, Y0, Y1) in VIEWS.items():
        px = lambda p: ((p[0] - X0) * PPM, (Y1 - p[1]) * PPM)   # noqa: E731
        for side, layers in SIDES:
            bg = os.path.join(tmp, f"{wall}_{side}_bg.png")
            subprocess.run([sys.executable, os.path.join(ROOT, "tools", "v4", "render_area.py"), str(X0), str(X1), str(Y0),
                            str(Y1), bg, "--layers", layers, "--ppm", str(PPM), "--board", board], check=True, capture_output=True)
            im = Image.open(bg).convert("RGBA")
            im = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
            ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(ov)
            wy, sgn = (WALL_P, 1) if wall == "primary" else (WALL_I, -1)
            for cx in CARDS_X:
                x0, x1 = cx - 16.5, cx + 16.5
                dr.rectangle([px((x0, max(wy, wy + sgn * 18))), px((x1, min(wy, wy + sgn * 18)))],
                             fill=(255, 160, 0, 40), outline=(255, 120, 0, 255), width=2)
            dr.line([px((X0, wy + sgn * 20)), px((X1, wy + sgn * 20))], fill=(0, 140, 0, 255), width=1)
            dr.text(px((X0 + 1, wy + sgn * 20 + (1.5 if sgn > 0 else -0.5))), "20 mm from the wall", fill=(0, 120, 0, 255))
            c0, c1, c2, c3 = CTRL_CARD
            dr.rectangle([px((c0, c3)), px((c2, c1))], outline=(30, 60, 220, 255), width=2)
            dr.text(px((c0 + 1, c3 - 0.5)), "control card outline (5.3 mm up)", fill=(30, 60, 220, 255))
            for k in range(int(X0 // 10 * 10), int(X1), 10):
                dr.text(px((k, Y1 - 0.3)), str(k), fill=(90, 90, 90, 255))
            path = os.path.join(out, f"band_{wall}_{side}.png")
            Image.alpha_composite(im, ov).convert("RGB").save(path)
            print(f"render_v6: {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
