#!/usr/bin/env python3
"""Extract SCUM admin/server commands. Source: ConZ_Files/AdminCommands/*.json →
_verb, _requiredExecutorLevel, _description (localized). Output: out/admin.json."""
import json, os, re, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ES_ROOT = "/tmp/scum-data"
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

loc = build_loc_by_key()
def lf(field):
    if not isinstance(field, dict): return {}
    d = dict(loc.get(field.get("Key", ""), {}))
    if "en" not in d and field.get("SourceString"): d["en"] = field["SourceString"]
    return d

LEVEL = lambda s: (s or "").split("::")[-1] if s else ""

cmds = []
for fp in sorted(glob.glob(os.path.join(ES_ROOT, "**", "AdminCommands", "*.json"), recursive=True)):
    if fp.endswith("_ES.json"): continue
    try: doc = json.load(open(fp, encoding="utf-8"))
    except Exception: continue
    o = next((x for x in (doc if isinstance(doc, list) else [doc])
              if isinstance(x, dict) and isinstance(x.get("Properties"), dict) and "_verb" in x["Properties"]), None)
    if not o: continue
    p = o["Properties"]
    cmds.append({
        "verb": p.get("_verb") or os.path.basename(fp)[:-5],
        "level": LEVEL(p.get("_requiredExecutorLevel")),
        "args": p.get("_argumentString") or p.get("_arguments") or None,
        "desc": lf(p.get("_description")),
    })

# de-dupe by verb, drop empty
seen, out = set(), []
for c in cmds:
    if c["verb"] in seen: continue
    seen.add(c["verb"]); out.append({k: v for k, v in c.items() if v})
out.sort(key=lambda c: (c.get("level", ""), c["verb"]))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "out", "admin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import collections
print(f"wrote {len(out)} admin commands -> out/admin.json | niveles: {dict(collections.Counter(c.get('level','?') for c in out))}", file=sys.stderr)
print(f"  con desc ES: {sum(1 for c in out if c.get('desc',{}).get('es'))}", file=sys.stderr)
