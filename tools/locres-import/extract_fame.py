#!/usr/bin/env python3
"""Extract the fame-point system: Data/FamePointSettings.json → Awards (gains) and
Penalties (losses), each a map action→fame points. Output: out/fame.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "/tmp/scum-data/SCUM/Content/ConZ_Files/Data/FamePointSettings.json"

doc = json.load(open(SRC, encoding="utf-8"))
P = next(o["Properties"] for o in (doc if isinstance(doc, list) else [doc])
         if isinstance(o, dict) and isinstance(o.get("Properties"), dict) and "Awards" in o["Properties"])

def clean(m):
    return [{"action": k, "fame": round(v, 5)} for k, v in (m or {}).items() if isinstance(v, (int, float)) and v != 0]

out = {"awards": clean(P.get("Awards")), "penalties": clean(P.get("Penalties"))}
out["awards"].sort(key=lambda x: -x["fame"])
out["penalties"].sort(key=lambda x: -x["fame"])
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "fame.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote fame: {len(out['awards'])} awards, {len(out['penalties'])} penalties -> out/fame.json", file=sys.stderr)
