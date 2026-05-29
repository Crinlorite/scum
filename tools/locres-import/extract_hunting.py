#!/usr/bin/env python3
"""Extract hunting spawn data per biome. Source: Hunting/BiomeData/BD_*.json →
BiomeTag + AnimalSpawnData (PackSize, clues, distances). Animal names are a small
fixed set (9), localized by hand (es/en; other langs fall back). Output: out/hunting.json."""
import json, os, re, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BDIR = "/tmp/scum-data/SCUM/Content/ConZ_Files/Hunting/BiomeData"

ANIMAL = {
    "bear": {"es": "Oso", "en": "Bear"}, "boar": {"es": "Jabalí", "en": "Boar"},
    "chicken": {"es": "Gallina", "en": "Chicken"}, "deer": {"es": "Ciervo", "en": "Deer"},
    "donkey": {"es": "Burro", "en": "Donkey"}, "goat": {"es": "Cabra", "en": "Goat"},
    "horse": {"es": "Caballo", "en": "Horse"}, "rabbit": {"es": "Conejo", "en": "Rabbit"},
    "wolf": {"es": "Lobo", "en": "Wolf"},
}
BIOME = {
    "Village": {"es": "Pueblo", "en": "Village"}, "Urban": {"es": "Urbano", "en": "Urban"},
    "Mountain": {"es": "Montaña", "en": "Mountain"}, "Mediterranean": {"es": "Mediterráneo", "en": "Mediterranean"},
    "ContinentalForest": {"es": "Bosque continental", "en": "Continental forest"},
    "ContinentalMeadow": {"es": "Pradera continental", "en": "Continental meadow"},
}

def animal_key(asset):
    return re.sub(r"\d+$", "", asset.split("/")[-1].split(".")[0].replace("BP_", "")).lower()

out = []
for fp in sorted(glob.glob(os.path.join(BDIR, "BD_*.json"))):
    doc = json.load(open(fp, encoding="utf-8"))
    P = next((o["Properties"] for o in (doc if isinstance(doc, list) else [doc])
              if isinstance(o, dict) and isinstance(o.get("Properties"), dict) and "AnimalSpawnData" in o["Properties"]), None)
    if not P:
        continue
    tag = (P.get("BiomeTag") or {}).get("TagName", "")
    biome = tag.split(".")[-1] if tag else os.path.basename(fp)[3:-5]
    for a in P["AnimalSpawnData"]:
        k = animal_key(a.get("Key", ""))
        v = a.get("Value") or {}
        out.append({
            "biome": biome,
            "biomeLabel": BIOME.get(biome, {"en": biome}),
            "animal": ANIMAL.get(k, {"en": k.title()}),
            "packMin": v.get("PackSizeMin"), "packMax": v.get("PackSizeMax"),
            "cluesMin": v.get("NumCluesMin"), "cluesMax": v.get("NumCluesMax"),
        })

os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "hunting.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
biomes = sorted(set(r["biome"] for r in out))
print(f"wrote {len(out)} biome·animal rows -> out/hunting.json | biomas: {biomes}", file=sys.stderr)
