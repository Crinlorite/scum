#!/usr/bin/env python3
"""Extract the in-game Codex (manual) as structured articles.
Source: Manual/Codex/Entries/*.json → CodexEntry {Category, Title, Description,
Elements[]}. Elements reference sibling objects (by ObjectPath index) of type
Title / Text / Image / HorizontalContainer (recursed), in render order.
Localized text via ST_UI_Manual keys in the .po. Output: out/codex.json."""
import json, os, re, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ES_ROOT = "/tmp/scum-data"
ENTRIES = os.path.join(ES_ROOT, "SCUM/Content/ConZ_Files/Manual/Codex/Entries")
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
TAG = re.compile(r"</?[^>]+>")  # UE rich-text tags: <blue>..</> , <bold> etc.
def clean(s): return TAG.sub("", s).strip() if s else s
def lf(field):
    if not isinstance(field, dict): return {}
    d = {k: clean(v) for k, v in loc.get(field.get("Key", ""), {}).items()}
    if "en" not in d and field.get("SourceString"): d["en"] = clean(field["SourceString"])
    return {k: v for k, v in d.items() if v}

def ref_index(ref):
    try: return int(str(ref.get("ObjectPath", "")).split(".")[-1])
    except Exception: return None

CAT = lambda s: (s or "").split("::")[-1]

def walk(refs, doc, out):
    for r in refs or []:
        i = ref_index(r)
        if i is None or i >= len(doc): continue
        o = doc[i]
        t = (o.get("Type") or "").replace("ModularCodexEntryElementData_", "")
        P = o.get("Properties", {}) or {}
        if t == "HorizontalContainer":
            walk(P.get("_elements"), doc, out)
        elif t in ("Title", "Text"):
            txt = lf(P.get("_text"))
            if txt: out.append({"t": "title" if t == "Title" else "text", "text": txt})
        elif t == "Image":
            ap = (P.get("_imageTexture") or {}).get("AssetPathName", "")
            if ap: out.append({"t": "image", "img": ap.split(".")[-1]})

entries = []
for fp in sorted(glob.glob(os.path.join(ENTRIES, "*.json"))):
    try: doc = json.load(open(fp, encoding="utf-8"))
    except Exception: continue
    if not isinstance(doc, list): continue
    ce = next((o for o in doc if o.get("Type") == "CodexEntry"), None)
    if not ce: continue
    P = ce.get("Properties", {})
    title = lf(P.get("Title"))
    blocks = []
    walk(P.get("Elements"), doc, blocks)
    slug = re.sub(r"[^a-z0-9]+", "-", (title.get("en") or ce.get("Name") or "").lower()).strip("-") or ce.get("Name", "").lower()
    entries.append({
        "id": ce.get("Name"),
        "slug": slug,
        "category": CAT(P.get("Category")),
        "title": title,
        "desc": lf(P.get("Description")),
        "blocks": blocks,
    })

# unique slugs
seen = {}
for e in entries:
    s = e["slug"]; n = seen.get(s, 0); seen[s] = n + 1
    if n: e["slug"] = f"{s}-{n+1}"

entries.sort(key=lambda e: (e["category"], e["slug"]))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(entries, open(os.path.join(HERE, "out", "codex.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import collections
print(f"wrote {len(entries)} codex articles -> out/codex.json", file=sys.stderr)
print(f"  categorías: {dict(collections.Counter(e['category'] for e in entries))}", file=sys.stderr)
print(f"  con título ES: {sum(1 for e in entries if e['title'].get('es'))} | con imágenes: {sum(1 for e in entries if any(b['t']=='image' for b in e['blocks']))}", file=sys.stderr)
