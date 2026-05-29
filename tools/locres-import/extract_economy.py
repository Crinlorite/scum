#!/usr/bin/env python3
"""Per-item economy from Table_TradeableDesc.json (2nd pass: flat per-item list).
Prices in SCUM are computed dynamically (modifiers + dynamic stock), so this
keeps the REAL fields (category, traders, buy/sell flags, price modifiers, fame
requirement) and does NOT invent absolute prices. Names joined to items.json.
Output: out/economy.json"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/tmp/scum-data/SCUM/Content/ConZ_Files"

def norm(a):
    a = a.split("/")[-1].split(".")[0]
    return re.sub(r"_C$", "", re.sub(r"_ES$", "", a)).lower()

items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
idx = {}
for it in items:
    idx.setdefault(norm(it["asset"]), it)

def clean_enum(s):
    return s.split("::")[-1] if isinstance(s, str) else s

d = json.load(open(os.path.join(DATA, "Economy", "Table_TradeableDesc.json"), encoding="utf-8"))
rows = (d[0] if isinstance(d, list) else d).get("Rows", {})

out, named = [], 0
for key, r in rows.items():
    ap = (r.get("TradeableClass") or {}).get("AssetPathName", "")
    asset = ap.split("/")[-1].split(".")[0] if ap else key
    it = idx.get(norm(ap or key))
    name = dict(it["name"]) if it else {}
    if not name:
        cap = r.get("TradingEntryCaption") or {}
        if cap.get("SourceString"):
            name = {"en": cap["SourceString"]}
    if name:
        named += 1
    out.append({
        "asset": asset,
        "slug": it["slug"] if it else None,
        "name": name,
        "category": clean_enum(r.get("TradeCategory")),
        "traders": [clean_enum(t) for t in (r.get("TraderTypes") or [])],
        "canBuy": r.get("CanBePurchasedByPlayer"),
        "canSell": r.get("CanBeSoldByPlayer"),
        "purchaseModifier": r.get("BasePurchasePriceModifier"),
        "saleModifier": r.get("BaseSalePriceReductionModifier"),
        "requiredFame": r.get("RequiredFamePoints"),
        "currency": clean_enum(r.get("PurchaseCurrencyType")),
    })

out.sort(key=lambda x: (x["category"] or "", x["asset"]))
json.dump(out, open(os.path.join(HERE, "out", "economy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} tradeables -> out/economy.json | con nombre: {named} | en catálogo: {sum(1 for x in out if x['slug'])}", file=sys.stderr)
