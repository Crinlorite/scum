// In-game Codex (the official game manual) as structured, localized articles.
// Built by tools/locres-import/extract_codex.py from Manual/Codex/Entries.
import codexData from './codex.json';
import codexImagesData from './codex_images.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';

const CODEX_IMG = new Set(codexImagesData as string[]);
export const codexImageUrl = (img?: string): string | null => (img && CODEX_IMG.has(img) ? `/manual-img/${img}.webp` : null);

type L = Partial<Record<LangCode, string>>;
export interface CodexBlock { t: 'title' | 'text' | 'image'; text?: L; img?: string; }
export interface CodexArticle { id: string; slug: string; category: string; title: L; desc: L; blocks: CodexBlock[]; }

export const CODEX = codexData as unknown as CodexArticle[];

const loc = (m: L | undefined, lang: LangCode) => (m && (m[lang] ?? m[FALLBACK_LANG] ?? m[DEFAULT_LANG])) ?? '';
export const codexTitle = (e: CodexArticle, lang: LangCode) => loc(e.title, lang) || e.slug;
export const codexDesc = (e: CodexArticle, lang: LangCode) => loc(e.desc, lang);
export const blockText = (b: CodexBlock, lang: LangCode) => loc(b.text, lang);
export const codexBySlug = (slug: string) => CODEX.find((e) => e.slug === slug);

const CAT: Record<string, L> = {
  Survival: { es: 'Supervivencia', en: 'Survival' },
  Metabolism: { es: 'Metabolismo', en: 'Metabolism' },
  Health: { es: 'Salud', en: 'Health' },
  Movement: { es: 'Movimiento', en: 'Movement' },
  Inventory: { es: 'Inventario', en: 'Inventory' },
  Crafting: { es: 'Fabricación', en: 'Crafting' },
  BaseBuilding: { es: 'Construcción de base', en: 'Base building' },
  AttributesAndSkills: { es: 'Atributos y habilidades', en: 'Attributes & skills' },
  Economy: { es: 'Economía', en: 'Economy' },
  Quests: { es: 'Misiones', en: 'Quests' },
  Squads: { es: 'Escuadras', en: 'Squads' },
  Vehicles: { es: 'Vehículos', en: 'Vehicles' },
  Minigames: { es: 'Minijuegos', en: 'Minigames' },
  '': { es: 'General', en: 'General' },
};
export function codexCategoryLabel(cat: string, lang: LangCode): string {
  return CAT[cat]?.[lang] ?? CAT[cat]?.[FALLBACK_LANG] ?? (cat || 'General');
}

export interface CodexGroup { cat: string; label: string; entries: CodexArticle[]; }
export function codexByCategory(lang: LangCode): CodexGroup[] {
  const by = new Map<string, CodexArticle[]>();
  for (const e of CODEX) {
    const a = by.get(e.category);
    if (a) a.push(e); else by.set(e.category, [e]);
  }
  const groups = [...by].map(([cat, entries]) => {
    entries.sort((a, b) => codexTitle(a, lang).localeCompare(codexTitle(b, lang)));
    return { cat, label: codexCategoryLabel(cat, lang), entries };
  });
  groups.sort((a, b) => b.entries.length - a.entries.length || a.label.localeCompare(b.label));
  return groups;
}
