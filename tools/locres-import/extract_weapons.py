#!/usr/bin/env python3
"""
Extract the SCUM "weapons" domain: stats for melee + ranged weapons, joined to
the official multi-language item names.

Data sources (FModel JSON exports, each file is a list of UObjects):
  * Items/Weapons/Ranged_Weapons/*.json   firearms, bows, launchers
  * Items/Weapons/New_Melee/*.json         melee weapons
  * Items/Weapons/*.json                   top-level spears
  * Items/Weapons/Weapon_Clips/*.json      magazines (capacity lives here)
  * Items/Ammunition/*.json                ammo (caliber identity)
  * Data/WeaponDesc_Table.json             melee impact descriptor table
                                           (Damage/Energy/Sharpness per asset)

Per-weapon stat properties live in the ClassDefaultObject (`Default__<Asset>_C`).
Variant/skin blueprints inherit their parent's properties via the
BlueprintGeneratedClass `SuperStruct` -> we resolve the inheritance chain so a
skin like Weapon_AK47_Engraved gets the AK47's ammo/category/etc.

What we extract per weapon:
  asset, slug, name {10 langs}, kind (melee|ranged), weaponCategory,
  damagePerShot (ranged), meleeDamage/energy/sharpness (from WeaponDesc_Table),
  fireModes (detected from WeaponState* sub-objects),
  ammunition (caliber tag + readable label + default ammo asset),
  magazine {capacity, asset} (resolved via magazine socket mount type),
  maxRange, rof, zeroRangeStep, rarity,
  attachments (per socket: bone + allowed mount-type classes).

Recoil/spread: SCUM does NOT store a scalar recoil on the weapon asset (verified:
no recoil/spread/sway/dispersion property exists on any weapon UObject). Recoil
is driven by animation montages + per-ammo projectile data and is not a clean
numeric field, so it is reported absent rather than invented.

Name join: primarily against the prebuilt catalog src/data/items.json (keyed by
asset, already in 10 languages). Falls back to the localization .po Caption.

Output: out/weapons.json  (UTF-8, ensure_ascii=False)
Run:    python3 extract_weapons.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = "/tmp/scum-data/SCUM/Content/ConZ_Files"
ITEMS_CATALOG = "/root/scum-crintech/site/src/data/items.json"
LOC_BASE = "/tmp/scum-locres/SCUM/Content/Localization/Game"

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}

WEAPON_DIRS = [
    os.path.join(DUMP, "Items/Weapons/Ranged_Weapons"),
    os.path.join(DUMP, "Items/Weapons/New_Melee"),
    os.path.join(DUMP, "Items/Weapons"),  # top-level spears
]

# ---------------------------------------------------------------------------
# Generic FModel helpers
# ---------------------------------------------------------------------------

def load_objs(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def default_object(objs):
    """The ClassDefaultObject holding the stat Properties."""
    for o in objs:
        nm = str(o.get("Name", ""))
        if nm.startswith("Default__") and "Properties" in o:
            return o
    return None


def class_obj(objs):
    for o in objs:
        if o.get("Type") == "BlueprintGeneratedClass":
            return o
    return None


def objname_class(ref):
    """Extract a class name like Weapon_AK47_C from {ObjectName:"BlueprintGeneratedClass'Weapon_AK47_C'"}."""
    if not isinstance(ref, dict):
        return None
    on = ref.get("ObjectName") or ""
    m = re.search(r"'([^']+)'", on)
    inner = m.group(1) if m else on
    return inner.split("/")[-1].split(".")[-1] or None


def path_to_assetfile(objpath):
    """SCUM/.../Weapon_AK47.0  ->  /tmp/.../Weapon_AK47.json (absolute)."""
    if not objpath:
        return None
    p = objpath
    # strip trailing .<index>
    p = re.sub(r"\.\d+$", "", p)
    # SCUM/Content/... -> DUMP root is .../Content/ConZ_Files
    # objpath is like SCUM/Content/ConZ_Files/Items/Weapons/.../Asset
    m = re.search(r"Content/(.*)$", p)
    if not m:
        return None
    rel = m.group(1)  # ConZ_Files/Items/...
    full = "/tmp/scum-data/SCUM/Content/" + rel + ".json"
    return full


# ---------------------------------------------------------------------------
# Build a global class-name -> default Properties index, with inheritance
# ---------------------------------------------------------------------------

class WeaponFile:
    __slots__ = ("asset", "path", "objs", "props", "super_path")

    def __init__(self, asset, path, objs):
        self.asset = asset
        self.path = path
        self.objs = objs
        d = default_object(objs)
        self.props = d.get("Properties", {}) if d else {}
        c = class_obj(objs)
        ss = c.get("SuperStruct") if c else None
        self.super_path = path_to_assetfile(ss.get("ObjectPath")) if isinstance(ss, dict) else None


def collect_weapon_files():
    files = {}
    seen = set()
    for d in WEAPON_DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            asset = os.path.basename(f)[:-5]
            if asset.endswith("_ES"):
                continue  # editor-settings sibling, no stats
            if f in seen:
                continue
            seen.add(f)
            try:
                objs = load_objs(f)
            except Exception as e:  # pragma: no cover
                print(f"  WARN parse {f}: {e}", file=sys.stderr)
                continue
            files[os.path.realpath(f)] = WeaponFile(asset, f, objs)
    # index by asset name too
    by_asset = {wf.asset: wf for wf in files.values()}
    return files, by_asset


def resolved_props(wf, files_by_path):
    """Merge this default-object's props over its inheritance chain (parent first)."""
    chain = []
    cur = wf
    guard = 0
    while cur is not None and guard < 12:
        chain.append(cur)
        nxt = None
        if cur.super_path:
            rp = os.path.realpath(cur.super_path)
            nxt = files_by_path.get(rp)
        cur = nxt
        guard += 1
    merged = {}
    for w in reversed(chain):  # parent -> child so child overrides
        for k, v in w.props.items():
            merged[k] = v
    return merged


# ---------------------------------------------------------------------------
# Domain extraction
# ---------------------------------------------------------------------------

AMMO_LABELS = {
    "12Gauge": "12 Gauge",
    "40x46": "40x46mm Grenade",
    "AT4Rocket": "AT4 Rocket",
    "BowArrow": "Arrow",
    "Cal22": ".22 LR",
    "Cal30-06": ".30-06 Springfield",
    "Cal308": ".308 Winchester",
    "Cal338": ".338 Lapua Magnum",
    "Cal357": ".357 Magnum",
    "Cal38": ".38 Special",
    "Cal44Magnum": ".44 Magnum",
    "Cal45": ".45 ACP",
    "Cal50AE": ".50 AE",
    "Cal50BMG": ".50 BMG",
    "Cal545x39mm": "5.45x39mm",
    "Cal556x45mm": "5.56x45mm NATO",
    "Cal762x39mm": "7.62x39mm",
    "Cal762x54mm": "7.62x54mmR",
    "Cal792x57mm": "7.92x57mm Mauser",
    "Cal9mm": "9x19mm",
    "Cal9x39mm": "9x39mm",
    "CrossbowBolt": "Crossbow Bolt",
    "FlareCartridge": "Flare Cartridge",
    "RPGRocket": "RPG Rocket",
}


def ammo_tag_label(tag):
    short = tag.rsplit(".", 1)[-1]
    return AMMO_LABELS.get(short, short)


def detect_fire_modes(props):
    """Determine selectable fire modes from the weapon's gameplay properties.

    NOTE: the `TempWeaponStateFiring*` sub-objects are NOT a signal -- FModel
    exports every state template on every weapon, so they are always all present.
    The real signal is:
      * SupportedFiringModes  -> explicit selectable-modes list (best source)
      * WeaponFiringStateType -> the single firing behaviour (Manual/SemiAuto/...)
      * _armedNPCWeaponManualClass ending in _Automatic_C -> a full-auto weapon
        whose mode list was inherited/omitted; combined with a 2-position
        selector (FiringModeBoneRotations[1]) this is Auto + SingleShot.
    Returns a deduplicated, ordered list of mode labels, or [] if unknown.
    """
    def norm(v):
        return clean_enum(v) if isinstance(v, str) else v

    supported = props.get("SupportedFiringModes")
    if isinstance(supported, list) and supported:
        modes = [norm(m) for m in supported]
    else:
        modes = []
        fst = norm(props.get("WeaponFiringStateType"))
        if fst:
            modes.append(fst)
        # infer from the NPC firing-behaviour class when the explicit fields are absent
        mc = objname_class(props.get("_armedNPCWeaponManualClass")) or ""
        if "Automatic" in mc and "Automatic" not in modes:
            modes.append("Automatic")
            # a selector with a second position implies a single-fire mode too
            if "FiringModeBoneRotations[1]" in props and "SingleShot" not in modes:
                modes.append("SingleShot")
        elif not modes and ("Bow" in mc or "Crossbow" in mc or "Manual" in mc):
            # bows, crossbows and bolt/pump actions are manual-fire
            modes.append("Manual")
    # dedupe preserving order
    seen = set()
    out = []
    for m in modes:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def clean_enum(v):
    if isinstance(v, str) and "::" in v:
        return v.split("::", 1)[1]
    return v


def extract_attachment_sockets(props):
    sockets = []
    raw = props.get("_attachmentSockets")
    if not isinstance(raw, list):
        return sockets
    for group in raw:
        items = (group or {}).get("Items") if isinstance(group, dict) else None
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            mt = objname_class(it.get("MountType"))
            bone = it.get("BoneName")
            if not mt:
                continue
            sockets.append({
                "bone": bone if bone and bone != "None" else None,
                "mountType": mt,
            })
    return sockets


def build_magazine_index():
    """mount-type class -> list of {asset, capacity, ammo[]}."""
    idx = {}
    clipdir = os.path.join(DUMP, "Items/Weapons/Weapon_Clips")
    for f in sorted(glob.glob(os.path.join(clipdir, "*.json"))):
        asset = os.path.basename(f)[:-5]
        if asset.endswith("_ES"):
            continue
        try:
            objs = load_objs(f)
        except Exception:
            continue
        d = default_object(objs)
        if not d:
            continue
        p = d.get("Properties", {})
        cap = p.get("_capacity")
        if cap is None:
            continue
        mt = objname_class(p.get("_attachmentSocketMountType"))
        if not mt:
            continue
        idx.setdefault(mt, []).append({
            "asset": asset,
            "capacity": cap,
            "ammo": p.get("AmmunitionTags") or [],
        })
    return idx


def magazine_for_weapon(asset, sockets, mag_index):
    """Resolve magazines for a weapon from its magazine-socket mount types.

    A socket mount type can be shared by several magazines (e.g. an AK mag and
    an RPK drum both fit the 7.62x39 socket). We list every compatible magazine
    with its capacity, and pick a `capacity` heuristic: the magazine whose asset
    name best matches this weapon's asset, else the smallest (the standard mag).
    """
    cands = {}
    for s in sockets:
        mt = s["mountType"]
        if "Magazine" not in mt and "Clip" not in mt:
            continue
        for m in mag_index.get(mt, []):
            cands[m["asset"]] = m
    if not cands:
        return None
    fits = sorted(cands.values(), key=lambda m: (m["capacity"], m["asset"]))
    # prefer a magazine that references this weapon's name (e.g. Weapon_AK47 -> Magazine_AK47)
    wkey = asset.replace("Weapon_", "")
    matched = [m for m in fits if wkey and wkey in m["asset"]]
    chosen = matched[0] if matched else fits[0]
    return {
        "capacity": chosen["capacity"],
        "capacityMagazine": chosen["asset"],
        "compatibleMagazines": [
            {"asset": m["asset"], "capacity": m["capacity"]} for m in fits
        ],
    }


def slugify(name, asset):
    base = (name or "").strip() or asset
    s = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return s or asset.lower()


# --- name join helpers -----------------------------------------------------

def load_catalog_names():
    by_asset = {}
    if os.path.exists(ITEMS_CATALOG):
        cat = json.load(open(ITEMS_CATALOG, encoding="utf-8"))
        for it in cat:
            by_asset[it["asset"]] = it.get("name", {})
    return by_asset


def catalog_name_for(asset, catalog_names):
    """The in-game caption lives on the `_ES` blueprint, so try that first."""
    for cand in (asset + "_ES", asset):
        nm = catalog_names.get(cand)
        if nm:
            return nm
    return {}


def _unescape(s):
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


def parse_po_captions():
    """asset -> {lang: caption} from localization .po (fallback for names)."""
    # key per asset (from EN), then translations per lang on that key
    by_lang_key = {}
    src_asset_key = {}
    for lang, locale in LANG_TO_LOCALE.items():
        po = os.path.join(LOC_BASE, locale, "Game.po")
        if not os.path.exists(po):
            continue
        cur = {}
        raw = {"msgid": "", "msgstr": "", "msgctxt": ""}
        state = None
        d = {}

        def flush(cur, raw):
            key = cur.get("key")
            sl = cur.get("srcloc", "")
            if key:
                d[key] = _unescape(raw["msgstr"])
                if lang == "en" and "/Items/" in sl and sl.endswith(".Caption"):
                    base = sl.rsplit(".", 1)[0]
                    asset = base.split("/")[-1].split(".")[0]
                    src_asset_key[asset] = key

        with open(po, encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("#. SourceLocation:"):
                    cur["srcloc"] = line.split("\t", 1)[-1].strip()
                elif line.startswith("#. Key:"):
                    cur["key"] = line.split("\t", 1)[-1].strip()
                elif line.startswith("msgctxt "):
                    raw["msgctxt"] = line[len("msgctxt "):].strip().strip('"'); state = "ctxt"
                elif line.startswith("msgid "):
                    raw["msgid"] = line[len("msgid "):].strip().strip('"'); state = "id"
                elif line.startswith("msgstr "):
                    raw["msgstr"] = line[len("msgstr "):].strip().strip('"'); state = "str"
                elif line.startswith('"') and state:
                    k = {"id": "msgid", "str": "msgstr", "ctxt": "msgctxt"}[state]
                    raw[k] += line.strip().strip('"')
                elif line.strip() == "":
                    flush(cur, raw)
                    cur = {}; raw = {"msgid": "", "msgstr": "", "msgctxt": ""}; state = None
            flush(cur, raw)
        by_lang_key[lang] = d
    return src_asset_key, by_lang_key


def po_name_for(asset, src_asset_key, by_lang_key):
    key = src_asset_key.get(asset + "_ES") or src_asset_key.get(asset)
    if not key:
        return {}
    out = {}
    for lang in LANG_TO_LOCALE:
        v = by_lang_key.get(lang, {}).get(key, "")
        if v and v.strip():
            out[lang] = v
    return out


def resolve_name(asset, wf, files_by_path, catalog_names, src_asset_key, by_lang_key):
    """Direct caption first; else inherit the parent skin's name. Returns (names, source)."""
    direct = catalog_name_for(asset, catalog_names) or po_name_for(asset, src_asset_key, by_lang_key)
    if direct:
        return direct, "direct"
    # walk SuperStruct chain to borrow the base weapon's name (skins/variants)
    cur = wf
    guard = 0
    while cur is not None and guard < 12:
        if cur.super_path:
            parent = files_by_path.get(os.path.realpath(cur.super_path))
            if parent is not None:
                pn = catalog_name_for(parent.asset, catalog_names) or \
                     po_name_for(parent.asset, src_asset_key, by_lang_key)
                if pn:
                    return pn, f"inherited:{parent.asset}"
                cur = parent
                guard += 1
                continue
        break
    return {}, "none"


# ---------------------------------------------------------------------------

def main():
    files_by_path, by_asset = collect_weapon_files()
    mag_index = build_magazine_index()
    catalog_names = load_catalog_names()
    src_asset_key, by_lang_key = parse_po_captions()

    # WeaponDesc_Table: melee impact stats keyed by asset-ish name
    wdt = {}
    wdt_path = os.path.join(DUMP, "Data/WeaponDesc_Table.json")
    if os.path.exists(wdt_path):
        wdt = load_objs(wdt_path)[0].get("Rows", {})

    weapons = []
    seen_slug = {}
    for rp, wf in files_by_path.items():
        asset = wf.asset
        # skip obvious non-weapons that slipped in (e.g. nothing): require some signal
        props = resolved_props(wf, files_by_path)

        cat = clean_enum(props.get("WeaponCategory"))
        ammo_tags = props.get("AmmunitionTags") or []
        damage_per_shot = props.get("DamagePerShot")
        max_range = props.get("MaxRange")
        rof = props.get("ROF")
        zero_step = props.get("ZeroRangeStep")
        rarity = clean_enum(props.get("_rarity"))
        default_ammo = objname_class(props.get("DefaultAmmunitionItemClass"))
        max_loaded = props.get("MaxLoadedAmmo")

        # determine kind
        is_ranged = bool(ammo_tags) or damage_per_shot is not None or cat in {
            "AutomaticRifles", "Rifles", "Handguns", "Shotguns", "SubmachineGuns", "Bow",
        } or asset.startswith("Weapon_") or "Bow" in asset

        # fire modes (from resolved gameplay props, not template state objects)
        fire_modes = detect_fire_modes(props)

        # attachment sockets (resolved, child may extend)
        sockets = extract_attachment_sockets(props)

        # magazine resolution
        magazine = magazine_for_weapon(asset, sockets, mag_index) if is_ranged else None

        # melee impact stats from WeaponDesc_Table
        melee = wdt.get(asset)
        melee_stats = None
        if melee:
            melee_stats = {
                "damage": melee.get("Damage"),
                "energy": melee.get("Energy"),
                "sharpnessSlash": melee.get("SharpnessSlash"),
                "sharpnessPierce": melee.get("SharpnessPierce"),
                "impactSound": clean_enum(melee.get("ImpactSoundCategory")),
            }

        kind = "ranged" if is_ranged else "melee"

        # Skip pure infrastructure files with no name and no stats and no melee row.
        names, name_source = resolve_name(
            asset, wf, files_by_path, catalog_names, src_asset_key, by_lang_key)
        has_signal = bool(names) or is_ranged or melee_stats is not None or sockets
        if not has_signal:
            continue

        en = names.get("en") or asset
        slug = slugify(en, asset)
        if slug in seen_slug:
            seen_slug[slug] += 1
            slug = f"{slug}-{seen_slug[slug]}"
        else:
            seen_slug[slug] = 1

        rec = {
            "asset": asset,
            "slug": slug,
            "kind": kind,
            "name": names,
            "nameSource": name_source,
            "weaponCategory": cat,
            "rarity": rarity,
            "fireModes": fire_modes,
            "maxRange": max_range,
            "rof": rof,
            "zeroRangeStep": zero_step,
            "chamberCapacity": max_loaded,
            "ammunition": {
                "tags": ammo_tags,
                "labels": [ammo_tag_label(t) for t in ammo_tags],
                "defaultAmmoAsset": default_ammo,
            } if (ammo_tags or default_ammo) else None,
            "magazine": magazine,
            "damagePerShot": damage_per_shot,
            "melee": melee_stats,
            "attachments": sockets,
        }
        weapons.append(rec)

    weapons.sort(key=lambda w: (w["kind"], w["asset"]))

    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "weapons.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(weapons, f, ensure_ascii=False, indent=2)

    # stats
    n = len(weapons)
    ranged = sum(1 for w in weapons if w["kind"] == "ranged")
    melee = n - ranged
    named = sum(1 for w in weapons if w["name"])
    with_mag = sum(1 for w in weapons if w["magazine"])
    with_ammo = sum(1 for w in weapons if w["ammunition"])
    with_attach = sum(1 for w in weapons if w["attachments"])
    with_firemode = sum(1 for w in weapons if w["fireModes"])
    print(f"wrote {n} weapons -> {out_path}", file=sys.stderr)
    print(f"  ranged={ranged} melee={melee}", file=sys.stderr)
    print(f"  named(any lang)={named}  ammo={with_ammo}  magazine={with_mag} "
          f"attachments={with_attach} fireModes={with_firemode}", file=sys.stderr)
    cov = {l: sum(1 for w in weapons if l in w["name"]) for l in LANG_TO_LOCALE}
    print("  name coverage:", {l: cov[l] for l in LANG_TO_LOCALE}, file=sys.stderr)


if __name__ == "__main__":
    main()
