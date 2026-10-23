#!/usr/bin/env python3
"""Render a rectangle of the board to PNG for a visual check (kicad-cli SVG export, cropped
by rewriting the viewBox, rasterised with librsvg/cairo via p2k.render_sheet.svg_to_png).

  python3 tools/v4/render_area.py X0 X1 Y0 Y1 out.png [--layers F.Cu,B.Cu,...] [--ppm 40]
                                  [--board FILE] [--mirror]

Coordinates in mm, IPC frame (Y up, as in reference/ipc356_pads.json and STATUS.md).
Default layers: F.Cu,B.Cu,F.SilkS,Edge.Cuts. Colours are kicad-cli's default theme.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
from p2k.render_sheet import svg_to_png  # noqa: E402

BOARD_X0, BOARD_Y1 = -128.2, 71.7  # board outline top-left (IPC frame), = SVG origin


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("x0", type=float)
    ap.add_argument("x1", type=float)
    ap.add_argument("y0", type=float)
    ap.add_argument("y1", type=float)
    ap.add_argument("out")
    ap.add_argument("--layers", default="F.Cu,B.Cu,F.SilkS,Edge.Cuts")
    ap.add_argument("--ppm", type=float, default=40, help="pixels per mm")
    ap.add_argument("--board", default=os.path.join(ROOT, "kicad", "ac_psu.kicad_pcb"))
    a = ap.parse_args()
    cli = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
    with tempfile.TemporaryDirectory() as td:
        svg = os.path.join(td, "b.svg")
        r = subprocess.run([cli, "pcb", "export", "svg", "--mode-single", "-l", a.layers, "--page-size-mode", "2",
                            "--exclude-drawing-sheet", "-o", svg, a.board], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(r.stdout + r.stderr)
        s = open(svg).read()
        w, h = a.x1 - a.x0, a.y1 - a.y0
        vx, vy = a.x0 - BOARD_X0, BOARD_Y1 - a.y1
        s = re.sub(r'width="[^"]*" height="[^"]*" viewBox="[^"]*"',
                   f'width="{w:.4f}mm" height="{h:.4f}mm" viewBox="{vx:.4f} {vy:.4f} {w:.4f} {h:.4f}"', s, count=1)
        open(svg, "w").write(s)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        svg_to_png(svg, a.out, int(w * a.ppm))
    print(f"render_area: {a.out} ({a.layers}, x {a.x0}..{a.x1}, y {a.y0}..{a.y1})")


if __name__ == "__main__":
    main()
