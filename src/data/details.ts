// Joins the game-data datasets onto a single item (by slug) so item pages can
// show real stats, weapon stats, how-to-craft, and cooking recipes that use it.
// All big JSON imports here are build-time only (never shipped to the client).
import itemStats from './item_stats.json';
import weaponsData from './weapons.json';
import recipesData from './recipes.json';
import craftingData from './crafting.json';
import type { LangCode } from '../i18n/languages';

type Localized = Partial<Record<LangCode, string>>;

export interface ItemStatRec {
  slug: string;
  category?: string;
  stats?: Record<string, number | string | boolean>;
  food?: { kcalPer100gDerived?: number; nutrients?: Record<string, number>; consumptionMethod?: string } | null;
}
export interface WeaponRec {
  slug: string;
  kind?: string;
  weaponCategory?: string | null;
  rarity?: string | null;
  fireModes?: string[];
  maxRange?: number | null;
  rof?: number | null;
  damagePerShot?: number | null;
  ammunition?: { labels?: string[] } | null;
  magazine?: { capacity?: number } | null;
  melee?: { damage?: number } | null;
}
export interface CraftRec {
  slug: string;
  name: Localized;
  skill?: string | null;
  duration?: number | null;
  productQuantity?: number | null;
  ingredients?: { options?: { name?: Localized }[] }[];
  result?: { slug?: string | null };
}
export interface CookRec {
  slug: string;
  name: Localized;
  mainIngredients?: { options?: { slug?: string | null }[] }[];
  optionalIngredients?: { options?: { slug?: string | null }[] }[];
}

const STATS = itemStats as unknown as ItemStatRec[];
const WEAPONS = weaponsData as unknown as WeaponRec[];
const RECIPES = recipesData as unknown as CookRec[];
const CRAFTING = craftingData as unknown as CraftRec[];

function push<K, V>(m: Map<K, V[]>, k: K, v: V) {
  const a = m.get(k);
  if (a) a.push(v); else m.set(k, [v]);
}

const statsBySlug = new Map<string, ItemStatRec>();
for (const s of STATS) if (s.slug && !statsBySlug.has(s.slug)) statsBySlug.set(s.slug, s);

const weaponBySlug = new Map<string, WeaponRec>();
for (const w of WEAPONS) if (w.slug && !weaponBySlug.has(w.slug)) weaponBySlug.set(w.slug, w);

const craftedBySlug = new Map<string, CraftRec[]>();
for (const c of CRAFTING) {
  const s = c.result?.slug;
  if (s) push(craftedBySlug, s, c);
}

const cookingUsingSlug = new Map<string, CookRec[]>();
for (const r of RECIPES) {
  const used = new Set<string>();
  for (const grp of [...(r.mainIngredients ?? []), ...(r.optionalIngredients ?? [])])
    for (const o of grp.options ?? []) if (o.slug) used.add(o.slug);
  for (const s of used) push(cookingUsingSlug, s, r);
}

export interface ItemDetail {
  stats?: ItemStatRec;
  weapon?: WeaponRec;
  craftedBy: CraftRec[];
  cookingUsing: CookRec[];
}

export function itemDetail(slug: string): ItemDetail {
  return {
    stats: statsBySlug.get(slug),
    weapon: weaponBySlug.get(slug),
    craftedBy: craftedBySlug.get(slug) ?? [],
    cookingUsing: cookingUsingSlug.get(slug) ?? [],
  };
}

export function hasDetail(d: ItemDetail): boolean {
  return !!(d.stats || d.weapon || d.craftedBy.length || d.cookingUsing.length);
}
