#!/usr/bin/env python3
"""v4 fix 5 (run once, kipy): restore the Kelvin connection of the AFE shunt R48 (FKK5R0020FE:
pads 1/2 = 2.9 x 1.0 mm sense, 3/4 = 2.9 x 5.6 mm force, as R91/R64).
v3 joined sense pad 1 to force pad 3 with a B.Cu track (pad 1 -> (3.891,-67.3) -> (4.317,-67.726)
-> (4.317,-70.893) -> (3.816,-71.394) -> pad 3). That track is deleted; the sense side keeps net
SHUNT1 (pad 1 -> U5-4, R58-2, C52/C53/C71/C73, D8-A) and the force side (pad 3, the B.Cu pour with
J5-1 and its spokes/stubs) becomes /01 afe/SHUNT1_FORCE."""
from v4board import Board, T

b = Board(4105)
FORCE = "/01 afe/SHUNT1_FORCE"
if b.b.FindNet(FORCE) is not None:
    raise SystemExit("fix 5 already applied")
JOIN = {((3.891, -67.3), (4.317, -67.726)), ((4.317, -67.726), (4.317, -68.667)),
        ((4.317, -68.667), (4.317, -70.893)), ((4.317, -70.893), (3.816, -71.394)),
        ((3.816, -71.394), (2.106, -71.394)), ((2.106, -71.394), (2.1, -71.4))}


def ends(t):
    s, e = t.GetStart(), t.GetEnd()
    return ((round(T(s.x), 3), round(-T(s.y), 3)), (round(T(e.x), 3), round(-T(e.y), 3)))


def joining(t):
    a, c = ends(t)
    return t.GetNetname() == "SHUNT1" and ((a, c) in JOIN or (c, a) in JOIN)


n = b.delete_tracks(joining)
if n != len(JOIN):
    raise SystemExit(f"fix 5: deleted {n} tracks, expected {len(JOIN)}")
for ref in ("R48", "J5"):
    b.sync_pads(ref)
moved = 0
for t in b.b.GetTracks():
    if t.GetNetname() == "SHUNT1" and max(p[1] for p in ends(t)) < -68.0:  # force side: below y -68
        t.SetNet(b.net(FORCE))
        moved += 1
for z in b.b.Zones():
    if z.GetNetname() == "SHUNT1":
        z.SetNet(b.net(FORCE))
        moved += 1
b.log.append(f"{moved} force-side tracks/zones SHUNT1 -> {FORCE}")
b.save("fix 5: R48 Kelvin split")
