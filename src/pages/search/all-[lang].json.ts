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
import { questsSection, skillsSection, medicalSection, vehiclesSection, fameSection, huntingSection, controlsSection } from '../../data/sections';
import { loadWiki } from '../../i18n/wiki';
import { CODEX, codexTitle } from '../../data/codex';

export function getStaticPaths() {
  return LANGUAGES.map((l) => ({ params: { lang: l.code } }));
}

export const GET: APIRoute = async ({ params }) => {
  const lang = params.lang as LangCode;
  const tr = useTranslations(lang);
  const out: { n: string; u: string; t?: string }[] = [];
  const qp = (path: string, name: string) => `${localizedPath(path, lang)}?q=${encodeURIComponent(name)}`;

  // Items are the bulk of results → no type badge (it just repeated "Ítems" on
  // every row) and no icon (icons live on the item page only).
  for (const it of ITEMS)
    out.push({ n: displayName(it, lang), u: localizedPath(`/items/${it.slug}`, lang) });
  for (const r of COOKING) out.push({ n: cookName(r, lang), u: localizedPath(`/recetas/${r.slug}`, lang), t: tr('recipes.title') });
  for (const r of CRAFTING) out.push({ n: craftName(r, lang), u: localizedPath(`/crafteo/${r.slug}`, lang), t: tr('crafting.title') });
  // skills/medical/vehicles/missions → su página de detalle propia (/info/<section>/<slug>).
  const info = (sec: string, slug: string) => localizedPath(`/info/${sec}/${slug}`, lang);
  for (const e of questsSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: e.slug ? info('misiones', e.slug) : qp('/misiones', e.name), t: tr('sec.quests.title') });
  for (const e of skillsSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: e.slug ? info('skills', e.slug) : qp('/skills', e.name), t: tr('sec.skills.title') });
  for (const e of medicalSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: e.slug ? info('medico', e.slug) : qp('/medico', e.name), t: tr('sec.medical.title') });
  for (const e of vehiclesSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: e.slug ? info('vehiculos', e.slug) : qp('/vehiculos', e.name), t: tr('sec.vehicles.title') });
  for (const e of fameSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: qp('/fama', e.name), t: tr('sec.fame.title') });
  for (const e of controlsSection(lang).groups.flatMap((g) => g.entries)) out.push({ n: e.name, u: qp('/controles', e.name), t: tr('sec.controls.title') });
  const huntSeen = new Set<string>();
  for (const e of huntingSection(lang).groups.flatMap((g) => g.entries)) {
    if (huntSeen.has(e.name)) continue;
    huntSeen.add(e.name);
    out.push({ n: e.name, u: qp('/caza', e.name), t: tr('sec.hunting.title') });
  }

  for (const a of CODEX)
    out.push({ n: codexTitle(a, lang), u: localizedPath(`/manual/${a.slug}`, lang), t: tr('manual.title') });

  const wiki = await loadWiki();
  for (const w of wiki)
    if (w.parsed.lang === lang)
      out.push({ n: w.data.title, u: localizedPath(`/wiki/${w.parsed.category}/${w.parsed.slug}`, lang), t: tr('nav.wiki') });

  return new Response(JSON.stringify(out), {
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
  });
};
