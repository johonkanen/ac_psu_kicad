#!/usr/bin/env python3
"""KiCad position file (kicad-cli pcb export pos --format csv --units mm) -> JLCPCB CPL for the
parts in fab/jlc_bom.csv.

  python3 fab/make_cpl.py POS.csv OUT.csv

Columns Designator, Mid X, Mid Y, Layer, Rotation. Coordinates are KiCad's (bottom side not
mirrored, as JLC expects). Rotation: KiCad's angle plus a per-package correction for JLC's
reel orientation (top: + corr, bottom: - corr). The corrections are the usual KiCad -> JLC
values for these library footprints; JLC's placement preview is the final check (every part,
both sides) before the order is confirmed.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORR = [  # (package regex, degrees)
    (r"^SOT-23", 180),                       # SOT-23, SOT-23-5 (also the Proteus-numbered SOT-23)
    (r"^SOIC-", 270), (r"^TSSOP-", 270),
    (r"^X2QFN|^Texas_UQFN", 270),
    (r"^D_SMA", 180), (r"^D_SOD-323", 180),
    (r"^CP_Elec", 180),
]


def corr(pkg):
    return next((d for rx, d in CORR if re.search(rx, pkg)), 0)


def main(pos, out):
    want = {d.strip() for r in csv.DictReader(open(os.path.join(HERE, "jlc_bom.csv"))) for d in r["Designator"].split(",")}
    rows, seen = [], set()
    for r in csv.DictReader(open(pos)):
        ref = r["Ref"]
        if ref not in want:
            continue
        seen.add(ref)
        side = r["Side"].strip().lower()
        c = corr(r["Package"])
        rot = (float(r["Rot"]) + (c if side == "top" else -c)) % 360
        rows.append([ref, f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                     "Top" if side == "top" else "Bottom", f"{rot:g}"])
    missing = sorted(want - seen)
    if missing:
        sys.exit(f"make_cpl: BOM parts not in the position file: {' '.join(missing)}")
    rows.sort(key=lambda r: (re.sub(r"\d", "", r[0]), int(re.sub(r"\D", "", r[0]) or 0)))
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(rows)
    print(f"make_cpl: {len(rows)} parts ({sum(r[3] == 'Top' for r in rows)} top, "
          f"{sum(r[3] == 'Bottom' for r in rows)} bottom) -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
