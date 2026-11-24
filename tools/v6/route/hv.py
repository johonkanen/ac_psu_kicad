"""High-voltage nets of the v6 board (mains, DC buses, aux flyback, and the side-1 nets of the floating
modulators U4 / U5, which sit at a line-frequency node since v6 step 1): 2.5 mm from every other net on a layer
(V5_LAYOUT_PLAN.md section 3, V6_PLAN.md section 4). Short net names (domains.short)."""
HV = {
    "CMFILT1", "CMFILT2", "FILTER_INPUT", "JEE", "LEMOUT", "AFE_RELAY", "INDUCTOR_OUTPUT", "INU_FILTER_INPUT",
    "AC_IN2", "AC_IN_1", "AC_OUT_1", "AC_OUT_2", "AFE_CHOKE1", "INU_CHOKE", "DC+", "ISODC+",
    "AUX_DRAIN", "AUX_CLAMP", "AUX_VIN", "AUX_ST1", "AUX_ST2", "AUX_LV1", "AUX_LV2",
    # U5 side 1 (floats on SHUNT1 = the AFE filter node) and U4 side 1 (on INU_SHUNT2 = the inverter output)
    "SHUNT1", "SHUNT2", "Net-(U5-VIN+)", "Net-(U5-VIN-)", "SDM_RAW_VOLTAGE", "Net-(D8-K)",
    "INU_SHUNT1", "INU_SHUNT2", "Net-(U4-VIN+)", "Net-(U4-VIN-)", "ISO_AFE_SDM_RAW_VOLTAGE", "Net-(D9-K)",
}


def is_hv(net):
    return net.split("/")[-1] in HV
