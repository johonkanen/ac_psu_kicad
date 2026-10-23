"""Search the JLCPCB parts library for the ac_psu small parts; writes results.json."""
import json, re, sys, time, urllib.request
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(kw, n=50):
    req = urllib.request.Request(URL, data=json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for _ in range(3):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            return (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
        except Exception as e:
            err = e; time.sleep(2)
    print("ERR", kw, err, file=sys.stderr); return []

norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())

# (refs, qty, comment, kicad footprint short, query, package, must-tokens in describe | mpn prefix)
R = lambda v: (f"{v}Ω",)
ITEMS = [
 # resistors
 ("R1,R8,R17,R21,R37,R38,R46,R51,R52,R53,R76", "10k", "0402", R("10k")),
 ("R7", "1k", "0402", R("1k")), ("R9,R18", "100R", "0402", R("100")),
 ("R19,R32", "420R", "0402", R("420")), ("R22", "39R", "0402", R("39")),
 ("R30,R40", "820R", "0402", R("820")), ("R39,R54,R56,R77", "8.2k", "0402", R("8.2k")),
 ("R50,R55,R72", "33R", "0402", R("33")), ("R86", "10R", "0402", R("10")),
 ("R57,R58,R73,R74,R92,R93", "12.4R", "0402", R("12.4")),  # v4 (picked C477607 Yageo RC0402FR-0712R4L by hand)
 ("R25", "15k", "0603", R("15k")), ("R29", "1.2k", "0603", R("1.2k")), ("R31", "1k", "0603", R("1k")),
 ("R44", "39k", "0603", R("39k")), ("R78,R88,R89,R90", "2.2k", "0603", R("2.2k")),
 ("R59,R75,R94", "470R", "0805", R("470")),
 ("R2,R3,R4,R5,R6,R11,R12,R13,R14,R15,R16,R27,R28,R35,R36,R41,R42,R60,R61,R62,R63,R65,R66,R67,R68,R69,R70,R71,R80,R81,R82,R83,R84,R85,R95,R256", "91k", "1206", R("91k")),
 ("R24,R33,R34,R43", "1M", "1206", R("1M")), ("R96,R97", "0R", "1206", R("0")),
 ("R23", "100R", "1206", R("100")), ("R45,R47", "2.49R", "1206", R("2.49")), ("R49", "12.1k", "1206", R("12.1k")),
 # capacitors
 ("C2,C9,C42,C88,C89", "1nF", "0402", ("1nF",)),
 ("C3,C4,C17,C18,C26,C27,C37,C38,C56,C64,C69,C70,C80,C81,C82,C83,C84,C85,C86,C87", "100nF", "0402", ("100nF",)),
 ("C5,C6,C16,C39,C40", "1uF", "0402", ("1uF",)),
 ("C43,C44,C55,C71,C73,C76,C77,C78", "100nF", "0603", ("100nF",)),
 ("C51,C52,C53,C54,C74,C75", "220pF", "0603", ("220pF",)),
 ("C90,C91,C92", "100nF C0G", "1206", ("100nF",)),  # v4: only 1206 NP0 stocked (C170182 1206N104J500CT) ("C63", "22pF", "0603", ("22pF",)),
 ("C36,C41,C65,C66", "4.7uF", "1206", ("4.7uF",)), ("C57,C58", "22uF", "1206", ("22uF",)),
 ("C62", "470pF", "1206", ("470pF",)), ("C67", "100uF", "1206", ("100uF",)), ("C68", "100nF", "1206", ("100nF",)),
 ("C1,C35,C45,C46,C47,C48,C49,C50", "2.2uF", "2220", ("2.2uF",)),
 ("L1", "22uH", "0805", ("22uH",)),
 # MPN parts
 ("C15,C28", "EEE-FTE221XAP", None, "mpn"), ("D1,D2", "ES1A", "SMA", "mpn"), ("D6", "S1M", "SMA", "mpn"),
 ("D3,D4,D5,D7,D10", "ZLLS400TA", None, "mpn"), ("D8,D9", "MM3Z5V1T1G", None, "mpn"),
 ("Q13,Q14", "2N7002", "SOT-23", "mpn"), ("REF1,REF2", "REF3025AIDBZR", None, "mpn"),
 ("AD1", "ADS7056IRUGR", None, "mpn"), ("U1,U7", "OPA2353EA", None, "mpn"),
 ("U2,U12,U14", "TLV316IDBVR", None, "mpn"), ("U3,U10", "TPS73033DBVR", None, "mpn"),
 ("U4,U5,U6", "ADUM7701-8BRIZ", None, "mpn"), ("U11", "SN74LV4051APWR", None, "mpn"),
 ("U13,U15,U17", "SI8661BD-B-IS", None, "mpn"), ("U16", "SI8660BD-B-IS", None, "mpn"),
 ("R48,R64,R91", "FKK5R0020FE", None, "mpn"), ("PWM1", "IW1830", None, "mpn"),
]

out = []
for refs, val, pkg, how in ITEMS:
    qty = len(refs.split(","))
    if how == "mpn":
        lst = search(val)
        cand = [c for c in lst if norm(c["componentModelEn"]).startswith(norm(val))]
        if pkg: cand = [c for c in cand if pkg.upper() in (c.get("componentSpecificationEn") or "").upper()] or cand
    else:
        kind = "Resistor" if val[-1] in "kMR" or val.endswith("R") else ""
        lst = search(f"{how[0]} {pkg}", 100)
        cand = [c for c in lst if (c.get("componentSpecificationEn") or "").startswith(pkg)
                and re.search(r"(^|\s)" + re.escape(how[0]) + r"(\s|$)", c.get("describe") or "")]
        if how[0].endswith("Ω"):
            cand = [c for c in cand if "Resistor" in (c.get("componentTypeEn") or "") and "Array" not in c.get("componentTypeEn","")]
        else:
            cand = [c for c in cand if "Resistor" not in (c.get("componentTypeEn") or "")]
    cand.sort(key=lambda c: (c["componentLibraryType"] != "base", not c.get("preferredComponentFlag"), -(c["stockCount"] or 0)))
    pick = [{k: c.get(k) for k in ("componentCode", "componentModelEn", "componentBrandEn", "componentSpecificationEn",
             "componentLibraryType", "preferredComponentFlag", "stockCount", "describe")} for c in cand[:4]]
    out.append({"refs": refs, "qty": qty, "value": val, "pkg": pkg, "cands": pick})
    best = pick[0] if pick else None
    print(f"{qty:3} {val:16} {pkg or '':7}", (f"{best['componentCode']:9} {best['componentLibraryType']:6} stock {best['stockCount']:>9}  {best['componentModelEn']}  | {best['describe'][:90]}" if best else "-- NOT FOUND"))
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
