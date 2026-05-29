#!/usr/bin/env python3
"""
Extract SCUM **cooking recipes** from the game's DataTables export
(Cooking/Recipes/Cook_*.json), joined to official multi-language names.

Real game data (FModel export of the .pak DataTables). Each recipe gives:
name, description, category, cooking time/temperature, main + optional
ingredient slots (each slot = a localized title + a list of accepted items),
and the resulting food.

Multi-language joins:
  - recipe name / description / ingredient titles  → looked up by their
    (Namespace, Key) in every language's Game.po  (namespace-keyed entries).
  - ingredient / result ITEMS  → matched by asset name to src/data/items.json
    (which already carries the official name in all 10 languages).

Inputs:
  --data   FModel export root   (default /tmp/scum-data)
  --locres .po root             (default /tmp/scum-locres/SCUM/Content/Localization/Game)
Output: out/recipes.json
"""
from __future__ import annotations
import json, os, re, sys, glob

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))


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
    """msgctxt ("Namespace,Key") -> msgstr."""
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
            continue
        for ctxt, txt in parse_po_by_ctxt(p).items():
            if txt and txt.strip():
                loc.setdefault(ctxt, {})[lang] = txt
    return loc


def loc_text(loc, ns, key, fallback_en):
    d = dict(loc.get(f"{ns},{key}", {}))
    if "en" not in d and fallback_en:
        d["en"] = fallback_en
    return d


def norm_asset(a):
    a = a.split("/")[-1].split(".")[0]          # path -> asset basename
    a = re.sub(r"_C$", "", a)
    a = re.sub(r"_ES$", "", a)
    return a.lower()


def build_item_index():
    items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
    idx = {}
    for it in items:
        idx.setdefault(norm_asset(it["asset"]), it)
    return idx


def resolve_item(asset_path, item_idx):
    if not asset_path:
        return None
    key = norm_asset(asset_path)
    it = item_idx.get(key)
    base = asset_path.split("/")[-1].split(".")[0]
    if it:
        return {"asset": base, "slug": it["slug"], "name": it["name"]}
    return {"asset": base, "slug": None, "name": {"en": base.replace("_", " ")}}


def loc_field(field, loc):
    """A recipe localized field: {Namespace,Key,SourceString} -> {lang:text}."""
    if not isinstance(field, dict):
        return {}
    return loc_text(loc, field.get("Namespace", ""), field.get("Key", ""), field.get("SourceString"))


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback).lower()).strip("-")
    return s or fallback.lower()


def ingredient_slots(arr, loc, item_idx):
    out = []
    for slot in arr or []:
        title = loc_field(slot.get("IngredientTitle"), loc)
        opts = []
        for opt in slot.get("PossibleIngredient", []) or []:
            it = (opt.get("Item") or {}).get("AssetPathName")
            r = resolve_item(it, item_idx)
            if r:
                r["usage"] = opt.get("Usage")
                r["liters"] = opt.get("Liters")
                opts.append(r)
        out.append({"title": title, "options": opts})
    return out


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    locres = args[args.index("--locres") + 1] if "--locres" in args else "/tmp/scum-locres/SCUM/Content/Localization/Game"

    loc = build_loc(locres)
    item_idx = build_item_index()
    print(f"  loc keys: {len(loc)} | item index: {len(item_idx)}", file=sys.stderr)

    files = sorted(glob.glob(os.path.join(data, "**", "Cooking", "Recipes", "Cook_*.json"), recursive=True))
    recipes = []
    for fp in files:
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        obj = next((o for o in doc if o.get("Type") == "CookingRecipe"), None) if isinstance(doc, list) else None
        if not obj:
            continue
        p = obj.get("Properties", {})
        if "RecipeName" not in p:
            continue
        name = loc_field(p.get("RecipeName"), loc)
        if not name:
            continue
        asset = obj.get("Name", os.path.basename(fp)[:-5])
        rf = p.get("ResultingFood")
        result_path = (rf.get("Item") or {}).get("AssetPathName") if isinstance(rf, dict) else None
        result = resolve_item(result_path, item_idx)
        cat = p.get("Category")
        category = cat[0].split(".")[-1] if isinstance(cat, list) and cat else None
        utility = [u.split(".")[-1] for u in (p.get("Utility") or []) if isinstance(u, str)]
        recipes.append({
            "asset": asset,
            "slug": slugify(name.get("en", ""), asset),
            "name": name,
            "description": loc_field(p.get("Description"), loc),
            "category": category,
            "utility": utility,
            "cookingTime": p.get("CookingTime"),
            "cookingTemperature": p.get("CookingTemperature"),
            "mainIngredients": ingredient_slots(p.get("MainIngredients"), loc, item_idx),
            "optionalIngredients": ingredient_slots(p.get("OptionalIngredients"), loc, item_idx),
            "result": result,
        })

    recipes.sort(key=lambda r: r["slug"])
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    json.dump(recipes, open(os.path.join(out_dir, "recipes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # stats
    langs = list(LANG_TO_LOCALE)
    cov = {l: sum(1 for r in recipes if l in r["name"]) for l in langs}
    resolved = sum(1 for r in recipes for s in r["mainIngredients"] for o in s["options"] if o["slug"])
    total_opts = sum(1 for r in recipes for s in r["mainIngredients"] for o in s["options"])
    print(f"\nwrote {len(recipes)} recipes -> out/recipes.json", file=sys.stderr)
    print(f"name coverage: " + ", ".join(f"{l}:{cov[l]}" for l in langs), file=sys.stderr)
    print(f"main-ingredient items resolved to catalog: {resolved}/{total_opts}", file=sys.stderr)


if __name__ == "__main__":
    main()
