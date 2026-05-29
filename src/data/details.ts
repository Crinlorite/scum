// Joins the game-data datasets onto a single item (by slug) so item pages can
// show real stats, weapon stats, how-to-craft, and cooking recipes that use it.
// All big JSON imports here are build-time only (never shipped to the client).
import itemStats from './item_stats.json';
import weaponsData from './weapons.json';
import recipesData from './recipes.json';
import craftingData from './crafting.json';
import economyData from './economy.json';
import lootData from './loot.json';
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

export interface EconomyRec {
  slug?: string | null; category?: string | null; traders?: string[];
  canBuy?: boolean; canSell?: boolean; requiredFame?: number | null;
  buyPrice?: number | null; sellPrice?: number | null; currency?: string | null;
}
export interface LootRec { slug: string; spawns?: { location: string; rarity?: string }[]; }

const STATS = itemStats as unknown as ItemStatRec[];
const WEAPONS = weaponsData as unknown as WeaponRec[];
const RECIPES = recipesData as unknown as CookRec[];
const CRAFTING = craftingData as unknown as CraftRec[];
const ECONOMY = economyData as unknown as EconomyRec[];
const LOOT = lootData as unknown as LootRec[];

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

const economyBySlug = new Map<string, EconomyRec>();
for (const e of ECONOMY) if (e.slug && !economyBySlug.has(e.slug)) economyBySlug.set(e.slug, e);

const lootBySlug = new Map<string, LootRec>();
for (const l of LOOT) if (l.slug && !lootBySlug.has(l.slug)) lootBySlug.set(l.slug, l);

export interface ItemDetail {
  stats?: ItemStatRec;
  weapon?: WeaponRec;
  craftedBy: CraftRec[];
  cookingUsing: CookRec[];
  economy?: EconomyRec;
  loot?: LootRec;
}

export function itemDetail(slug: string): ItemDetail {
  return {
    stats: statsBySlug.get(slug),
    weapon: weaponBySlug.get(slug),
    craftedBy: craftedBySlug.get(slug) ?? [],
    cookingUsing: cookingUsingSlug.get(slug) ?? [],
    economy: economyBySlug.get(slug),
    loot: lootBySlug.get(slug),
  };
}

export function hasDetail(d: ItemDetail): boolean {
  return !!(d.stats || d.weapon || d.craftedBy.length || d.cookingUsing.length || d.economy || d.loot?.spawns?.length);
}
