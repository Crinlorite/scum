#!/usr/bin/env python3
"""
Extract SCUM **character skills** from the game's FModel export
(SCUM/Content/ConZ_Files/Skills/*.json), joined to official multi-language
names and descriptions.

Real game data. Each player skill lives in two files:
  - <Skill>.json        : the gameplay definition (effects per level band,
                          XP award rates, modifier curves, recipes known...).
  - <Skill>UIData.json  : the UI data object, which only carries a
                          `_description` (a StringTable reference into
                          ST_UI_Skills -> namespace "UI_Skills").

Skills are organised into level *bands* (the in-game "levels"):
    No Skill -> Basic -> Medium -> Advanced -> Above Advanced
For every band the definition file may hold:
    <Band>SkillParameters        -> the *effects* of that band, each a
                                     {ValueWhenExperienceIsMinimal/Maximal}
                                     interpolation (the XP curve *within* the band)
    <Band>SkillExperienceAwards  -> how many XP points each action grants
                                     while in that band (the XP *gain* curve)
Some skills instead reference UE CurveFloat assets (e.g. Thievery, Tactics);
those curves are resolved to their raw key/value points.

Multi-language joins (10 site languages):
  - skill NAME  -> the C++ source registers it as msgctxt
        "<ClassNamespace>,<EnglishName>" with SourceLocation
        Source/ConZ/Skills/<Attribute>/<Class>.cpp .  We build an index of
        every such entry across all locales and match it to the skill's class.
  - skill DESCRIPTION -> the UIData `_description` is a StringTable ref into
        namespace "UI_Skills"; joined by msgctxt "UI_Skills,<Key>".
  - level-band labels ("No Skill".."Above Advanced") -> msgctxt "Skill,<Label>".

Inputs:
  --data   FModel export root   (default /tmp/scum-data)
  --locres .po root             (default /tmp/scum-locres/SCUM/Content/Localization/Game)
Output: out/skills.json
"""
from __future__ import annotations
import json, os, re, sys, glob

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))

# Level bands, in progression order. Property prefixes vary in casing/underscore,
# so we match case-insensitively against these canonical tokens.
BANDS = [
    ("noSkill", "No Skill", ["noskill", "no"]),
    ("basic", "Basic", ["basic"]),
    ("medium", "Medium", ["medium"]),
    ("advanced", "Advanced", ["advanced"]),
    ("aboveAdvanced", "Above Advanced", ["aboveadvanced"]),
]


def _unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(s[i + 1], s[i + 1])); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def _q(line, p):
    b = line[p:].strip()
    return b[1:-1] if len(b) >= 2 and b[0] == '"' and b[-1] == '"' else b


def parse_po(path):
    """Parse a UE .po into entries {ctxt, srcloc, msgstr, msgid}."""
    entries, cur, state, raw = [], {}, None, {"id": "", "str": "", "ctxt": ""}

    def flush():
        if cur or any(raw.values()):
            cur["ctxt"] = _unescape(raw["ctxt"])
            cur["msgstr"] = _unescape(raw["str"]) or _unescape(raw["id"])
            entries.append(dict(cur))

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#. SourceLocation:"):
                cur["srcloc"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgctxt "):
                raw["ctxt"] = _q(line, 8); state = "ctxt"
            elif line.startswith("msgid "):
                raw["id"] = _q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["str"] = _q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[{"id": "id", "str": "str", "ctxt": "ctxt"}[state]] += _q(line, 0)
            elif line.strip() == "":
                if cur or any(raw.values()):
                    flush(); cur, state, raw = {}, None, {"id": "", "str": "", "ctxt": ""}
    if cur or any(raw.values()):
        flush()
    return entries


def build_loc(locres_root):
    """{ "Namespace,Key": {lang: text} } across all locales, by msgctxt."""
    loc = {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(locres_root, locale, "Game.po")
        if not os.path.exists(p):
            print(f"  WARN missing {p}", file=sys.stderr); continue
        for e in parse_po(p):
            ctxt, txt = e.get("ctxt"), e.get("msgstr")
            if ctxt and txt and txt.strip():
                loc.setdefault(ctxt, {})[lang] = txt
    return loc


def build_name_index(locres_root):
    """Map skill CLASS name -> {'ctxt', 'attribute'} using the EN .po source
    locations (Source/ConZ/Skills/<Attribute>/<Class>.cpp). Class is the file
    stem; the registered namespace may differ (e.g. UAviationSkill)."""
    idx = {}
    p = os.path.join(locres_root, LANG_TO_LOCALE["en"], "Game.po")
    for e in parse_po(p):
        sl = e.get("srcloc") or ""
        ctxt = e.get("ctxt") or ""
        m = re.match(r"Source/ConZ/Skills/([^/]+)/([A-Za-z]+Skill)\.cpp", sl)
        if not m or "," not in ctxt:
            continue
        attribute, cls = m.group(1), m.group(2)
        ns, key = ctxt.split(",", 1)
        # Only the skill-name entry: its key equals the english display name and
        # the namespace ends in the class name (handles the UAviationSkill 'U').
        if ns.endswith(cls) and key == e.get("msgstr"):
            idx.setdefault(cls, {"ctxt": ctxt, "attribute": attribute})
    return idx


def loc_by_ctxt(loc, ctxt, fallback_en=None):
    d = dict(loc.get(ctxt, {}))
    if "en" not in d and fallback_en:
        d["en"] = fallback_en
    return d


def loc_field(field, loc):
    """A localized text field {Namespace,Key,SourceString}. Skill descriptions
    are StringTable refs whose msgctxt is 'UI_Skills,<Key>' (Namespace omitted
    in the export, so we hard-bind to the StringTable's namespace UI_Skills)."""
    if not isinstance(field, dict):
        return {}
    key = field.get("Key")
    src = field.get("SourceString") or field.get("LocalizedString")
    if not key:
        return {"en": src} if src else {}
    ns = field.get("Namespace") or "UI_Skills"
    out = loc_by_ctxt(loc, f"{ns},{key}", src)
    if not out and src:
        out = {"en": src}
    return out


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback).lower()).strip("-")
    return s or fallback.lower()


def short_obj(ref):
    """A {ObjectName,ObjectPath} reference -> short asset name."""
    if not isinstance(ref, dict):
        return None
    name = ref.get("ObjectName") or ""
    m = re.search(r"'([^']+)'", name)
    base = (m.group(1) if m else name)
    return base.split(".")[-1] or None


def load_curve(data_root, ref):
    """Resolve a CurveFloat asset reference to its raw {time,value} points."""
    asset = short_obj(ref)
    if not asset:
        return None
    asset = re.sub(r"_C$", "", asset)
    hits = glob.glob(os.path.join(data_root, "**", f"{asset}.json"), recursive=True)
    for fp in hits:
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for o in doc if isinstance(doc, list) else []:
            fc = (o.get("Properties") or {}).get("FloatCurve")
            if isinstance(fc, dict) and "Keys" in fc:
                pts = [{"x": k.get("Time"), "y": k.get("Value")} for k in fc["Keys"]]
                interp = fc["Keys"][0].get("InterpMode", "").replace("RCIM_", "") if fc["Keys"] else None
                return {"asset": asset, "interp": interp, "points": pts}
    return {"asset": asset, "interp": None, "points": None}


def band_match(prop_key):
    """Return (canonical band id, remaining role) if prop_key starts with a band
    token, else (None, prop_key). E.g. 'AdvancedSkillParameters' ->
    ('advanced','SkillParameters'); '_basicParameters' -> ('basic','Parameters')."""
    k = prop_key.lstrip("_")
    low = k.lower()
    for canon, _label, tokens in BANDS:
        for tok in tokens:
            if low.startswith(tok):
                rest = k[len(tok):]
                return canon, rest
    return None, prop_key


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    locres = args[args.index("--locres") + 1] if "--locres" in args else \
        "/tmp/scum-locres/SCUM/Content/Localization/Game"
    skills_dir = os.path.join(data, "SCUM", "Content", "ConZ_Files", "Skills")

    loc = build_loc(locres)
    name_idx = build_name_index(locres)
    print(f"  loc keys: {len(loc)} | name index: {len(name_idx)} skill classes", file=sys.stderr)

    # Localized band labels (shared by every skill).
    band_labels = {canon: loc_by_ctxt(loc, f"Skill,{label}", label)
                   for canon, label, _ in BANDS}

    # Map each base skill file to its UIData file (for the description).
    files = sorted(glob.glob(os.path.join(skills_dir, "*.json")))
    base_files = [f for f in files
                  if re.search(r"Skill\.json$", f) and "UIData" not in f and "UI_Data" not in f
                  and not os.path.basename(f).startswith("FC_")]

    skills = []
    for fp in base_files:
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        obj = next((o for o in doc if isinstance(o, dict) and o.get("Type", "").endswith("Skill")
                    and "Properties" in o), None)
        if not obj:
            continue
        cls = obj.get("Type") or os.path.basename(fp)[:-5]
        props = obj.get("Properties", {})

        # --- NAME (multi-lang) ---
        ni = name_idx.get(cls)
        if ni:
            name = loc_by_ctxt(loc, ni["ctxt"])
            attribute = ni["attribute"]
        else:
            name, attribute = {}, None
        if not name:
            name = {"en": re.sub(r"Skill$", "", cls)}

        # --- DESCRIPTION (multi-lang) via UIData ---
        ui_ref = props.get("_uiDataClass")
        ui_asset = short_obj(ui_ref)
        description = {}
        if ui_asset:
            ui_asset_base = re.sub(r"_C$", "", ui_asset)
            for cand in glob.glob(os.path.join(skills_dir, "*.json")):
                if re.sub(r"\.json$", "", os.path.basename(cand)).replace("_", "") not in \
                        (ui_asset_base.replace("_", ""),):
                    continue
                try:
                    udoc = json.load(open(cand, encoding="utf-8"))
                except Exception:
                    continue
                uobj = next((o for o in udoc if "Properties" in o
                             and "_description" in o.get("Properties", {})), None)
                if uobj:
                    description = loc_field(uobj["Properties"]["_description"], loc)
                break

        # --- LEVEL BANDS: effects (parameters) + XP awards ---
        bands = {}
        other = {}
        for k, v in props.items():
            if k in ("_uiDataClass", "_skillIcon", "AnimationsPreset"):
                continue
            canon, role = band_match(k)
            if canon:
                low = role.lower()
                slot = bands.setdefault(canon, {})
                if "experience" in low or "award" in low:
                    slot.setdefault("experienceAwards", {}).update(v if isinstance(v, dict) else {"value": v})
                elif "parameter" in low:
                    slot.setdefault("effects", {}).update(v if isinstance(v, dict) else {"value": v})
                else:
                    slot.setdefault("other", {})[role or k] = v
            else:
                other[k] = v

        # --- modifier curves (Thievery / Tactics ...) ---
        curves = {}
        for k, v in list(other.items()):
            if "Curve" in k and isinstance(v, dict) and "ObjectPath" in v:
                curves[re.sub(r"^_", "", k)] = load_curve(data, v)
                del other[k]

        # --- recipes known by default (Cooking) ---
        recipes_default = None
        if "_recipesKnownByDefault" in other:
            recipes_default = [r.get("PrimaryAssetName") for r in other.pop("_recipesKnownByDefault")
                               if isinstance(r, dict) and r.get("PrimaryAssetName")]

        # Build ordered levels list with localized labels.
        levels = []
        for canon, label, _ in BANDS:
            if canon in bands:
                entry = {"id": canon, "label": band_labels.get(canon, {"en": label})}
                entry.update(bands[canon])
                levels.append(entry)

        skills.append({
            "asset": cls,
            "slug": slugify(name.get("en", ""), cls),
            "attribute": attribute,
            "name": name,
            "description": description,
            "availableInCharacterCreation": props.get("IsAvailableInCharacterCreation"),
            "levels": levels,
            "modifierCurves": curves or None,
            "recipesKnownByDefault": recipes_default,
            "extraParameters": other or None,
            "skillIcon": short_obj(props.get("_skillIcon")),
        })

    skills.sort(key=lambda s: (s["attribute"] or "z", s["slug"]))

    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "skills.json")
    json.dump(skills, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # --- stats ---
    langs = list(LANG_TO_LOCALE)
    ncov = {l: sum(1 for s in skills if l in s["name"]) for l in langs}
    dcov = {l: sum(1 for s in skills if l in s["description"]) for l in langs}
    print(f"\nwrote {len(skills)} skills -> {out_path}", file=sys.stderr)
    print("name coverage : " + ", ".join(f"{l}:{ncov[l]}" for l in langs), file=sys.stderr)
    print("desc coverage : " + ", ".join(f"{l}:{dcov[l]}" for l in langs), file=sys.stderr)
    print("with levels   : " + str(sum(1 for s in skills if s["levels"])), file=sys.stderr)
    print("with curves   : " + str(sum(1 for s in skills if s["modifierCurves"])), file=sys.stderr)


if __name__ == "__main__":
    main()
