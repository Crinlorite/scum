#!/usr/bin/env python3
"""
Extract SCUM **item stats** from the game's CDO (Class Default Object) export
under ConZ_Files/Items and ConZ_Files/GameResources, joined to official
multi-language names.

What a "stat" is here -------------------------------------------------------
Each gameplay item is exported by FModel as a JSON *array* of UObjects. The
Class Default Object is the object whose Name starts with "Default__" and ends
in "_C" (e.g. Default__Whiskey_ES_C). Its `Properties` carry the item's
authored values.

In this build the data is split across a PAIR of files per item:
  X.json      -> base/parent class CDO  (Default__X_C):     carries
                 _resourceTypeForConsumption (link to the food/drink resource
                 with the actual nutrients), _rarity, ShelfLife (food spoilage
                 hours), _warmth, _waterResistance, _camouflageBonus, _capacity.
  X_ES.json   -> the gameplay class CDO  (Default__X_ES_C), extends X_C:
                 Weight (mass, kg), GridInventoryRowSpan/ColumnSpan (the
                 inventory size in grid cells = slots), GridInventorySortGroup,
                 MaxHealth (durability), MaxHealthRatioAfterReachingBadQuality,
                 CanBecomeBadQuality, Caption + Description (localized text).
We MERGE the two: stat fields come from whichever CDO defines them (the _ES
one wins on conflict because it is the concrete gameplay class), the resource
link comes from the base CDO.

Food / nutrients ------------------------------------------------------------
_resourceTypeForConsumption -> a GameResource asset under
GameResources/Food/{Solids,Liquids,...}. That asset holds a
GameResourceConsumptionData object with macros (Protein, TotalFat,
TotalCarbohydrate, Sugars, Fiber, Starch, SaturatedFat), Water (hydration %),
Alcohol, every vitamin (A, C, D, E, K, B1..B12) and mineral (Calcium, Iron,
Magnesium, Phosphorus, Potassium, Sodium, Zinc, Copper, Selenium, Manganese),
plus Density and digestion timings. SCUM has NO stored "calories" field; in
game energy is derived from the macros, so we emit the macros and also a
derived `kcalPer100g` (Atwater: 4*carb + 9*fat + 4*protein) as a convenience,
flagged as derived.

Stack size ------------------------------------------------------------------
There is no authored "max stack" property on the CDO in this build (the only
`Quantity` fields are spawner min/max ranges, not stack sizes). Stacking is
driven by item tags at runtime, so we do NOT emit a stack field. Reported in
the run notes rather than invented.

Name join -------------------------------------------------------------------
The CDO Caption/Description are {Namespace,Key,SourceString} structs. The Key
is a GUID that is identical across every language's Game.po (`#. Key:` line),
so we resolve the display name/description in all 10 languages by that GUID.
We also join to src/data/items.json by normalized asset name (strip _ES/_C) to
reuse its slug + curated name where available.

Output: out/item_stats.json
Run:    python3 extract_item_stats.py [--data DIR] [--locres DIR]
"""
from __future__ import annotations
import json, os, re, sys, glob

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))

# Nutrient / consumption fields we copy verbatim from GameResourceConsumptionData.
NUTRIENT_FIELDS = [
    "Density", "Water", "Alcohol",
    "TotalCarbohydrate", "Sugars", "Starch", "Fiber",
    "TotalFat", "SaturatedFat", "Protein",
    "VitaminA", "VitaminC", "VitaminD", "VitaminE", "VitaminK",
    "VitaminB1", "VitaminB2", "VitaminB3", "VitaminB4", "VitaminB5",
    "VitaminB6", "VitaminB9", "VitaminB12",
    "Calcium", "Iron", "Magnesium", "Phosphorus", "Potassium",
    "Sodium", "Zinc", "Copper", "Selenium", "Manganese",
    "MaxMassPerSingleConsume", "DisgustAmountPerGramOfRawFood",
]


# ---------------------------------------------------------------------------
# .po parsing (join names by GUID Key, identical across languages)
# ---------------------------------------------------------------------------
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


def parse_po_by_key(path):
    """{ GUID Key -> msgstr } for one language's Game.po."""
    out = {}
    cur_key = None
    raw = {"id": "", "str": ""}
    state = None

    def flush():
        if cur_key is not None:
            txt = _unescape(raw["str"]) or _unescape(raw["id"])
            if txt and txt.strip():
                out[cur_key] = txt

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#. Key:"):
                # new entry begins at the Key comment block; flush previous
                flush()
                cur_key = line.split("\t", 1)[-1].strip()
                raw = {"id": "", "str": ""}; state = None
            elif line.startswith("msgid "):
                raw["id"] = _q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["str"] = _q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[state] += _q(line, 0)
            elif line.strip() == "":
                pass  # keep accumulating; key block persists until next "#. Key:"
    flush()
    return out


def parse_po_by_ctxt(path):
    """{ "Namespace,Key" -> msgstr } (for namespaced strings like
    GameResourceNames,Milk)."""
    out, ctxt, raw, state = {}, None, {"id": "", "str": ""}, None

    def flush():
        if ctxt is not None:
            txt = _unescape(raw["str"]) or _unescape(raw["id"])
            if txt and txt.strip():
                out[ctxt] = txt

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("msgctxt "):
                flush()
                ctxt = _q(line, 8); raw = {"id": "", "str": ""}; state = None
            elif line.startswith("msgid "):
                raw["id"] = _q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["str"] = _q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[state] += _q(line, 0)
    flush()
    return out


def build_loc_by_key(locres_root):
    """{ GUID Key -> {lang: text} } and { "Namespace,Key" -> {lang: text} }."""
    loc, loc_ctxt = {}, {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(locres_root, locale, "Game.po")
        if not os.path.exists(p):
            print(f"  WARN missing {p}", file=sys.stderr); continue
        d = parse_po_by_key(p)
        for k, v in d.items():
            loc.setdefault(k, {})[lang] = v
        for k, v in parse_po_by_ctxt(p).items():
            loc_ctxt.setdefault(k, {})[lang] = v
        print(f"  parsed {lang:5} ({locale}): {len(d)} keyed entries", file=sys.stderr)
    return loc, loc_ctxt


def loc_text_struct(field, loc, loc_ctxt=None):
    """A {Namespace,Key,SourceString} struct -> {lang: text} (10 langs).

    Item Captions are GUID-keyed (empty namespace) -> look up by Key in `loc`.
    Some GameResource names are namespaced (e.g. GameResourceNames,Milk) ->
    look up by "Namespace,Key" in `loc_ctxt`. Falls back to the source string
    so every named record has at least `en`."""
    if not isinstance(field, dict):
        return {}
    key = field.get("Key")
    ns = field.get("Namespace", "")
    out = dict(loc.get(key, {})) if key else {}
    if loc_ctxt and key:
        for lang, v in loc_ctxt.get(f"{ns},{key}", {}).items():
            out.setdefault(lang, v)
    src = field.get("SourceString") or field.get("LocalizedString")
    if "en" not in out and src and src.strip():
        out["en"] = src
    return out


# ---------------------------------------------------------------------------
# Asset / resource helpers
# ---------------------------------------------------------------------------
def norm_asset(a):
    """Path or class name -> lowercase base, suffixes _ES / _C stripped."""
    a = a.split("/")[-1]
    a = a.split(".")[0]
    a = re.sub(r"_C$", "", a)
    a = re.sub(r"_ES$", "", a)
    return a.lower()


def respath_to_file(object_path):
    """'SCUM/Content/.../AgaricusAugustus.0' -> /tmp/scum-data/SCUM/Content/.../AgaricusAugustus.json"""
    if not object_path:
        return None
    base = object_path.rsplit(".", 1)[0]  # drop trailing export index
    return os.path.join(DATA_ROOT, base + ".json")


def find_cdo(doc):
    if not isinstance(doc, list):
        return None
    for o in doc:
        nm = str(o.get("Name", ""))
        if nm.startswith("Default__") and nm.endswith("_C"):
            return o
    return None


def load_doc(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def tag_name(v):
    if isinstance(v, dict):
        return v.get("TagName")
    return v


def enum_tail(v):
    if isinstance(v, str) and "::" in v:
        return v.split("::", 1)[1]
    return v


# ---------------------------------------------------------------------------
# Resource (nutrient) resolution, cached
# ---------------------------------------------------------------------------
_RES_CACHE: dict[str, dict | None] = {}


def parse_resource_file(fp):
    """Parse a GameResource file -> {resourceAsset, resourceName(struct),
    nutrients, durations, kcalPer100gDerived}. Returns None if no nutrients
    and no localizable name (e.g. pure-water utility resources)."""
    doc = load_doc(fp)
    if not isinstance(doc, list):
        return None
    cd = next((o for o in doc if o.get("Type") == "GameResourceConsumptionData"), None)
    rname = next((o for o in doc if str(o.get("Name", "")).startswith("Default__")), None)
    res = {"resourceAsset": os.path.basename(fp)[:-5]}
    if rname:
        nm = (rname.get("Properties") or {}).get("ResourceName")
        if isinstance(nm, dict):
            res["resourceName"] = nm  # full struct for localization
    if cd:
        p = cd.get("Properties") or {}
        nutrients = {k: p[k] for k in NUTRIENT_FIELDS
                     if k in p and isinstance(p[k], (int, float))}
        res["consumptionDuration"] = tag_name(p.get("ConsumptionDuration"))
        res["digestionDuration"] = tag_name(p.get("DigestionDuration"))
        res["consumptionMethod"] = enum_tail(p.get("ConsumptionMethod"))
        res["nutrients"] = nutrients
        # Derived energy (Atwater). SCUM stores no calories field.
        carb, fat, prot = nutrients.get("TotalCarbohydrate"), nutrients.get("TotalFat"), nutrients.get("Protein")
        if any(x is not None for x in (carb, fat, prot)):
            res["kcalPer100gDerived"] = round(4 * (carb or 0) + 9 * (fat or 0) + 4 * (prot or 0), 1)
    if not res.get("nutrients") and "resourceName" not in res:
        return None
    return res


def resolve_resource(object_path):
    """Resolve a _resourceTypeForConsumption ObjectPath to a nutrients dict,
    trimmed for embedding inside an item record."""
    if not object_path:
        return None
    if object_path in _RES_CACHE:
        return _RES_CACHE[object_path]
    fp = respath_to_file(object_path)
    res = None
    if fp and os.path.exists(fp):
        full = parse_resource_file(fp)
        if full:
            res = dict(full)
            nm = res.pop("resourceName", None)
            if isinstance(nm, dict):
                res["resourceNameKey"] = nm.get("Key")
                res["resourceNameSource"] = nm.get("SourceString")
    _RES_CACHE[object_path] = res
    return res


# ---------------------------------------------------------------------------
# items.json index for slug + curated names
# ---------------------------------------------------------------------------
def build_item_index():
    p = os.path.join(HERE, "..", "..", "src", "data", "items.json")
    if not os.path.exists(p):
        return {}
    items = json.load(open(p, encoding="utf-8"))
    idx = {}
    for it in items:
        idx.setdefault(norm_asset(it["asset"]), it)
    return idx


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback).lower()).strip("-")
    return s or fallback.lower()


# ---------------------------------------------------------------------------
# Stat extraction from a (possibly merged) CDO Properties dict
# ---------------------------------------------------------------------------
def extract_stats(props):
    out = {}
    if isinstance(props.get("Weight"), (int, float)):
        out["weight"] = props["Weight"]              # kg
    rs = props.get("GridInventoryRowSpan")
    cs = props.get("GridInventoryColumnSpan")
    if isinstance(rs, int) or isinstance(cs, int):
        out["gridRows"] = rs
        out["gridColumns"] = cs
        if isinstance(rs, int) and isinstance(cs, int):
            out["gridSlots"] = rs * cs
    sg = tag_name(props.get("GridInventorySortGroup"))
    if sg:
        out["sortGroup"] = sg
    if isinstance(props.get("MaxHealth"), (int, float)):
        out["maxHealth"] = props["MaxHealth"]        # durability
    if isinstance(props.get("MaxHealthRatioAfterReachingBadQuality"), (int, float)):
        out["maxHealthRatioAfterBadQuality"] = props["MaxHealthRatioAfterReachingBadQuality"]
    if "CanBecomeBadQuality" in props:
        out["canBecomeBadQuality"] = props["CanBecomeBadQuality"]
    if isinstance(props.get("ShelfLife"), (int, float)):
        out["shelfLife"] = props["ShelfLife"]        # food spoilage (hours)
    if "_rarity" in props:
        out["rarity"] = enum_tail(props["_rarity"])
    if isinstance(props.get("_warmth"), (int, float)):
        out["warmth"] = props["_warmth"]
    if isinstance(props.get("_waterResistance"), (int, float)):
        out["waterResistance"] = props["_waterResistance"]
    if isinstance(props.get("_camouflageBonus"), (int, float)):
        out["camouflageBonus"] = props["_camouflageBonus"]
    if isinstance(props.get("_capacity"), (int, float)):
        out["capacity"] = props["_capacity"]
    if isinstance(props.get("_damageOverTime"), (int, float)):
        out["damageOverTime"] = props["_damageOverTime"]
    return out


# ---------------------------------------------------------------------------
def main():
    global DATA_ROOT
    args = sys.argv[1:]
    DATA_ROOT = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    dump_root = os.path.join(DATA_ROOT, "SCUM", "Content", "ConZ_Files")
    locres = args[args.index("--locres") + 1] if "--locres" in args else \
        "/tmp/scum-locres/SCUM/Content/Localization/Game"

    loc, loc_ctxt = build_loc_by_key(locres)
    item_idx = build_item_index()
    print(f"  loc keys: {len(loc)} | ctxt keys: {len(loc_ctxt)} | items.json index: {len(item_idx)}", file=sys.stderr)

    # 1) Index every CDO-bearing file under Items/ (the gameplay items).
    items_root = os.path.join(dump_root, "Items")
    all_files = glob.glob(os.path.join(items_root, "**", "*.json"), recursive=True)

    file_cdo: dict[str, dict] = {}  # filepath -> (cdo_name, props)
    for fp in all_files:
        doc = load_doc(fp)
        cdo = find_cdo(doc)
        if not cdo:
            continue
        file_cdo[fp] = {"name": cdo.get("Name"), "props": cdo.get("Properties") or {}}

    # 2) Group base + _ES siblings.
    groups: dict[str, dict] = {}
    for fp, info in file_cdo.items():
        base_name = os.path.basename(fp)[:-5]            # strip .json
        is_es = base_name.endswith("_ES")
        stem_fp = fp[:-len("_ES.json")] if is_es else fp[:-len(".json")]  # path w/o suffix+ext
        g = groups.setdefault(stem_fp, {"es": None, "base": None})
        if is_es:
            g["es"] = (fp, info)
        else:
            g["base"] = (fp, info)

    records = []
    seen_slug: dict[str, int] = {}

    for stem_fp, g in groups.items():
        es = g["es"]
        base = g["base"]
        # The stat-carrying CDO: prefer _ES; require it to have authored gameplay
        # values (Weight/Caption/grid). Skip pure scaffolding.
        primary = es or base
        if not primary:
            continue
        # Merge props: start from base, overlay es (es is the concrete class).
        merged = {}
        if base:
            merged.update(base[1]["props"])
        if es:
            merged.update(es[1]["props"])

        # Resource link lives on the base CDO (or merged if base absent).
        res_link = None
        if base and "_resourceTypeForConsumption" in base[1]["props"]:
            res_link = base[1]["props"]["_resourceTypeForConsumption"]
        elif "_resourceTypeForConsumption" in merged:
            res_link = merged["_resourceTypeForConsumption"]

        stats = extract_stats(merged)
        caption = merged.get("Caption")
        description = merged.get("Description")
        food = resolve_resource(res_link.get("ObjectPath")) if isinstance(res_link, dict) else None

        # An item record is worth keeping if it has any stat, a name, or food data.
        if not stats and not isinstance(caption, dict) and not food:
            continue

        # Asset identity: prefer the _ES file's asset name (matches items.json),
        # falling back to the base name.
        asset_fp = es[0] if es else base[0]
        asset = os.path.basename(asset_fp)[:-5]          # e.g. Whiskey_ES
        norm = norm_asset(asset)
        cat_rel = os.path.relpath(asset_fp, dump_root)
        top = cat_rel.split(os.sep)[0]                   # Items | GameResources
        category = cat_rel.split(os.sep)[1] if len(cat_rel.split(os.sep)) > 2 else top

        # Names: from CDO Caption (10 langs by GUID), enriched/falling back to items.json.
        name = loc_text_struct(caption, loc, loc_ctxt)
        desc = loc_text_struct(description, loc, loc_ctxt)
        cat_item = item_idx.get(norm)
        if cat_item:
            # items.json names are curated/official; union them in (don't overwrite CDO).
            for lang, v in (cat_item.get("name") or {}).items():
                name.setdefault(lang, v)
            slug = cat_item["slug"]
        else:
            slug = slugify(name.get("en", ""), norm)
            if slug in seen_slug:
                seen_slug[slug] += 1
                slug = f"{slug}-{seen_slug[slug]}"
            else:
                seen_slug[slug] = 1

        rec = {
            "asset": asset,
            "norm": norm,
            "slug": slug,
            "source": top,                # Items or GameResources
            "category": category,
            "inCatalog": cat_item is not None,
            "name": name,
            "description": desc,
            "stats": stats,
        }
        if food:
            rec["food"] = food
        records.append(rec)

    # 3) Standalone GameResources consumption data (liquids like beer/milk/soft
    #    drinks, raw fish/meat, water variants) that no item links via
    #    _resourceTypeForConsumption. These are consumed from containers/sources
    #    at runtime, so their nutrients would otherwise be lost.
    linked = {os.path.basename(respath_to_file(op))[:-5]
              for op in _RES_CACHE if _RES_CACHE.get(op)}
    gr_files = glob.glob(os.path.join(dump_root, "GameResources", "**", "*.json"), recursive=True)
    gr_added = 0
    for fp in gr_files:
        asset = os.path.basename(fp)[:-5]
        if asset in linked:
            continue  # already embedded in an item record
        res = parse_resource_file(fp)
        if not res or not res.get("nutrients"):
            continue  # only keep resources that carry actual nutrient values
        nm = res.pop("resourceName", None)
        name = loc_text_struct(nm, loc, loc_ctxt) if isinstance(nm, dict) else {}
        norm = norm_asset(asset)
        cat_rel = os.path.relpath(fp, dump_root)
        parts = cat_rel.split(os.sep)
        category = parts[1] if len(parts) > 2 else parts[0]
        slug = slugify(name.get("en", ""), norm)
        if slug in seen_slug:
            seen_slug[slug] += 1; slug = f"{slug}-{seen_slug[slug]}"
        else:
            seen_slug[slug] = 1
        records.append({
            "asset": asset,
            "norm": norm,
            "slug": slug,
            "source": "GameResources",
            "category": category,
            "inCatalog": False,
            "name": name,
            "description": {},
            "stats": {},
            "food": res,
        })
        gr_added += 1

    records.sort(key=lambda r: (r["source"], r["category"], r["slug"]))

    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "item_stats.json")
    json.dump(records, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- stats ----
    langs = list(LANG_TO_LOCALE)
    named = [r for r in records if r["name"]]
    cov = {l: sum(1 for r in records if l in r["name"]) for l in langs}
    with_weight = sum(1 for r in records if "weight" in r["stats"])
    with_grid = sum(1 for r in records if "gridSlots" in r["stats"])
    with_dur = sum(1 for r in records if "maxHealth" in r["stats"])
    with_food = sum(1 for r in records if "food" in r)
    in_cat = sum(1 for r in records if r["inCatalog"])
    n_gr = sum(1 for r in records if r["source"] == "GameResources")
    print(f"\nwrote {len(records)} item-stat records -> {out_path}", file=sys.stderr)
    print(f"  named: {len(named)} | joined to items.json: {in_cat} | standalone GameResources: {n_gr}", file=sys.stderr)
    print(f"  weight: {with_weight} | grid/slots: {with_grid} | durability: {with_dur} | food: {with_food}", file=sys.stderr)
    print("  name coverage per language:", file=sys.stderr)
    for l in langs:
        print(f"    {l:5}: {cov[l]:4}/{len(records)}", file=sys.stderr)


if __name__ == "__main__":
    main()
