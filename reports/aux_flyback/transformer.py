"""Wind the EE25 transformer (margin tape, interleaved P/2-S1-S2-P/2-Bias), evaluate it with MKF.

Reads inputs.json (run inputs.py first); writes magnetic.json, winding.svg and prints the report.
"""
import json, os
import PyOpenMagnetics as p
from params import *

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {"coreLosses": "IGSE", "reluctance": "ZHANG", "gapReluctance": "ZHANG"}


def core_with_gap(g):
    c = {"functionalDescription": {"type": "two-piece set", "shape": CORE_SHAPE, "material": CORE_MATERIAL,
                                   "gapping": [{"type": "subtractive", "length": g}], "numberStacks": 1}}
    return p.calculate_core_data(c, False)


def gap_for(coil, op, target):
    """Centre-leg gap giving `target` Lm on MKF's reluctance model (bisection; MKF's gapping solver errors out)."""
    lo, hi = 20e-6, 2e-3
    for _ in range(40):
        mid = (lo * hi) ** 0.5
        if p.calculate_inductance_from_number_turns_and_gapping(core_with_gap(mid), coil, op, MODELS) > target:
            lo = mid
        else:
            hi = mid
    return hi


def wind():
    windings = [
        {"name": "Primary", "numberTurns": NP, "numberParallels": 1, "wire": W_PRI, "isolationSide": "primary"},
        {"name": "Out1", "numberTurns": NS, "numberParallels": 1, "wire": W_SEC, "isolationSide": "secondary"},
        {"name": "Out2", "numberTurns": NS, "numberParallels": 1, "wire": W_SEC, "isolationSide": "tertiary"},
        {"name": "Bias", "numberTurns": NB, "numberParallels": 1, "wire": W_BIAS, "isolationSide": "primary"},
    ]
    coil = {"bobbin": p.find_bobbin_by_name(BOBBIN), "functionalDescription": windings}
    coil = p.set_intersection_insulation(coil, TAPE, 1)
    # margin pairs go per section in pattern order: P1, Out1, Out2, P2 get margins; the bias (next to P2 only) none
    return p.wind(coil, 1, [0.4, 0.2, 0.2, 0.2], [0, 1, 2, 0, 3], [[MARGIN, MARGIN]] * 4 + [[0, 0]])


def report(inputs, mag):
    core, coil = mag["core"], mag["coil"]
    op0 = inputs["operatingPoints"][0]
    lm = p.calculate_inductance_from_number_turns_and_gapping(core, coil, op0, MODELS)
    print(f"MKF Lm at the catalogue gap {CATALOGUE_GAP*1e3:.2f} mm: {lm*1e3:.3f} mH "
          f"(datasheet AL gives {LP*1e3:.3f} mH); fits: {p.are_sections_and_layers_fitting(coil)}")
    print(f"peak flux at ILIM max (datasheet AL): {LP*ILIM_MAX/(NP*51.8e-6)*1e3:.0f} mT")
    for op in inputs["operatingPoints"]:
        cl = p.calculate_core_losses(core, coil, {"operatingPoints": [op], "designRequirements": inputs["designRequirements"]}, MODELS)
        wl = p.calculate_winding_losses({"core": core, "coil": coil}, op, 80)
        print(f'  {op["name"]}: Bpk {cl.get("magneticFluxDensityPeak", 0)*1e3:.0f} mT  core {cl["coreLosses"]:.3f} W  '
              f'winding {wl["windingLosses"]:.3f} W')
    for ref in range(4):
        lk = p.calculate_leakage_inductance({"core": core, "coil": coil}, FSW, ref)
        print(f"  leakage ref {coil['functionalDescription'][ref]['name']:7}:",
              [round(x["nominal"] * 1e6, 2) for x in lk["leakageInductancePerWinding"]], "uH")
    print("layers (inner -> outer):")
    for l in coil["layersDescription"]:
        n = sum(1 for t in coil["turnsDescription"] if t["layer"] == l["name"]) if l["type"] == "conduction" else ""
        print(f'  {l["name"][:46]:46} {l["type"]:10} t {l["dimensions"][0]*1e3:.3f} w {l["dimensions"][1]*1e3:5.2f} mm {n}')
    for s in coil["sectionsDescription"]:
        if s["type"] == "conduction":
            print(f'  {s["name"]:20} margin {[round(m*1e3, 2) for m in (s.get("margin") or [0, 0])]} mm')
    ins = p.calculate_insulation(inputs)
    print("insulation requirement (IEC 62368-1 reinforced):", {k: v for k, v in ins.items() if v})


if __name__ == "__main__":
    p.load_databases({})
    s = p.get_settings(); s["coilEqualizeMargins"] = False; p.set_settings(s)   # else MKF halves the P2 margins
    inputs = json.load(open(os.path.join(HERE, "inputs.json")))
    coil = wind()
    g = gap_for(coil, inputs["operatingPoints"][0], LP)
    print(f"MKF gap for {LP*1e3:.3f} mH: {g*1e3:.3f} mm (MKF reads ~12% high vs the TDK datasheet AL)")
    mag = {"core": core_with_gap(CATALOGUE_GAP), "coil": coil}
    report(inputs, mag)
    json.dump(mag, open(os.path.join(HERE, "magnetic.json"), "w"))
    svg = p.plot_turns(mag)
    open(os.path.join(HERE, "winding.svg"), "w").write(svg if isinstance(svg, str) else (svg.get("svg") or svg.get("data")))
