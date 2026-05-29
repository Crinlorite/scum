# locres-import — official SCUM item names

Extracts the **official, in-game item names and descriptions** (all supported
site languages) straight from SCUM's own localization data, so the wiki shows
exactly what players see in-game — not literal/machine translations.

## Where the data comes from

SCUM ships Unreal Engine localization under
`SCUM/Content/Localization/Game/<locale>/`. We obtained those files from a
local game install and uploaded the zip to the VPS (`/tmp/scum-locres.zip`).

Each locale folder has:
- `Game.locres` — the **compiled** runtime table (GUID key → text). Opaque:
  no hint of what each string is.
- `Game.po` — the **gettext export**. Same strings, but each entry carries a
  `#. SourceLocation` comment telling us *what* it is (item Caption vs
  Description, and the item's category from its asset path). **This is what we
  parse.** The `#. Key` GUID is identical across locales, so it joins
  translations.

Item naming convention in the data:
```
/Game/ConZ_Files/Items/<Category>/.../<Asset>.Default__<Asset>_C.Caption
    .Caption     → official display name   (what we extract as the item name)
    .Description → in-game description
```

## Files

- `locres.py` — pure-Python parser for the binary `.locres` (UE v1–v4).
  Kept for completeness/verification; **not** used by the item extraction
  (the `.po` is richer). Fixed bugs: magic GUID ends in `…7F1B` (not `8B`),
  and v3/v4 "Optimized" entries are prefixed by a `uint32` hash on both the
  namespace and the key.
- `extract_items.py` — parses every language's `Game.po`, filters item
  Captions/Descriptions, joins translations by GUID, writes `out/items.json`.

## Regenerate

```bash
# 1. unzip the game localization (if /tmp was cleared)
mkdir -p /tmp/scum-locres && unzip -o /tmp/scum-locres.zip -d /tmp/scum-locres

# 2. extract  (defaults to /tmp/scum-locres/SCUM/Content/Localization/Game)
python3 extract_items.py
#   → writes out/items.json  (≈2k items, name coverage ~96% per language)

# 3. publish to the site
cp out/items.json ../../src/data/items.json
```

The site consumes it via `src/data/items.ts` (`ITEMS`, `itemName(item, lang)`,
`itemsByCategory`, …), with EN→ES fallback for the ~75 items the game itself
leaves untranslated.

## Languages

Site code → SCUM locale: `es→es-ES en→en-US de→de-DE ru→ru-RU zh→zh-Hans-CN
fr→fr-FR pt→pt-BR zh-tw→zh-Hant th→th-TH pl→pl-PL`.
