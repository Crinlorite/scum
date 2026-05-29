#!/usr/bin/env python3
"""Extract clothing/armor protection. Source: clothing BP files (_index.json
'clothing'), Properties with underscore-prefixed gameplay fields:
  _warmth, _waterResistance, _camouflageBonus, _sharpMeleeDamageReduction,
  _bluntMeleeDamageReduction, _totalEnergyAbsorption (ballistic), _armor.
Joined to items.json by base-name norm. Output: out/clothing.json."""
import json, os, re, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ES_ROOT = "/tmp/scum-data"
ITEMS = os.path.join(HERE, "..", "..", "src", "data", "items.json")

def norm(a):
    return re.sub(r"_ES$", "", re.sub(r"_C$", "", a.split("/")[-1].split(".")[0])).lower()

items = json.load(open(ITEMS, encoding="utf-8"))
by_norm = {}
for it in items:
    by_norm.setdefault(norm(it["asset"]), it)

# Clothing lives under Items/Clothes/; glob is simpler and complete vs _index paths.
out, seen = [], set()
for fp in glob.glob(os.path.join(ES_ROOT, "SCUM/Content/ConZ_Files/Items/Clothes/**", "*.json"), recursive=True):
    if fp.endswith("_ES.json"):
        continue
    try:
        doc = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    obj = None
    for o in (doc if isinstance(doc, list) else [doc]):
        p = o.get("Properties") if isinstance(o, dict) else None
        if isinstance(p, dict) and ("_sharpMeleeDamageReduction" in p or "_warmth" in p or "_armor" in p):
            obj = o; break
    if not obj:
        continue
    P = obj["Properties"]
    base = norm(os.path.basename(fp))
    it = by_norm.get(base)
    if not it or it["slug"] in seen:
        continue

    def pct(v):  # 0-1 fraction -> integer %
        return round(v * 100) if isinstance(v, (int, float)) else None
    rec = {"slug": it["slug"]}
    if isinstance(P.get("_warmth"), (int, float)) and P["_warmth"]: rec["warmth"] = round(P["_warmth"], 2)
    if isinstance(P.get("_waterResistance"), (int, float)) and P["_waterResistance"]: rec["waterRes"] = round(P["_waterResistance"], 2)
    c = pct(P.get("_camouflageBonus"));        rec["camo"] = c if c else None
    s = pct(P.get("_sharpMeleeDamageReduction")); rec["sharp"] = s if s else None
    b = pct(P.get("_bluntMeleeDamageReduction")); rec["blunt"] = b if b else None
    if isinstance(P.get("_totalEnergyAbsorption"), (int, float)) and P["_totalEnergyAbsorption"]:
        rec["ballistic"] = round(P["_totalEnergyAbsorption"])
    if isinstance(P.get("_armor"), (int, float)) and P["_armor"]: rec["armor"] = round(P["_armor"], 2)
    rec = {k: v for k, v in rec.items() if v is not None}
    if len(rec) <= 1:  # only slug, nothing useful
        continue
    seen.add(it["slug"])
    out.append(rec)

out.sort(key=lambda r: r["slug"])
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "clothing.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} clothing/armor -> out/clothing.json", file=sys.stderr)
for k in ("warmth", "waterRes", "camo", "sharp", "blunt", "ballistic", "armor"):
    print(f"  con {k}: {sum(1 for r in out if k in r)}", file=sys.stderr)
