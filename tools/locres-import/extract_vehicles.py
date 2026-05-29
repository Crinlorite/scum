#!/usr/bin/env python3
"""
Extract SCUM vehicles (cars, bikes, boats, planes, ATV, tractor, wheelbarrows)
from the FModel JSON dump, joining official names/descriptions to 10 languages.

Data sources (all under SCUM/Content/ConZ_Files/Vehicles/):

  <Name>_ES.json   -> VehicleUIData: the canonical "this is a vehicle" record.
      .Caption     = {Namespace,Key,SourceString,LocalizedString}  (display name)
      .Description = localized blurb (Key joins to .po)
      .Actor       = {AssetPathName: ".../BPC_<Name>.BPC_<Name>_C"} -> the BP
    We treat an _ES file as a real vehicle iff its Actor points at a BP blueprint
    file that exists on disk under Vehicles/ (this excludes the *_CraftedItem and
    *_Item_Container UI-data variants, which point at item/container classes).

  BPC_<Name>.json / BP_<Name>.json  -> the vehicle blueprint array.  The default
    object (Name startswith "Default__") carries:
      _mountSlotsBySwitchSeatIndex  -> list of seat tags (seat count)
      _itemContainerClass           -> storage container class
      _damageHandlerParams.DamageRegions -> destructible regions (count)
      _maxCarryWeight (sometimes), _maxPushForce, _inWaterDestructionTimeInSeconds
    The DriveComponent object (Type DcxWheeled*DriveComponent*) carries:
      GearboxData (gear ratios), ChassisMass, EngineData.
    The engine *attachment* file (Attachments/*Engine*.json, not Alternator/
    Battery/Item) carries EngineSetup: FuelResourceType, RpmMax, RpmLimiter.

Name/description join: the .po `#. Key:` GUID is identical across locales and
equals the Caption/Description `Key`.  msgctxt is ",<Key>" and msgstr is the
translation.

Output: out/vehicles.json  — list, sorted by type then slug, each:
  { asset, type, slug, esFile, bpAsset,
    nameKey, name:{lang:str}, descKey, descName:{lang:str},
    fuel:{type, engineRpmMax, engineRpmLimiter},
    drivetrain:{gearCount, topGearRatio, reverseGearRatio, chassisMass},
    seats, seatsSource,
    storage:{containerClass, maxCarryWeight, storageExpansionSlots},
    health:{chassis, engine, totalAttachmentHealth, attachmentsWithHealth,
            damageRegions},
    extras:{maxPushForce, inWaterDestructionSeconds} }

Run:  python3 extract_vehicles.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import glob

DUMP = "/tmp/scum-data/SCUM/Content/ConZ_Files"
VEH_DIR = os.path.join(DUMP, "Vehicles")
LOC_BASE = "/tmp/scum-locres/SCUM/Content/Localization/Game"

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
SOURCE_LANG = "en"


# ---------- .po parsing (key -> msgstr per language) ----------

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


def parse_po_key_to_str(path: str) -> dict[str, str]:
    """Return {Key -> translated msgstr}."""
    out: dict[str, str] = {}
    key = None
    raw = {"msgid": "", "msgstr": ""}
    state = None

    def flush():
        nonlocal key
        if key is not None:
            s = _unescape(raw["msgstr"])
            if s.strip():
                out[key] = s
        key = None
        raw["msgid"] = raw["msgstr"] = ""

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#. Key:"):
                key = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgid "):
                raw["msgid"] = _po_quoted(line, len("msgid ")); state = "id"
            elif line.startswith("msgstr "):
                raw["msgstr"] = _po_quoted(line, len("msgstr ")); state = "str"
            elif line.startswith('"') and state:
                raw["msgid" if state == "id" else "msgstr"] += _po_quoted(line, 0)
            elif line.strip() == "":
                flush(); state = None
    flush()
    return out


def load_locales() -> dict[str, dict[str, str]]:
    by_lang: dict[str, dict[str, str]] = {}
    for lang, locale in LANG_TO_LOCALE.items():
        p = os.path.join(LOC_BASE, locale, "Game.po")
        if not os.path.exists(p):
            print(f"  WARN missing {p}", file=sys.stderr)
            by_lang[lang] = {}
            continue
        by_lang[lang] = parse_po_key_to_str(p)
        print(f"  parsed {lang:5} ({locale}): {len(by_lang[lang])} keys", file=sys.stderr)
    return by_lang


def join_by_key(by_lang, key, fallback_source) -> dict[str, str]:
    if not key:
        return {}
    out = {}
    for lang in LANG_TO_LOCALE:
        v = by_lang.get(lang, {}).get(key)
        if v and v.strip():
            out[lang] = v
    if SOURCE_LANG not in out and fallback_source:
        out[SOURCE_LANG] = fallback_source
    return out


# ---------- FModel helpers ----------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def default_obj(arr):
    """The Default__<Class>_C UObject that holds the real property values."""
    for o in arr:
        if (o.get("Name", "") or "").startswith("Default__"):
            return o
    return None


# A BP is a *real drivable vehicle* (vs a *_CraftedItem / *_Item_Container UI
# variant) iff its default object carries vehicle-actor properties.
VEHICLE_KEYS = {
    "_mountSlotsBySwitchSeatIndex", "_driveComponent", "_itemContainerClass",
    "_maxPushForce", "_vehicleSystems", "_vehicleMeshComponent", "_chassisSlot",
}


def is_vehicle_bp(bp_props: dict) -> bool:
    return bool(VEHICLE_KEYS & set(bp_props.keys()))


def caption_record(arr):
    """Return the (obj, props) whose Properties have both Actor and Caption."""
    for o in arr:
        pr = o.get("Properties") or {}
        if "Actor" in pr and "Caption" in pr:
            return o, pr
    return None, None


def asset_to_dump_path(asset_path: str) -> str | None:
    """'/Game/ConZ_Files/Vehicles/Car/Laika/BPC_Laika.BPC_Laika_C' -> file path."""
    if not asset_path:
        return None
    pkg = asset_path.split(".", 1)[0]            # /Game/ConZ_Files/.../BPC_Laika
    pkg = pkg.replace("/Game/", "", 1)           # ConZ_Files/.../BPC_Laika
    return os.path.join(DUMP, pkg[len("ConZ_Files/"):] if pkg.startswith("ConZ_Files/") else pkg) + ".json"


def slugify(name, asset):
    base = (name or "").strip() or asset
    s = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return s or asset.lower()


# Directory category -> friendly vehicle type
def category_for(bp_path: str) -> str:
    rel = bp_path.split("/Vehicles/", 1)[-1]
    top = rel.split("/", 1)[0]
    return {
        "Car": "car", "Bike": "bike", "Boat": "boat", "Airplane": "airplane",
        "ATV": "atv", "Tractor": "tractor", "WheelBarrow": "wheelbarrow",
    }.get(top, top.lower())


def find_engine_setup(bp_path: str):
    """Search the vehicle's directory tree for the engine attachment EngineSetup."""
    vdir = os.path.dirname(bp_path)
    cands = glob.glob(os.path.join(vdir, "**", "*Engine*.json"), recursive=True)
    for f in sorted(cands):
        bn = os.path.basename(f)
        if any(x in bn for x in ("Alternator", "Battery", "_Item", "Item_")):
            continue
        try:
            arr = load_json(f)
        except Exception:
            continue
        o = default_obj(arr)
        if not o:
            continue
        es = (o.get("Properties") or {}).get("EngineSetup")
        if isinstance(es, dict) and es.get("FuelResourceType"):
            ft = (es.get("FuelResourceType") or {}).get("ObjectName", "")
            m = re.search(r"'([^']+?)(?:_C)?'", ft)
            return {
                "type": (m.group(1) if m else ft) or None,
                "engineRpmMax": es.get("RpmMax"),
                "engineRpmLimiter": es.get("RpmLimiter"),
                "engineFile": os.path.relpath(f, DUMP),
            }
    return None


def drive_component(arr):
    for o in arr:
        t = o.get("Type", "") or ""
        if "DriveComponent" in t:
            return o.get("Properties") or {}
    return {}


def chassis_health(bp_path: str):
    """_maxHealth of the chassis attachment, plus total over all attachments."""
    vdir = os.path.dirname(bp_path)
    att = glob.glob(os.path.join(vdir, "Attachments", "*.json"))
    chassis = engine = None
    total = 0.0
    count = 0
    for f in att:
        bn = os.path.basename(f)
        try:
            arr = load_json(f)
        except Exception:
            continue
        o = default_obj(arr)
        if not o:
            continue
        hp = (o.get("Properties") or {}).get("_maxHealth")
        if isinstance(hp, (int, float)):
            total += hp
            count += 1
            if "Chassis" in bn and chassis is None:
                chassis = hp
            if "Engine" in bn and "Alternator" not in bn and "Battery" not in bn and engine is None:
                engine = hp
    return {
        "chassis": chassis,
        "engine": engine,
        "totalAttachmentHealth": round(total, 1) if count else None,
        "attachmentsWithHealth": count,
    }


SEAT_RE = re.compile(r"(Seat|Driver|Passenger)", re.I)
PUSH_RE = re.compile(r"Push", re.I)


def seat_count(props: dict, bp_path: str):
    """Prefer _mountSlotsBySwitchSeatIndex; else dedup seat mount-slot files."""
    msbs = props.get("_mountSlotsBySwitchSeatIndex")
    if isinstance(msbs, list) and msbs:
        return len(msbs), "_mountSlotsBySwitchSeatIndex"
    # fallback: count mount-slot files that are seats, collapsing Driver_* variants
    vdir = os.path.dirname(bp_path)
    files = glob.glob(os.path.join(vdir, "MountSlots", "*.json"))
    seen = set()
    for f in files:
        bn = os.path.basename(f).replace(".json", "")
        if PUSH_RE.search(bn) or not SEAT_RE.search(bn):
            continue
        # collapse Driver_Rowing / Driver_Engine / Driver_Sail -> "Driver"
        key = re.sub(r"_(Rowing|Engine|Sail)$", "", bn)
        key = re.split(r"MountSlot_", key, 1)[-1]
        seen.add(key)
    if seen:
        return len(seen), "mountslot_files"
    return None, None


def storage_expansion_slots(props: dict) -> int | None:
    """Count attachment slots whose tag mentions storage/inventory expansion."""
    n = 0
    found = False
    for k, v in props.items():
        if not isinstance(v, dict):
            continue
        s = json.dumps(v, ensure_ascii=False).lower()
        if "expansion" in s or "storagerack" in s or "storage_rack" in s:
            found = True
            n += 1
    return n if found else None


def main():
    print("loading localization...", file=sys.stderr)
    by_lang = load_locales()

    here = os.path.dirname(os.path.abspath(__file__))

    # collect all _ES (VehicleUIData) files under Vehicles/, indexed by directory
    # so we can borrow translations from sibling UI variants when needed.
    es_files = glob.glob(os.path.join(VEH_DIR, "**", "*_ES.json"), recursive=True)

    # dir -> list of caption dicts ({Key,SourceString,...}) from every _ES variant
    sibling_captions: dict[str, list[dict]] = {}
    for esf in es_files:
        try:
            arr = load_json(esf)
        except Exception:
            continue
        _, pr = caption_record(arr)
        if pr and pr.get("Caption"):
            sibling_captions.setdefault(os.path.dirname(esf), []).append(pr["Caption"])

    def best_name(primary_cap: dict, sib_dir: str) -> tuple[str | None, dict]:
        """Pick the caption (primary or a sibling in the same dir) that joins to
        the most languages. Lets BPC_<X> borrow a localized name from the sibling
        <X>_CraftedItem / <X>_Item_Container UI-data when its own Key is untranslated."""
        cands = [primary_cap] + [c for c in sibling_captions.get(sib_dir, []) if c is not primary_cap]
        best_key, best_name_map, best_n = None, {}, -1
        for c in cands:
            k = c.get("Key") or None
            src = c.get("SourceString") or c.get("LocalizedString")
            nm = join_by_key(by_lang, k, src)
            if len(nm) > best_n:
                best_key, best_name_map, best_n = k, nm, len(nm)
        return best_key, best_name_map

    vehicles = []
    seen_slug: dict[str, int] = {}

    for esf in sorted(es_files):
        try:
            arr = load_json(esf)
        except Exception:
            continue
        _, pr = caption_record(arr)
        if not pr:
            continue
        actor = (pr.get("Actor") or {}).get("AssetPathName", "")
        bp_path = asset_to_dump_path(actor)
        # Real drivable vehicle iff the actor BP file exists on disk under Vehicles/
        if not bp_path or "/Vehicles/" not in bp_path or not os.path.exists(bp_path):
            continue

        bp_arr = load_json(bp_path)
        bp_default = default_obj(bp_arr)
        bp_props = (bp_default or {}).get("Properties", {}) if bp_default else {}

        # Exclude *_CraftedItem / *_Item_Container / storage-rack UI variants:
        # only the actual vehicle-actor blueprint qualifies.
        if not is_vehicle_bp(bp_props):
            continue

        cap = pr.get("Caption") or {}
        name_key, name = best_name(cap, os.path.dirname(esf))

        desc = pr.get("Description") or {}
        desc_key = desc.get("Key") or None
        desc_src = desc.get("SourceString") or desc.get("LocalizedString")
        desc_name = join_by_key(by_lang, desc_key, desc_src)

        asset = os.path.basename(bp_path).replace(".json", "")
        vtype = category_for(bp_path)

        slug = slugify(name.get(SOURCE_LANG, ""), asset)
        if slug in seen_slug:
            seen_slug[slug] += 1
            slug = f"{slug}-{seen_slug[slug]}"
        else:
            seen_slug[slug] = 1

        # drivetrain
        dc = drive_component(bp_arr)
        gb = dc.get("GearboxData") or {}
        gears = gb.get("ForwardGears") or []
        top_gear = gears[-1].get("Ratio") if gears else None
        drivetrain = {
            "gearCount": len(gears) if gears else None,
            "topGearRatio": top_gear,
            "reverseGearRatio": gb.get("ReverseGearRatio"),
            "chassisMass": dc.get("ChassisMass"),
        }

        fuel = find_engine_setup(bp_path) or {"type": None, "engineRpmMax": None,
                                              "engineRpmLimiter": None, "engineFile": None}

        seats, seats_src = seat_count(bp_props, bp_path)

        icc = bp_props.get("_itemContainerClass") or {}
        cont = (icc.get("ObjectName") or "")
        m = re.search(r"'([^']+)'", cont)
        container_class = m.group(1) if m else (cont or None)

        dh = bp_props.get("_damageHandlerParams") or {}
        regions = dh.get("DamageRegions") if isinstance(dh, dict) else None
        health = chassis_health(bp_path)
        health["damageRegions"] = len(regions) if isinstance(regions, list) else None

        vehicles.append({
            "asset": asset,
            "type": vtype,
            "slug": slug,
            "esFile": os.path.relpath(esf, DUMP),
            "bpAsset": actor,
            "nameKey": name_key,
            "name": name,
            "descKey": desc_key,
            "descName": desc_name,
            "fuel": {
                "type": fuel["type"],
                "engineRpmMax": fuel["engineRpmMax"],
                "engineRpmLimiter": fuel["engineRpmLimiter"],
            },
            "drivetrain": drivetrain,
            "seats": seats,
            "seatsSource": seats_src,
            "storage": {
                "containerClass": container_class,
                "maxCarryWeight": bp_props.get("_maxCarryWeight"),
                "storageExpansionSlots": storage_expansion_slots(bp_props),
            },
            "health": health,
            "extras": {
                "maxPushForce": bp_props.get("_maxPushForce"),
                "inWaterDestructionSeconds": bp_props.get("_inWaterDestructionTimeInSeconds"),
            },
        })

    vehicles.sort(key=lambda v: (v["type"], v["slug"]))

    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "vehicles.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(vehicles, f, ensure_ascii=False, indent=2)

    # stats
    langs = list(LANG_TO_LOCALE)
    print(f"\nwrote {len(vehicles)} vehicles -> {out_path}", file=sys.stderr)
    print("name coverage per language:", file=sys.stderr)
    for l in langs:
        c = sum(1 for v in vehicles if l in v["name"])
        print(f"  {l:5}: {c:3}/{len(vehicles)}", file=sys.stderr)
    print("with fuel type:", sum(1 for v in vehicles if v["fuel"]["type"]), file=sys.stderr)
    print("with seats:", sum(1 for v in vehicles if v["seats"]), file=sys.stderr)
    print("with chassis health:", sum(1 for v in vehicles if v["health"]["chassis"]), file=sys.stderr)
    print("with storage container:", sum(1 for v in vehicles if v["storage"]["containerClass"]), file=sys.stderr)


if __name__ == "__main__":
    main()
