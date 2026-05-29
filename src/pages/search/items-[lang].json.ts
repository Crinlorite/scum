// Static per-language item search index, served at /search/items-<lang>.json.
// Each entry: { s: slug, n: official name in that language }.
// The global search box (ItemSearch.astro) lazy-fetches the file for the
// active language and filters it client-side.
import type { APIRoute } from 'astro';
import { LANGUAGES, type LangCode } from '../../i18n/languages';
import { ITEMS, itemName } from '../../data/items';

export function getStaticPaths() {
  return LANGUAGES.map((l) => ({ params: { lang: l.code } }));
}

export const GET: APIRoute = ({ params }) => {
  const lang = params.lang as LangCode;
  const index = ITEMS.map((it) => ({ s: it.slug, n: itemName(it, lang) }));
  return new Response(JSON.stringify(index), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
    },
  });
};
