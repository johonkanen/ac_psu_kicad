"""Board helpers for the per-sheet transcription scripts (tools/sheets/sheetNN.py);
the generic ones (grid, labels, power symbols, two-pin parts, terminals) are p2k.sheetkit.

Each script rebuilds its sub-sheet from scratch (Sheet.clear()) so it can be re-run after
a fix. Coordinates: schematic mm, Y down, 1.27 mm grid. Rotations CCW like eeschema.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "p2k"))  # proteus2kicad
from p2k.sch_builder import Sheet  # noqa: E402,F401
from p2k.sheetkit import *  # noqa: E402,F401,F403  (generic helpers)
from p2k.sheetkit import _two_pin_rot  # noqa: E402,F401

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


def diff_amp(sh, xb, top, unit, plus, minus, r_ref, ref_label, r_fb, r_out, out_label, first=g(12), top_plus=None,
             opamp=("OPA2353UA", "U1"), rval="91K", pins=None, ref_power=None, out_cap=None, top_power=None):
    """Difference amplifier (sheets 1, 4, 5): three `rval` resistors per input from `top` down
    to the op-amp (plus chain in the inner column xa = xb + 6 grid, minus chain in xb), r_ref
    from the + node up to ref_label (a global label, or a power symbol pointing left when
    ref_power is set), r_fb feedback, r_out to out_label. pins = (plus, minus, out) pin
    numbers (default by OPA2353 unit); out_cap = (ref, val, gnd_net) hangs a capacitor from
    the output label node to gnd_net; top_power = (plus_net, minus_net) puts power symbols on
    the chain tops instead of leaving them for the caller. Returns a dict of points."""
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
    if pins is None:
        pins = (5, 6, 7) if unit == 2 else (3, 2, 1)
    pinp, pinm, out = (u.pin(p) for p in pins)
    sh.wire((xa, rows_[2] + 3.81), (xa, pinp[1]), pinp)
    sh.wire((xb, rows_[2] + 3.81), (xb, pinm[1]), pinm)
    xr = xa + g(8)
    _, rt, rb = vert2(sh, "R", r_ref[0], xr, pinp[1] - g(6), r_ref[1], top=1)
    sh.wire(rb, (xr, pinp[1])); sh.junction(xr, pinp[1])
    sh.wire(rt, up(rt, 2))
    if ref_power:
        power_at(sh, ref_power, up(rt, 2), "left")
    else:
        sh.glabel(ref_label, *up(rt, 2), 90)
    n = right(out, 2)
    sh.wire(out, n); sh.junction(*n)
    _, ol, or_ = horiz2(sh, "R", r_out[0], xu + g(14), yu, r_out[1], left=2)
    sh.wire(n, ol)
    lab = right(or_, 2)
    if out_cap:
        sh.wire(or_, lab); sh.junction(*lab)
        sh.wire(lab, right(lab, 4)); sh.glabel(out_label, *right(lab, 4), 0)
        _, ct, cb = vert2(sh, "C", out_cap[0], lab[0], lab[1] + g(6), out_cap[1], top=1)
        sh.wire(lab, ct); sh.wire(cb, down(cb, 2)); power_at(sh, out_cap[2], down(cb, 2), "down")
    else:
        glabel_right(sh, out_label, or_, 2)
    fb = yu + g(6)
    _, fl, fr = horiz2(sh, "R", r_fb[0], xu, fb, r_fb[1], left=2, text="below")
    sh.wire(n, (n[0], fb), fr)
    sh.wire(fl, (pinm[0], fb), pinm)
    sh.junction(*pinm)
    pa = (xa, top_plus if top_plus is not None else top)
    pm = (xb, top)
    if top_power:
        power_at(sh, top_power[0], pa, "up")
        power_at(sh, top_power[1], pm, "left")
    return {"plus_top": pa, "minus_top": pm, "u": u, "xu": xu, "yu": yu}
