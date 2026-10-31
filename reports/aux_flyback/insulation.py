"""IEC 60664-1 / 62368-1 / 61558-1 insulation requirements from MKF over the working voltage (the
IEC 61010-1 check in V5_PLAN.md 5.3 uses the IEC 60664-1 basis). Run: python insulation.py > insulation.txt"""
import json, sys, copy
sys.path.insert(0, ".")
import PyOpenMagnetics as p
p.load_databases({})
base = json.load(open("inputs.json"))
def run(std, typ, v, pd="P2", cti="Group IIIA", ovc="OVC-II"):
    inp = copy.deepcopy(base)
    ins = {"insulationType": typ, "pollutionDegree": pd, "overvoltageCategory": ovc, "cti": cti,
           "altitude": {"maximum": 2000}, "mainSupplyVoltage": {"nominal": v, "maximum": v}, "standards": [std]}
    inp["designRequirements"]["insulation"] = ins
    inp = p.process_inputs(inp)
    try:
        r = p.calculate_insulation(inp)
        return {k: (round(val*1e3, 2) if k != "withstandVoltage" else val) for k, val in r.items()}
    except Exception as e:
        return f"ERR {e}"
for std in ["IEC 60664-1", "IEC 62368-1", "IEC 61558-1"]:
    for v in (230, 300, 450, 500, 630, 800):
        for typ in ("Basic", "Reinforced"):
            print(std, v, typ, run(std, typ, v))
print("--- 60664-1 PD1 (impregnated) / material groups, 500 and 800 V reinforced")
for pd in ("P1", "P2"):
    for cti in ("Group I", "Group II", "Group IIIA"):
        for v in (500, 800):
            print("60664-1", pd, cti, v, run("IEC 60664-1", "Reinforced", v, pd, cti))
