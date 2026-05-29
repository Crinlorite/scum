// Official SCUM item names + descriptions in every supported language,
// extracted from the game's own localization export.
//
// Source of truth: tools/locres-import/  (run extract_items.py to regenerate
// src/data/items.json from the game's Game.po files). The names here are the
// real in-game captions — NOT literal translations — so a Spanish player sees
// exactly what the game shows them.
//
// `items.json` is imported as data; we cast through `unknown` to keep
// `astro check` fast (it would otherwise infer a ~2k-element literal type).
import itemsData from './items.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';

/** A localized string map; not every language is guaranteed present. */
export type Localized = Partial<Record<LangCode, string>>;

export interface ScumItem {
  /** Game asset name, e.g. "Weapon_AWP_ES". Stable internal id. */
  asset: string;
  /** Game category from the asset path: Food, Weapons, Clothes, Ammunition… */
  category: string;
  /** URL-safe slug derived from the English name (unique). */
  slug: string;
  /** Localization GUID for the name (joins translations across languages). */
  nameKey: string;
  /** Localization GUID for the description, if the item has one. */
  descKey: string | null;
  name: Localized;
  description: Localized;
}

export const ITEMS = itemsData as unknown as ScumItem[];

/** Official item name in `lang`, falling back EN → ES → asset id. */
export function itemName(item: ScumItem, lang: LangCode): string {
  return (
    item.name[lang] ??
    item.name[FALLBACK_LANG] ??
    item.name[DEFAULT_LANG] ??
    item.asset
  );
}

/** Official description in `lang`, falling back EN → ES, or undefined. */
export function itemDescription(item: ScumItem, lang: LangCode): string | undefined {
  return item.description[lang] ?? item.description[FALLBACK_LANG] ?? item.description[DEFAULT_LANG];
}

/** Distinct game categories, sorted, e.g. ["Ammunition", "Clothes", …]. */
export const ITEM_CATEGORIES: readonly string[] = [
  ...new Set(ITEMS.map((i) => i.category)),
].sort();

export function itemsByCategory(category: string): ScumItem[] {
  return ITEMS.filter((i) => i.category === category);
}

export function findItemBySlug(slug: string): ScumItem | undefined {
  return ITEMS.find((i) => i.slug === slug);
}

// Localized labels for the game's item categories. Anything not listed (or a
// language with no label) falls back to the de-underscored raw category name.
const CATEGORY_LABELS: Record<string, Partial<Record<LangCode, string>>> = {
  Food: { es: 'Comida', en: 'Food' },
  Crafting: { es: 'Fabricación', en: 'Crafting' },
  Weapons: { es: 'Armas', en: 'Weapons' },
  Equipment: { es: 'Equipo', en: 'Equipment' },
  Clothes: { es: 'Ropa', en: 'Clothing' },
  Ammunition: { es: 'Munición', en: 'Ammunition' },
  Farming: { es: 'Agricultura', en: 'Farming' },
  Vehicle: { es: 'Vehículos', en: 'Vehicles' },
  Christmas_Items: { es: 'Navidad', en: 'Christmas' },
  Drink: { es: 'Bebidas', en: 'Drinks' },
  Fishing: { es: 'Pesca', en: 'Fishing' },
  Medications: { es: 'Medicinas', en: 'Medications' },
  Fortifications: { es: 'Fortificaciones', en: 'Fortifications' },
  Traps: { es: 'Trampas', en: 'Traps' },
  Books: { es: 'Libros', en: 'Books' },
  Economy: { es: 'Economía', en: 'Economy' },
  Smokables: { es: 'Fumables', en: 'Smokables' },
  Grenades: { es: 'Granadas', en: 'Grenades' },
  MetalDetector: { es: 'Detector de metales', en: 'Metal Detector' },
  BaseBuilding: { es: 'Construcción', en: 'Base Building' },
  Explosives: { es: 'Explosivos', en: 'Explosives' },
  Binoculars: { es: 'Prismáticos', en: 'Binoculars' },
  DigitalDeluxeContent: { es: 'Edición Deluxe', en: 'Deluxe Edition' },
};

export function categoryLabel(category: string, lang: LangCode): string {
  const m = CATEGORY_LABELS[category];
  return m?.[lang] ?? m?.[FALLBACK_LANG] ?? category.replace(/_/g, ' ');
}

export interface CategoryGroup {
  category: string;
  label: string;
  items: ScumItem[];
}

/** Items grouped by category, sorted by item count (desc), each list A→Z. */
export function itemsGroupedByCategory(lang: LangCode): CategoryGroup[] {
  const byCat = new Map<string, ScumItem[]>();
  for (const it of ITEMS) {
    const arr = byCat.get(it.category) ?? [];
    arr.push(it);
    byCat.set(it.category, arr);
  }
  const groups: CategoryGroup[] = [];
  for (const [category, items] of byCat) {
    items.sort((a, b) => itemName(a, lang).localeCompare(itemName(b, lang), lang));
    groups.push({ category, label: categoryLabel(category, lang), items });
  }
  groups.sort((a, b) => b.items.length - a.items.length || a.label.localeCompare(b.label));
  return groups;
}
