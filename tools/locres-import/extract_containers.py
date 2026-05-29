#!/usr/bin/env python3
"""Extract storage capacity of every container item (chests, backpacks, wardrobes,
barrels, crates…). Source: <Item>_ES.json → an EntityGridInventoryComponentSetup
object with NumRows / NumColumns / MaxContainedWeight (kg). Joined to items.json by
base-name norm. Output: out/containers.json [{slug, rows, cols, slots, maxWeightKg}]"""
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

out, seen = [], set()
for fp in glob.glob(os.path.join(ES_ROOT, "**", "*_ES.json"), recursive=True):
    try:
        doc = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(doc, list):
        continue
    inv = next((o for o in doc if isinstance(o, dict)
                and o.get("Type") == "EntityGridInventoryComponentSetup"
                and isinstance(o.get("Properties"), dict)
                and ("NumRows" in o["Properties"] or "MaxContainedWeight" in o["Properties"])), None)
    if not inv:
        continue
    p = inv["Properties"]
    rows = p.get("NumRows")
    cols = p.get("NumColumns")
    maxw = p.get("MaxContainedWeight")
    if not rows and not cols and not maxw:
        continue
    base = norm(os.path.basename(fp).replace("_ES.json", ""))
    it = by_norm.get(base)
    if not it or it["slug"] in seen:
        continue
    seen.add(it["slug"])
    rec = {"slug": it["slug"]}
    if isinstance(rows, int): rec["rows"] = rows
    if isinstance(cols, int): rec["cols"] = cols
    if isinstance(rows, int) and isinstance(cols, int): rec["slots"] = rows * cols
    if isinstance(maxw, (int, float)): rec["maxWeightKg"] = round(maxw, 1)
    out.append(rec)

out.sort(key=lambda r: r["slug"])
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "containers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} containers -> out/containers.json", file=sys.stderr)
print(f"  con peso máx: {sum(1 for r in out if 'maxWeightKg' in r)} | con rejilla: {sum(1 for r in out if 'slots' in r)}", file=sys.stderr)
