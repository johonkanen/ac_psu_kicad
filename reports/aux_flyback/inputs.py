"""Converter operating points at Vin 100 / 300 / 450 V -> inputs.json (MAS Inputs for the transformer).
Full design load (params.OUTPUTS) at the full-load frequency of the UCC28710 (FM region at VCST(max))."""
import json, os
import PyOpenMagnetics as p
from params import *

HERE = os.path.dirname(os.path.abspath(__file__))
WNAMES = ["Primary"] + [o[0] for o in OUTPUTS]
POUT = sum(v * i for _, v, i, _, _ in OUTPUTS)
F_FULL = POUT / (0.5 * LP * IPP ** 2 * ETA_XFMR)

flyback = {
    "inputVoltage": {"minimum": VIN_MIN, "nominal": VIN_MID, "maximum": VIN_MAX},
    "desiredInductance": LP,
    "desiredTurnsRatios": [NP / TURNS[o[0]] for o in OUTPUTS],
    "maximumDutyCycle": 0.6,
    "efficiency": ETA,
    "diodeVoltageDrop": 0.6,
    "currentRippleRatio": 1.0,
    "maximumDrainSourceVoltage": VDS_PK,
    "operatingPoints": [{
        "outputVoltages": [o[1] for o in OUTPUTS],
        "outputCurrents": [o[2] for o in OUTPUTS],
        "switchingFrequency": F_FULL,
        "ambientTemperature": T_AMB,
    }],
}


def ops_at(vin):
    """process_converter only emits the nominal point, so run it once per input voltage."""
    spec = json.loads(json.dumps(flyback))
    spec["inputVoltage"] = {"minimum": vin, "nominal": vin, "maximum": vin}
    proc = p.process_converter("flyback", spec, False)
    for op in proc["operatingPoints"]:
        op["name"] = f"Vin {vin:.0f} V"
        for e, n in zip(op["excitationsPerWinding"], WNAMES):
            e["name"] = n
    return proc["designRequirements"], proc["operatingPoints"]


if __name__ == "__main__":
    p.load_databases({})
    dr, ops = None, []
    for v in (VIN_MIN, VIN_MID, VIN_MAX):
        d, o = ops_at(v)
        dr = dr or d
        ops += o
    dr["insulation"] = {
        "insulationType": "Reinforced", "pollutionDegree": "P2", "overvoltageCategory": "OVC-II",
        "cti": "Group IIIA", "altitude": {"maximum": 2000}, "mainSupplyVoltage": {"nominal": 500, "maximum": 500},
        "standards": ["IEC 62368-1"],
    }
    dr["isolationSides"] = [s for s in ["primary"] + [o[4] for o in OUTPUTS]]
    inputs = p.process_inputs({"designRequirements": dr, "operatingPoints": ops})
    print(f"design load {POUT:.1f} W at {F_FULL/1e3:.1f} kHz")
    for op in inputs["operatingPoints"]:
        print(op["name"], "  ".join(f'{e["name"]}: Ipk {e["current"]["processed"]["peak"]:.2f} Irms {e["current"]["processed"]["rms"]:.2f}'
                                    for e in op["excitationsPerWinding"]))
    json.dump(inputs, open(os.path.join(HERE, "inputs.json"), "w"))
