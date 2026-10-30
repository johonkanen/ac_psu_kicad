import json, sys, re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
d = json.load(open(sys.argv[1])); nets = d["nets"]; refs = d["refs"]
def draw(ax, rx, layers, color, alpha, z, label=None):
    first = True
    for n, ls in nets.items():
        if not re.search(rx, n): continue
        for L, rings in ls.items():
            if L not in layers: continue
            for r in rings:
                ax.add_patch(Polygon(r, closed=True, fc=color, ec="none", alpha=alpha, zorder=z,
                                     label=label if first else None)); first = False
def fig(name, x0, x1, y0, y1, specs, title, labels=()):
    f, ax = plt.subplots(figsize=(12, 12 * (y1 - y0) / (x1 - x0) + 0.8), dpi=110)
    for rx, layers, color, alpha, z, lab in specs: draw(ax, rx, layers, color, alpha, z, lab)
    for r in labels:
        if r in refs: x, y = refs[r]; ax.annotate(r, (x, y), fontsize=8, ha="center", zorder=20, color="k",
                                                  bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.7, lw=0))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=10); ax.legend(loc="upper left", fontsize=7, framealpha=0.9)
    ax.set_xlabel("x (mm, IPC frame)"); ax.set_ylabel("y (mm)")
    f.tight_layout(); f.savefig(sys.argv[2] + "/" + name, dpi=110); plt.close(f)
ALL = ("F", "In1", "In2", "B")
TAP = r"^Net-\((U(1|7)[AB]|U2|U14)-[+-]\)$|^Net-\(R(2|5)-Pad1\)$"
SW = r"^(G1_SOURCE_HI|G3_SOURCE_HI|DAB_SOURCE_HI_PRI|DAB_SOURCE_HI_SEC|Q5_S|Q7_S|/07 Auxiliary supply/AUX_SWITCH_NODE|/01 afe/SHUNT1_FORCE|Net-\(J7-Pad1\))$"
GATE = r"(_GATE_|^Q[5-8]_G$)"
fig("01_overview_taps.png", -130, 120, -85, 75,
    [(r"^(GND|PGND)$", ("In1",), "#bbbbbb", 0.5, 1, "GND/PGND In1"), (r"^ISOGND$", ("In1",), "#c8d8c8", 0.5, 1, "ISOGND In1"),
     (SW, ALL, "red", 0.6, 3, "switch nodes (all layers)"), (GATE, ALL, "orange", 0.8, 4, "gate drive (all layers)"),
     (TAP, ALL, "blue", 1.0, 6, "diff-amp input/tap nodes (91k/10k)")],
    "Overview: diff-amp input nodes (blue) vs switch nodes (red) and gate drive (orange)",
    ("U1", "U7", "U14", "U2", "J1", "J2", "J3", "J4", "J6", "J8", "J11", "R96", "R97", "U4", "U5", "U6", "Q1", "Q5", "Q7", "Q9", "Q11"))
fig("02_inverter_U7_U2_In2.png", 0, 100, 25, 75,
    [(r"^3V3_ISO$", ("In2",), "#e0d8f0", 0.6, 1, "3V3_ISO In2 plane"),
     (SW, ALL, "red", 0.6, 3, "switch nodes"), (GATE, ALL, "orange", 0.9, 4, "gate drive"),
     (r"^Net-\((U7[AB]|U2)-[+-]\)$", ALL, "blue", 1.0, 6, "U7A/U7B/U2 input nodes")],
    "VSI side: U7A/U7B/U2 input nodes (In2 runs) crossing the J8/J6 gate and source traces at y = 50.6",
    ("U7", "U2", "J8", "J6", "Q5", "Q6", "Q7", "Q8", "U4", "R91", "R97"))
fig("03_afe_side_U1_U14.png", -10, 75, -30, 15,
    [(r"^GND$", ("In1",), "#bbbbbb", 0.6, 1, "GND In1 plane"), (r"^VCC$", ("In2",), "#f0e0c0", 0.4, 1, "VCC In2"),
     (r"^PGND$", ALL, "#996633", 0.5, 2, "PGND"),
     (r"^Net-\(U1[AB]-[+-]\)$|^Net-\(U14-[+-]\)$|^Net-\(R(2|5)-Pad1\)$", ALL, "blue", 1.0, 6, "U1/U14 input + chain nodes"),
     (r"^REF_1V65$", ALL, "magenta", 1.0, 7, "REF_1V65 (no capacitor)"), (r"^ADA[1-3]$", ALL, "green", 1.0, 7, "ADA1-3")],
    "Primary side: U1 (mains/filter voltage), U14 (DC+), REF_1V65, ADA lines; R96 = GND-PGND link",
    ("U1", "U14", "U11", "U12", "AD1", "R96", "REF1", "R7", "R21", "R18", "R9", "U3"))
for nm, (x0,x1,y0,y1), labs in (("04_shunt_R48_U5.png", (-5, 20, -75, -55), ("R48","U5","C91")), ("05_shunt_R91_U4.png", (0, 25, 34, 60), ("R91","U4","C90"))):
    fig(nm, x0, x1, y0, y1,
        [(SW, ALL, "red", 0.5, 3, "switch node / force"), (r"^(SHUNT[12]|INU_SHUNT[12])$", ALL, "blue", 1.0, 6, "shunt sense nets"),
         (r"^Net-\(U[45]-VIN[+-]\)$", ALL, "cyan", 1.0, 7, "modulator inputs")],
        "Shunt, Kelvin sense pair and modulator inputs (v4 fix 4/5 included)", labs)
print("ok")
