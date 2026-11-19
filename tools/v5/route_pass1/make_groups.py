#!/usr/bin/env python3
"""Net groups of the first routing pass from reports/v5_layout/routing_list.md (stdlib only).

Writes tools/v5/route_pass1/groups.json (read by routing.json "groups_file") and hv_clearances.json (the
high-voltage aux nets at 2.5 mm, passed to the router as --net-clearances).

  python3 tools/v5/route_pass1/make_groups.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SECT = {"1": "sdm", "2": "taps", "3": "pwm", "4": "j11", "5": "ctrl_analog", "6": "buck", "7": "primary", "8a": "aux",
        "8": "iso_supply", "9": "other"}
# nets that are a plane in the card area or a supply rail: routed last, as supply stubs
SUPPLY = {"3V3_CTRL", "CTRLGND_A", "CTRLGND", "5V_CTRL", "3V3_ISO", "ISOGND", "GND", "VCC",
          "15V_ISO", "5V_ISOL", "15V", "5V_CTRL_A"}
WIRES = {"ISODC+", "ISOPGND"}          # off-board wire links: stay open
HV = ["AUX_DRAIN", "AUX_CLAMP", "AUX_VIN", "DC+", "AUX_ST1", "AUX_ST2", "AUX_LV1", "AUX_LV2"]
# nets that pass north of J11 (x 40..59, y 51.1..55): one step, In3 / In4 only there
PASSAGE = ["INU_ADCLK", "MDATA_INU", "PWM_Q5", "PWM_Q7", "PWM_TRANS6", "GPIO_BYPASS_RLY_ISO",
           "Net-(U2-+)", "Net-(U2--)", "Net-(U7A-+)", "Net-(U7A--)", "Net-(U7B-+)", "Net-(U7B--)"]


J11_TOP = ["ISOADA3_CTRL", "ISOADA2_CTRL", "ISOADA1_CTRL", "MDATA_ISO", "ADCLK_ISO", "GPIO_BYPASS_RLY_ISOLATED",
           "ADASEL2_ISO", "ADASEL1_ISO", "ADASEL0_ISO", "SDATA1_ISO", "CS1_ISO", "CLK1_ISO", "PWM_TRANS1_ISO",
           "PWM_TRANS2_ISO", "PWM_TRANS3_ISO", "PWM_G4_ISO", "PWM_G2_ISO", "PWM_G1_ISO", "PWM_G3_ISO",
           "DAB_PWM_PRI_HI_ISO", "DAB_PWM_PRI_LO_ISO"]


def main():
    groups, dom, sec = {}, {}, None
    for line in open(os.path.join(ROOT, "reports", "v5_layout", "routing_list.md")):
        m = re.match(r"## (\w+)\. ", line)
        if m:
            sec = SECT.get(m.group(1))
            continue
        m = re.match(r"\| (\S+) \| ([PICE]) \| (\d+) \|", line)
        if m and sec:
            net = m.group(1)
            dom[net] = m.group(2)
            if net in WIRES:
                continue
            groups.setdefault("supply_" + m.group(2) if net in SUPPLY else sec, []).append(net)
    groups["passage"] = PASSAGE
    for g in ("sdm", "taps", "pwm"):
        groups[g + "_rest"] = [n for n in groups[g] if n not in PASSAGE]
    # J11 fan-out to the top-side isolators U15 / U13 / U16: planar on F.Cu when routed in pin order (J11 pin n in
    # y order goes to the isolator pins in x order), innermost first; the three filter nets at pins 1 / 3 / 4 first
    groups["j11_top"] = J11_TOP
    groups["j11_bot"] = [n for n in groups["j11"] if n not in J11_TOP]
    groups["aux_hv"] = [n for n in groups["aux"] if n in HV]
    groups["aux_lv"] = [n for n in groups["aux"] if n not in HV and dom[n] == "P"]
    groups["aux_iso"] = [n for n in groups["aux"] if dom[n] == "I"]
    groups["hv"] = HV
    groups["signals"] = sorted({n for g, v in groups.items() if not g.startswith("supply") for n in v})
    groups["supply"] = sorted({n for g, v in groups.items() if g.startswith("supply") for n in v})
    json.dump(groups, open(os.path.join(HERE, "groups.json"), "w"), indent=1)
    json.dump({n: 2.5 for n in HV}, open(os.path.join(HERE, "hv_clearances.json"), "w"), indent=1)
    # for the step that routes the HV nets themselves: every other net at 2.5 mm, HV to HV at 1.0 mm (the chain
    # nodes and the pads of R98 / D12 / D13 are placed 1.0 .. 2.0 mm apart, so 2.5 mm between two HV nets cannot hold)
    pro = json.load(open(os.path.join(ROOT, "kicad", "ac_psu.kicad_pro")))
    allnets = [p["pattern"] for p in pro["net_settings"]["netclass_patterns"]]
    json.dump({n: (1.0 if n in HV else 2.5) for n in allnets}, open(os.path.join(HERE, "hv_step_clearances.json"), "w"), indent=1)
    json.dump(dom, open(os.path.join(HERE, "net_domains.json"), "w"), indent=1, sort_keys=True)
    for g, v in groups.items():
        print(f"{g:14s} {len(v):3d}  {' '.join(v)[:150]}")


main()
