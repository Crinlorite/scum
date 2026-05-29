#!/usr/bin/env python3
"""
Extract the SCUM **loot** domain from the game's DataTables export.

Two data sources under Data/Tables/Items/Spawning/ :

  Nodes/ILTN_<Location>.json   -- one "Item Loot Tree Node" DataTable per loot
                                  *location type* (Bar, Barn, Police, Military,
                                  Hospital, ArmedNPCs, DeadPuppets, ...). Each
                                  table is a tree expressed as GameplayTag
                                  hierarchy in the Row *keys*, e.g.
                                    ItemLootTreeNodes.Bar
                                    ItemLootTreeNodes.Bar.Items
                                    ItemLootTreeNodes.Bar.Items.Blades
                                    ItemLootTreeNodes.Bar.Items.Blades.1H_Bushman   <- leaf
                                  Every node row carries:
                                    Rarity  (EItemRarity::Abundant..ExtremelyRare)
                                            = the spawn weight at that branch
                                    DevComment  (human label of the rarity)
                                    PostSpawnActions (e.g. cash amount on NPC money)
                                  A *leaf* (a tag that is not the prefix of any
                                  other tag) represents an actual item; its final
                                  tag segment is the item's asset/BP name and it
                                  matches a key of ItemSpawningParameters (6561/6568).

  ItemSpawningParameters.json  -- DataTable keyed by item asset name. Per item:
                                    AllowedLocations  (map of 15 location-classes
                                                       -> bool: where it may spawn)
                                    CooldownGroup, CooldownPerSquadMember,
                                    MaxOccurrences, Variations (alternate assets).

So "which items appear in which loot category/location with what probability" =
walk each location tree, and for every leaf emit
  { location, item, categoryPath, rarity (leaf), rarityChain (ancestors) }.
The per-item AllowedLocations / cooldown are attached as item metadata.

Name join to 10 languages: leaf asset -> src/data/items.json (which already
carries official names in every language). Items.json is keyed by the localized
"_ES" assets, so we normalize (strip _C/_ES, lowercase). ~81% of leaf
occurrences resolve to a catalog item; the rest (plain BP items whose caption
lives only in a runtime StringTable, not joinable by asset here) fall back to a
humanized name in English only. This is reported, not hidden.

Output: out/loot.json   (UTF-8, ensure_ascii=False)

Run:  python3 extract_loot.py [--data DIR] [--items items.json]
"""
from __future__ import annotations
import json, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
LANGS = ["es", "en", "de", "ru", "zh", "fr", "pt", "zh-tw", "th", "pl"]

# EItemRarity -> (rank 0=most common, approximate relative weight used by the game)
RARITY_INFO = {
    "EItemRarity::Abundant":       {"rank": 0, "label": "Abundant"},
    "EItemRarity::Common":         {"rank": 1, "label": "Common"},
    "EItemRarity::Uncommon":       {"rank": 2, "label": "Uncommon"},
    "EItemRarity::Rare":           {"rank": 3, "label": "Rare"},
    "EItemRarity::VeryRare":       {"rank": 4, "label": "Very Rare"},
    "EItemRarity::ExtremelyRare":  {"rank": 5, "label": "Extremely Rare"},
}


def norm_asset(a: str) -> str:
    a = a.split("/")[-1].split(".")[0]
    a = re.sub(r"_C$", "", a)
    a = re.sub(r"_ES$", "", a)
    return a.lower()


def humanize(asset: str) -> str:
    s = re.sub(r"_C$", "", asset)
    s = re.sub(r"_ES$", "", s)
    s = re.sub(r"^(BP_|1H_|2H_)", "", s)
    s = s.replace("_", " ").strip()
    return s or asset


def build_item_index(items_path: str) -> dict:
    items = json.load(open(items_path, encoding="utf-8"))
    idx = {}
    for it in items:
        idx.setdefault(norm_asset(it["asset"]), it)
    return idx


def rarity_obj(r):
    info = RARITY_INFO.get(r)
    return {
        "enum": r,
        "label": info["label"] if info else (r.split("::")[-1] if r else None),
        "rank": info["rank"] if info else None,
    }


def parse_location_tree(fp: str):
    """Return (location_name, list_of_leaf_records) for one ILTN_*.json."""
    doc = json.load(open(fp, encoding="utf-8"))
    table = next((o for o in doc if o.get("Type") == "DataTable" and "Rows" in o), None)
    if not table:
        return None, []
    rows = table["Rows"]
    tags = set(rows.keys())

    location = os.path.basename(fp)[len("ILTN_"):-len(".json")]
    # tag prefix shared by all rows, e.g. "ItemLootTreeNodes.Bar"
    root = min(tags, key=len) if tags else ""

    def is_branch(t):  # has children -> not a leaf
        pre = t + "."
        return any(o.startswith(pre) for o in tags)

    leaves = []
    for t in tags:
        if is_branch(t):
            continue
        segs = t.split(".")
        # ancestor chain (every existing tag that is a prefix of this leaf),
        # ordered shallow->deep, excluding the leaf itself
        ancestors = []
        for i in range(2, len(segs)):  # skip "ItemLootTreeNodes" + location root
            anc_tag = ".".join(segs[:i])
            if anc_tag in rows:
                ancestors.append(anc_tag)
        # category path = the segment names between the location root and the leaf
        # e.g. Bar.Items.Blades.1H_Bushman -> ["Items","Blades"]
        cat_path = []
        root_segs = root.split(".")
        leaf_body = segs[len(root_segs):-1] if len(segs) > len(root_segs) else []
        cat_path = leaf_body

        leaf_asset = segs[-1]
        leaf_row = rows[t]
        post = [a.get("AssetPathName", "").split("/")[-1].split(".")[0]
                for a in (leaf_row.get("PostSpawnActions") or []) if a.get("AssetPathName")]
        leaves.append({
            "asset": leaf_asset,
            "tag": t,
            "categoryPath": cat_path,
            "rarity": rarity_obj(leaf_row.get("Rarity")),
            "rarityChain": [rarity_obj(rows[a].get("Rarity")) for a in ancestors],
            "categoryTags": ancestors,
            "postSpawnActions": post or None,
        })
    leaves.sort(key=lambda x: (x["categoryPath"], x["asset"]))
    return location, leaves


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    items_path = args[args.index("--items") + 1] if "--items" in args else \
        os.path.join(HERE, "..", "..", "src", "data", "items.json")

    spawn_dir = None
    for cand in glob.glob(os.path.join(data, "**", "Items", "Spawning"), recursive=True):
        if os.path.isdir(os.path.join(cand, "Nodes")):
            spawn_dir = cand
            break
    if not spawn_dir:
        print("ERROR: could not find Items/Spawning dir under", data, file=sys.stderr)
        sys.exit(1)

    item_idx = build_item_index(items_path)
    print(f"  item catalog index: {len(item_idx)}", file=sys.stderr)

    # ItemSpawningParameters -> per-item metadata
    isp_path = os.path.join(spawn_dir, "ItemSpawningParameters.json")
    isp_rows = {}
    if os.path.exists(isp_path):
        doc = json.load(open(isp_path, encoding="utf-8"))
        tbl = next((o for o in doc if o.get("Type") == "DataTable" and "Rows" in o), None)
        if tbl:
            isp_rows = tbl["Rows"]
    print(f"  ItemSpawningParameters rows: {len(isp_rows)}", file=sys.stderr)

    def item_meta(asset: str):
        row = isp_rows.get(asset)
        if not row:
            return None
        allowed = {k: v for k, v in (row.get("AllowedLocations") or {}).items() if v}
        variations = [v.get("AssetPathName", "").split("/")[-1].split(".")[0]
                      for v in (row.get("Variations") or []) if v.get("AssetPathName")]
        cg = row.get("CooldownGroup") or {}
        return {
            "allowedLocations": sorted(allowed.keys()) or None,
            "maxOccurrences": row.get("MaxOccurrences"),
            "cooldownGroup": cg.get("RowName") if cg.get("RowName") not in (None, "None") else None,
            "variations": variations or None,
        }

    def resolve_name(asset: str):
        it = item_idx.get(norm_asset(asset))
        if it:
            return it["slug"], dict(it["name"]), True
        return None, {"en": humanize(asset)}, False

    # ---- walk every location ----
    node_files = sorted(glob.glob(os.path.join(spawn_dir, "Nodes", "ILTN_*.json")))
    locations = []
    # also aggregate per-item: where does this item appear?
    item_appearances: dict[str, dict] = {}

    total_leaves = 0
    joined = 0
    for fp in node_files:
        loc, leaves = parse_location_tree(fp)
        if loc is None:
            continue
        entries = []
        for lf in leaves:
            total_leaves += 1
            slug, name, ok = resolve_name(lf["asset"])
            if ok:
                joined += 1
            meta = item_meta(lf["asset"])
            entry = {
                "asset": lf["asset"],
                "slug": slug,
                "name": name,
                "categoryPath": lf["categoryPath"],
                "rarity": lf["rarity"],
                "rarityChain": lf["rarityChain"],
            }
            if lf["postSpawnActions"]:
                entry["postSpawnActions"] = lf["postSpawnActions"]
            entries.append(entry)

            ap = item_appearances.setdefault(lf["asset"], {
                "asset": lf["asset"], "slug": slug, "name": name,
                "spawnParams": meta, "locations": [],
            })
            ap["locations"].append({
                "location": loc,
                "categoryPath": lf["categoryPath"],
                "rarity": lf["rarity"]["label"],
            })

        locations.append({
            "location": loc,
            "itemCount": len(entries),
            "items": entries,
        })

    locations.sort(key=lambda x: x["location"])
    item_list = sorted(item_appearances.values(), key=lambda x: (x["slug"] or "~" + x["asset"]))

    out = {
        "_meta": {
            "domain": "loot",
            "source": "Data/Tables/Items/Spawning (ILTN_*.json + ItemSpawningParameters.json)",
            "rarityScale": [RARITY_INFO[k]["label"] for k in
                            sorted(RARITY_INFO, key=lambda k: RARITY_INFO[k]["rank"])],
            "rarityNote": "Rarity is the spawn weight at a loot-tree branch; Abundant=most likely, Extremely Rare=least. Each node and its ancestors carry their own rarity (rarityChain).",
            "locationCount": len(locations),
            "uniqueItemCount": len(item_list),
            "leafOccurrences": total_leaves,
            "namesJoined": f"{joined}/{total_leaves}",
        },
        "locations": locations,
        "items": item_list,
    }

    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "loot.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # stats
    cov = {l: sum(1 for it in item_list if l in (it["name"] or {})) for l in LANGS}
    print(f"\nwrote {len(locations)} locations / {len(item_list)} unique items -> {out_path}", file=sys.stderr)
    print(f"leaf occurrences: {total_leaves}  | names joined to catalog: {joined} ({100*joined/max(1,total_leaves):.1f}%)", file=sys.stderr)
    print("unique-item name coverage per language:", file=sys.stderr)
    for l in LANGS:
        print(f"  {l:5}: {cov[l]:4}/{len(item_list)}", file=sys.stderr)


if __name__ == "__main__":
    main()
