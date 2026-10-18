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


def _two_pin_rot(sym, pin, want):
    """Rotation that puts `pin` of two-pin symbol `sym` at `want` ('top' or 'left')."""
    from sch_builder import lib, _rot
    from sexpr import find, walk
    for p in walk(lib()[sym], "pin"):
        if find(p, "number")[1] == str(pin):
            at = find(p, "at")
            px, py = float(at[1]), float(at[2])
            break
    else:
        raise KeyError(f"{sym} has no pin {pin}")
    for rot in (0, 90, 180, 270):
        dx, dy = _rot(px, py, rot)      # lib coords, y up
        if want == "top" and abs(dx) < 1e-6 and dy > 0:
            return rot
        if want == "left" and abs(dy) < 1e-6 and dx < 0:
            return rot
    raise ValueError(f"{sym} pin {pin} cannot be placed at {want}")


def vert2(sh, sym, ref, x, y, value=None, top=1, **kw):
    """Two-pin symbol (R, C, D, L ...) placed vertically with pin `top` at the top.
    Returns (placed, top_point, bottom_point)."""
    p = sh.place(sym, ref, x, y, _two_pin_rot(sym, top, "top"), value=value, **kw)
    pins = sorted(p.pins.values(), key=lambda q: q[1])
    return p, pins[0], pins[-1]


def horiz2(sh, sym, ref, x, y, value=None, left=1, **kw):
    """Two-pin symbol placed horizontally with pin `left` on the left.
    Returns (placed, left_point, right_point)."""
    p = sh.place(sym, ref, x, y, _two_pin_rot(sym, left, "left"), value=value, **kw)
    pins = sorted(p.pins.values(), key=lambda q: q[0])
    return p, pins[0], pins[-1]


def adum_block(sh, UX, UY, ref, value, raw_label, r_raw, zener, caps_vdd, vinp, vinm, gnd1_label,
               vdd2, gnd2, clk_label, r_mdat, mdat_label, decoupling, note=None):
    """ADuM7701 sigma-delta modulator floating on a shunt, drawn like the Proteus sheets 8/10:
    VDD1 rail fed through r_raw from raw_label and clamped by `zener` (None = no diode in the
    IPC), caps_vdd = two (ref, val) on that rail, vinp/vinm = ((rref, rval), label, (cref, cval))
    series resistor + cap for VIN+/VIN-, GND1 rail = gnd1_label (the VIN- resistor's far side).
    Right side: vdd2/gnd2 power nets, clk_label on MCLKIN, r_mdat = (ref, val) into mdat_label,
    decoupling = (ref, val) cap between vdd2 and gnd2."""
    u = sh.place("ADUM7701-8BRIZ", ref, UX, UY, value=value)
    VDD1, VINP, VINM, GND1 = u.pin(1), u.pin(2), u.pin(3), u.pin(4)
    VDD2, MCLK, MDAT, GND2 = u.pin(8), u.pin(7), u.pin(6), u.pin(5)
    T = UY - g(10)          # VDD1 rail (Proteus auto-net)
    B = UY + g(16)          # GND1 rail
    XL = UX - g(74)         # left end of the rails (cap bank)
    sh.wire(VDD1, (UX - g(12), VDD1[1]), (UX - g(12), T), (XL, T))
    sh.wire(GND1, (UX - g(11), GND1[1]), (UX - g(11), B), (XL, B))
    # VIN+ : series R from its label, C to the GND1 rail
    (rr, rv), lab, (cr, cv) = vinp
    _, rl, rr_ = horiz2(sh, "R", rr, UX - g(36), VINP[1], rv, left=2, text="above")
    sh.wire(VINP, rr_)
    sh.junction(UX - g(30), VINP[1])
    _, ct, cb = vert2(sh, "C", cr, UX - g(30), UY + g(10), cv, top=1, text="left")
    sh.wire((UX - g(30), VINP[1]), ct)
    sh.wire(cb, (cb[0], B))
    sh.junction(cb[0], B)
    glabel_left(sh, lab, rl, 2)
    # VIN- : drops below the IC, series R from its label (= GND1 net), C to the rail
    (rr, rv), lab, (cr, cv) = vinm
    row = UY + g(6)
    sh.wire(VINM, (UX - g(12), VINM[1]), (UX - g(12), row))
    _, rl, rr_ = horiz2(sh, "R", rr, UX - g(24), row, rv, left=2, text="below")
    sh.wire((UX - g(12), row), rr_)
    sh.junction(UX - g(16), row)
    _, ct, cb = vert2(sh, "C", cr, UX - g(16), UY + g(10), cv, top=1)
    sh.wire((UX - g(16), row), ct)
    sh.wire(cb, (cb[0], B))
    sh.junction(cb[0], B)
    sh.wire(rl, (rl[0], B))
    sh.junction(rl[0], B)
    # cap bank between the rails (+ zener, cathode to VDD1)
    mid = (T + B) / 2
    bank = [(UX - g(58), ("C", caps_vdd[0][0], caps_vdd[0][1], 1, None)),
            (UX - g(66), ("C", caps_vdd[1][0], caps_vdd[1][1], 1, None))]
    if zener:
        bank.append((UX - g(74), ("D_Zener", zener[0], zener[1], "C", "left")))
    for xcol, (sym, cref, cval, top, text) in bank:
        _, pt, pb = vert2(sh, sym, cref, xcol, mid, cval, top=top, text=text)
        sh.wire(pt, (xcol, T))
        sh.wire(pb, (xcol, B))
        if xcol != XL:
            sh.junction(xcol, T)
            sh.junction(xcol, B)
    if not zener:
        sh.text("(Proteus shows an unlabelled zener here; it has no refdes and is not in the layout)",
                XL - g(2), mid + g(1))
    # raw supply through r_raw into the VDD1 rail
    _, rl, rr_ = horiz2(sh, "R", r_raw[0], UX - g(84), T, r_raw[1], left=2)
    sh.wire((XL, T), rr_)
    glabel_left(sh, raw_label, rl, 2)
    sh.wire((XL, B), (XL - g(2), B))
    sh.glabel(gnd1_label, XL - g(2), B, 180)
    # both floating supply pins are fed from passives only -> power flags
    sh.pwr_flag(UX - g(52), T, 0)
    sh.junction(UX - g(52), T)
    sh.pwr_flag(UX - g(52), B, 180)
    sh.junction(UX - g(52), B)
    # isolated / logic side
    sh.wire(VDD2, right(VDD2, 4))
    power_at(sh, vdd2, right(VDD2, 4), "up")
    sh.wire(GND2, right(GND2, 4))
    power_at(sh, gnd2, right(GND2, 4), "down")
    glabel_right(sh, clk_label, MCLK, 4)
    _, rl, rr_ = horiz2(sh, "R", r_mdat[0], UX + g(22), MDAT[1], r_mdat[1], left=1, text="below")
    sh.wire(MDAT, rl)
    glabel_right(sh, mdat_label, rr_, 2)
    cx = UX + g(50)
    _, ct, cb = vert2(sh, "C", decoupling[0], cx, UY, decoupling[1], top=2)
    sh.wire(ct, up(ct, 2))
    power_at(sh, vdd2, up(ct, 2), "up")
    sh.wire(cb, down(cb, 2))
    power_at(sh, gnd2, down(cb, 2), "down")
    if note:
        sh.text(note, UX - g(94), B + g(8))
    return u


def terminal(sh, ref, x, y, direction="up"):
    """Proteus-style PIN terminal (ac_psu:PIN) with its connection point at (x, y) and the
    circle pointing in `direction`. Texts are kept horizontal beside the circle."""
    rot = {"up": 0, "left": 90, "down": 180, "right": 270}[direction]
    kw = {}
    if direction == "right":     # KiCad mirrors justification for rot 270: "right" draws left-justified
        kw = dict(ref_at=(x + 5.08, y - 1.27, 90, "right"), value_at=(x + 5.08, y + 1.27, 90, "right"))
    elif direction == "left":
        kw = dict(ref_at=(x - 5.08, y - 1.27, 270, "left"), value_at=(x - 5.08, y + 1.27, 270, "left"))
    return sh.place("PIN", ref, x, y, rot, value="PIN", **kw)


def diff_amp(sh, xb, top, unit, plus, minus, r_ref, ref_label, r_fb, r_out, out_label, first=g(12), top_plus=None,
             opamp=("OPA2353UA", "U1"), rval="91K"):
    """OPA2353 difference amplifier (sheets 1 and 5): three `rval` resistors per input from `top` down to the op-amp (plus chain in the inner
    column xa, minus chain in the outer column xb), r_ref from the + node up to ref_label,
    r_fb feedback, r_out to out_label. Returns the chain top points (plus, minus)."""
    xa = xb + g(6)
    rows_ = [top + first + g(8 * i) for i in range(3)]
    for col, chain, text, t0 in ((xa, plus, None, top_plus if top_plus is not None else top), (xb, minus, "left", top)):
        prev = (col, t0)
        for ref, row in zip(chain, rows_):
            _, t, b = vert2(sh, "R", ref, col, row, rval, top=2, text=text)
            sh.wire(prev, t)
            prev = b
    yu = rows_[2] + g(8)
    xu = xa + g(16)
    u = sh.place(opamp[0], opamp[1], xu, yu, unit=unit, value=opamp[0])
    pinp, pinm, out = (u.pin(5), u.pin(6), u.pin(7)) if unit == 2 else (u.pin(3), u.pin(2), u.pin(1))
    sh.wire((xa, rows_[2] + 3.81), (xa, pinp[1]), pinp)
    sh.wire((xb, rows_[2] + 3.81), (xb, pinm[1]), pinm)
    xr = xa + g(8)
    _, rt, rb = vert2(sh, "R", r_ref[0], xr, pinp[1] - g(6), r_ref[1], top=1)
    sh.wire(rb, (xr, pinp[1])); sh.junction(xr, pinp[1])
    sh.wire(rt, up(rt, 2)); sh.glabel(ref_label, *up(rt, 2), 90)
    n = right(out, 2)
    sh.wire(out, n); sh.junction(*n)
    _, ol, or_ = horiz2(sh, "R", r_out[0], xu + g(14), yu, r_out[1], left=2)
    sh.wire(n, ol); glabel_right(sh, out_label, or_, 2)
    fb = yu + g(6)
    _, fl, fr = horiz2(sh, "R", r_fb[0], xu, fb, r_fb[1], left=2, text="below")
    sh.wire(n, (n[0], fb), fr)
    sh.wire(fl, (pinm[0], fb), pinm)
    sh.junction(*pinm)
    return (xa, top_plus if top_plus is not None else top), (xb, top)


