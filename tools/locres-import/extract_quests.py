#!/usr/bin/env python3
"""Extract SCUM quests/missions (Quests/QuestData/<Trader>/T<n>/<Type>/*.json).
Each file has a QuestSetup: trader, tier (fame gate), localized title/description,
rewards (fame, currency, unlocked trade deals/items), time limit, and objective
conditions (with map locations). Names joined to items.json + .po. Output: out/quests.json"""
import json, os, re, glob, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
QDIR = "/tmp/scum-data/SCUM/Content/ConZ_Files/Quests/QuestData"
LOCRES = "/tmp/scum-locres/SCUM/Content/Localization/Game"
LANG_TO_LOCALE = {"es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant", "th": "th-TH", "pl": "pl-PL"}

def _q(line, p):
    b = line[p:].strip()
    return b[1:-1] if len(b) >= 2 and b[0] == '"' and b[-1] == '"' else b
def _unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(s[i+1], s[i+1])); i += 2
        else: out.append(s[i]); i += 1
    return "".join(out)

def build_loc_by_key():
    """{ bareKey: {lang: text} }  (quest keys are unique names)."""
    loc = {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(LOCRES, locale, "Game.po")
        if not os.path.exists(p): continue
        key, msg, state = None, "", None
        for line in open(p, encoding="utf-8-sig"):
            line = line.rstrip("\n")
            if line.startswith("#. Key:"): key = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgstr "): msg = _q(line, 7); state = "s"
            elif line.startswith("msgid "): state = "i"
            elif line.startswith('"') and state == "s": msg += _q(line, 0)
            elif line.strip() == "":
                if key and msg: loc.setdefault(key, {})[lang] = _unescape(msg)
                key, msg, state = None, "", None
        if key and msg: loc.setdefault(key, {})[lang] = _unescape(msg)
    return loc

def norm(a): return re.sub(r"_C$", "", re.sub(r"_ES$", "", a.split("/")[-1].split(".")[0])).lower()
items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
item_idx = {}
for it in items: item_idx.setdefault(norm(it["asset"]), it)

loc = build_loc_by_key()
def lf(field):
    """Localized text field {TableId,Key,SourceString} -> {lang}."""
    if not isinstance(field, dict): return {}
    d = dict(loc.get(field.get("Key", ""), {}))
    if "en" not in d and field.get("SourceString"): d["en"] = field["SourceString"]
    return d
def item_name(ap):
    it = item_idx.get(norm(ap)) if ap and ap != "None" else None
    return {"asset": ap.split("/")[-1].split(".")[0], "name": it["name"], "slug": it["slug"]} if it else None

TRADER = {"Armorer": {"es":"Armero","en":"Armorer"}, "Doctor": {"es":"Doctor","en":"Doctor"},
    "GeneralGoods": {"es":"Bazar","en":"General Goods"}, "Hunting": {"es":"Caza","en":"Hunting"},
    "Mechanic": {"es":"Mecánico","en":"Mechanic"}}

quests = []
for fp in sorted(glob.glob(os.path.join(QDIR, "**", "*.json"), recursive=True)):
    try: doc = json.load(open(fp, encoding="utf-8"))
    except Exception: continue
    qs = next((o for o in doc if isinstance(o, dict) and o.get("Type") == "QuestSetup"), None) if isinstance(doc, list) else None
    if not qs: continue
    p = qs.get("Properties", {})
    rel = fp.split("/QuestData/")[1]
    trader = rel.split("/")[0]
    m = re.search(r"_(Fetch|Interact|Kill|Survive|Craft|Deliver)_", os.path.basename(fp))
    qtype = m.group(1) if m else "Other"
    # rewards
    rfame = rcur = 0
    rewards_items = []
    for rw in p.get("PossibleRewards", []) or []:
        rfame = max(rfame, rw.get("RewardFame") or 0)
        for c in rw.get("RewardCurrency", []) or []:
            if "Normal" in str(c.get("Key", "")): rcur = max(rcur, c.get("Value") or 0)
        for td in rw.get("RewardTradeDeals", []) or []:
            r = item_name((td.get("TradeableClass") or {}).get("AssetPathName", ""))
            if r: r["price"] = td.get("BasePurchasePrice"); rewards_items.append(r)
        for ri in rw.get("RewardItems", []) or []:
            r = item_name((ri.get("ItemClass") or ri.get("Item") or {}).get("AssetPathName", "") if isinstance(ri, dict) else "")
            if r: rewards_items.append(r)
    title = lf(p.get("Title"))
    quests.append({
        "slug": re.sub(r"[^a-z0-9]+", "-", (title.get("en") or os.path.basename(fp)[:-5]).lower()).strip("-"),
        "trader": trader, "traderLabel": TRADER.get(trader, {"en": trader}),
        "tier": p.get("Tier"), "type": qtype,
        "title": title,
        "description": lf((p.get("DescriptionSegments") or [{}])[0]),
        "rewardFame": rfame, "rewardCurrency": rcur,
        "rewardItems": rewards_items,
        "timeLimitMin": round(p.get("TimeLimit") / 60) if isinstance(p.get("TimeLimit"), (int, float)) else None,
    })

quests.sort(key=lambda q: (q["trader"], q["tier"] or 0, q["slug"]))
json.dump(quests, open(os.path.join(HERE, "out", "quests.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
byT = collections.Counter(q["trader"] for q in quests)
named = sum(1 for q in quests if q["title"].get("es"))
print(f"wrote {len(quests)} quests -> out/quests.json | por comerciante: {dict(byT)} | con título ES: {named}", file=sys.stderr)
