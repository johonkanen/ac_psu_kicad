"""Converter operating points at Vin min/nom/max -> inputs.json (MAS Inputs for the transformer)."""
import json, os
import PyOpenMagnetics as p
from params import *

HERE = os.path.dirname(os.path.abspath(__file__))
WNAMES = ["Primary", "Out1", "Out2", "Bias"]

flyback = {
    "inputVoltage": {"minimum": VIN_MIN, "nominal": VIN_NOM, "maximum": VIN_MAX},
    "desiredInductance": LP,
    "desiredTurnsRatios": [NP / NS, NP / NS, NP / NB],
    "maximumDutyCycle": 0.6,
    "efficiency": ETA,
    "diodeVoltageDrop": 0.4,
    "currentRippleRatio": 0.8,
    "maximumDrainSourceVoltage": VDS_TARGET,
    "operatingPoints": [{
        "outputVoltages": [VOUT, VOUT, VBIAS],
        "outputCurrents": [IOUT, IOUT, IBIAS],
        "switchingFrequency": FSW,
        "ambientTemperature": 60,
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
    for v in (VIN_MIN, VIN_NOM, VIN_MAX):
        d, o = ops_at(v)
        dr = dr or d
        ops += o
    dr["insulation"] = {
        "insulationType": "Reinforced", "pollutionDegree": "P2", "overvoltageCategory": "OVC-II",
        "cti": "Group IIIA", "altitude": {"maximum": 2000}, "mainSupplyVoltage": {"nominal": 500, "maximum": 500},
        "standards": ["IEC 62368-1"],
    }
    dr["isolationSides"] = ["primary", "secondary", "tertiary", "primary"]
    inputs = p.process_inputs({"designRequirements": dr, "operatingPoints": ops})
    for op in inputs["operatingPoints"]:
        print(op["name"], "  ".join(f'{e["name"]}: Ipk {e["current"]["processed"]["peak"]:.3f} Irms {e["current"]["processed"]["rms"]:.3f}'
                                    for e in op["excitationsPerWinding"]))
    json.dump(inputs, open(os.path.join(HERE, "inputs.json"), "w"))
