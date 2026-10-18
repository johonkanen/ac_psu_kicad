#!/usr/bin/env python3
"""Sheet 6 - Dual Active Bridge (PDF page 6): primary half bridge Q9/Q10 on DC+/PGND with the
split capacitor C35||C1 / C46||C45, secondary half bridge Q11/Q12 on ISODC+/DAB_GROUND with
C48||C47 / C50||C49, and the off-board ETD34 transformer TR1 (excluded from board) wired
through the DAB_PRI_x / DAB_SEC_x terminals."""
from _common import *  # noqa: F401,F403

sh = sheet("06_dual_active_bridge.kicad_sch")
DCP, PG, MID = g(28), g(82), g(55)
CU, CL = g(42), g(68)          # centres of the upper / lower split capacitors
TX, TY = g(82), g(57)
tr1 = sh.place("ETD34_TRAN_1P1S", "TR1", TX, TY, value="ETD34 TRAN 1P1S")


def half_bridge(xq, qhi, qlo, g_hi, g_lo):
    hi = sh.place("C3M0065090D", qhi, xq, g(40), value="C3M0065090D")
    lo = sh.place("C3M0065090D", qlo, xq, g(70), value="C3M0065090D")
    col = hi.pin(2)[0]
    sh.wire(hi.pin(2), (col, DCP))
    sh.wire(hi.pin(3), lo.pin(2))
    sh.wire(lo.pin(3), (col, PG))
    glabel_left(sh, g_hi, hi.pin(1), 4)
    glabel_left(sh, g_lo, lo.pin(1), 4)
    return col


def split_caps(x1, x2, upper, lower, top_net, mid_net, bot_net):
    """Two parallel caps between top rail and mid node, two between mid node and bottom rail.
    Pin 1 of every capacitor is on the upper side (IPC)."""
    for x, ref in zip((x1, x2), upper):
        _, t, b = vert2(sh, "C", ref, x, CU, "2.2u", top=1)
        sh.wire(t, (x, DCP)); sh.wire(b, (x, MID))
    for x, ref in zip((x1, x2), lower):
        _, t, b = vert2(sh, "C", ref, x, CL, "2.2u", top=1)
        sh.wire(t, (x, MID)); sh.wire(b, (x, PG))
    sh.wire((x1, MID), (x2, MID))


# ---- primary side -----------------------------------------------------------------------------
XC1, XC2 = g(22), g(30)
split_caps(XC1, XC2, ("C35", "C1"), ("C46", "C45"), "DC+", "DAB_CAP_PRI", "PGND")
col_p = half_bridge(g(60), "Q9", "Q10", "DAB_GATE_HI_PRI", "DAB_GATE_LO_PRI")
sh.wire((XC1, DCP), (col_p, DCP)); sh.junction(XC2, DCP)
sh.wire((XC1, PG), (col_p, PG)); sh.junction(XC2, PG)
power_at(sh, "DC+", (g(44), DCP), "up"); sh.junction(g(44), DCP)
power_at(sh, "PGND", (g(44), PG), "down"); sh.junction(g(44), PG)
sh.wire((XC1, MID), (g(18), MID)); sh.glabel("DAB_CAP_PRI", g(18), MID, 180)
sh.junction(g(26), MID); terminal(sh, "DAB_PRI_2", g(26), MID, "down")
# TR1 primary: 1 = half-bridge midpoint (DAB_PRI_1), 2 = capacitor midpoint (DAB_PRI_2)
p1, p2 = tr1.pin(1), tr1.pin(2)
sh.wire(p1, (col_p, p1[1])); sh.junction(col_p, p1[1])
sh.junction(g(68), p1[1]); terminal(sh, "DAB_PRI_1", g(68), p1[1], "up")
sh.glabel("DAB_SOURCE_HI_PRI", g(66), p1[1], 270)
sh.wire(p2, left(p2, 2)); sh.glabel("DAB_CAP_PRI", *left(p2, 2), 270)

# ---- secondary side ---------------------------------------------------------------------------
col_s = half_bridge(g(104), "Q11", "Q12", "DAB_GATE_HI_SEC", "DAB_GATE_LO_SEC")
XC3, XC4 = g(122), g(130)
split_caps(XC3, XC4, ("C48", "C47"), ("C50", "C49"), "ISODC+", "DAB_CAP_SEC", "DAB_GROUND")
sh.wire((col_s, DCP), (XC4, DCP)); sh.junction(XC3, DCP)
sh.wire((col_s, PG), (XC4, PG)); sh.junction(XC3, PG)
power_at(sh, "ISODC+", (g(114), DCP), "up"); sh.junction(g(114), DCP)
power_at(sh, "DAB_GROUND", (g(114), PG), "down"); sh.junction(g(114), PG)
sh.wire((XC4, MID), (g(134), MID)); sh.glabel("DAB_CAP_SEC", g(134), MID, 0)
sh.junction(g(126), MID); terminal(sh, "DAB_SEC_2", g(126), MID, "down")
p3, p4 = tr1.pin(3), tr1.pin(4)
sh.wire(p3, (col_s, p3[1])); sh.junction(col_s, p3[1])
sh.junction(g(98), p3[1]); terminal(sh, "DAB_SEC_1", g(98), p3[1], "down")
sh.glabel("DAB_SOURCE_HI_SEC", g(94), p3[1], 90)
sh.wire(p4, right(p4, 2)); sh.glabel("DAB_CAP_SEC", *right(p4, 2), 90)

sh.text("TR1 is not on the PCB (excluded from board): it connects through the DAB_PRI_1/2 and DAB_SEC_1/2 terminals.",
        g(20), g(100))
sh.text("PDF notes: TR1 core 227 nH; winding 52/8/3 || 7/3/3/42.", g(20), g(103))
sh.text("DC+, PGND, ISODC+ and DAB_GROUND are flagged on sheets 1, 1, 5 and 8.", g(20), g(106))
sh.save()
print("sheet06: written")
