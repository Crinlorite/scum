// Normalizers that turn the raw game datasets (weapons/skills/medical/vehicles)
// into a uniform shape for the generic <DataSection> component.
import weaponsData from './weapons.json';
import skillsData from './skills.json';
import medicalData from './medical.json';
import vehiclesData from './vehicles.json';
import questsData from './quests.json';
import adminData from './admin.json';
import fameData from './fame.json';
import huntingData from './hunting.json';
import controlsData from './controls.json';
import itemsData from './items.json';
import { FALLBACK_LANG, DEFAULT_LANG, type LangCode } from '../i18n/languages';
import { localizedPath, useTranslations } from '../i18n/utils';

type L = Partial<Record<LangCode, string>>;
const loc = (m: L | undefined, lang: LangCode) => (m && (m[lang] ?? m[FALLBACK_LANG] ?? m[DEFAULT_LANG])) ?? '';
const pretty = (s: string) => s.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/_/g, ' ');

export interface SecRel { label: string; links: { label: string; href: string }[]; }
export interface SecEntry { slug?: string; name: string; names?: L; desc?: string; meta: { k: string; v: string }[]; link?: string; rels?: SecRel[]; }
export interface SecGroup { key: string; label: string; entries: SecEntry[]; }
export interface Section { groups: SecGroup[]; total: number; }

function group(entries: SecEntry[], catOf: (e: SecEntry) => string, labelOf: (k: string) => string): SecGroup[] {
  const by = new Map<string, SecEntry[]>();
  for (const e of entries) { const k = catOf(e); const a = by.get(k); if (a) a.push(e); else by.set(k, [e]); }
  const groups = [...by].map(([key, es]) => {
    es.sort((a, b) => a.name.localeCompare(b.name));
    return { key, label: labelOf(key), entries: es, _cat: key };
  }) as (SecGroup & { _cat: string })[];
  groups.sort((a, b) => b.entries.length - a.entries.length || a.label.localeCompare(b.label));
  return groups;
}

function labelFrom(map: Record<string, L>, lang: LangCode) {
  return (k: string) => map[k]?.[lang] ?? map[k]?.[FALLBACK_LANG] ?? pretty(k);
}

// ---- weapons ----
const WCAT: Record<string, L> = {
  Melee: { es: 'Cuerpo a cuerpo', en: 'Melee' }, Ranged: { es: 'A distancia', en: 'Ranged' },
};
export function weaponsSection(lang: LangCode): Section {
  const cat = labelFrom(WCAT, lang);
  const entries: (SecEntry & { _c: string })[] = (weaponsData as any[]).map((w) => {
    const meta: { k: string; v: string }[] = [];
    if (w.kind === 'melee' && typeof w.melee?.damage === 'number') meta.push({ k: 'dmg', v: String(w.melee.damage) });
    if (w.ammunition?.labels?.length) meta.push({ k: 'ammo', v: w.ammunition.labels.join(', ') });
    if (typeof w.maxRange === 'number') meta.push({ k: 'range', v: `${w.maxRange} m` });
    if (w.fireModes?.length) meta.push({ k: 'fire', v: w.fireModes.join(', ') });
    return {
      slug: w.slug, name: loc(w.name, lang) || w.slug, names: w.name, meta,
      link: w.slug ? localizedPath(`/items/${w.slug}`, lang) : undefined,
      _c: w.weaponCategory ? pretty(w.weaponCategory) : (w.kind === 'melee' ? 'Melee' : 'Ranged'),
    };
  });
  return { total: entries.length, groups: group(entries, (e: any) => e._c, cat) };
}

// ---- skills ----
const ATTR: Record<string, L> = {
  Strength: { es: 'Fuerza', en: 'Strength' }, Dexterity: { es: 'Destreza', en: 'Dexterity' },
  Constitution: { es: 'Constitución', en: 'Constitution' }, Intelligence: { es: 'Inteligencia', en: 'Intelligence' },
};
export function skillsSection(lang: LangCode): Section {
  const cat = labelFrom(ATTR, lang);
  const entries: (SecEntry & { _c: string })[] = (skillsData as any[]).map((s) => ({
    slug: s.slug, name: loc(s.name, lang) || s.slug, names: s.name, desc: loc(s.description, lang),
    meta: Array.isArray(s.levels) && s.levels.length ? [{ k: 'lvl', v: `${s.levels.length}` }] : [],
    _c: s.attribute || 'Other',
  }));
  return { total: entries.length, groups: group(entries, (e: any) => e._c, cat) };
}

// ---- medical ----
const MCAT: Record<string, L> = {
  disease: { es: 'Enfermedades', en: 'Diseases' }, infection: { es: 'Infecciones', en: 'Infections' },
  poisoning: { es: 'Intoxicaciones', en: 'Poisoning' }, injury: { es: 'Lesiones', en: 'Injuries' },
  deficiency: { es: 'Deficiencias', en: 'Deficiencies' }, radiation: { es: 'Radiación', en: 'Radiation' },
  environment: { es: 'Ambiental', en: 'Environment' }, general: { es: 'General', en: 'General' },
};
export function medicalSection(lang: LangCode): Section {
  const cat = labelFrom(MCAT, lang);
  const entries: (SecEntry & { _c: string })[] = (medicalData as any[]).map((m) => ({
    slug: m.slug, name: loc(m.name, lang) || m.slug, names: m.name, desc: loc(m.description, lang),
    meta: m.treatment ? [{ k: 'cure', v: typeof m.treatment === 'string' ? m.treatment : loc(m.treatment, lang) }] : [],
    _c: m.category || m.kind || 'general',
  }));
  return { total: entries.length, groups: group(entries, (e: any) => e._c, cat) };
}

// ---- vehicles ----
const VTYPE: Record<string, L> = {
  car: { es: 'Coches', en: 'Cars' }, bike: { es: 'Motos/Bicis', en: 'Bikes' }, boat: { es: 'Barcos', en: 'Boats' },
  airplane: { es: 'Aviones', en: 'Aircraft' }, atv: { es: 'Quads', en: 'ATVs' }, tractor: { es: 'Tractores', en: 'Tractors' },
  wheelbarrow: { es: 'Carretillas', en: 'Wheelbarrows' },
};
// Piezas que componen un vehículo: items de categoría "Vehicle" cuyo slug empieza
// por el prefijo del vehículo (alias para los que difieren, p.ej. wolfswagen→ww).
const VEHICLE_PART_ALIAS: Record<string, string> = { wolfswagen: 'ww' };
const VEHICLE_PART_ITEMS = (itemsData as any[]).filter((i) => i.category === 'Vehicle' && i.slug);
export function vehiclesSection(lang: LangCode): Section {
  const tr = useTranslations(lang);
  const cat = labelFrom(VTYPE, lang);
  const entries: (SecEntry & { _c: string })[] = (vehiclesData as any[]).map((v) => {
    const meta: { k: string; v: string }[] = [];
    if (v.fuel?.type) meta.push({ k: 'fuel', v: String(v.fuel.type) });
    if (typeof v.seats === 'number') meta.push({ k: 'seats', v: String(v.seats) });
    const pre = (VEHICLE_PART_ALIAS[v.slug] ?? v.slug) + '-';
    const partLinks = VEHICLE_PART_ITEMS
      .filter((i) => i.slug.startsWith(pre))
      .map((i) => ({ label: loc(i.name, lang) || i.slug, href: localizedPath(`/items/${i.slug}`, lang) }))
      .sort((a, b) => a.label.localeCompare(b.label));
    const rels: SecRel[] = partLinks.length ? [{ label: tr('sec.vehicle.parts' as any), links: partLinks }] : [];
    return { slug: v.slug, name: loc(v.name, lang) || v.slug, names: v.name, desc: loc(v.descName, lang) || loc(v.description, lang), meta, rels: rels.length ? rels : undefined, _c: v.type || 'other' };
  });
  return { total: entries.length, groups: group(entries, (e: any) => e._c, cat) };
}

// ---- quests / missions ----
export function questsSection(lang: LangCode): Section {
  const tr = useTranslations(lang);
  // Items required/rewarded by a quest → clickable links to each item page
  // (deduped by slug; names are already localized in quests.json).
  const itemLinks = (arr: any[] | undefined) => {
    const seen = new Set<string>();
    const links: { label: string; href: string }[] = [];
    for (const it of arr ?? []) {
      if (!it?.slug || seen.has(it.slug)) continue;
      seen.add(it.slug);
      const lbl = (loc(it.name, lang) || it.slug).trim();
      links.push({ label: it.count && it.count > 1 ? `${lbl} ×${it.count}` : lbl, href: localizedPath(`/items/${it.slug}`, lang) });
    }
    return links;
  };
  const entries: (SecEntry & { _c: string })[] = (questsData as any[]).map((q) => {
    const meta: { k: string; v: string }[] = [];
    if (q.tier) meta.push({ k: 'tier', v: `T${q.tier}` });
    if (q.rewardFame) meta.push({ k: 'fame', v: `+${q.rewardFame}` });
    if (q.rewardCurrency) meta.push({ k: 'money', v: String(q.rewardCurrency) });
    const rels: SecRel[] = [];
    const req = itemLinks(q.requiredItems);
    const rew = itemLinks(q.rewardItems);
    if (req.length) rels.push({ label: tr('sec.quest.requires' as any), links: req });
    if (rew.length) rels.push({ label: tr('sec.quest.rewards' as any), links: rew });
    return {
      slug: q.slug,
      name: loc(q.title, lang) || q.slug,
      names: q.title,
      desc: loc(q.description, lang),
      meta,
      rels: rels.length ? rels : undefined,
      _c: (q.traderLabel && (q.traderLabel[lang] ?? q.traderLabel[FALLBACK_LANG])) || q.trader || 'Other',
    };
  });
  return { total: entries.length, groups: group(entries, (e: any) => e._c, (k) => k) };
}

// ---- admin / server commands ----
const ADMIN_LVL: Record<string, L> = {
  SuperAdmin: { es: 'Super Admin', en: 'Super Admin' }, Admin: { es: 'Admin', en: 'Admin' },
  Elevated: { es: 'Elevado', en: 'Elevated' }, Regular: { es: 'Normal', en: 'Regular' },
  '': { es: 'Otros', en: 'Other' },
};
export function adminSection(lang: LangCode): Section {
  const entries: (SecEntry & { _c: string })[] = (adminData as any[]).map((c) => ({
    name: c.verb,
    desc: loc(c.desc, lang),
    meta: c.args ? [{ k: 'args', v: String(c.args) }] : [],
    _c: c.level || '',
  }));
  return { total: entries.length, groups: group(entries, (e: any) => e._c, (k) => ADMIN_LVL[k]?.[lang] ?? ADMIN_LVL[k]?.[FALLBACK_LANG] ?? (k || 'Otros')) };
}

// ---- fame system ----
const FAME_KIND: Record<string, L> = {
  award: { es: 'Ganancias', en: 'Gains' }, pen: { es: 'Penalizaciones', en: 'Penalties' },
};
export function fameSection(lang: LangCode): Section {
  const mk = (arr: any[], kind: string, sign: string) =>
    arr.map((a) => ({ name: pretty(a.action), meta: [{ k: 'fame', v: `${sign}${a.fame}` }], _c: kind }));
  const entries = [...mk(fameData.awards as any[], 'award', '+'), ...mk(fameData.penalties as any[], 'pen', '−')];
  return { total: entries.length, groups: group(entries, (e: any) => e._c, (k) => FAME_KIND[k]?.[lang] ?? FAME_KIND[k]?.[FALLBACK_LANG] ?? k) };
}

// ---- hunting (animals per biome) ----
export function huntingSection(lang: LangCode): Section {
  const range = (a?: number, b?: number) => (a === b ? String(a ?? '') : `${a ?? '?'}–${b ?? '?'}`);
  const entries: (SecEntry & { _c: string })[] = (huntingData as any[]).map((r) => ({
    name: loc(r.animal, lang) || r.animal.en,
    names: r.animal,
    meta: [
      { k: 'pack', v: range(r.packMin, r.packMax) },
      ...(r.cluesMax ? [{ k: 'clues', v: range(r.cluesMin, r.cluesMax) }] : []),
    ],
    _c: loc(r.biomeLabel, lang) || r.biomeLabel.en,
  }));
  return { total: entries.length, groups: group(entries, (e: any) => e._c, (k) => k) };
}

// ---- controles (teclas por defecto) ----
const CTRL_CAT: Record<string, L> = {
  movement: { es: 'Movimiento', en: 'Movement' }, combat: { es: 'Combate', en: 'Combat' },
  fishing: { es: 'Pesca', en: 'Fishing' }, vehicle: { es: 'Vehículos', en: 'Vehicles' },
  minigame: { es: 'Minijuegos', en: 'Minigames' }, building: { es: 'Construcción', en: 'Building' },
  interface: { es: 'Interfaz', en: 'Interface' }, view: { es: 'Cámara y vista', en: 'Camera & view' },
  emotes: { es: 'Gestos', en: 'Emotes' }, music: { es: 'Música', en: 'Music' }, other: { es: 'Otros', en: 'Other' },
};
export function controlsSection(lang: LangCode): Section {
  const entries: (SecEntry & { _c: string })[] = (controlsData as any[]).map((c) => ({
    name: c.action,
    meta: [{ k: 'key', v: (c.key && (c.key[lang] ?? c.key.en)) || '' }],
    _c: c.cat,
  }));
  return { total: entries.length, groups: group(entries, (e: any) => e._c, (k) => CTRL_CAT[k]?.[lang] ?? CTRL_CAT[k]?.[FALLBACK_LANG] ?? k) };
}

// ---- detalle por entidad: cada cosa tiene su página con descripción completa ----
// Armas enlazan a su ficha de item (ya completa); el resto a /info/<section>/<slug>.
export const SECTION_DETAIL: Record<string, { titleKey: string; base: string; fn: (l: LangCode) => Section }> = {
  skills: { titleKey: 'sec.skills.title', base: '/skills', fn: skillsSection },
  medico: { titleKey: 'sec.medical.title', base: '/medico', fn: medicalSection },
  vehiculos: { titleKey: 'sec.vehicles.title', base: '/vehiculos', fn: vehiclesSection },
  misiones: { titleKey: 'sec.quests.title', base: '/misiones', fn: questsSection },
};

export function sectionEntry(section: string, slug: string, lang: LangCode): SecEntry | undefined {
  const def = SECTION_DETAIL[section];
  if (!def) return undefined;
  for (const g of def.fn(lang).groups) for (const e of g.entries) if (e.slug === slug) return e;
  return undefined;
}

// Todas las (section, slug) para getStaticPaths (slugs únicos por sección).
export function allSectionPaths(): { section: string; slug: string }[] {
  const out: { section: string; slug: string }[] = [];
  for (const [section, def] of Object.entries(SECTION_DETAIL)) {
    const seen = new Set<string>();
    for (const g of def.fn(DEFAULT_LANG).groups) for (const e of g.entries) {
      if (e.slug && !seen.has(e.slug)) { seen.add(e.slug); out.push({ section, slug: e.slug }); }
    }
  }
  return out;
}
