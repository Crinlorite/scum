import { DEFAULT_LANG, FALLBACK_LANG, isSupportedLang, LANGUAGES, type LangCode } from './languages';
import { UI, type UIKey } from './ui';

export function getLocaleFromUrl(url: URL): LangCode {
  const segments = url.pathname.split('/').filter(Boolean);
  // Hyphenated locales (zh-tw) come through as a single path segment.
  const first = segments[0];
  if (first && isSupportedLang(first)) return first;
  return DEFAULT_LANG;
}

// Walks lang → EN → ES → key. A visitor on /de/ sees English (not
// Spanish) for any string the German dict has not translated yet.
export function t(key: UIKey, lang: LangCode, vars?: Record<string, string | number>): string {
  let value: string =
    UI[lang]?.[key] ??
    UI[FALLBACK_LANG]?.[key] ??
    UI[DEFAULT_LANG]?.[key] ??
    key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      value = value.replaceAll(`{${k}}`, String(v));
    }
  }
  return value;
}

export function useTranslations(lang: LangCode) {
  return (key: UIKey, vars?: Record<string, string | number>) => t(key, lang, vars);
}

// Always returns a path with trailing slash so it matches Astro's static
// canonical URLs (Google treats `/en` and `/en/` as different URLs).
export function localizedPath(path: string, lang: LangCode): string {
  const clean = path.startsWith('/') ? path : `/${path}`;
  const withTrail = clean === '/' ? '/' : clean.endsWith('/') ? clean : `${clean}/`;
  if (lang === DEFAULT_LANG) return withTrail;
  return withTrail === '/' ? `/${lang}/` : `/${lang}${withTrail}`;
}

export function getAllLocales() {
  return LANGUAGES;
}

export function alternateHref(currentPath: string, currentLang: LangCode, targetLang: LangCode): string {
  let stripped = currentPath;
  if (currentLang !== DEFAULT_LANG) {
    const prefix = `/${currentLang}`;
    stripped = currentPath.startsWith(prefix) ? currentPath.slice(prefix.length) || '/' : currentPath;
  }
  return localizedPath(stripped, targetLang);
}
