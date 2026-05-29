#!/usr/bin/env python3
"""
Extract SCUM **medical / health domain** from the FModel JSON export.

Source of truth: the Prisoner BodySimulation effect blueprints under
  Characters/Prisoner/Blueprints/BodyEffects/
    Conditions/   (Diseases, Infections, Poisonings, Radiation, Injuries,
                   Deficiencies, Environment, and standalone conditions)
    Symptoms/     (Coughing, Fever, Nausea, Pain, Hallucinations, ...)

Each effect is a BlueprintGeneratedClass. Its class-default-object (CDO,
the `Default__*_C` object) carries gameplay Properties and a reference
`_uiDataClass` to a paired `*UIData.json` that holds the localized
`_name` / `_description` (StringTable keys into ST_UI_Health).

We also harvest the three Codex "Health" manual entries as general
treatment guides (namespace UI_Manual).

Multi-language join:
  every localized text is {TableId/Namespace, Key, SourceString} and is
  looked up by (Namespace, Key) in each language's Game.po. StringTable
  texts use namespace "ST_UI_Health"; Codex texts use "UI_Manual".

Structured gameplay extracted per condition where present:
  - category (disease / infection / poisoning / radiation / injury /
    deficiency / environment / general)
  - pathogenType, maxSeverity, duration
  - lifeThreatening (severity range)
  - transmission (coughing / sneezing + range)
  - nutrientEffects: nutrients whose intake changes pathogen load
    (negative end-value => curative / helps recovery)
  - symptoms: the side-effect symptom classes it produces, with their
    localized names joined
  - treatment: detected treatment interactions (bandage / disinfect /
    gel / antibiotics) + any "Treatment:" line parsed from the EN desc

Output: out/medical.json  (UTF-8, ensure_ascii=False)

Inputs:
  --data   FModel export root  (default /tmp/scum-data)
  --locres .po root            (default /tmp/scum-locres/SCUM/Content/Localization/Game)
"""
from __future__ import annotations
import json, os, re, sys, glob

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- .po parsing
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


def parse_po_by_ctxt(path):
    out, cur, state, raw = {}, {"ctxt": None}, None, {"id": "", "str": "", "ctxt": ""}
    def flush():
        if cur["ctxt"] is not None:
            out[cur["ctxt"]] = _unescape(raw["str"]) or _unescape(raw["id"])
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("msgctxt "):
                raw = {"id": "", "str": "", "ctxt": _q(line, 8)}; cur = {"ctxt": raw["ctxt"]}; state = "ctxt"
            elif line.startswith("msgid "):
                raw["id"] = _q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["str"] = _q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[state] += _q(line, 0)
            elif line.strip() == "":
                if cur["ctxt"] is not None:
                    flush(); cur, state, raw = {"ctxt": None}, None, {"id": "", "str": "", "ctxt": ""}
    if cur["ctxt"] is not None:
        flush()
    return out


def build_loc(locres_root):
    loc = {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(locres_root, locale, "Game.po")
        if not os.path.exists(p):
            continue
        for ctxt, txt in parse_po_by_ctxt(p).items():
            if txt and txt.strip():
                loc.setdefault(ctxt, {})[lang] = txt
    return loc


def loc_text(loc, ns, key, fallback_en):
    d = dict(loc.get(f"{ns},{key}", {}))
    if "en" not in d and fallback_en:
        d["en"] = fallback_en
    return d


def loc_field(field, loc):
    """A localized text field. Handles both StringTable form (TableId/Key)
    and the {Namespace,Key,SourceString} form."""
    if not isinstance(field, dict):
        return {}
    src = field.get("SourceString") or field.get("LocalizedString")
    key = field.get("Key", "")
    ns = field.get("Namespace")
    if ns is None:
        table = field.get("TableId") or ""
        # /Game/.../ST_UI_Health.ST_UI_Health -> namespace is the table name
        ns = table.split(".")[-1] if "." in table else table.split("/")[-1]
    return loc_text(loc, ns, key, src)


# ------------------------------------------------------------ FModel helpers
def load_doc(fp):
    try:
        doc = json.load(open(fp, encoding="utf-8"))
        return doc if isinstance(doc, list) else None
    except Exception:
        return None


def cdo(doc):
    """The class-default-object: Type ends with _C and Name starts Default__."""
    for o in doc:
        if str(o.get("Name", "")).startswith("Default__") and str(o.get("Type", "")).endswith("_C"):
            return o
    return None


def ref_basename(ref):
    """A {ObjectName,ObjectPath} reference -> the asset/class base name (no _C)."""
    if not isinstance(ref, dict):
        return None
    on = ref.get("ObjectName") or ""
    m = re.search(r"'([^']+)'", on)
    nm = m.group(1) if m else on
    nm = nm.split(":")[-1]
    return nm


def strip_c(name):
    return re.sub(r"_C$", "", name) if name else name


def enum_tail(v):
    if isinstance(v, str) and "::" in v:
        return v.split("::")[-1]
    return v


def curve_end_value(curve):
    """Last key value of an EditorCurveData curve (the steady-state effect)."""
    try:
        keys = curve["EditorCurveData"]["Keys"]
        return round(keys[-1]["Value"], 4) if keys else None
    except Exception:
        return None


# ------------------------------------------------------------ category logic
def categorize(rel):
    r = rel.replace("\\", "/")
    if "/Diseases/" in r:
        return "disease"
    if "/Infections/" in r:
        return "infection"
    if "/Poisonings/" in r:
        return "poisoning"
    if "/Radiation/" in r:
        return "radiation"
    if "/Injuries/" in r:
        return "injury"
    if "/Deficiencies/" in r:
        return "deficiency"
    if "/Environment/" in r:
        return "environment"
    return "general"


# detected treatment interactions by class-name substring
TREATMENT_HINTS = [
    ("applybandages", "apply_bandages"),
    ("removebandages", "remove_bandages"),
    ("disinfect", "disinfect"),
    ("applygel", "apply_gel"),
    ("antibiotic", "antibiotics"),
    ("suture", "suture"),
    ("splint", "splint"),
]


def detect_treatment(p, doc):
    methods = set()
    # _initialInteractions / _disinfectData / _applyBandagesData presence
    if "_disinfectData" in p:
        methods.add("disinfect")
    if "_applyBandagesData" in p:
        methods.add("apply_bandages")
    for ref in p.get("_initialInteractions", []) or []:
        bn = (ref_basename(ref) or "").lower()
        for hint, label in TREATMENT_HINTS:
            if hint in bn:
                methods.add(label)
    return sorted(methods)


# parse "Treatment:" line(s) out of an English description
def parse_treatment_line(desc_en):
    if not desc_en:
        return None
    m = re.search(r"Treatment:\s*(.+)", desc_en, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


NUTRIENT_LABEL = {
    "VitaminC": "Vitamin C", "VitaminD": "Vitamin D", "VitaminA": "Vitamin A",
    "VitaminE": "Vitamin E", "VitaminK": "Vitamin K", "VitaminB": "Vitamin B",
    "Zinc": "Zinc", "Iron": "Iron", "Calcium": "Calcium", "Sodium": "Sodium",
    "Potassium": "Potassium", "Magnesium": "Magnesium",
}


def nutrient_effects(p):
    out = []
    for e in p.get("_pathogenChangeRatesVsAbsorbedNutrientRatio", []) or []:
        key = enum_tail(e.get("Key"))
        endv = curve_end_value(e.get("Value", {}))
        out.append({
            "nutrient": key,
            "label": NUTRIENT_LABEL.get(key, key),
            "pathogenChangeAtFull": endv,          # negative => reduces pathogen (curative)
            "curative": endv is not None and endv < 0,
        })
    return out


def slugify(name, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (name or fallback).lower()).strip("-")
    return s or fallback.lower()


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else "/tmp/scum-data"
    locres = args[args.index("--locres") + 1] if "--locres" in args else "/tmp/scum-locres/SCUM/Content/Localization/Game"

    loc = build_loc(locres)
    print(f"  loc keys: {len(loc)}", file=sys.stderr)

    be_root = os.path.join(data, "SCUM", "Content", "ConZ_Files", "Characters",
                           "Prisoner", "Blueprints", "BodyEffects")
    if not os.path.isdir(be_root):
        # fall back to glob discovery
        cand = glob.glob(os.path.join(data, "**", "Blueprints", "BodyEffects"), recursive=True)
        be_root = cand[0] if cand else be_root

    # ---- index every UIData file by its asset basename (e.g. CommonColdUIData)
    ui_index = {}   # basename(no _C) -> {"name":{...}, "description":{...}, "asset":...}
    for fp in glob.glob(os.path.join(be_root, "**", "*UIData.json"), recursive=True):
        doc = load_doc(fp)
        if not doc:
            continue
        o = cdo(doc)
        if not o:
            continue
        pr = o.get("Properties", {})
        asset = os.path.basename(fp)[:-5]            # strip .json
        rec = {
            "asset": asset,
            "name": loc_field(pr.get("_name"), loc),
            "description": loc_field(pr.get("_description"), loc),
        }
        ui_index[strip_c(asset)] = rec
        ui_index[strip_c(o.get("Name", "").replace("Default__", ""))] = rec

    # ---- build a symptom-name lookup keyed by symptom class basename
    symptom_name = {}   # "Coughing" -> {lang:name}
    sym_files = [f for f in glob.glob(os.path.join(be_root, "Symptoms", "**", "*.json"), recursive=True)
                 if not f.endswith("UIData.json")]
    for fp in sym_files:
        doc = load_doc(fp)
        if not doc:
            continue
        o = cdo(doc)
        if not o:
            continue
        base = strip_c(o.get("Name", "").replace("Default__", ""))
        ui_ref = ref_basename(o.get("Properties", {}).get("_uiDataClass"))
        ui = ui_index.get(strip_c(ui_ref)) if ui_ref else None
        if ui:
            symptom_name[base] = ui["name"]

    records = []

    def build_effect(fp, kind):
        doc = load_doc(fp)
        if not doc:
            return None
        o = cdo(doc)
        if not o:
            return None
        p = o.get("Properties", {})
        rel = os.path.relpath(fp, be_root)
        base = strip_c(o.get("Name", "").replace("Default__", ""))

        ui_ref = ref_basename(p.get("_uiDataClass"))
        ui = ui_index.get(strip_c(ui_ref)) if ui_ref else None
        name = (ui or {}).get("name", {})
        desc = (ui or {}).get("description", {})
        # skip controller / shared-no-name internal effects without a name
        if not name:
            return None

        category = categorize(rel) if kind == "condition" else "symptom"

        # symptoms produced (side effects that map to a symptom class)
        symptoms = []
        seen = set()
        for se in p.get("_sideEffects", []) or []:
            sub = ref_basename(se)
            if not sub:
                continue
            # find subobject in this doc to read _symptomClass
            scls = None
            for s in doc:
                if s.get("Name") == sub:
                    scls = ref_basename(s.get("Properties", {}).get("_symptomClass"))
                    break
            if scls:
                sb = strip_c(scls)
                if sb not in seen:
                    seen.add(sb)
                    symptoms.append({"class": sb, "name": symptom_name.get(sb, {"en": sb})})

        # life threatening range
        life = None
        if p.get("_useSeverityToDetermineLifeThreateningStatus"):
            rng = p.get("_severityRangeToBeLifeThreatening")
            if isinstance(rng, dict):
                life = {
                    "min": rng.get("LowerBound", {}).get("Value"),
                    "max": rng.get("UpperBound", {}).get("Value"),
                }
            else:
                life = True

        # transmission
        transmission = {}
        if p.get("_transmittableByCoughing"):
            transmission["coughing"] = True
            if "_transmissionRangeByCoughing" in p:
                transmission["coughingRange"] = p["_transmissionRangeByCoughing"]
        if p.get("_transmittableBySneezing"):
            transmission["sneezing"] = True

        nutr = nutrient_effects(p)
        treat_methods = detect_treatment(p, doc)
        treat_line = parse_treatment_line(desc.get("en"))

        rec = {
            "asset": base,
            "kind": kind,
            "category": category,
            "slug": slugify(name.get("en", ""), base),
            "name": name,
            "description": desc,
        }
        if kind == "condition":
            if p.get("_pathogenType") is not None:
                rec["pathogenType"] = enum_tail(p.get("_pathogenType"))
            if p.get("_maxSeverity") is not None:
                rec["maxSeverity"] = p.get("_maxSeverity")
            if p.get("_duration") is not None:
                rec["durationSeconds"] = p.get("_duration")
            if life is not None:
                rec["lifeThreatening"] = life
            if transmission:
                rec["transmission"] = transmission
            if nutr:
                rec["nutrientEffects"] = nutr
                rec["curativeNutrients"] = [n["label"] for n in nutr if n["curative"]]
            if symptoms:
                rec["symptoms"] = symptoms
            if p.get("_foreignSubstanceClass") is not None:
                rec["foreignSubstance"] = strip_c(ref_basename(p.get("_foreignSubstanceClass")))
            treat = {}
            if treat_methods:
                treat["methods"] = treat_methods
            if treat_line:
                treat["text"] = treat_line
            if treat:
                rec["treatment"] = treat
        return rec

    cond_files = [f for f in glob.glob(os.path.join(be_root, "Conditions", "**", "*.json"), recursive=True)
                  if not f.endswith("UIData.json")]
    for fp in sorted(cond_files):
        r = build_effect(fp, "condition")
        if r:
            records.append(r)

    for fp in sorted(sym_files):
        r = build_effect(fp, "symptom")
        if r:
            records.append(r)

    # ---- Codex Health manual entries -> general guides
    codex_dir = os.path.join(data, "SCUM", "Content", "ConZ_Files", "Manual", "Codex", "Entries")
    for fp in sorted(glob.glob(os.path.join(codex_dir, "Health_*.json"))):
        doc = load_doc(fp)
        if not doc:
            continue
        title = {}
        body = []
        for o in doc:
            pr = o.get("Properties", {})
            t = pr.get("Title")
            if isinstance(t, dict) and not title:
                title = loc_field(t, loc)
            tx = pr.get("_text")
            if isinstance(tx, dict) and ("Key" in tx or "SourceString" in tx):
                txt = loc_field(tx, loc)
                if txt:
                    body.append(txt)
        if not title:
            continue
        asset = os.path.basename(fp)[:-5]
        records.append({
            "asset": asset,
            "kind": "guide",
            "category": "guide",
            "slug": slugify(title.get("en", ""), asset),
            "name": title,
            "description": loc_field(
                next((o.get("Properties", {}).get("Description") for o in doc
                      if isinstance(o.get("Properties", {}).get("Description"), dict)), None), loc),
            "guideText": body,
        })

    records.sort(key=lambda r: (r["kind"], r["category"], r["slug"]))
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "medical.json")
    json.dump(records, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- stats
    langs = list(LANG_TO_LOCALE)
    named = [r for r in records if r.get("name")]
    cov = {l: sum(1 for r in named if l in r["name"]) for l in langs}
    by_kind = {}
    for r in records:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    by_cat = {}
    for r in records:
        if r["kind"] == "condition":
            by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(f"\nwrote {len(records)} records -> {out_path}", file=sys.stderr)
    print(f"by kind: {by_kind}", file=sys.stderr)
    print(f"conditions by category: {by_cat}", file=sys.stderr)
    print(f"name coverage: " + ", ".join(f"{l}:{cov[l]}" for l in langs), file=sys.stderr)
    print(f"conditions w/ nutrient cures: {sum(1 for r in records if r.get('nutrientEffects'))}", file=sys.stderr)
    print(f"conditions w/ symptoms list: {sum(1 for r in records if r.get('symptoms'))}", file=sys.stderr)
    print(f"conditions w/ treatment: {sum(1 for r in records if r.get('treatment'))}", file=sys.stderr)


if __name__ == "__main__":
    main()
