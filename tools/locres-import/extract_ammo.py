#!/usr/bin/env python3
"""Extract ammunition ballistics. Source: Items/Ammunition/.../BP_WeaponBullet_*.json
→ ProjectileData (InitialDamage, MuzzleVelocity [cm/s], Caliber [mm], PenetrationFactor,
BallisticCoefficient). Joined to items.json by base-name norm. Output: out/ammo.json."""
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
for fp in glob.glob(os.path.join(ES_ROOT, "**", "BP_WeaponBullet_*.json"), recursive=True):
    b = os.path.basename(fp)
    if b.endswith("_ES.json") or "_TR" in b or "Sentry" in b or "Dropship" in b:
        continue
    try:
        doc = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    pd = None
    for o in (doc if isinstance(doc, list) else [doc]):
        p = o.get("Properties") if isinstance(o, dict) else None
        if isinstance(p, dict) and isinstance(p.get("ProjectileData"), dict):
            pd = p["ProjectileData"]; break
    if not pd:
        continue
    base = norm(b)
    it = by_norm.get(base)
    if not it or it["slug"] in seen:
        continue
    rec = {"slug": it["slug"]}
    if isinstance(pd.get("InitialDamage"), (int, float)): rec["damage"] = round(pd["InitialDamage"], 1)
    if isinstance(pd.get("MuzzleVelocity"), (int, float)): rec["muzzleVel"] = round(pd["MuzzleVelocity"] / 100)  # cm/s → m/s
    if isinstance(pd.get("Caliber"), (int, float)): rec["caliber"] = round(pd["Caliber"], 1)
    if isinstance(pd.get("PenetrationFactor"), (int, float)): rec["penetration"] = round(pd["PenetrationFactor"], 2)
    if isinstance(pd.get("BallisticCoefficient"), (int, float)): rec["ballisticCoef"] = round(pd["BallisticCoefficient"], 3)
    if len(rec) <= 1:
        continue
    seen.add(it["slug"])
    out.append(rec)

out.sort(key=lambda r: r["slug"])
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "ammo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} ammo ballistics -> out/ammo.json", file=sys.stderr)
