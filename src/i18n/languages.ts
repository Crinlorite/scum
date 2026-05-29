// Metadata per supported language.
//
// The list of "official" languages mirrors SCUM's Steam page (10 langs).
// Source: https://store.steampowered.com/app/513710/SCUM/
//
// Adding a new language? Append an entry here, list the code in
// `astro.config.mjs > i18n.locales` (already auto-derived from this
// array), drop the matching dict in `ui.ts` (optional — falls back to
// EN then ES), and place MDX under `src/content/wiki/<code>/<cat>/`.
// `beta: false` = idioma revisado por hablante nativo (es + en).
// `beta: true`  = traducción en progreso; parte del contenido puede salir en
// inglés. La UI lo marca con un badge y un aviso, para fijar expectativas.
export const LANGUAGES = [
  // Project languages (es is the project's default; en is the primary fallback)
  { code: 'es',    label: 'Español',              native: 'Español',      bcp47: 'es-ES', ogLocale: 'es_ES', dir: 'ltr', beta: false },
  { code: 'en',    label: 'English',              native: 'English',      bcp47: 'en-US', ogLocale: 'en_US', dir: 'ltr', beta: false },

  // Other SCUM official languages, in the order Steam lists them — Beta hasta revisión nativa
  { code: 'de',    label: 'German',               native: 'Deutsch',      bcp47: 'de-DE', ogLocale: 'de_DE', dir: 'ltr', beta: true },
  { code: 'ru',    label: 'Russian',              native: 'Русский',      bcp47: 'ru-RU', ogLocale: 'ru_RU', dir: 'ltr', beta: true },
  { code: 'zh',    label: 'Simplified Chinese',   native: '简体中文',      bcp47: 'zh-CN', ogLocale: 'zh_CN', dir: 'ltr', beta: true },
  { code: 'fr',    label: 'French',               native: 'Français',     bcp47: 'fr-FR', ogLocale: 'fr_FR', dir: 'ltr', beta: true },
  { code: 'pt',    label: 'Portuguese (Brazil)',  native: 'Português',    bcp47: 'pt-BR', ogLocale: 'pt_BR', dir: 'ltr', beta: true },
  { code: 'zh-tw', label: 'Traditional Chinese',  native: '繁體中文',      bcp47: 'zh-TW', ogLocale: 'zh_TW', dir: 'ltr', beta: true },
  { code: 'th',    label: 'Thai',                 native: 'ไทย',          bcp47: 'th-TH', ogLocale: 'th_TH', dir: 'ltr', beta: true },
  { code: 'pl',    label: 'Polish',               native: 'Polski',       bcp47: 'pl-PL', ogLocale: 'pl_PL', dir: 'ltr', beta: true },
] as const;

export type LangCode = (typeof LANGUAGES)[number]['code'];
export type LanguageMeta = (typeof LANGUAGES)[number];

export const DEFAULT_LANG: LangCode = 'es';
// Used by t() as a secondary fallback before falling back to the project's
// default lang. Rationale: a German visitor on /de/ expects English over
// Spanish while their translation is in progress.
export const FALLBACK_LANG: LangCode = 'en';

const SUPPORTED = new Set<string>(LANGUAGES.map((l) => l.code));
const BY_CODE = new Map<string, LanguageMeta>(LANGUAGES.map((l) => [l.code, l]));

export function isSupportedLang(value: string): value is LangCode {
  return SUPPORTED.has(value);
}

export function getLanguageMeta(code: LangCode): LanguageMeta {
  return BY_CODE.get(code)!;
}

/** Idiomas revisados por nativo (sin badge Beta). Hoy: es, en. */
export const STABLE_LANGS: LangCode[] = LANGUAGES.filter((l) => !l.beta).map((l) => l.code);

/** True si el contenido del idioma es una traducción en progreso (Beta). */
export function isBeta(code: LangCode): boolean {
  return getLanguageMeta(code).beta === true;
}
