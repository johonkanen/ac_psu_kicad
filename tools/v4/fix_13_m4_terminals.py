#!/usr/bin/env python3
"""v4 fix 13 (run once, kipy): M4 ring-lug terminals instead of the soldered lead pins (user
decision 2026-10-31; about 4 kW, leads 17-25 A). Footprint ac_psu:Wuerth_REDCUBE-THR_74650074_M4_PTH
(Wuerth REDCUBE THR 74650074R, M4 through thread, 7 x 7 mm, 4 solder pins, 50 A; plated 4.3 mm centre
hole in a 7.4 mm square pad 1 on every layer, so the old pin's tracks still land on copper).

Only the terminals with room for the 10 x 10 mm courtyard and a ring lug (12 mm to the next
terminal of another net) are swapped here. Positions: the nearest spot (0.25 mm grid, <= 3.5 mm
from the pin) whose courtyard is clear of other parts, whose copper keeps 0.6 mm to other nets'
pads/tracks/vias (5.0 / 2.5 mm to other domains) and that sits in the terminal's own pour, found
with /tmp/claude-1000/v4term/place.py and fixed here. Pours of other nets refill around the new pads
(fix 14 then restores the insulation gaps). The 4 terminal pairs (DAB_PRI_1/2, DAB_SEC_1/2,
ACIN1/2, ACOUT1/2), AFE_OUT (its terminal would cut the B.Cu G1_SOURCE_HI pour in two) and PE1-PE8
do not fit without re-layout and stay pins (STATUS.md)."""
import pcbnew
from v4board import Board, P, T, load_fp

TERMINALS = {   # ref: new centre (IPC frame, mm)
    "FILTER_IN": (-14.40, -57.30),
    "FILTER_OUT": (-33.00, -52.00),
    "INU_OUT2": (47.00, 60.00),
    "J5": (-14.70, -75.65),
    "J7": (-71.80, 65.60),
    "J9": (-71.90, 48.40),
    "J10": (-58.20, 42.15),
}
FPID = "ac_psu:Wuerth_REDCUBE-THR_74650074_M4_PTH"

b = Board(4113)
keep = []   # removed footprints stay referenced (SWIG wrappers, see fix 6)
for ref, (x, y) in TERMINALS.items():
    old = b.fp(ref)
    if old.GetFPIDAsString() == FPID:
        raise SystemExit("fix 13 already applied")
    c = b.comps[ref]
    if c["footprint"] != FPID:
        raise SystemExit(f"{ref}: schematic footprint {c['footprint']}, expected {FPID} (re-run the sheets)")
    oc = old.GetPosition()
    ox, oy = T(oc.x), -T(oc.y)
    net = b.pin_net[(ref, "1")]
    b.b.Remove(old)
    keep.append(old)
    fp = load_fp(FPID)
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    for fname, ftype in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
        fp.GetField(ftype).SetText(c["fields"].get(fname, ""))
    fp.SetPath(pcbnew.KIID_PATH(c["sheet_tstamps"] + c["tstamps"][0]))
    fp.SetSheetname(c["sheetname"])
    fp.SetSheetfile(c["sheetfile"])
    b.b.Add(fp)
    fp.thisown = False
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(0)
    for pad in fp.Pads():
        if pad.GetNumber() == "1":
            pad.SetNet(b.net(net))
    b.log.append(f"{ref} {net}: lead pin at ({ox:.3f},{oy:.3f}) -> M4 terminal {FPID} at ({x:.3f},{y:.3f})")
b.save("fix 13: M4 ring-lug terminals (REDCUBE THR 74650074R) on 7 lead connections")
