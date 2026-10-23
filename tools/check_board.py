#!/usr/bin/env python3
"""Check the saved board kicad/ac_psu.kicad_pcb against the IPC-D-356A file (run under kipy).

Pads:  every IPC component pad has a footprint pad with that refdes and pin id within
       0.05 mm, and every footprint pad has an IPC pad (same check in reverse);
       nets: IPC nets and KiCad nets map one-to-one through the pads; N/C pins (and R87-4/5,
       which have no IPC net) sit on no net or KiCad's "unconnected-(...)" net.
Holes: the 4 IPC 'hole' records are plated mounting holes (3.0 mm drill, 4.0 mm pad, no net).
Vias:  every IPC via has a board via at its position (0.01 mm) on the IPC net, and every board
       via is an IPC via.
Copper: every track and via has a net, every zone has a net (after tools/make_pcb.sh).

Usage: tools/p2k/bin/kipy tools/check_board.py [--pads-only]
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_common as bc  # noqa: E402
import deviations  # noqa: E402


def mm(v):
    return pcbnew.ToMM(v)


def check_pads(board, recs, errors):
    ipc = {}
    for p in recs:
        if p["kind"] == "pad":
            ipc.setdefault((p["refdes"], p["pin"]), []).append(p)
    mapping, problems = bc.ipc_to_kicad_nets(board)
    errors.extend(problems)
    worst, npads, used = 0.0, 0, set()
    v4pads, pending = [], []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsBoardOnly():
            continue
        for pad in fp.Pads():
            npads += 1
            key = (ref, pad.GetNumber())
            c = pad.GetPosition()
            x, y = mm(c.x), -mm(c.y)
            cands = ipc.get(key, [])
            added = deviations.added_parts().get(ref)
            if added and not cands:
                # v4 part: no Proteus position; its pads must be on the listed nets
                want = added["pins"].get(pad.GetNumber())
                if want is None:
                    errors.append(f"{ref}-{pad.GetNumber()}: v4 part pad not in lib/v4_deviations.csv")
                else:
                    v4pads.append(f"{ref}-{pad.GetNumber()}@({x:.3f},{y:.3f})")
                    pending.append((ref, pad.GetNumber(), want, pad.GetNetname()))
                continue
            if not cands:
                errors.append(f"{ref}-{pad.GetNumber()}: footprint pad without IPC pad")
                continue
            q = min(cands, key=lambda q: math.hypot(x - q["x_mm"], y - q["y_mm"]))
            d = math.hypot(x - q["x_mm"], y - q["y_mm"])
            used.add(id(q))
            worst = max(worst, d)
            if d > bc.TOL:
                errors.append(f"{ref}-{pad.GetNumber()}: {d:.3f} mm from the IPC pad")
            kn = pad.GetNetname()
            if q["net_raw"] == "N/C" or not q["net"]:
                if not bc.is_unconnected_net(kn):
                    errors.append(f"{ref}-{pad.GetNumber()}: N/C in IPC but on net {kn}")
            elif mapping.get(q["net"]) != kn:
                errors.append(f"{ref}-{pad.GetNumber()}: net {kn}, IPC net {q['net']} -> {mapping.get(q['net'])}")
    for ref, pin, want, kn in pending:
        if mapping.get(want, want) != kn:
            errors.append(f"{ref}-{pin}: net {kn}, v4 list {want} -> {mapping.get(want)}")
    if v4pads:
        print(f"check_board: v4 pads without Proteus pad (nets checked): {' '.join(v4pads)}")
    for key, qs in ipc.items():
        for q in qs:
            if id(q) not in used:
                errors.append(f"{key[0]}-{key[1]}: IPC pad without footprint pad")
    return worst, npads, mapping


def check_holes(board, recs, errors):
    holes = [p for p in recs if p["kind"] == "hole"]
    fps = [fp for fp in board.GetFootprints() if fp.IsBoardOnly()]
    for h in holes:
        hit = []
        for fp in fps:
            for pad in fp.Pads():
                c = pad.GetPosition()
                if math.hypot(mm(c.x) - h["x_mm"], -mm(c.y) - h["y_mm"]) < 0.01:
                    hit.append((fp, pad))
        if len(hit) != 1:
            errors.append(f"mounting hole at ({h['x_mm']}, {h['y_mm']}): {len(hit)} board pads")
            continue
        fp, pad = hit[0]
        if abs(mm(pad.GetDrillSizeX()) - h["drill"]) > 1e-3 or abs(mm(pad.GetSizeX()) - h["pad_w"]) > 1e-3 \
                or pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH or pad.GetNetname():
            errors.append(f"{fp.GetReference()}: hole {mm(pad.GetDrillSizeX())}/{mm(pad.GetSizeX())} mm, "
                          f"net {pad.GetNetname()!r} (want plated {h['drill']}/{h['pad_w']} mm, no net)")
    if len(fps) != len(holes):
        errors.append(f"{len(fps)} board-only footprints, {len(holes)} IPC holes")
    return len(holes)


def check_copper(board, recs, mapping, errors):
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    tracks = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA"]
    ipc_vias = [p for p in recs if p["kind"] == "via"]
    grid = {}
    for v in vias:
        c = v.GetPosition()
        grid.setdefault((round(mm(c.x), 1), round(-mm(c.y), 1)), []).append(v)
    matched = set()
    for q in ipc_vias:
        hit = None
        for dx in (-0.1, 0, 0.1):
            for dy in (-0.1, 0, 0.1):
                for v in grid.get((round(q["x_mm"] + dx, 1), round(q["y_mm"] + dy, 1)), []):
                    c = v.GetPosition()
                    if math.hypot(mm(c.x) - q["x_mm"], -mm(c.y) - q["y_mm"]) < 0.01:
                        hit = v
        if hit is None:
            errors.append(f"IPC via ({q['x_mm']}, {q['y_mm']}) {q['net']}: no board via")
            continue
        matched.add(hit.m_Uuid.AsString())
        want = mapping.get(q["net"])
        if want is None:
            errors.append(f"IPC via ({q['x_mm']}, {q['y_mm']}): IPC net {q['net']} has no KiCad net")
        elif hit.GetNetname() != want:
            errors.append(f"via ({q['x_mm']}, {q['y_mm']}): net {hit.GetNetname()!r}, IPC {q['net']} -> {want}")
    v4vias = deviations.vias()
    nv4 = 0
    for v in vias:
        if v.m_Uuid.AsString() not in matched:
            c = v.GetPosition()
            x, y = mm(c.x), -mm(c.y)
            hit = [d for d in v4vias if math.hypot(d[0] - x, d[1] - y) < 0.01]
            if not hit:
                errors.append(f"board via ({x:.3f}, {y:.3f}) is neither an IPC via nor a v4 via (lib/v4_copper.csv)")
            elif mapping.get(hit[0][2], hit[0][2]) != v.GetNetname():
                errors.append(f"v4 via ({x:.3f}, {y:.3f}): net {v.GetNetname()}, list {hit[0][2]}")
            else:
                nv4 += 1
    if nv4 != len(v4vias):
        errors.append(f"{len(v4vias)} v4 vias listed, {nv4} found on the board")
    if v4vias:
        print(f"check_board: {nv4} v4 vias (lib/v4_copper.csv) at their positions and nets")
    nonet = [t for t in tracks if t.GetNetCode() <= 0]
    if nonet:
        errors.append(f"{len(nonet)} tracks without net")
    zones = list(board.Zones())
    zn = [z for z in zones if z.GetNetCode() <= 0 and not z.GetIsRuleArea()]
    if zn:
        errors.append(f"{len(zn)} zones without net")
    return len(tracks), len(vias), len(zones)


def main():
    board = pcbnew.LoadBoard(bc.BOARD)
    recs = bc.ipc_records()
    errors = []
    worst, npads, mapping = check_pads(board, recs, errors)
    nholes = check_holes(board, recs, errors)
    print(f"check_board: {len(board.GetFootprints())} footprints, {npads} pads, worst pad offset {worst:.3f} mm "
          f"(limit {bc.TOL}), {len(mapping)} IPC nets mapped 1:1, {nholes} mounting holes")
    if "--pads-only" not in sys.argv:
        nt, nv, nz = check_copper(board, recs, mapping, errors)
        print(f"check_board: {nt} tracks, {nv} vias, {nz} zones")
    for e in errors[:60]:
        print("check_board: ERROR " + e)
    if len(errors) > 60:
        print(f"check_board: ... {len(errors) - 60} more errors")
    print("check_board: " + ("FAILED" if errors else "OK"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
