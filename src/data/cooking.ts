// Cooking recipes (recipes.json) accessor for the /recetas section.
import data from './recipes.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';

type L = Partial<Record<LangCode, string>>;
export interface CookOption { slug?: string | null; name: L; }
export interface CookSlot { title: L; options: CookOption[]; }
export interface CookRecipe {
  slug: string;
  name: L;
  description: L;
  category?: string | null;
  utility?: string[];
  cookingTime?: number | null;
  mainIngredients?: CookSlot[];
  optionalIngredients?: CookSlot[];
  result?: { slug?: string | null; name: L } | null;
}

export const COOKING = data as unknown as CookRecipe[];

const loc = (m: L | undefined, lang: LangCode) =>
  (m && (m[lang] ?? m[FALLBACK_LANG] ?? m[DEFAULT_LANG])) ?? '';

export const cookName = (r: CookRecipe, lang: LangCode) => loc(r.name, lang) || r.slug;
export const cookDesc = (r: CookRecipe, lang: LangCode) => loc(r.description, lang);
export const slotTitle = (s: CookSlot, lang: LangCode) => loc(s.title, lang);
export const optName = (o: CookOption, lang: LangCode) => loc(o.name, lang);

export interface CookGroup { category: string; recipes: CookRecipe[]; }
export function cookingByCategory(lang: LangCode): CookGroup[] {
  const by = new Map<string, CookRecipe[]>();
  for (const r of COOKING) {
    const c = r.category || 'Other';
    const a = by.get(c); if (a) a.push(r); else by.set(c, [r]);
  }
  const groups = [...by].map(([category, recipes]) => {
    recipes.sort((a, b) => cookName(a, lang).localeCompare(cookName(b, lang), lang));
    return { category, recipes };
  });
  groups.sort((a, b) => b.recipes.length - a.recipes.length || a.category.localeCompare(b.category));
  return groups;
}
