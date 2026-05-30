import { getCollection, type CollectionEntry } from 'astro:content';
import { isSupportedLang, type LangCode } from './languages';

export type WikiEntry = CollectionEntry<'wiki'>;
export type WikiCategory = 'guides' | 'mechanics' | 'server';

export const WIKI_CATEGORIES: readonly WikiCategory[] = ['guides', 'mechanics', 'server'] as const;

interface Parsed {
  lang: LangCode;
  category: WikiCategory;
  slug: string;
}

/** Wiki entry IDs look like "es/guides/empezando.mdx". */
export function parseEntryId(id: string): Parsed | null {
  const parts = id.replace(/\.mdx?$/, '').split('/');
  if (parts.length !== 3) return null;
  const [lang, category, slug] = parts;
  if (!isSupportedLang(lang)) return null;
  if (!WIKI_CATEGORIES.includes(category as WikiCategory)) return null;
  return { lang, category: category as WikiCategory, slug };
}

export type ParsedWikiEntry = WikiEntry & { parsed: Parsed };

export async function loadWiki(): Promise<ParsedWikiEntry[]> {
  const all = await getCollection('wiki', (entry: WikiEntry) => !entry.data.draft);
  const out: ParsedWikiEntry[] = [];
  for (const entry of all) {
    const parsed = parseEntryId(entry.id);
    if (parsed) out.push({ ...entry, parsed });
  }
  return out;
}

export async function loadWikiByLangCategory(lang: LangCode, category: WikiCategory) {
  const all = await loadWiki();
  return all.filter((e) => e.parsed.lang === lang && e.parsed.category === category);
}
