#!/usr/bin/env python3
"""Routing stage 0 (run under tools/p2k/bin/kipy): pad nets of the swapped isolator channels.

  tools/p2k/bin/kipy tools/v5/route/s0_swap.py IN.kicad_pcb OUT.kicad_pcb

The channel order of U19/U20 was changed in tools/sheets/sheet11.py (PW) so that the ISO-side signals leave
in the order of their destinations (J8, J6, J4). The pads of U19 and U20 take their nets from the schematic.
"""
import os
import sys

import pcbnew

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [TOOLS, os.path.join(TOOLS, "p2k")]
import board_common as bc  # noqa: E402


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    _, nets = bc.export_netlist()
    pin_net = {(r, p): n for n, nodes in nets.items() for r, p in nodes}
    n = 0
    for ref in ("U19", "U20"):
        for pad in board.FindFootprintByReference(ref).Pads():
            want = pin_net.get((ref, pad.GetNumber()))
            if want and pad.GetNetname() != want:
                ni = board.FindNet(want)
                if ni is None:
                    sys.exit(f"s0_swap: net {want} is not on the board")
                print(f"s0_swap: {ref}-{pad.GetNumber()}: {pad.GetNetname()} -> {want}")
                pad.SetNet(ni)
                n += 1
    pcbnew.SaveBoard(sys.argv[2], board)
    print(f"s0_swap: {n} pad nets changed -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
