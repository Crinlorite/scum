#!/usr/bin/env python3
"""Per-item economy from Table_TradeableDesc.json with ABSOLUTE prices.

Price model (SCUM): buy = basePurchase[ETradeCategory] * item.purchaseModifier;
sell = buy / (saleReduction[ETradeCategory] * item.saleModifier). Base/reduction
per category from EconomySpecificData.json; the ETradeCategory enum order
(name->index) comes from scum-enums.json (extracted from SCUM.exe's reflection
table). Dynamic curves (player count, durability) adjust at runtime; these are
the BASE prices (server-tunable). Names joined to items.json. Output: out/economy.json
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/tmp/scum-data/SCUM/Content/ConZ_Files"

def norm(a):
    a = a.split("/")[-1].split(".")[0]
    return re.sub(r"_C$", "", re.sub(r"_ES$", "", a)).lower()
def clean_enum(s):
    return s.split("::")[-1] if isinstance(s, str) else s

items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
idx = {}
for it in items:
    idx.setdefault(norm(it["asset"]), it)

# ETradeCategory name -> index (from SCUM.exe reflection dump)
enums = json.load(open(os.path.join(HERE, "scum-enums.json"), encoding="utf-8"))
cat_index = {k: int(v) for k, v in enums["ETradeCategory"]["by_name"].items()}

# base price + sale reduction per category index (from EconomySpecificData)
eco = json.load(open(os.path.join(DATA, "Economy", "EconomySpecificData.json"), encoding="utf-8"))
ep = (eco[0] if isinstance(eco, list) else eco).get("Properties", {})
def arr(prefix):
    out, i = [], 0
    while True:
        k = prefix if i == 0 else f"{prefix}[{i}]"
        if k in ep: out.append(ep[k]); i += 1
        else: break
    return out
base_purchase = arr("BasePriceModifierPerTradeCategory")
sale_reduction = arr("BaseSalePriceReductionModifierPerTradeCategory")

d = json.load(open(os.path.join(DATA, "Economy", "Table_TradeableDesc.json"), encoding="utf-8"))
rows = (d[0] if isinstance(d, list) else d).get("Rows", {})

out, named, priced = [], 0, 0
for key, r in rows.items():
    ap = (r.get("TradeableClass") or {}).get("AssetPathName", "")
    asset = ap.split("/")[-1].split(".")[0] if ap else key
    it = idx.get(norm(ap or key))
    name = dict(it["name"]) if it else {}
    if not name:
        cap = r.get("TradingEntryCaption") or {}
        if cap.get("SourceString"): name = {"en": cap["SourceString"]}
    if name: named += 1

    cat = clean_enum(r.get("TradeCategory"))
    ci = cat_index.get(cat)
    pmod = r.get("BasePurchasePriceModifier") or 1.0
    smod = r.get("BaseSalePriceReductionModifier") or 1.0
    buy = sell = None
    if ci is not None and ci < len(base_purchase):
        buy = round(base_purchase[ci] * pmod)
        red = (sale_reduction[ci] if ci < len(sale_reduction) else 1.0) * smod
        sell = round(buy / red) if red else None
        priced += 1

    out.append({
        "asset": asset, "slug": it["slug"] if it else None, "name": name,
        "category": cat, "traders": [clean_enum(t) for t in (r.get("TraderTypes") or [])],
        "canBuy": r.get("CanBePurchasedByPlayer"), "canSell": r.get("CanBeSoldByPlayer"),
        "buyPrice": buy, "sellPrice": sell, "currency": clean_enum(r.get("PurchaseCurrencyType")),
        "requiredFame": r.get("RequiredFamePoints"),
        "purchaseModifier": pmod, "saleModifier": smod,
    })

out.sort(key=lambda x: (x["category"] or "", x["asset"]))
json.dump(out, open(os.path.join(HERE, "out", "economy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} tradeables | con nombre: {named} | en catálogo: {sum(1 for x in out if x['slug'])} | CON PRECIO: {priced}", file=sys.stderr)
