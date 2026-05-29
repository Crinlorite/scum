#!/usr/bin/env python3
"""
Extract the SCUM **economy / trader** domain from the game's DataTable export
(ConZ_Files/Economy/Table_TradeableDesc.json), joined to official multi-language
item names.

Real game data (FModel export of the .pak DataTables). The single DataTable
`Table_TradeableDesc` has 2815 Rows, one per tradeable. Each row tells us:

  - which ITEM it is             -> TradeableClass.AssetPathName  (joined to
                                    src/data/items.json by asset basename, giving
                                    the official name in all 10 site languages)
  - a localized TRADING CAPTION  -> TradingEntryCaption {Namespace,Key,...}
                                    (joined to every language's Game.po by
                                    "Namespace,Key"; this is the name the trader
                                    UI shows, sometimes differing from the item's
                                    own caption — e.g. "Trainer Shoes" for the
                                    HighTop_Shoes item)
  - which TRADERS sell/buy it    -> TraderTypes  (ETraderType::GeneralGoods, ...)
  - buy/sell availability        -> CanBePurchasedByPlayer / CanBeSoldByPlayer
  - per-item PRICE MODIFIERS     -> BasePurchasePriceModifier (multiplies the
                                    purchase base) and BaseSalePriceReductionModifier
  - trade category               -> TradeCategory (ETradeCategory::Pants, ...)
  - fame gate, stock limits, currency, DLC, etc.

ABSOLUTE PRICES — IMPORTANT CAVEAT
----------------------------------
The rows do NOT carry an absolute base price. SCUM derives the base price from
`EconomySpecificData.BasePriceModifierPerTradeCategory[idx]` (a per-trade-category
base) scaled by the per-item `BasePurchasePriceModifier`. The mapping from the
TradeCategory *enum name* (ETradeCategory::Pants) to the numeric *array index*
[idx] is defined in C++ headers that are NOT present in this asset dump, so it
cannot be resolved deterministically. We therefore:
  * emit each item's authoritative per-item modifiers verbatim,
  * emit the full EconomySpecificData per-category base table under
    `categoryBasePrices` (keyed by raw index) as a reference, and
  * flag the unresolved enum->index mapping in the output `_meta.notes`.
We do NOT fabricate computed absolute prices.

Inputs:
  --data    FModel export root  (default /tmp/scum-data)
  --locres  .po root            (default /tmp/scum-locres/SCUM/Content/Localization/Game)
Output: out/economy.json
"""
from __future__ import annotations
import json, os, re, sys

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- .po parsing
def _unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(s[i + 1], s[i + 1])); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def _q(line, p):
    b = line[p:].strip()
    return b[1:-1] if len(b) >= 2 and b[0] == '"' and b[-1] == '"' else b


def parse_po_by_ctxt(path):
    """msgctxt ("Namespace,Key") -> msgstr (falling back to msgid)."""
    out, cur, state, raw = {}, {"ctxt": None}, None, {"id": "", "str": "", "ctxt": ""}

    def flush():
        if cur["ctxt"] is not None:
            out[cur["ctxt"]] = _unescape(raw["str"]) or _unescape(raw["id"])

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("msgctxt "):
                raw = {"id": "", "str": "", "ctxt": _q(line, 8)}; cur = {"ctxt": raw["ctxt"]}; state = "ctxt"
            elif line.startswith("msgid "):
                raw["id"] = _q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["str"] = _q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[state] += _q(line, 0)
            elif line.strip() == "":
                if cur["ctxt"] is not None:
                    flush(); cur, state, raw = {"ctxt": None}, None, {"id": "", "str": "", "ctxt": ""}
    if cur["ctxt"] is not None:
        flush()
    return out


def build_loc(locres_root):
    """{ "Namespace,Key": {lang: text} }"""
    loc = {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(locres_root, locale, "Game.po")
        if not os.path.exists(p):
            print(f"  WARN missing {p}", file=sys.stderr); continue
        for ctxt, txt in parse_po_by_ctxt(p).items():
            if txt and txt.strip():
                loc.setdefault(ctxt, {})[lang] = txt
    return loc


def loc_field(field, loc):
    """A localized field {Namespace,Key,SourceString} -> {lang:text} (+en fallback)."""
    if not isinstance(field, dict):
        return {}
    ns, key = field.get("Namespace", ""), field.get("Key", "")
    d = dict(loc.get(f"{ns},{key}", {})) if (ns or key) else {}
    if "en" not in d and field.get("SourceString"):
        d["en"] = field["SourceString"]
    return d


# ---------------------------------------------------------------- item join
def norm_asset(a):
    a = a.split("/")[-1].split(".")[0]
    a = re.sub(r"_C$", "", a)
    a = re.sub(r"_ES$", "", a)
    return a.lower()


def build_item_index():
    p = os.path.join(HERE, "..", "..", "src", "data", "items.json")
    items = json.load(open(p, encoding="utf-8"))
    idx = {}
    for it in items:
        idx.setdefault(norm_asset(it["asset"]), it)
    return idx


def resolve_item(asset_path, item_idx):
    if not asset_path:
        return None
    base = asset_path.split("/")[-1].split(".")[0]
    it = item_idx.get(norm_asset(asset_path))
    if it:
        return {"asset": base, "slug": it["slug"], "name": it["name"], "category": it.get("category")}
    return {"asset": base, "slug": None, "name": {}, "category": None}


# ---------------------------------------------------------------- helpers
def enum_tail(v):
    """ETraderType::GeneralGoods -> GeneralGoods ; passthrough otherwise."""
    if isinstance(v, str) and "::" in v:
        return v.split("::", 1)[1]
    return v


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback or "").lower()).strip("-")
    return s or (fallback or "").lower()


def category_base_prices(data_root):
    """Read EconomySpecificData.BasePriceModifierPerTradeCategory[idx] and the
    sale-reduction counterpart, keyed by raw numeric index (0..27)."""
    p = os.path.join(data_root, "SCUM", "Content", "ConZ_Files", "Economy", "EconomySpecificData.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(open(p, encoding="utf-8"))
    props = doc[0].get("Properties", {}) if isinstance(doc, list) and doc else {}

    def collect(prefix):
        out = {}
        for k, v in props.items():
            if k == prefix:
                out["0"] = v
            else:
                m = re.fullmatch(re.escape(prefix) + r"\[(\d+)\]", k)
                if m:
                    out[m.group(1)] = v
        return out

    purchase = collect("BasePriceModifierPerTradeCategory")
    sale = collect("BaseSalePriceReductionModifierPerTradeCategory")
    idxs = sorted(set(purchase) | set(sale), key=lambda x: int(x))
    return {i: {"purchaseBase": purchase.get(i), "saleReductionBase": sale.get(i)} for i in idxs}


# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    locres = args[args.index("--locres") + 1] if "--locres" in args \
        else "/tmp/scum-locres/SCUM/Content/Localization/Game"

    loc = build_loc(locres)
    item_idx = build_item_index()
    cat_base = category_base_prices(data)
    print(f"  loc keys: {len(loc)} | item index: {len(item_idx)} | category base entries: {len(cat_base)}",
          file=sys.stderr)

    table = os.path.join(data, "SCUM", "Content", "ConZ_Files", "Economy", "Table_TradeableDesc.json")
    doc = json.load(open(table, encoding="utf-8"))
    obj = next((o for o in doc if o.get("Type") == "DataTable" and "Rows" in o), None) if isinstance(doc, list) else None
    if not obj:
        print("ERROR: no DataTable with Rows in Table_TradeableDesc.json", file=sys.stderr)
        sys.exit(1)
    rows = obj["Rows"]

    tradeables = []
    for row_key, r in rows.items():
        tc = r.get("TradeableClass") or {}
        asset_path = tc.get("AssetPathName")
        item = resolve_item(asset_path, item_idx)

        caption = loc_field(r.get("TradingEntryCaption"), loc)

        # Name: prefer the official item name (catalog), fall back to the
        # localized trading caption, per language.
        name = {}
        item_name = item["name"] if item else {}
        for lang in LANG_TO_LOCALE:
            v = item_name.get(lang) or caption.get(lang)
            if v and v.strip():
                name[lang] = v

        traders = [enum_tail(t) for t in (r.get("TraderTypes") or [])]
        trade_category = enum_tail(r.get("TradeCategory"))

        fame_group = r.get("TradeableFamePointPenaltyGroup") or {}
        rarity = r.get("TradeableRotationRarity") or {}

        tradeables.append({
            "rowKey": row_key,
            "asset": item["asset"] if item else (asset_path or "").split("/")[-1].split(".")[0],
            "slug": item["slug"] if (item and item["slug"]) else
                    slugify(name.get("en", ""), (asset_path or row_key).split("/")[-1].split(".")[0]),
            "matchedCatalog": bool(item and item["slug"]),
            "assetPath": asset_path,
            "itemCategory": item["category"] if item else None,
            "name": name,
            "tradingCaption": caption,
            "tradeCategory": trade_category,
            "traders": traders,
            "canBePurchasedByPlayer": r.get("CanBePurchasedByPlayer"),
            "canBeSoldByPlayer": r.get("CanBeSoldByPlayer"),
            "purchasePriceModifier": r.get("BasePurchasePriceModifier"),
            "salePriceReductionModifier": r.get("BaseSalePriceReductionModifier"),
            "purchaseCurrency": enum_tail(r.get("PurchaseCurrencyType")),
            "alternateCurrencyPurchasePrice": r.get("AlternateCurrencyPurchasePrice"),
            "requiredFamePoints": r.get("RequiredFamePoints"),
            "maxAmountPurchasedAtOnce": r.get("MaxAmountPurchasedAtOnce"),
            "isStockAmountUnlimited": r.get("IsStockAmountUnlimited"),
            "customStockAmountMin": r.get("CustomStockAmountMin"),
            "customStockAmountMax": r.get("CustomStockAmountMax"),
            "onlyAvailableAfterPlayerSale": r.get("OnlyAvailableAfterPlayerSale"),
            "spawnType": enum_tail(r.get("SpawnType")),
            "famePenaltyGroup": fame_group.get("TagName") if fame_group.get("TagName") != "None" else None,
            "rotationRarity": rarity.get("TagName") if rarity.get("TagName") != "None" else None,
            "requiredDLC": enum_tail(r.get("RequiredDLC")),
        })

    tradeables.sort(key=lambda t: (t["tradeCategory"] or "", t["slug"] or "", t["rowKey"]))

    payload = {
        "_meta": {
            "domain": "economy",
            "source": "ConZ_Files/Economy/Table_TradeableDesc.json",
            "rowCount": len(tradeables),
            "notes": (
                "Per-item fields are taken verbatim from the DataTable. "
                "purchasePriceModifier / salePriceReductionModifier are MULTIPLIERS, "
                "not absolute prices: SCUM multiplies them by a per-trade-category base "
                "(EconomySpecificData.BasePriceModifierPerTradeCategory[idx]). The enum "
                "ETradeCategory::X -> numeric index [idx] mapping lives in C++ headers not "
                "present in this dump, so absolute prices are NOT computed here. "
                "categoryBasePrices below is keyed by the raw numeric index for reference."
            ),
            "categoryBasePrices": cat_base,
        },
        "tradeables": tradeables,
    }

    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "economy.json")
    json.dump(payload, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- stats
    langs = list(LANG_TO_LOCALE)
    cov = {l: sum(1 for t in tradeables if l in t["name"]) for l in langs}
    matched = sum(1 for t in tradeables if t["matchedCatalog"])
    cap_any = sum(1 for t in tradeables if t["tradingCaption"])
    print(f"\nwrote {len(tradeables)} tradeables -> {out_path}", file=sys.stderr)
    print(f"matched to items.json catalog: {matched}/{len(tradeables)}", file=sys.stderr)
    print(f"rows with a localized trading caption: {cap_any}/{len(tradeables)}", file=sys.stderr)
    print("name coverage per language:", file=sys.stderr)
    for l in langs:
        print(f"  {l:5}: {cov[l]:4}/{len(tradeables)}", file=sys.stderr)


if __name__ == "__main__":
    main()
