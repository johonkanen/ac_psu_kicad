"""Where can a through via of an ISO signal stand around the passage north of J11? (run under tools/p2k/bin/kipy)

  kipy via_scan.py BOARD [NET]

Scans a 0.25 mm grid over x 15..95, y 36..55.3 with the rules of scripted.py (pads, tracks, vias, pours of other
nets on F.Cu / B.Cu, keep-outs) and prints a character map: '#' = a via fits, '.' = no. One row per 0.5 mm in y
(a row is '#' if either of its two grid rows fits), one column per 0.5 mm in x. Shows that north of the DC bus band
the pours on F.Cu / B.Cu leave no place for a via, so In4 cannot be entered there.
"""
import sys

import pcbnew

import scripted as S

b = pcbnew.LoadBoard(sys.argv[1])
net = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "PWM_Q5"
S.STRICT_POUR = "--loose" not in sys.argv      # default: the zone's own clearance to pours (1.95 mm at the ISODC+ pour)
cx = S.Ctx(b)
X0, X1, Y0, Y1 = 15.0, 95.0, 36.0, 55.25
n = 0
y = Y1
print("x 15 .. 95 (0.5 mm per column), net", net)
while y >= Y0:
    row = ""
    x = X0
    while x <= X1:
        ok = any(cx.via_ok(net, x + dx, y - dy) is not None for dx in (0, 0.25) for dy in (0, 0.25))
        n += ok
        row += "#" if ok else "."
        x += 0.5
    print(f"{y:5.1f} {row}")
    y -= 0.5
