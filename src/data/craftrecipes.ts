// Crafting recipes (crafting.json) accessor for the /crafteo section.
import data from './crafting.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';

type L = Partial<Record<LangCode, string>>;
export interface CraftOption { tag?: string; name?: L; }
export interface CraftIngredient { options?: CraftOption[]; }
export interface CraftRecipe {
  slug: string;
  type?: string;
  name: L;
  description: L;
  categories?: string[];
  skill?: string | null;
  duration?: number | null;
  productQuantity?: number | null;
  result?: { slug?: string | null; name: L } | null;
  ingredients?: CraftIngredient[];
  tools?: { name?: L }[];
}

export const CRAFTING = data as unknown as CraftRecipe[];

const loc = (m: L | undefined, lang: LangCode) =>
  (m && (m[lang] ?? m[FALLBACK_LANG] ?? m[DEFAULT_LANG])) ?? '';

export const craftBySlug = (slug: string) => CRAFTING.find((r) => r.slug === slug);
export const craftName = (r: CraftRecipe, lang: LangCode) => loc(r.name, lang) || r.slug;
export const craftDesc = (r: CraftRecipe, lang: LangCode) => loc(r.description, lang);
export function ingredientText(ing: CraftIngredient, lang: LangCode): string {
  return (ing.options ?? []).map((o) => loc(o.name, lang)).filter(Boolean).join(' / ');
}

const SKILL_LABELS: Record<string, L> = {
  Engineering: { es: 'Ingeniería', en: 'Engineering' },
  Cooking: { es: 'Cocina', en: 'Cooking' },
  Medical: { es: 'Medicina', en: 'Medical' },
  Awareness: { es: 'Percepción', en: 'Awareness' },
  Survival: { es: 'Supervivencia', en: 'Survival' },
  Rifles: { es: 'Rifles', en: 'Rifles' },
  Archery: { es: 'Arquería', en: 'Archery' },
  Demolition: { es: 'Demolición', en: 'Demolition' },
  Thievery: { es: 'Hurto', en: 'Thievery' },
  Camouflage: { es: 'Camuflaje', en: 'Camouflage' },
};
export function skillLabel(skill: string | null | undefined, lang: LangCode): string {
  if (!skill) return '';
  return SKILL_LABELS[skill]?.[lang] ?? SKILL_LABELS[skill]?.[FALLBACK_LANG] ?? skill;
}

export interface CraftGroup { key: string; label: string; recipes: CraftRecipe[]; }
/** Group by type (item vs placeable) then it reads cleanly; placeables are base-building. */
export function craftingByGroup(lang: LangCode): CraftGroup[] {
  const TYPE_LABEL: Record<string, L> = {
    item: { es: 'Objetos', en: 'Items' },
    placeable: { es: 'Construcción y colocables', en: 'Building & placeables' },
  };
  const by = new Map<string, CraftRecipe[]>();
  for (const r of CRAFTING) {
    const k = r.type === 'placeable' ? 'placeable' : 'item';
    const a = by.get(k); if (a) a.push(r); else by.set(k, [r]);
  }
  const groups = [...by].map(([key, recipes]) => {
    recipes.sort((a, b) => craftName(a, lang).localeCompare(craftName(b, lang), lang));
    return { key, label: TYPE_LABEL[key]?.[lang] ?? TYPE_LABEL[key]?.[FALLBACK_LANG] ?? key, recipes };
  });
  groups.sort((a, b) => a.key.localeCompare(b.key));
  return groups;
}
