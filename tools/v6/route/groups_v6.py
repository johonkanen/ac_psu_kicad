#!/usr/bin/env python3
"""v6 pass 1 net groups (routing list, reports/v6/pass1/routing_list.md) and the open count per group from a
kicad-cli DRC report (stdlib only).

  python3 tools/v6/route/groups_v6.py DRC.json        -> open connections per group, nets with opens
"""
import collections
import json
import re
import sys

GROUPS = [   # (key, title, test(short net name))
    ("bus", "DC buses and pour stitching", lambda n: n in ("DC+", "PGND", "ISODC+", "ISOPGND", "DAB_GROUND")),
    ("sense", "Current-sense groups, U29 / U30, D17 / R257 (side-1 HV nets)", lambda n: n in (
        "SHUNT1", "INU_SHUNT1", "INU_SHUNT2", "AFE_CHOKE1", "INU_CHOKE", "LEMOUT", "INDUCTOR_OUTPUT", "SDM_RAW_VOLTAGE",
        "ISO_AFE_SDM_RAW_VOLTAGE", "ISO_DAB_SDM_RAW_VOLTAGE", "Net-(U5-MDAT)", "Net-(U4-MDAT)") or
        re.fullmatch(r"Net-\((U4|U5)-VIN[+-]\)|Net-\(D(8|9|17)-K\)", n)),
    ("sdm", "Sigma-delta links (drawn)", lambda n: n in ("MDATA", "ADCLK", "MDATA_INU", "INU_ADCLK", "INU_ADCLK_U21")),
    ("supply_p", "Primary supplies and grounds (headers J21..J23, U29, U5)", lambda n: n in ("15V", "5V", "GND", "VCC")),
    ("supply_i", "ISO supplies and grounds (headers J24..J26, U30, U4, relay)", lambda n: n in ("15V_ISO", "5V_ISOL", "ISOGND", "3V3_ISO")),
    ("pwm_p", "Card PWM, primary (U13 / U15 / U16 -> J21 / J22 / J23)", lambda n: re.fullmatch(r"PWM_G\d|PWM_TRANS[123]|DAB_PWM_PRI_(HI|LO)", n)),
    ("pwm_i", "Card PWM, ISO (U19 / U20 -> J24 / J25 / J26)", lambda n: re.fullmatch(r"PWM_Q\d|PWM_TRANS[456]|DAB_PWM_(HI|LO)_SEC", n)),
    ("west_i", "ISO runs west of J11 (divider taps, relay)", lambda n: n.startswith(("Net-(U7", "Net-(U2")) or
        n in ("GPIO_BYPASS_RLY_ISO",)),
    ("logic_p", "Primary logic (ADC, reference, isolator P side)", lambda n: re.fullmatch(
        r"ADASEL\d|CLK1|CS1|SDATA1|GPIO_BYPASS_RLY|REF_1V65|ADA\d|Net-\((U11|U15|AD1|REF1)[^)]*\)", n)),
    ("logic_i", "ISO logic (U22..U24 inputs, U6, reference, DAB sense)", lambda n: re.fullmatch(
        r"ISOADA\d(_AIN)?|REF_1V65_ISO|MDATA_DAB|ADCLK_DAB|DAB_SHUNT\d|SHUNT2|Net-\((U6|REF2)[^)]*\)", n)),
    ("ctrl", "CTRL area under the control card (J11 / J12 fan-outs, analog chain, buck, CTRL supplies)", lambda n:
        n.endswith(("_CTRL", "_ISO", "_ISOLATED")) or n.startswith("CTRL") or
        re.fullmatch(r"ISOADA\d_(N|P|M|PL|OUT)|OPA_SPARE|5V_CTRL_A|3V3_CTRL|5V_CTRL|CTRLGND_A|CTRLGND|ADCLK_ISO|MDATA_ISO", n)),
]


def group_of(net):
    n = net.split("/")[-1]
    for k, _, f in GROUPS:
        if f(n):
            return k
    return "other"


def main():
    d = json.load(open(sys.argv[1]))
    per = collections.Counter()
    nets = collections.defaultdict(collections.Counter)
    for v in d["unconnected_items"]:
        m = re.search(r"\[([^\]]+)\]", v["items"][0]["description"])
        net = m.group(1) if m else "?"
        g = group_of(net)
        per[g] += 1
        nets[g][net.split("/")[-1]] += 1
    titles = {k: t for k, t, _ in GROUPS}
    titles["other"] = "other"
    print(f"total {sum(per.values())}")
    for k in [g[0] for g in GROUPS] + ["other"]:
        if per[k]:
            print(f"{per[k]:4}  {titles[k]}: " + ", ".join(f"{n} {c}" for n, c in sorted(nets[k].items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
