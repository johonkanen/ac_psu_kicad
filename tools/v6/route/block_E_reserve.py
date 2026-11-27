#!/usr/bin/env python3
"""Chain step (kipy): block_E.RESERVE applied to a board.   kipy block_E_reserve.py IN OUT"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_E as BE  # noqa: E402

b = pcbnew.LoadBoard(sys.argv[1])
log = []
BE.shrink_reserve(b, log)
print("reserve:", *(log or ["already shrunk"]))
pcbnew.SaveBoard(sys.argv[2], b)
