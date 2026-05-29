// Unified per-language search index for the global Nav search: items, missions,
// cooking recipes, crafting, skills, health, vehicles and wiki articles.
// Each entry: { n: name, u: url, t: type label }. Items/weapons link to their
// detail page; section entries link to the section with ?q= to auto-filter.
import type { APIRoute } from 'astro';
import { LANGUAGES, type LangCode } from '../../i18n/languages';
import { localizedPath, useTranslations } from '../../i18n/utils';
import { ITEMS, displayName } from '../../data/items';
import { COOKING, cookName } from '../../data/cooking';
import { CRAFTING, craftName } from '../../data/craftrecipes';
import { questsSection, skillsSection, medicalSection, vehiclesSection } from '../../data/sections';
import { loadWiki } from '../../i18n/wiki';

export function getStaticPaths() {
  return LANGUAGES.map((l) => ({ params: { lang: l.code } }));
}

export const GET: APIRoute = async ({ params }) => {
  const lang = params.lang as LangCode;
  const tr = useTranslations(lang);
  const out: { n: string; u: string; t: string }[] = [];
  const qp = (path: string, name: string) => `${localizedPath(path, lang)}?q=${encodeURIComponent(name)}`;

  for (const it of ITEMS)
    out.push({ n: displayName(it, lang), u: localizedPath(`/items/${it.slug}`, lang), t: tr('nav.items') });
  for (const r of COOKING) { const n = cookName(r, lang); out.push({ n, u: qp('/recetas', n), t: tr('recipes.title') }); }
  for (const r of CRAFTING) { const n = craftName(r, lang); out.push({ n, u: qp('/crafteo', n), t: tr('crafting.title') }); }
  for (const g of questsSection(lang).groups) for (const e of g.entries) out.push({ n: e.name, u: qp('/misiones', e.name), t: tr('sec.quests.title') });
  for (const e of skillsSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: qp('/skills', e.name), t: tr('sec.skills.title') });
  for (const e of medicalSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: qp('/medico', e.name), t: tr('sec.medical.title') });
  for (const e of vehiclesSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: qp('/vehiculos', e.name), t: tr('sec.vehicles.title') });

  const wiki = await loadWiki();
  for (const w of wiki)
    if (w.parsed.lang === lang)
      out.push({ n: w.data.title, u: localizedPath(`/wiki/${w.parsed.category}/${w.parsed.slug}`, lang), t: tr('nav.wiki') });

  return new Response(JSON.stringify(out), {
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};
