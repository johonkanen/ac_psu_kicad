#!/usr/bin/env python3
"""Stock check of every JLC code in fab/jlc_bom.csv (and the JLC codes named in fab/hand_fit.csv)
against the JLCPCB parts library; prints need vs stock and writes fab/jlc_stock_<date>.json.

  python3 fab/jlc_bom_check.py [BOARDS]      (default 1 board)
"""
import csv, datetime, json, os, re, sys, time, urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
HERE = os.path.dirname(os.path.abspath(__file__))


def lookup(code):
    req = urllib.request.Request(URL, data=json.dumps({"keyword": code, "currentPage": 1, "pageSize": 10}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for _ in range(3):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            lst = (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
            return next((c for c in lst if c["componentCode"] == code), None)
        except Exception:
            time.sleep(2)
    return None


def main():
    boards = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    items = []
    for r in csv.DictReader(open(os.path.join(HERE, "jlc_bom.csv"))):
        items.append(("bom", r["Comment"], r["Designator"], r["JLCPCB Part #"]))
    for r in csv.DictReader(open(os.path.join(HERE, "hand_fit.csv"))):
        for code in re.findall(r"\bC\d{4,}\b", r["Source"]):
            items.append(("hand", r["Comment"], r["Designator"], code))
    out, short = [], 0
    for src, comment, refs, code in items:
        need = len(refs.split(",")) * boards
        c = lookup(code)
        stock = (c or {}).get("stockCount") or 0
        ok = stock >= need
        short += src == "bom" and not ok
        out.append({"source": src, "comment": comment, "refs": refs, "code": code, "need": need, "stock": stock,
                    "type": (c or {}).get("componentLibraryType"), "mpn": (c or {}).get("componentModelEn"),
                    "describe": (c or {}).get("describe")})
        print(f"{'' if ok else '!!'}{src:4} {code:10} need {need:4} stock {stock:>9} {(c or {}).get('componentLibraryType') or '-':6} "
              f"{((c or {}).get('componentModelEn') or 'NOT FOUND')[:28]:28} {comment[:40]}")
        time.sleep(0.3)
    path = os.path.join(HERE, f"jlc_stock_{datetime.date.today().isoformat()}.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"jlc_bom_check: {len(out)} codes, {short} BOM lines short for {boards} board(s); {path}")


if __name__ == "__main__":
    main()
