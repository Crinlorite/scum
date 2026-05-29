#!/usr/bin/env python3
"""
Extract SCUM **crafting recipes** (ingredients -> result, tools, skill) from the
game's FModel export, joined to official multi-language names.

WHERE THE DATA LIVES (per-file, one recipe per asset):
  - Item recipes:      ConZ_Files/Items/Crafting/Recipes/Items/CR_*.json
                       (object Type "ItemCraftingRecipe"; produces an inventory Item)
  - Placeable recipes: ConZ_Files/Items/Crafting/Recipes/Placeables/**/CR_*.json
                       (object Type "PlaceableCraftingRecipe"; produces a base-building / world placeable;
                        carries its own inline localized Caption + Description)
  Each recipe file ALSO contains 0..n "CraftingMetadata_RecipeCategory" objects giving the
  in-game crafting menu category (CraftingCategoryTag.TagName, e.g. "CraftingCategory.Items.MeleeWeapons").

RECIPE SHAPE (Properties of the *CraftingRecipe object):
  Product            -> {AssetPathName} of the produced item / placeable
  ProductQuantity    -> int (default 1)
  Ingredients[]      -> each:
                          AllowedTypes[] -> references to CraftingIngredientTag's (the accepted item *group*)
                          Amount         -> per skill tier {NoSkill,Basic,Medium,Advanced,AboveAdvanced}
                          Purpose        -> Material (consumed) | Tool (required, not consumed)
  RelevantSkill      -> {ObjectName "Class'EngineeringSkill'"...}  the skill that gates / levels the recipe
  Duration           -> seconds per skill tier
  ExperienceReward / FamePointReward -> per skill tier

INGREDIENT NAMING (the hard part):
  An ingredient is a CraftingIngredientTag (a *group*, e.g. CI_Plank, CI_Group_Sticks), defined under
  ConZ_Files/Items/Crafting/Ingredients/CI_*.json. The tag is the canonical identity we always keep.
  For a human name we try, in order:
    1. tag.ClassRepresentativeCaption  -> localized group caption ("Any Stick", "Any Toolbox")  [multi-lang]
    2. tag.UIClassRepresentative       -> a representative item asset -> items.json name             [multi-lang]
    3. items.json asset match on the tag token (strip CI_/CL_, 1H_/2H_)                              [multi-lang]
    4. localization .po key lookup on the token (GameResourceNames / TradeCaptions / UI_Items / ...)  [multi-lang]
    5. humanized token (English only) as a last resort.

Localized strings come from SCUM/Content/Localization/Game/<locale>/Game.po, keyed by msgctxt
"<Namespace>,<Key>". Inline Caption/Description use {Namespace,Key} directly; string-table refs use
{TableId,Key} where the namespace is the table name without the leading "ST_" (we also fall back to a
namespace-agnostic key lookup, since SCUM keys are near-unique).

Output: out/crafting.json
Run:    python3 extract_crafting.py
"""
from __future__ import annotations
import json, os, re, sys, glob, collections

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/tmp/scum-data/SCUM/Content/ConZ_Files"
LOCRES = "/tmp/scum-locres/SCUM/Content/Localization/Game"
INGREDIENTS_DIR = os.path.join(DATA, "Items", "Crafting", "Ingredients")
RECIPES_DIR = os.path.join(DATA, "Items", "Crafting", "Recipes")

# preferred namespaces when a key exists under several (most specific / most "name-like" first)
NS_PREF = ("GameResourceNames", "TradeCaptions", "UI_Items", "Crafting", "UI_BaseBuilding", "")

# Curated tag -> items.json asset, ONLY for high-traffic CraftingIngredientTags whose name does not
# match any item asset/localization key (the tag is a gameplay tag, not an asset name). Mapping to a
# real catalog item gives full 10-language names. Each target verified present in src/data/items.json.
TAG_ITEM_ALIASES = {
    "CI_Plank": "Wooden_Plank",
    "CI_Sand_Bag": "SandBag",
    "CI_Duct_Tape": "Duct_Tape",          # may stay loc/fallback if not in catalog
    "CI_Cork": "WineCork",
    "CI_Rubber_Sheet": "Rubber_Sheet",
    "CI_Phone": "Mobile_Phone",
    "CI_Empty_Bag": "Empty_Bag",
}


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


def parse_po(path):
    """-> (by_ctxt: {"ns,key": text}, by_key: {key: {ns: text}})."""
    by_ctxt, by_key = {}, collections.defaultdict(dict)
    cur, state = {"ctxt": None}, None
    raw = {"id": "", "str": "", "ctxt": ""}

    def flush():
        if cur["ctxt"] is not None:
            txt = _unescape(raw["str"]) or _unescape(raw["id"])
            if txt and txt.strip():
                by_ctxt[cur["ctxt"]] = txt
                if "," in cur["ctxt"]:
                    ns, key = cur["ctxt"].split(",", 1)
                    by_key[key][ns] = txt

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
    return by_ctxt, by_key


def build_loc():
    """{ "ns,key": {lang:text} }  and  { key: {lang: {ns:text}} } across all languages."""
    by_ctxt = {}                                   # "ns,key" -> {lang: text}
    by_key = collections.defaultdict(dict)          # key -> {lang: {ns: text}}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(LOCRES, locale, "Game.po")
        if not os.path.exists(p):
            print(f"  WARN missing {p}", file=sys.stderr); continue
        ctxt, keyed = parse_po(p)
        for c, t in ctxt.items():
            by_ctxt.setdefault(c, {})[lang] = t
        for k, nsmap in keyed.items():
            by_key[k][lang] = nsmap
    return by_ctxt, by_key


def loc_by_ctxt(by_ctxt, ns, key):
    return dict(by_ctxt.get(f"{ns},{key}", {}))


def loc_by_key(by_key, key):
    """Resolve a localization Key across namespaces -> {lang: text}, preferring NS_PREF."""
    nsmaps = by_key.get(key)
    if not nsmaps:
        return {}
    out = {}
    for lang, nsmap in nsmaps.items():
        chosen = None
        for pref in NS_PREF:
            if pref in nsmap:
                chosen = nsmap[pref]; break
        if chosen is None:
            chosen = next(iter(nsmap.values()))
        out[lang] = chosen
    return out


# ---- localized field on a recipe / tag (handles inline {Namespace,Key} and {TableId,Key}) ----
def loc_field(field, by_ctxt, by_key):
    if not isinstance(field, dict):
        return {}
    key = field.get("Key")
    if not key:
        return {}
    # 1. inline namespace/key
    if "Namespace" in field:
        d = loc_by_ctxt(by_ctxt, field.get("Namespace", ""), key)
        if d:
            return _with_en(d, field)
    # 2. string table -> derive namespace from TableId (strip ST_), then namespace-agnostic
    if field.get("TableId"):
        ns = field["TableId"].split("/")[-1].split(".")[-1]
        ns = re.sub(r"^ST_", "", ns)
        d = loc_by_ctxt(by_ctxt, ns, key)
        if d:
            return _with_en(d, field)
    d = loc_by_key(by_key, key)
    return _with_en(d, field)


def _with_en(d, field):
    d = dict(d)
    if "en" not in d:
        src = field.get("LocalizedString") or field.get("SourceString")
        if src:
            d["en"] = src
    return d


# ---------------- item catalog (Product + representative items) ----------------
def norm_asset(a):
    a = a.split("/")[-1].split(".")[0]
    a = re.sub(r"_C$", "", a)
    a = re.sub(r"_ES$", "", a)
    return a.lower()


def build_item_index():
    items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
    idx = {}
    for it in items:
        idx.setdefault(norm_asset(it["asset"]), it)
    return idx


def resolve_product(asset_path, item_idx):
    if not asset_path:
        return None
    base = asset_path.split("/")[-1].split(".")[0]
    it = item_idx.get(norm_asset(asset_path))
    if it:
        return {"asset": base, "slug": it["slug"], "name": dict(it["name"])}
    return {"asset": base, "slug": None, "name": {"en": base.replace("_", " ")}}


# ---------------- ingredient tag index ----------------
def humanize(token):
    t = re.sub(r"^(CI_Group_|CI_|CL_)", "", token)
    t = re.sub(r"_", " ", t)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)   # CamoJacket -> Camo Jacket
    return t.strip()


def build_tag_index(by_ctxt, by_key, item_idx):
    """tag asset name -> {isGroup, name:{lang:str}, representative:{asset,slug}|None, resolution}."""
    tags = {}
    for fp in glob.glob(os.path.join(INGREDIENTS_DIR, "*.json")):
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for o in doc:
            if o.get("Type") != "CraftingIngredientTag":
                continue
            name = o.get("Name")
            p = o.get("Properties", {})
            tags[name] = _resolve_tag(name, p, by_ctxt, by_key, item_idx)
    return tags


def _resolve_tag(name, p, by_ctxt, by_key, item_idx):
    is_group = name.startswith("CI_Group_")
    rep = None
    rep_field = p.get("UIClassRepresentative")
    if isinstance(rep_field, dict) and rep_field.get("AssetPathName"):
        r = resolve_product(rep_field["AssetPathName"], item_idx)
        if r:
            rep = {"asset": r["asset"], "slug": r["slug"]}

    # 1. explicit group caption
    cap = p.get("ClassRepresentativeCaption")
    if isinstance(cap, dict) and (cap.get("Key") or cap.get("SourceString")):
        d = loc_field(cap, by_ctxt, by_key)
        if d:
            return {"isGroup": is_group, "name": d, "representative": rep, "resolution": "caption"}

    # 2. representative item name
    if rep and rep["slug"]:
        it = item_idx.get(norm_asset(rep["asset"]))
        if it:
            return {"isGroup": is_group, "name": dict(it["name"]), "representative": rep, "resolution": "representative"}

    # 3 + 4 fall through to token resolution
    return _resolve_token(name, is_group, rep, by_key, item_idx)


def _resolve_token(name, is_group, rep, by_key, item_idx):
    token = re.sub(r"^(CI_Group_|CI_|CL_)", "", name)
    n = token.lower()
    # 3a curated alias -> catalog item (full multi-language)
    alias = TAG_ITEM_ALIASES.get(name)
    if alias and norm_asset(alias) in item_idx:
        it = item_idx[norm_asset(alias)]
        return {"isGroup": is_group, "name": dict(it["name"]), "representative": rep, "resolution": "alias"}
    # 3b items.json exact / no weapon prefix
    for cand in (n, re.sub(r"^[12]h_", "", n)):
        it = item_idx.get(cand)
        if it:
            return {"isGroup": is_group, "name": dict(it["name"]), "representative": rep, "resolution": "item"}
    # 4 localization key lookups
    for key in (token, "TradeCaption_" + token, "Recipe_" + token):
        d = loc_by_key(by_key, key)
        if d:
            return {"isGroup": is_group, "name": d, "representative": rep, "resolution": "loc"}
    # 5 humanized fallback
    return {"isGroup": is_group, "name": {"en": humanize(name)}, "representative": rep, "resolution": "fallback"}


def tag_from_objectname(on):
    m = re.search(r"'([^']+)'", on or "")
    if not m:
        return None
    return m.group(1).split(":")[-1]   # strip outer if any


def tier(d):
    if not isinstance(d, dict):
        return None
    return {k: d.get(k) for k in ("NoSkill", "Basic", "Medium", "Advanced", "AboveAdvanced")}


def skill_name(rs):
    if not isinstance(rs, dict):
        return None
    m = re.search(r"'([^']+)'", rs.get("ObjectName", ""))
    s = m.group(1) if m else rs.get("ObjectName")
    return re.sub(r"Skill$", "", s) if s else None   # EngineeringSkill -> Engineering


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback).lower()).strip("-")
    return s or fallback.lower()


def parse_ingredients(arr, tag_idx):
    materials, tools = [], []
    for ing in arr or []:
        tagnames = [tag_from_objectname(at.get("ObjectName")) for at in (ing.get("AllowedTypes") or [])]
        tagnames = [t for t in tagnames if t]
        opts = []
        for tn in tagnames:
            ti = tag_idx.get(tn)
            if ti:
                opts.append({"tag": tn, "name": ti["name"], "isGroup": ti["isGroup"],
                             "resolution": ti["resolution"]})
            else:
                opts.append({"tag": tn, "name": {"en": humanize(tn)}, "isGroup": tn.startswith("CI_Group_"),
                             "resolution": "unknown-tag"})
        entry = {
            "options": opts,                       # any one of these satisfies the slot
            "amount": tier(ing.get("Amount")),
            "additionalAmount": tier(ing.get("AdditionalAmount")),
            "productQualityInfluence": ing.get("ProductQualityInfluence"),
            "returnOnUncraft": ing.get("ReturnOnUncraft"),
        }
        purpose = (ing.get("Purpose") or "").split("::")[-1]
        if purpose == "Tool":
            tools.append(entry)
        else:
            materials.append(entry)
    return materials, tools


def category_from_doc(doc):
    cats = []
    for o in doc:
        if o.get("Type") == "CraftingMetadata_RecipeCategory":
            tag = o.get("Properties", {}).get("CraftingCategoryTag", {})
            tn = tag.get("TagName") if isinstance(tag, dict) else None
            if tn:
                cats.append({"tag": tn, "priority": o.get("Properties", {}).get("DisplayPriority")})
    cats.sort(key=lambda c: (c["priority"] if c["priority"] is not None else 999))
    return cats


def main():
    by_ctxt, by_key = build_loc()
    item_idx = build_item_index()
    tag_idx = build_tag_index(by_ctxt, by_key, item_idx)
    print(f"  loc ctxt:{len(by_ctxt)} loc keys:{len(by_key)} items:{len(item_idx)} ingredient tags:{len(tag_idx)}",
          file=sys.stderr)

    files = sorted(glob.glob(os.path.join(RECIPES_DIR, "Items", "*.json")) +
                   glob.glob(os.path.join(RECIPES_DIR, "Placeables", "**", "*.json"), recursive=True))
    recipes = []
    seen_slug = collections.Counter()
    for fp in files:
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        obj = next((o for o in doc if o.get("Type") in ("ItemCraftingRecipe", "PlaceableCraftingRecipe")), None)
        if not obj:
            continue
        rtype = "placeable" if obj["Type"] == "PlaceableCraftingRecipe" else "item"
        p = obj.get("Properties", {})
        asset = obj.get("Name", os.path.basename(fp)[:-5])

        product = resolve_product((p.get("Product") or {}).get("AssetPathName"), item_idx)

        # name / description
        if rtype == "placeable":
            name = loc_field(p.get("Caption"), by_ctxt, by_key)
            description = loc_field(p.get("Description"), by_ctxt, by_key)
            if not name and product:
                name = dict(product["name"])
        else:
            name = dict(product["name"]) if product else {}
            description = {}

        materials, tools = parse_ingredients(p.get("Ingredients"), tag_idx)

        slug = slugify(name.get("en", ""), asset)
        seen_slug[slug] += 1
        if seen_slug[slug] > 1:
            slug = f"{slug}-{seen_slug[slug]}"

        recipes.append({
            "asset": asset,
            "slug": slug,
            "type": rtype,
            "name": name,
            "description": description,
            "categories": category_from_doc(doc),
            "skill": skill_name(p.get("RelevantSkill")),
            "result": product,
            "productQuantity": p.get("ProductQuantity", 1),
            "duration": tier(p.get("Duration")),
            "experienceReward": tier(p.get("ExperienceReward")),
            "famePointReward": tier(p.get("FamePointReward")),
            "isDLC": bool(p.get("IsDLC")),
            "ingredients": materials,
            "tools": tools,
        })

    recipes.sort(key=lambda r: (r["type"], r["slug"]))
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "crafting.json")
    json.dump(recipes, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- stats ----
    langs = list(LANG_TO_LOCALE)
    cov = {l: sum(1 for r in recipes if l in r["name"]) for l in langs}
    n_item = sum(1 for r in recipes if r["type"] == "item")
    n_plac = sum(1 for r in recipes if r["type"] == "placeable")
    # ingredient option resolution quality
    res = collections.Counter()
    for r in recipes:
        for slot in r["ingredients"] + r["tools"]:
            for o in slot["options"]:
                res[o["resolution"]] += 1
    with_skill = sum(1 for r in recipes if r["skill"])
    print(f"\nwrote {len(recipes)} recipes -> {out_path}", file=sys.stderr)
    print(f"  item recipes: {n_item} | placeable recipes: {n_plac} | with skill: {with_skill}", file=sys.stderr)
    print("  name coverage: " + ", ".join(f"{l}:{cov[l]}" for l in langs), file=sys.stderr)
    print("  ingredient-option name resolution: " + ", ".join(f"{k}:{v}" for k, v in res.most_common()), file=sys.stderr)


if __name__ == "__main__":
    main()
