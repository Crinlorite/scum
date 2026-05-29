#!/usr/bin/env python3
"""
Extract the "world_zones" domain from the SCUM FModel JSON dump.

IMPORTANT — what this dump does and does NOT contain
----------------------------------------------------
This is an ASSET / DataAsset / Blueprint export (FModel), not a level (.umap)
export.  There are therefore NO placed-actor world coordinates anywhere:
the actual X/Y positions of bunkers, POIs, cities, etc. live on instances
placed inside the level streams, which are not part of this dump.  (The task
brief already notes the dump carries no map image; it also carries no map
geo-coordinates.)  The numeric X/Y/Z values that *do* appear inside e.g.
BP_AbandonedBunker are RelativeLocations of sub-components within that one
actor's local space — they are not map coordinates and are intentionally
NOT emitted as POI positions.

What IS extractable here are the DATA definitions of zones / POIs:

  1. encounter_zone   — Encounters/EncounterZones/**.  Named POI / zone TYPE
                        templates, classified by category (Settlement, Factory,
                        Military, Medical, Police, Prison, TV_Bunker, POI,
                        Radiation, ...) and threat level (Low/Medium/High).
                        Carry encounter spawn parameters + distance ranges.
                        These are internal templates -> no localized name.
  2. zone_config      — Data/ZoneConfigurations/**.  Behavioural zone configs
                        (Outpost flag, disabled interactions, ...).
  3. custom_zone      — Data/CustomZoneData.json.  Admin "custom zone" system:
                        categories + per-category events + configuration
                        settings, each with a LOCALIZED name/description that
                        we join to all 10 site languages via the .po `#. Key`.

Output: out/world_zones.json  (UTF-8, ensure_ascii=False)
  {
    "meta": {... counts, note about missing coordinates ...},
    "encounter_zones": [ {kind, name, file, category, threat, properties} ],
    "zone_configs":    [ {kind, name, file, configuration} ],
    "custom_zones":    { "categories": [...], "configuration_settings": [...] }
  }

Run:  python3 extract_world_zones.py
"""
from __future__ import annotations
import json
import os
import re
import sys

DUMP_ROOT = "/tmp/scum-data/SCUM/Content/ConZ_Files"
LOCRES_BASE = "/tmp/scum-locres/SCUM/Content/Localization/Game"

# site lang code -> SCUM localization folder
LANG_TO_LOCALE = {
    "es":    "es-ES",
    "en":    "en-US",
    "de":    "de-DE",
    "ru":    "ru-RU",
    "zh":    "zh-Hans-CN",
    "fr":    "fr-FR",
    "pt":    "pt-BR",
    "zh-tw": "zh-Hant",
    "th":    "th-TH",
    "pl":    "pl-PL",
}
SOURCE_LANG = "en"


# --------------------------------------------------------------------------- #
# .po parsing (join localized strings by `#. Key`)                            #
# --------------------------------------------------------------------------- #
def _unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _po_quoted(line: str, prefix_len: int) -> str:
    body = line[prefix_len:].strip()
    if len(body) >= 2 and body[0] == '"' and body[-1] == '"':
        body = body[1:-1]
    return body


def parse_po(path: str) -> list[dict]:
    entries: list[dict] = []
    cur: dict = {}
    state = None
    raw = {"msgid": "", "msgstr": "", "msgctxt": ""}

    def flush():
        if not cur and not any(raw.values()):
            return
        cur["msgid"] = _unescape(raw["msgid"])
        cur["msgstr"] = _unescape(raw["msgstr"])
        cur["msgctxt"] = _unescape(raw["msgctxt"])
        if cur.get("key") is not None or cur["msgid"]:
            entries.append(dict(cur))

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#. Key:"):
                cur["key"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgctxt "):
                raw["msgctxt"] = _po_quoted(line, len("msgctxt ")); state = "ctxt"
            elif line.startswith("msgid "):
                raw["msgid"] = _po_quoted(line, len("msgid ")); state = "id"
            elif line.startswith("msgstr "):
                raw["msgstr"] = _po_quoted(line, len("msgstr ")); state = "str"
            elif line.startswith('"') and state:
                k = {"id": "msgid", "str": "msgstr", "ctxt": "msgctxt"}[state]
                raw[k] += _po_quoted(line, 0)
            elif line.strip() == "":
                if cur or any(raw.values()):
                    flush(); cur = {}; raw = {"msgid": "", "msgstr": "", "msgctxt": ""}; state = None
    if cur or any(raw.values()):
        flush()
    return entries


def load_locres() -> dict[str, dict[str, str]]:
    """lang -> {po_key: msgstr}."""
    by_lang: dict[str, dict[str, str]] = {}
    for lang, locale in LANG_TO_LOCALE.items():
        po = os.path.join(LOCRES_BASE, locale, "Game.po")
        if not os.path.exists(po):
            print(f"  WARN missing {po}", file=sys.stderr)
            continue
        ents = parse_po(po)
        by_lang[lang] = {e["key"]: e["msgstr"] for e in ents if e.get("key") and e["msgstr"]}
        print(f"  parsed {lang:5} ({locale}): {len(by_lang[lang])} keyed entries", file=sys.stderr)
    return by_lang


# A few upstream .po entries (e.g. some th-TH lines) have a corrupt msgstr that
# leaked the entry metadata instead of a real translation, like:
#   "Key:\t<GUID>\nSourceLocation:\t/Game/..."
# Drop those so we don't surface garbage as a "translation".
_LEAKED_META = re.compile(r"^Key:\s|SourceLocation:\s*/Game/")


def _clean_translation(v: str) -> str:
    if not v or not v.strip():
        return ""
    if _LEAKED_META.search(v):
        return ""
    return v


def loc_text(loc_obj: dict | None, by_lang: dict[str, dict[str, str]]) -> dict[str, str]:
    """A FModel localized string {Namespace,Key,SourceString,LocalizedString} ->
    {lang: text}.  Joins by Key across languages; SourceString seeds EN."""
    if not isinstance(loc_obj, dict):
        return {}
    key = loc_obj.get("Key")
    src = (loc_obj.get("SourceString") or "").strip()
    out: dict[str, str] = {}
    if key:
        for lang in LANG_TO_LOCALE:
            v = _clean_translation(by_lang.get(lang, {}).get(key, ""))
            if v:
                out[lang] = v
    if SOURCE_LANG not in out and src:
        out[SOURCE_LANG] = src
    return out


def rel(path: str) -> str:
    return os.path.relpath(path, DUMP_ROOT).replace("\\", "/")


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1. Encounter zones (POI / zone type templates)                              #
# --------------------------------------------------------------------------- #
# Filename prefix / folder -> human threat level
def threat_from(name: str, relpath: str) -> str:
    if name.startswith("HTZ") or "/Hight_Threat/" in "/" + relpath:
        return "High"
    if name.startswith("MTZ") or "/Medium_Threat/" in "/" + relpath:
        return "Medium"
    if name.startswith("LTZ") or "LowThreat" in name:
        return "Low"
    return "Unknown"


# token after threat prefix -> broad category
CATEGORY_TOKENS = [
    "Settlement", "Factory", "Military", "Medical", "Medical_Hospital",
    "Police", "Prison", "Radiation", "POI", "Civilian", "CoalMine",
    "Zeljava", "Airfield", "Airport", "Trainyard", "Bunker", "Gas_Station",
    "Road_Block", "Village", "Farm", "Vineyard", "Big_City", "WW2",
]


def category_from(name: str) -> str:
    # Names look like MTZ_POI_Airfield, HTZ_Military_TV_Bunker, MTZ_Settlement_Farm
    body = re.sub(r"^(HTZ|MTZ|LTZ|DA_EncounterZone)_?", "", name)
    parts = body.split("_")
    if not parts or not parts[0]:
        return "Other"
    # First meaningful token is the category bucket
    first = parts[0]
    # Normalise a few
    mapping = {"POI": "POI", "Settlement": "Settlement", "Factory": "Factory",
               "Military": "Military", "Medical": "Medical", "Police": "Police",
               "Prison": "Prison", "Radiation": "Radiation", "Civilian": "Civilian",
               "CoalMine": "CoalMine", "Zeljava": "Zeljava", "Road": "RoadBlock",
               "LowThreat": "Generic"}
    return mapping.get(first, first)


def extract_encounter_zones(by_lang) -> list[dict]:
    base = os.path.join(DUMP_ROOT, "Encounters", "EncounterZones")
    recs: list[dict] = []
    for dirpath, _dirs, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            data = load_json(fp)
            for obj in data:
                if obj.get("Type") != "EncounterZoneData":
                    continue
                name = obj.get("Name", fn[:-5])
                props = obj.get("Properties", {}) or {}
                relp = rel(fp)
                # Encounter class references (the spawn content) – keep names only
                encounters = []
                for e in props.get("EncounterData", []) or []:
                    cls = e.get("EncounterClass", {}) or {}
                    cname = cls.get("ObjectName", "")
                    m = re.search(r"'([^']+)'", cname)
                    encounters.append({
                        "encounterClass": m.group(1) if m else cname,
                        "weight": e.get("EncounterWeight"),
                    })
                # Selected numeric params worth surfacing (no coords exist here)
                keep = {}
                for k in ("EncounterSpawnChance", "SingleEncounterPerZone",
                          "SubjectToLargePOIServerSettings"):
                    if k in props:
                        keep[k] = props[k]
                for k in ("CharacterSpawnDistanceRange", "CharacterRespawnDistanceRange",
                          "EncounterCooldownInterval", "EncounterSpawnCheckInterval",
                          "InitialEncounterSpawnDelay"):
                    if k in props and isinstance(props[k], dict):
                        keep[k] = {kk: vv for kk, vv in props[k].items()
                                   if kk in ("Min", "Max")}
                recs.append({
                    "kind": "encounter_zone",
                    "name": name,
                    "file": relp,
                    "threat": threat_from(name, relp),
                    "category": category_from(name),
                    "encounters": encounters,
                    "params": keep,
                    "hasCoordinates": False,
                })
    recs.sort(key=lambda r: (r["threat"], r["category"], r["name"]))
    return recs


# --------------------------------------------------------------------------- #
# 2. Zone configurations (behavioural)                                        #
# --------------------------------------------------------------------------- #
def extract_zone_configs() -> list[dict]:
    base = os.path.join(DUMP_ROOT, "Data", "ZoneConfigurations")
    recs: list[dict] = []
    if not os.path.isdir(base):
        return recs
    for fn in sorted(os.listdir(base)):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(base, fn)
        for obj in load_json(fp):
            if obj.get("Type") != "ZoneConfigurationDataAsset":
                continue
            props = obj.get("Properties", {}) or {}
            recs.append({
                "kind": "zone_config",
                "name": obj.get("Name", fn[:-5]),
                "file": rel(fp),
                "configuration": props.get("Configuration", {}),
            })
    return recs


# --------------------------------------------------------------------------- #
# 3. Custom zone data (admin custom zones, localized)                         #
# --------------------------------------------------------------------------- #
def extract_custom_zones(by_lang) -> dict:
    fp = os.path.join(DUMP_ROOT, "Data", "CustomZoneData.json")
    if not os.path.exists(fp):
        return {}
    data = load_json(fp)
    props = (data[0].get("Properties", {}) if data else {}) or {}

    categories = []
    for cat in props.get("Categories", []) or []:
        events = []
        for ev in cat.get("Events", []) or []:
            events.append({
                "event": ev.get("Event"),
                "asDamageEvent": ev.get("AsDamageEvent"),
                "damageChannel": ev.get("DamageChannel"),
                "damageActor": ev.get("DamageActor"),
                "receiverDamageActor": ev.get("ReceiverDamageActor"),
                "nameKey": (ev.get("Name") or {}).get("Key"),
                "name": loc_text(ev.get("Name"), by_lang),
                "description": loc_text(ev.get("Description"), by_lang),
            })
        categories.append({
            "nameKey": (cat.get("Name") or {}).get("Key"),
            "name": loc_text(cat.get("Name"), by_lang),
            "events": events,
        })

    config_settings = []
    for cs in props.get("ConfigurationSettingsDisplayData", []) or []:
        config_settings.append({
            "setting": cs.get("Setting"),
            "title": loc_text(cs.get("Title"), by_lang),
            "description": loc_text(cs.get("Description"), by_lang),
        })

    handling = []
    for h in props.get("HandlingMethodDisplayData", []) or []:
        handling.append({
            "method": h.get("Method") or h.get("HandlingMethod"),
            "title": loc_text(h.get("Title"), by_lang),
            "description": loc_text(h.get("Description"), by_lang),
        })

    return {
        "file": rel(fp),
        "categories": categories,
        "configurationSettings": config_settings,
        "handlingMethods": handling,
    }


# --------------------------------------------------------------------------- #
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    print("Loading localization...", file=sys.stderr)
    by_lang = load_locres()

    print("Extracting encounter zones...", file=sys.stderr)
    encounter_zones = extract_encounter_zones(by_lang)
    print("Extracting zone configurations...", file=sys.stderr)
    zone_configs = extract_zone_configs()
    print("Extracting custom zone data...", file=sys.stderr)
    custom_zones = extract_custom_zones(by_lang)

    # localization coverage over custom-zone localized strings
    loc_records = []
    for c in custom_zones.get("categories", []):
        loc_records.append(c["name"])
        for e in c["events"]:
            loc_records.append(e["name"])
            loc_records.append(e["description"])
    for cs in custom_zones.get("configurationSettings", []):
        loc_records.append(cs["title"]); loc_records.append(cs["description"])
    loc_records = [r for r in loc_records if r]
    cov = {l: sum(1 for r in loc_records if l in r) for l in LANG_TO_LOCALE}

    total = len(encounter_zones) + len(zone_configs) \
        + len(custom_zones.get("categories", [])) \
        + len(custom_zones.get("configurationSettings", []))

    out = {
        "meta": {
            "domain": "world_zones",
            "dumpRoot": DUMP_ROOT,
            "note": (
                "Asset/DataAsset dump (FModel) — contains zone/POI DATA "
                "definitions but NO map geo-coordinates: placed-actor world "
                "positions live in the level (.umap) streams not present here. "
                "Numeric X/Y/Z inside bunker BPs are local component offsets, "
                "not map coordinates, and are deliberately not emitted as POIs."
            ),
            "counts": {
                "encounter_zones": len(encounter_zones),
                "zone_configs": len(zone_configs),
                "custom_zone_categories": len(custom_zones.get("categories", [])),
                "custom_zone_configuration_settings":
                    len(custom_zones.get("configurationSettings", [])),
            },
            "localizationCoverage": cov,
            "languages": list(LANG_TO_LOCALE),
        },
        "encounter_zones": encounter_zones,
        "zone_configs": zone_configs,
        "custom_zones": custom_zones,
    }

    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "world_zones.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\nwrote -> {out_path}", file=sys.stderr)
    print(f"  encounter_zones: {len(encounter_zones)}", file=sys.stderr)
    print(f"  zone_configs:    {len(zone_configs)}", file=sys.stderr)
    print(f"  custom_zone categories: {len(custom_zones.get('categories', []))}, "
          f"config settings: {len(custom_zones.get('configurationSettings', []))}",
          file=sys.stderr)
    print(f"  total records:   {total}", file=sys.stderr)
    print(f"  localized custom-zone strings: {len(loc_records)}", file=sys.stderr)
    print("  loc coverage:", {l: cov[l] for l in LANG_TO_LOCALE}, file=sys.stderr)


if __name__ == "__main__":
    main()
