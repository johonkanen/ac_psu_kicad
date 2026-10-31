"""Wind and evaluate the v5 aux flyback transformer candidates with MKF (PyOpenMagnetics 1.7.35).

Interleaved P1 - CTRL - Out2 - P2 - Out1 - Bias. Out2 and CTRL are triple-insulated wire (TIW,
Rubadue TCA3), which carries the reinforced insulation to the primary group and between each other,
so no margin tape is needed. One 25 um tape layer between sections is mechanical only.

Reads inputs.json (run inputs.py first). `python transformer.py` evaluates all CANDIDATES and writes
magnetic.json / winding.svg for CHOSEN.
"""
import json, math, os, sys
import PyOpenMagnetics as p
from params import *

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {"coreLosses": "IGSE", "reluctance": "ZHANG", "gapReluctance": "ZHANG"}
CHOSEN = "E30"
ORDER = ["Primary", "Out1", "Out2", "CTRL", "Bias"]          # winding index order (= inputs.json)
PATTERN = [0, 3, 2, 0, 1, 4]                                 # P1, CTRL, Out2, P2, Out1, Bias
PROPORTION = [0.36, 0.14, 0.16, 0.24, 0.10]


def core_with_gap(shape, g):
    c = {"functionalDescription": {"type": "two-piece set", "shape": shape, "material": MATERIAL,
                                   "gapping": [{"type": "subtractive", "length": g}], "numberStacks": 1}}
    return p.calculate_core_data(c, False)


def gap_for(shape, coil, op, target):
    """Centre-leg gap giving `target` Lm on MKF's reluctance model (bisection; MKF's gapping solver errors out)."""
    lo, hi = 20e-6, 3e-3
    for _ in range(40):
        mid = (lo * hi) ** 0.5
        if p.calculate_inductance_from_number_turns_and_gapping(core_with_gap(shape, mid), coil, op, MODELS) > target:
            lo = mid
        else:
            hi = mid
    return hi


def wind(bobbin):
    sides = {"Primary": "primary", "Bias": "primary"}
    sides.update({o[0]: o[4] for o in OUTPUTS})
    windings = [{"name": n, "numberTurns": TURNS[n], "numberParallels": WIRES[n][1], "wire": WIRES[n][0],
                 "isolationSide": sides[n]} for n in ORDER]
    coil = {"bobbin": p.find_bobbin_by_name(bobbin), "functionalDescription": windings}
    coil = p.set_intersection_insulation(coil, TAPE, 1)
    return p.wind(coil, 1, PROPORTION, PATTERN, [[0, 0]] * len(PATTERN))


def thermal_rth(core):
    """Free-convection thermal resistance estimate R = 53 * Ve^-0.54 K/W (Ve in cm^3; Ferroxcube/McLyman
    rule of thumb for an EE set with its winding, vertical surfaces, no airflow)."""
    ve = core["processedDescription"]["effectiveParameters"]["effectiveVolume"] * 1e6
    return 53.0 * ve ** -0.54


def evaluate(name, inputs, out=print):
    shape, bobbin = CANDIDATES[name]
    coil = wind(bobbin)
    op0 = inputs["operatingPoints"][0]
    g = gap_for(shape, coil, op0, LP)
    core = core_with_gap(shape, g)
    mag = {"core": core, "coil": coil}
    eff = core["processedDescription"]["effectiveParameters"]
    lm = p.calculate_inductance_from_number_turns_and_gapping(core, coil, op0, MODELS)
    out(f"== {name}: {shape} N87, {bobbin}")
    out(f"   Ae {eff['effectiveArea']*1e6:.1f} mm2, Ve {eff['effectiveVolume']*1e9:.0f} mm3; centre gap {g*1e3:.3f} mm "
        f"for Lm {lm*1e6:.0f} uH (AL {lm/NP**2*1e9:.0f} nH); fits: {p.are_sections_and_layers_fitting(coil)}")
    out(f"   peak flux at Ipp(max) (VCST max 810 mV): {LP*IPP*0.81/0.78/(NP*eff['effectiveArea'])*1e3:.0f} mT")
    rth = thermal_rth(core)
    worst = 0.0
    for op in inputs["operatingPoints"]:
        cl = p.calculate_core_losses(core, coil, {"operatingPoints": [op], "designRequirements": inputs["designRequirements"]}, MODELS)
        wl = p.calculate_winding_losses(mag, op, T_AMB + 40)
        tot = cl["coreLosses"] + wl["windingLosses"]
        worst = max(worst, tot)
        def wsum(w):
            t = (w.get("ohmicLosses") or {}).get("losses", 0)
            for k in ("skinEffectLosses", "proximityEffectLosses"):
                t += sum(x for x in ((w.get(k) or {}).get("lossesPerHarmonic") or []) if isinstance(x, (int, float)))
            return t
        perw = " ".join(f'{w["name"]} {wsum(w):.3f}' for w in wl.get("windingLossesPerWinding") or [])
        out(f'   {op["name"]}: Bpk {cl.get("magneticFluxDensityPeak", 0)*1e3:.0f} mT  core {cl["coreLosses"]:.3f} W  '
            f'winding {wl["windingLosses"]:.3f} W  total {tot:.2f} W  -> ~{T_AMB + tot*rth:.0f} C at {T_AMB:.0f} C air '
            f'(Rth ~{rth:.0f} K/W)  [{perw}]')
    return mag, worst


def report(mag, inputs, out=print):
    core, coil = mag["core"], mag["coil"]
    for ref, n in enumerate(ORDER[:4]):
        lk = p.calculate_leakage_inductance(mag, 80e3, ref)
        out(f"   leakage ref {n:7}:", [round(x["nominal"] * 1e6, 2) for x in lk["leakageInductancePerWinding"]], "uH")
    out("   layers (inner -> outer):")
    for l in coil["layersDescription"]:
        n = sum(1 for t in coil["turnsDescription"] if t["layer"] == l["name"]) if l["type"] == "conduction" else ""
        out(f'     {l["name"][:46]:46} {l["type"]:10} t {l["dimensions"][0]*1e3:.3f} w {l["dimensions"][1]*1e3:5.2f} mm {n}')
    ins = p.calculate_insulation(inputs)
    out("   insulation requirement (MKF, IEC 62368-1 reinforced, 500 V, PD2, OVC II, IIIa): "
        + str({k: v for k, v in ins.items() if v}))


if __name__ == "__main__":
    p.load_databases({})
    s = p.get_settings(); s["coilEqualizeMargins"] = False; p.set_settings(s)
    inputs = json.load(open(os.path.join(HERE, "inputs.json")))
    names = sys.argv[1:] or list(CANDIDATES)
    lines = []
    def out(*a):
        t = " ".join(str(x) for x in a); print(t); lines.append(t)
    out("params:"); out(summary())
    result = {}
    for n in names:
        try:
            result[n] = evaluate(n, inputs, out)
        except Exception as e:
            out(f"== {n}: MKF error {e}")
    if CHOSEN in result:
        mag = result[CHOSEN][0]
        out(f"== chosen {CHOSEN}: leakage and build")
        report(mag, inputs, out)
        json.dump(mag, open(os.path.join(HERE, "magnetic.json"), "w"))
        svg = p.plot_turns(mag)
        open(os.path.join(HERE, "winding.svg"), "w").write(svg if isinstance(svg, str) else (svg.get("svg") or svg.get("data")))
    if not sys.argv[1:]:
        open(os.path.join(HERE, "report.txt"), "w").write("\n".join(lines) + "\n")
