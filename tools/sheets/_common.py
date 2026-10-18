"""Shared helpers for the per-sheet transcription scripts (tools/sheets/sheetNN.py).

Each script rebuilds its sub-sheet from scratch (Sheet.clear()) so it can be re-run after
a fix. Coordinates: schematic mm, Y down, 1.27 mm grid. Rotations CCW like eeschema.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from sch_builder import Sheet  # noqa: E402,F401

G = 1.27  # grid


def g(n):
    """n grid units in mm."""
    return round(n * G, 4)


def sheet(fname):
    return Sheet(os.path.join(ROOT, "kicad", fname)).clear()


def left(p, n=2):
    return (round(p[0] - g(n), 4), p[1])


def right(p, n=2):
    return (round(p[0] + g(n), 4), p[1])


def up(p, n=2):
    return (p[0], round(p[1] - g(n), 4))


def down(p, n=2):
    return (p[0], round(p[1] + g(n), 4))


def glabel_left(sh, name, p, n=2):
    """Wire n grid units to the left of pin point p and put a global label there."""
    q = left(p, n)
    sh.wire(p, q)
    sh.glabel(name, *q, 180)
    return q


def glabel_right(sh, name, p, n=2):
    q = right(p, n)
    sh.wire(p, q)
    sh.glabel(name, *q, 0)
    return q


def label_left(sh, name, p, n=2):
    q = left(p, n)
    sh.wire(p, q)
    sh.label(name, *q, 180)
    return q


def label_right(sh, name, p, n=2):
    q = right(p, n)
    sh.wire(p, q)
    sh.label(name, *q, 0)
    return q


def power_at(sh, net, p, direction):
    """Power symbol whose connection point is p, body pointing in `direction`
    ('up', 'down', 'left', 'right'). Works for the ground-style (pin dir 270) and
    supply-style (pin dir 90) project power symbols."""
    from sch_builder import lib
    from sexpr import find, walk
    sym = lib()[net]
    pin_dir = int(float(find(next(walk(sym, "pin")), "at")[3]))
    body = {90: "up", 270: "down"}[pin_dir]
    want = {"up": 0, "left": 90, "down": 180, "right": 270}[direction]
    have = {"up": 0, "left": 90, "down": 180, "right": 270}[body]
    rot = (want - have) % 360
    value_at = None
    if direction == "left":
        value_at = (round(p[0] - 3.3, 4), p[1], rot, "left")
    elif direction == "right":
        value_at = (round(p[0] + 3.3, 4), p[1], rot, "right")
    return sh.power(net, p[0], p[1], rot, value_at=value_at)


def bus_group(sh, pins, label_pin, side, label=None, power=None, n=2, m=2):
    """Join vertically stacked pin points `pins` (list of (x,y)) with a bus line n grid
    units outward (side 'left'/'right'), then branch m more units outward at the y of
    `label_pin` and attach a global label or a power symbol there."""
    sgn = -1 if side == "left" else 1
    xv = round(pins[0][0] + sgn * g(n), 4)
    ys = sorted(p[1] for p in pins)
    for p in pins:
        sh.wire(p, (xv, p[1]))
    if len(pins) > 1:
        sh.wire((xv, ys[0]), (xv, ys[-1]))
    ly = label_pin[1]
    q = (round(xv + sgn * g(m), 4), ly)
    sh.wire((xv, ly), q)
    if len(pins) > 1 and ys[0] < ly < ys[-1] or (len(pins) > 1 and ly in (ys[0], ys[-1])):
        # T or 3-way meeting point
        sh.junction(xv, ly)
    if label:
        sh.glabel(label, *q, 180 if side == "left" else 0)
    if power:
        power_at(sh, power, q, side)
    return q


def flagged_power(sh, net, x, y):
    """A power symbol with a PWR_FLAG attached by a short vertical wire (supply symbols
    point up with the flag below, ground symbols point down with the flag above).
    Returns the power-symbol connection point (x, y)."""
    from sch_builder import lib
    from sexpr import find, walk
    pin_dir = int(float(find(next(walk(lib()[net], "pin")), "at")[3]))
    if pin_dir == 90:      # supply style: body up
        power_at(sh, net, (x, y), "up")
        q = down((x, y), 2)
        sh.wire((x, y), q)
        sh.pwr_flag(q[0], q[1], 180)
    else:                  # ground style: body down
        power_at(sh, net, (x, y), "down")
        q = up((x, y), 2)
        sh.wire((x, y), q)
        sh.pwr_flag(q[0], q[1], 0)
    return (x, y)
