import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { LANGUAGES, DEFAULT_LANG } from './src/i18n/languages.ts';

// Build {code: bcp47} map for sitemap's i18n config.
const sitemapLocales = Object.fromEntries(LANGUAGES.map((l) => [l.code, l.bcp47]));

export default defineConfig({
  site: 'https://scumwiki.crintech.pro',
  integrations: [
    mdx(),
    sitemap({
      i18n: {
        defaultLocale: DEFAULT_LANG,
        locales: sitemapLocales,
      },
    }),
  ],
  i18n: {
    defaultLocale: DEFAULT_LANG,
    locales: LANGUAGES.map((l) => l.code),
    routing: {
      prefixDefaultLocale: false,
      redirectToDefaultLocale: false,
    },
  },
});
