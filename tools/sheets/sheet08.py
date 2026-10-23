#!/usr/bin/env python3
"""Sheet 8 - SDM current measurements (PDF page 8): ADuM7701 modulators U5 (AFE shunt R48,
primary logic side) and U6 (DAB shunt R64, isolated side), and the DAB shunt R64 itself."""
from _common import *  # noqa: F401,F403

sh = sheet("08_sdm_current_measurements.kicad_sch")

adum_block(sh, g(150), g(40), "U5", "ADUM7701-8BRIZ-RL7", "SDM_RAW_VOLTAGE", ("R59", "470R"),
           ("D8", "MM3Z5V1T1"), (("C71", "100n"), ("C73", "100n")),
           (("R57", "12.4R"), "SHUNT2", ("C53", "220p")), (("R58", "12.4R"), "SHUNT1", ("C52", "220p")),
           "SHUNT1", "VCC", "GND", "ADCLK", ("R55", "33R"), "MDATA", ("C64", "100n"),
           note="U5 floats on the AFE shunt R48 (sheet 1): GND1 = SHUNT1 (R48 sense pin 1), VDD1 = 5.1 V from D8 via R59.",
           cdiff=("C91", "100n C0G"))

adum_block(sh, g(150), g(104), "U6", "ADUM7701-8BRIZ-RL7", "ISO_DAB_SDM_RAW_VOLTAGE", ("R75", "470R"),
           None, (("C76", "100n"), ("C77", "100n")),
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
sh.text("R64: 2 mOhm Kelvin shunt between ISOPGND and the DAB secondary ground DAB_GROUND (J4 15-20).",
        SX + g(6), SY + g(10))
sh.save()
print("sheet08: written")
