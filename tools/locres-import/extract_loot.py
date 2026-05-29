#!/usr/bin/env python3
"""Per-item loot (2nd pass): for each item, WHERE it spawns + rarity.
Each Data/Tables/Items/Spawning/Nodes/ILTN_<Location>.json is a loot tree whose
row keys are a gameplay-tag hierarchy; a leaf whose last tag segment matches an
item asset = that item spawning in <Location> with a Rarity. Output: out/loot.json
(per item: {asset, slug, name, spawns:[{location, rarity}]})."""
import json, os, re, glob, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
NODES = "/tmp/scum-data/SCUM/Content/ConZ_Files/Data/Tables/Items/Spawning/Nodes"

def norm(a):
    a = a.split("/")[-1].split(".")[0]
    return re.sub(r"_C$", "", re.sub(r"_ES$", "", a)).lower()

items = json.load(open(os.path.join(HERE, "..", "..", "src", "data", "items.json"), encoding="utf-8"))
idx = {}
for it in items:
    idx.setdefault(norm(it["asset"]), it)

by_item = collections.OrderedDict()
locations = set()
for fp in sorted(glob.glob(os.path.join(NODES, "ILTN_*.json"))):
    loc = re.sub(r"^ILTN_", "", os.path.basename(fp)[:-5])
    locations.add(loc)
    doc = json.load(open(fp, encoding="utf-8"))
    rows = (doc[0] if isinstance(doc, list) else doc).get("Rows", {})
    for key, r in rows.items():
        tag = r.get("Tag") or key
        leaf = tag.split(".")[-1]
        it = idx.get(norm(leaf))
        if not it:
            continue
        rarity = (r.get("Rarity") or "").split("::")[-1]
        e = by_item.setdefault(it["slug"], {"asset": leaf, "slug": it["slug"], "name": it["name"], "spawns": []})
        if not any(s["location"] == loc for s in e["spawns"]):
            e["spawns"].append({"location": loc, "rarity": rarity})

out = list(by_item.values())
for e in out:
    e["spawns"].sort(key=lambda s: s["location"])
out.sort(key=lambda e: e["slug"])
json.dump(out, open(os.path.join(HERE, "out", "loot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} items con loot -> out/loot.json | ubicaciones: {len(locations)} | total spawns: {sum(len(e['spawns']) for e in out)}", file=sys.stderr)
print("ubicaciones:", ", ".join(sorted(locations)), file=sys.stderr)
