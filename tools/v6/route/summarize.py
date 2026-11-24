#!/usr/bin/env python3
"""Per-step table of a chain run (stdlib): from the chain's console log and reports/v6/pass1/NN_name.check.

  python3 tools/v6/route/summarize.py CHAIN_LOG      -> markdown table on stdout
"""
import os
import re
import sys

L = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "reports", "v6", "pass1")
log = open(sys.argv[1]).read().splitlines()
rows, cur = [], None
for line in log:
    m = re.match(r"== (\d\d) (\S+)", line)
    if m:
        cur = {"n": m.group(1), "name": m.group(2), "time": "", "note": []}
        rows.append(cur)
        continue
    if cur is None:
        continue
    m = re.match(r"\s+(\d+) s$", line)
    if m:
        cur["time"] = m.group(1)
    if "TIMED OUT" in line:
        cur["note"].append("timed out")
    if "router failed" in line:
        cur["note"].append("router failed")
    m = re.search(r"not routed: (.*)", line)
    if m:
        nets = re.findall(r"'net(?:_name)?': '([^']+)'", m.group(1))
        cur["note"].append("open: " + ", ".join(sorted(set(nets)))[:120])
    for k in ("taps drawn", "west: drawn", "replayed", "planes: ", "j11:", "length"):
        if line.startswith(("sdm:", "west:", "sense:", "planes:", "j11:")) and k in line and "all" in line or \
                (k in ("west: drawn", "taps drawn", "j11:") and k in line):
            cur["note"].append(line.split(": ", 1)[1][:120])
print("| Step | Time s | Unconnected after | Copper DRC errors | Islands | Notes |")
print("|---|---|---|---|---|---|")
for r in rows:
    chk = os.path.join(L, f"{r['n']}_{r['name']}.check")
    unc = cop = isl = ""
    if os.path.exists(chk):
        t = open(chk).read()
        m = re.search(r"unconnected (\d+)", t)
        unc = m.group(1) if m else ""
        m = re.search(r"copper errors (\d+)", t)
        cop = m.group(1) if m else ""
        isl = "WORSE: " + "; ".join(re.findall(r"WORSE\s+(\S+)", t)) if "WORSE" in t else "none worse"
    print(f"| {r['n']} {r['name']} | {r['time']} | {unc} | {cop} | {isl} | {'; '.join(dict.fromkeys(r['note']))} |")
