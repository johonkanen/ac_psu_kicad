#!/usr/bin/env python3
"""Sheet 8 - SDM current measurements (PDF page 8): ADuM7701 modulators U5 (AFE shunt R48,
primary logic side) and U6 (DAB shunt R64, isolated side), and the DAB shunt R64 itself."""
from _common import *  # noqa: F401,F403

sh = sheet("08_sdm_current_measurements.kicad_sch")

# v6: U5 with its input filter and supply is on the AFE leg-1 power card. Its MDAT comes back on the card's CTRL
# header (sheet 2) and still passes R55 into MDATA; ADCLK goes out on the same header.
import sys as _sys
_sys.path.insert(0, os.path.join(TOOLS, "v6"))
import v6_parts as V6  # noqa: E402
part2(sh, "R", "R55", g(150), g(40), "33R", "MDAT_AFE", "MDATA", horizontal=True)
sh.text("v6: the AFE leg-1 shunt and its ADuM7701 are on the power card; MDAT_AFE = pin 10 of J21 (sheet 2).", g(56), g(52))

adum_block(sh, g(150), g(104), "U6", "ADUM7701-8BRIZ-RL7", "ISO_DAB_SDM_RAW_VOLTAGE", ("R75", "470R"),
           ("D17", V6.VALUE["D17"]), (("C76", "100n"), ("C77", "100n")),
           (("R73", "12.4R"), "DAB_SHUNT1", ("C75", "220p")), (("R74", "12.4R"), "DAB_SHUNT2", ("C74", "220p")),
           "DAB_SHUNT2", "3V3_ISO", "ISOGND", "ADCLK_DAB", ("R72", "33R"), "MDATA_DAB", ("C80", "100n"),
           note="U6 floats on the DAB shunt R64: GND1 = DAB_SHUNT2.", cdiff=("C92", "100n C0G"))

# R64 DAB shunt (Kelvin): pins 1/3 = DAB_SHUNT2 end, 2/4 = DAB_SHUNT1 end... no: 1 = DAB_SHUNT2,
# 2 = DAB_SHUNT1, 3 = ISOPGND, 4 = DAB_GROUND (IPC). Force path 3 -> 4 (ISOPGND -> DAB_GROUND),
# sense taps 1 (top) and 2 (bottom) go to the U6 inputs.
SX, SY = g(60), g(150)
r64 = sh.place("FKK5R0020FE-TR", "R64", SX, SY, value="FKK5R0020FE-TR",
               ref_at=(SX - g(3), SY - 1.27, 0, "right"), value_at=(SX - g(3), SY + 1.27, 0, "right"))
p1, p2, p3, p4 = r64.pin(1), r64.pin(2), r64.pin(3), r64.pin(4)
sh.wire(p1, up(p1, 2)); sh.glabel("DAB_SHUNT2", *up(p1, 2), 90)
sh.wire(p2, down(p2, 2)); sh.glabel("DAB_SHUNT1", *down(p2, 2), 270)
sh.wire(p3, right(p3, 16)); power_at(sh, "ISOPGND", right(p3, 16), "up")
sh.wire(p4, right(p4, 16)); power_at(sh, "DAB_GROUND", right(p4, 16), "down")
# ISOPGND and DAB_GROUND are only joined through this shunt: flag both here
sh.pwr_flag(*right(p3, 6), rot=0); sh.junction(*right(p3, 6))
sh.pwr_flag(*right(p4, 6), rot=180); sh.junction(*right(p4, 6))
sh.text("R64: 2 mOhm Kelvin shunt between ISOPGND and the DAB secondary ground DAB_GROUND (DC- terminal J42 of the DAB secondary card).",
        SX + g(6), SY + g(10))
# v6: U6 side 1 is fed from 15V_ISO (was pin 25 of the DAB secondary gate card): R257 + R75 drop, D17 clamps to 5.1 V
part2(sh, "R", "R257", g(40), g(84), V6.VALUE["R257"], "15V_ISO", "ISO_DAB_SDM_RAW_VOLTAGE", horizontal=True)
sh.text("v6: U6 VDD1 = 5.1 V (D17) from 15V_ISO through R257 + R75: 11.5 .. 13.8 mA at 15 .. 17 V.", g(20), g(78))
sh.save()
print("sheet08: written")
