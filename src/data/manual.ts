// In-game Manual + Survival Tips, verbatim from SCUM's own localization,
// in every supported language (see tools/locres-import/extract_manual.py).
// This is the game's OWN text (official, professionally translated) — our own
// original guides, when we write them, will live in the wiki and be marked as
// such. Categories are assigned heuristically; the text itself is untouched.
import manualData from './manual.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';

export interface ManualEntry {
  id: string;
  cat: string;
  text: Partial<Record<LangCode, string>>;
}

export const MANUAL = manualData as unknown as ManualEntry[];

/** Entry text in `lang`, falling back EN → ES. */
export function entryText(e: ManualEntry, lang: LangCode): string {
  return e.text[lang] ?? e.text[FALLBACK_LANG] ?? e.text[DEFAULT_LANG] ?? '';
}

const CAT_LABELS: Record<string, Partial<Record<LangCode, string>>> = {
  tips:        { es: 'Consejos de supervivencia', en: 'Survival tips' },
  metabolism:  { es: 'Metabolismo', en: 'Metabolism' },
  health:      { es: 'Salud', en: 'Health' },
  combat:      { es: 'Combate', en: 'Combat' },
  crafting:    { es: 'Crafteo y construcción', en: 'Crafting & building' },
  agriculture: { es: 'Agricultura', en: 'Farming' },
  animals:     { es: 'Animales y caza', en: 'Animals & hunting' },
  survival:    { es: 'Supervivencia', en: 'Survival' },
  vehicles:    { es: 'Vehículos', en: 'Vehicles' },
  skills:      { es: 'Habilidades', en: 'Skills' },
  controls:    { es: 'Controles', en: 'Controls' },
  general:     { es: 'General', en: 'General' },
};

export function manualCatLabel(cat: string, lang: LangCode): string {
  const m = CAT_LABELS[cat];
  return m?.[lang] ?? m?.[FALLBACK_LANG] ?? cat;
}

const ORDER = [
  'tips', 'metabolism', 'health', 'combat', 'crafting', 'agriculture',
  'animals', 'survival', 'vehicles', 'skills', 'controls', 'general',
];

export interface ManualGroup { cat: string; label: string; entries: ManualEntry[]; }

/** Entries grouped by category, in a sensible reading order. */
export function manualByCategory(lang: LangCode): ManualGroup[] {
  const by = new Map<string, ManualEntry[]>();
  for (const e of MANUAL) {
    const arr = by.get(e.cat) ?? [];
    arr.push(e);
    by.set(e.cat, arr);
  }
  const groups: ManualGroup[] = [];
  for (const [cat, entries] of by) groups.push({ cat, label: manualCatLabel(cat, lang), entries });
  const rank = (c: string) => { const i = ORDER.indexOf(c); return i === -1 ? 99 : i; };
  groups.sort((a, b) => rank(a.cat) - rank(b.cat) || a.label.localeCompare(b.label));
  return groups;
}
