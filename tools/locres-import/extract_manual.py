#!/usr/bin/env python3
"""
Extract the in-game **Manual / Survival Tips / Cooking / Crafting / Skills /
Health / Metabolism** text from SCUM's own localization (Game.po per language).

Same legitimacy & method as extract_items.py: this is the game's OWN text
(factual game reference, documented on an unofficial fan wiki with disclaimer),
NOT scraped from another wiki. Joined across languages by the GUID `#. Key`.

Use: this is *source material* to compose curated wiki guides — not meant to be
dumped verbatim. Output:
  out/manual.json   — { table: [ {key, text:{lang:str}} ] }
  out/manual_en.md  — readable EN dump grouped by table (review / compose input)

Run:  python3 extract_manual.py [/path/to/Localization/Game]
"""
from __future__ import annotations
import json, os, re, sys

LANG_TO_LOCALE = {
    "es": "es-ES", "en": "en-US", "de": "de-DE", "ru": "ru-RU",
    "zh": "zh-Hans-CN", "fr": "fr-FR", "pt": "pt-BR", "zh-tw": "zh-Hant",
    "th": "th-TH", "pl": "pl-PL",
}
SOURCE_LANG = "en"

# String tables / suffixes that hold guide-style prose (from .po SourceLocation).
GUIDE_TABLES = [
    "ST_UI_Manual", "ST_UI_SurvivalTips", "ST_UI_Cooking", "ST_UI_Crafting",
    "ST_Crafting", "ST_UI_Skills", "ST_UI_Health", "ST_Metabolism",
    "ST_UI_Metabolism",
]


def _unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def _camel(s: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s).strip()


def clean(text: str) -> str:
    if not text:
        return ""
    # $$Mapping_HoldBreath$$ -> "Hold Breath"
    text = re.sub(r"\$\$Mapping_([A-Za-z0-9_]+)\$\$", lambda m: _camel(m.group(1).replace("_", " ")), text)
    # other $$Token$$ -> drop the $$ markers
    text = re.sub(r"\$\$([^$]*)\$\$", r"\1", text)
    # UE rich-text tags: <blue>..</>, <Important>..</>, <color=..>..</> -> keep inner text
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
    text = text.replace("</>", "")
    return text.strip()


def _po_q(line: str, p: int) -> str:
    b = line[p:].strip()
    return b[1:-1] if len(b) >= 2 and b[0] == '"' and b[-1] == '"' else b


def parse_po(path: str) -> list[dict]:
    ents, cur, state = [], {}, None
    raw = {"msgid": "", "msgstr": ""}

    def flush():
        if cur.get("key") or raw["msgid"] or raw["msgstr"]:
            cur["msgid"] = _unescape(raw["msgid"]); cur["msgstr"] = _unescape(raw["msgstr"]); ents.append(dict(cur))

    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#. SourceLocation:"):
                cur["srcloc"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("#. Key:"):
                cur["key"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("msgid "):
                raw["msgid"] = _po_q(line, 6); state = "id"
            elif line.startswith("msgstr "):
                raw["msgstr"] = _po_q(line, 7); state = "str"
            elif line.startswith('"') and state:
                raw[{"id": "msgid", "str": "msgstr"}[state]] += _po_q(line, 0)
            elif line.strip() == "":
                if cur or any(raw.values()):
                    flush(); cur, raw, state = {}, {"msgid": "", "msgstr": ""}, None
    if cur or any(raw.values()):
        flush()
    return ents


def table_of(srcloc: str) -> str | None:
    if not srcloc or "." not in srcloc:
        return None
    suf = srcloc.rsplit(".", 1)[1]
    return suf if suf in GUIDE_TABLES else None


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "/tmp/scum-locres/SCUM/Content/Localization/Game"
    here = os.path.dirname(os.path.abspath(__file__))

    by_lang_key: dict[str, dict[str, str]] = {}
    src: list[dict] = []
    for lang, locale in LANG_TO_LOCALE.items():
        po = os.path.join(base, locale, "Game.po")
        if not os.path.exists(po):
            print(f"  WARN missing {po}", file=sys.stderr); continue
        ents = parse_po(po)
        by_lang_key[lang] = {e["key"]: clean(e["msgstr"]) for e in ents if e.get("key")}
        if lang == SOURCE_LANG:
            src = ents
        print(f"  parsed {lang:5} ({locale})", file=sys.stderr)

    out: dict[str, list] = {t: [] for t in GUIDE_TABLES}
    seen = set()
    for e in src:
        t = table_of(e.get("srcloc") or "")
        if not t or not e.get("key") or e["key"] in seen:
            continue
        seen.add(e["key"])
        en_txt = clean(e.get("msgstr") or "")
        if len(en_txt) < 3:
            continue
        text = {}
        for lang in LANG_TO_LOCALE:
            v = by_lang_key.get(lang, {}).get(e["key"], "")
            if v and v.strip():
                text[lang] = v
        if SOURCE_LANG not in text:
            text[SOURCE_LANG] = en_txt
        out[t].append({"key": e["key"], "text": text})

    out_dir = os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manual.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # readable EN dump for review / composition input
    with open(os.path.join(out_dir, "manual_en.md"), "w", encoding="utf-8") as f:
        for t in GUIDE_TABLES:
            f.write(f"\n## {t}  ({len(out[t])} entries)\n\n")
            for row in out[t]:
                f.write(f"- {row['text'].get('en','')}\n")

    total = sum(len(v) for v in out.values())
    print(f"\nwrote {total} guide entries -> out/manual.json + manual_en.md", file=sys.stderr)
    for t in GUIDE_TABLES:
        cov_es = sum(1 for r in out[t] if 'es' in r['text'])
        print(f"  {t:22} {len(out[t]):4}  (es {cov_es})", file=sys.stderr)


if __name__ == "__main__":
    main()
