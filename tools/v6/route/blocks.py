#!/usr/bin/env python3
"""Routing blocks of the v6 baseboard (V6_PLAN.md section 16): outlines, corridors, and the block of a point.

  python3 tools/v6/route/blocks.py            prints the outlines
  tools/p2k/bin/kipy tools/v6/route/blocks.py nets
        nets with pads in more than one block (signal nets; pour / plane nets listed apart) -> the port list to plan

IPC frame (mm, Y up). Block G (aux flyback) lies inside the rectangles of C and E; it wins where they overlap.
"""
import os
import sys

BLOCKS = {
    "A": ("AFE input / filter / AFE sense (P)", (-128.3, -83.1, -2.0, -12.0)),
    "B": ("Inverter filter / AC out / INV sense (I)", (-128.3, -12.0, -38.0, 71.8)),
    "C": ("Primary card band (P)", (-2.0, -83.1, 118.7, -46.0)),
    "D": ("ISO card band + west of J11 (I)", (-38.0, 46.0, 118.7, 71.8)),
    "D2": ("ISO card band, inverter leg B header part (I)", (-38.0, 38.0, 40.0, 46.0)),   # J24 / J37 / J38 bodies
    "E": ("Control-card area (C / I / P)", (40.0, -46.0, 118.7, 46.0)),
    "F": ("Bulk caps / dividers / op-amps (P / I)", (-38.0, -46.0, 40.0, 46.0)),
    "G": ("Aux flyback (routed, frozen)", (67.0, -54.6, 97.5, -4.0)),
}
ORDER = ["G", "A", "B", "C", "D", "D2", "E", "F"]          # G first: it overrides C / E where they overlap
# nets carried by pours / planes: not routed as tracks between blocks, joined by plane vias
POUR_NETS = {"GND", "PGND", "ISOGND", "ISOPGND", "CTRLGND", "CTRLGND_A", "DC+", "ISODC+", "VCC", "3V3_ISO", "3V3_CTRL",
             "5V_CTRL", "15V", "15V_ISO", "5V", "5V_ISOL", "DAB_GROUND"}


# Port windows: where the nets of a group leave a block (edge, fixed coordinate, range along the edge, layers).
# The block router puts each crossing net's stub end on its window; the trunk step joins the stubs of two blocks.
WINDOWS = {
    "E-C primary PWM (PWM_G1..G4, PWM_TRANS1..3, DAB_PWM_PRI_HI / LO)": ("E", "y", -46.0, (41.0, 66.0), "F.Cu In3.Cu B.Cu"),
    "E-D ISO PWM (PWM_Q5..Q8, PWM_TRANS4..6, DAB_PWM_HI / LO_SEC), U7A-": ("E", "y", 46.0, (59.0, 117.0), "F.Cu In3.Cu B.Cu"),
    "E-A sigma-delta AFE (MDATA, ADCLK), GPIO_BYPASS_RLY, dividers R2 / R5, U1A inputs": ("E", "x", 40.0, (-45.0, -15.0), "In3.Cu F.Cu B.Cu"),
    "E-F op-amp inputs (U2 / U7), PWM_TRANS6": ("E", "x", 40.0, (-15.0, 25.0), "F.Cu In3.Cu B.Cu"),
    "E-B sigma-delta INV (MDATA_INU, INU_ADCLK), GPIO_BYPASS_RLY_ISO": ("E", "x", 40.0, (25.0, 45.0), "In3.Cu F.Cu B.Cu"),
}


def block_of(x, y):
    for k in ORDER:
        x0, y0, x1, y1 = BLOCKS[k][1]
        if x0 <= x <= x1 and y0 <= y <= y1:
            return k[0]
    return None


def crossing_nets(board_path):
    import pcbnew
    T = pcbnew.ToMM
    b = pcbnew.LoadBoard(board_path)
    nets = {}
    for f in b.GetFootprints():
        if -T(f.GetPosition().y) < -88:
            continue
        for p in f.Pads():
            n = p.GetNetname()
            if not n or n.startswith("unconnected-"):
                continue
            q = p.GetPosition()
            nets.setdefault(n, []).append((f.GetReference(), p.GetNumber(), block_of(T(q.x), -T(q.y)), T(q.x), -T(q.y)))
    return nets


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "nets":
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        nets = crossing_nets(os.path.join(root, "kicad", "ac_psu.kicad_pcb"))
        sig, pour = [], []
        for n, pads in sorted(nets.items()):
            bl = sorted({p[2] for p in pads if p[2]})
            if len(bl) > 1:
                (pour if n.split("/")[-1] in POUR_NETS else sig).append((n.split("/")[-1], bl, pads))
        print(f"signal nets crossing blocks: {len(sig)}")
        for n, bl, pads in sig:
            print(f"  {n:28s} {'-'.join(bl):8s} " + " ".join(f"{r}.{p}:{b}" for r, p, b, _, _ in pads)[:150])
        print(f"pour / plane nets crossing blocks: {len(pour)}: " + " ".join(f"{n}({'-'.join(bl)})" for n, bl, _ in pour))
    else:
        for k, (name, box) in BLOCKS.items():
            print(f"{k} {name:42s} x {box[0]} .. {box[2]}, y {box[1]} .. {box[3]}")
