#!/usr/bin/env python3
"""
Extract official SCUM item names + descriptions, in every site language, from
the game's exported localization (.po files under
SCUM/Content/Localization/Game/<locale>/Game.po).

Why .po and not the binary .locres?  The .po carries a `#. SourceLocation`
comment per entry that tells us *what* each string is (e.g. an item Caption vs
a Description, and the item's category from its asset path).  The compiled
.locres only has opaque GUID keys -> text, so it can't tell items apart without
an external asset map.  The GUID `#. Key` is identical across locales, so we
join translations on it.

Item naming convention in SCUM localization:
  SourceLocation = /Game/ConZ_Files/Items/<Category>/.../<Asset>.Default__<Asset>_C.Caption
    .Caption     -> the official, in-game display name  (what we want)
    .Description -> the in-game description
Caption and Description for the same item share the asset "base"
(everything up to the final '.'), but have different GUID keys.

Output: out/items.json  — list of items, each:
  { "asset", "category", "slug", "nameKey", "descKey",
    "name": {lang: str, ...}, "description": {lang: str, ...} }

Run:  python3 extract_items.py [/path/to/Localization/Game]
"""
from __future__ import annotations
import json
import os
import re
import sys

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
SOURCE_LANG = "en"  # canonical identity (asset/category/which entries are items)

ITEMS_MARKER = "/Items/"


def _unescape(s: str) -> str:
    out = []
    i = 0
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
    """Content of a `msgid "..."` / `msgstr "..."` / continuation `"..."` line."""
    body = line[prefix_len:].strip()
    if len(body) >= 2 and body[0] == '"' and body[-1] == '"':
        body = body[1:-1]
    return body  # still escaped; unescape once fully assembled


def parse_po(path: str) -> list[dict]:
    """Parse a UE-exported .po into entries {key, srcloc, msgid, msgstr}."""
    entries: list[dict] = []
    cur: dict = {}
    state = None  # 'id' | 'str' | 'ctxt'
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
            if line.startswith("#. SourceLocation:"):
                cur["srcloc"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("#. Key:"):
                cur["key"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgctxt "):
                raw["msgctxt"] = _po_quoted(line, len("msgctxt ")); state = "ctxt"
            elif line.startswith("msgid "):
                raw["msgid"] = _po_quoted(line, len("msgid ")); state = "id"
            elif line.startswith("msgstr "):
                raw["msgstr"] = _po_quoted(line, len("msgstr ")); state = "str"
            elif line.startswith('"') and state:
                key = {"id": "msgid", "str": "msgstr", "ctxt": "msgctxt"}[state]
                raw[key] += _po_quoted(line, 0)
            elif line.strip() == "":
                if cur or any(raw.values()):
                    flush(); cur = {}; raw = {"msgid": "", "msgstr": "", "msgctxt": ""}; state = None
    if cur or any(raw.values()):
        flush()
    return entries


def slugify(name: str, asset: str) -> str:
    base = name.strip() or asset
    s = base.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or asset.lower()


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else \
        "/tmp/scum-locres/SCUM/Content/Localization/Game"
    here = os.path.dirname(os.path.abspath(__file__))

    # key -> msgstr per language
    by_lang_key: dict[str, dict[str, str]] = {}
    src_entries: list[dict] = []
    for lang, locale in LANG_TO_LOCALE.items():
        po = os.path.join(base_dir, locale, "Game.po")
        if not os.path.exists(po):
            print(f"  WARN missing {po}", file=sys.stderr); continue
        ents = parse_po(po)
        by_lang_key[lang] = {e["key"]: e["msgstr"] for e in ents if e.get("key")}
        if lang == SOURCE_LANG:
            src_entries = ents
        print(f"  parsed {lang:5} ({locale}): {len(ents)} entries", file=sys.stderr)

    # Group source (EN) item entries by asset base -> {suffix: entry}
    bases: dict[str, dict] = {}
    for e in src_entries:
        sl = e.get("srcloc") or ""
        if ITEMS_MARKER not in sl or "." not in sl:
            continue
        base, suffix = sl.rsplit(".", 1)
        bucket = bases.setdefault(base, {})
        bucket[suffix] = e

    items = []
    seen_slug: dict[str, int] = {}
    for base, suffixes in bases.items():
        name_e = suffixes.get("Caption")
        if not name_e or not (name_e.get("msgstr") or "").strip():
            continue  # an item is something with an official name (Caption)
        desc_e = suffixes.get("Description")
        asset = base.split("/")[-1].split(".")[0]
        category = base.split(ITEMS_MARKER, 1)[1].split("/")[0]

        def collect(entry):
            if not entry or not entry.get("key"):
                return {}
            k = entry["key"]
            out = {}
            for lang in LANG_TO_LOCALE:
                v = by_lang_key.get(lang, {}).get(k, "")
                if v and v.strip():
                    out[lang] = v
            return out

        name = collect(name_e)
        if SOURCE_LANG not in name:
            name[SOURCE_LANG] = name_e["msgstr"]
        slug = slugify(name.get(SOURCE_LANG, ""), asset)
        if slug in seen_slug:
            seen_slug[slug] += 1
            slug = f"{slug}-{seen_slug[slug]}"
        else:
            seen_slug[slug] = 1

        items.append({
            "asset": asset,
            "category": category,
            "slug": slug,
            "nameKey": name_e["key"],
            "descKey": desc_e["key"] if desc_e and desc_e.get("key") else None,
            "name": name,
            "description": collect(desc_e),
        })

    items.sort(key=lambda it: (it["category"], it["slug"]))
    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "items.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # Stats
    langs = list(LANG_TO_LOCALE)
    cov = {l: sum(1 for it in items if l in it["name"]) for l in langs}
    print(f"\nwrote {len(items)} items -> {out_path}", file=sys.stderr)
    print("name coverage per language:", file=sys.stderr)
    for l in langs:
        pct = 100 * cov[l] / max(1, len(items))
        print(f"  {l:5}: {cov[l]:4}/{len(items)}  ({pct:5.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
